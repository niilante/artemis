# this is the data access layer
import json
import uuid
import UserDict
import httplib

import pyes
from werkzeug import generate_password_hash, check_password_hash
from flaskext.login import UserMixin

from artemis.config import config

def init_db():
    conn, db = get_conn()
    try:
        conn.create_index(db)
        mappings = config["mappings"]
        for mapping in mappings:
            #conn.put_mapping(mapping,{"properties":mappings[mapping]},[db])
            host = str(config['ELASTIC_SEARCH_HOST']).rstrip('/')
            db_name = config['ELASTIC_SEARCH_DB']
            fullpath = '/' + db_name + '/' + mapping + '/_mapping'
            c =  httplib.HTTPConnection(host)
            c.request('PUT', fullpath, json.dumps(mappings[mapping]))
            c.getresponse()
    except pyes.exceptions.IndexAlreadyExistsException:
        pass

def get_conn():
    host = str(config["ELASTIC_SEARCH_HOST"])
    db_name = config["ELASTIC_SEARCH_DB"]
    conn = pyes.ES([host])
    if "default_indices" in config:
        if isinstance(config["default_indices"],list) and len(config["default_indices"]) > 0:
            conn.default_indices = config["default_indices"]
    return conn, db_name


class DomainObject(UserDict.IterableUserDict):
    # set __type__ on inheriting class to determine elasticsearch object
    __type__ = None

    def __init__(self, **kwargs):
        '''Initialize a domain object with key/value pairs of attributes.
        '''
        # IterableUserDict expects internal dictionary to be on data attribute
        if '_source' in kwargs:
            self.data = dict(kwargs['_source'])
            self.meta = dict(kwargs)
            del self.meta['_source']
        else:
            self.data = dict(kwargs)

    @property
    def id(self):
        '''Get id of this object.'''
        return self.data.get('id', None)
        
    @property
    def version(self):
        return self.meta.get('_version', None)

    def save(self):
        '''Save to backend storage.'''
        # TODO: refresh object with result of save
        return self.upsert(self.data)

    @classmethod
    def get(cls, id_):
        '''Retrieve object by id.'''
        conn, db = get_conn()
        try:
            out = conn.get(db, cls.__type__, id_)
            return cls(**out)
        except pyes.exceptions.ElasticSearchException, inst:
            if inst.status == 404:
                return None
            else:
                raise

    @classmethod
    def get_mapping(cls):
        conn, db = get_conn()
        return conn.get_mapping(cls.__type__, db)

    @classmethod
    def upsert(cls, data, state=None):
        '''Update backend object with a dictionary of data.

        If no id is supplied an uuid id will be created before saving.
        '''
        conn, db = get_conn()
        if 'id' in data:
            id_ = data['id']
        else:
            id_ = uuid.uuid4().hex[0:5]
            while Record.get(id_):
                id_ = uuid.uuid4().hex[0:5]
            data['id'] = id_
        conn.index(data, db, cls.__type__, id_)
        # TODO: ES >= 0.17 automatically re-indexes on GET so this not needed
        conn.refresh()
        # TODO: should we really do a cls.get() ?
        return cls(**data)

    @classmethod
    def bulk_upsert(cls, dataset, state=None):
        '''Bulk update backend object with a list of dicts of data.
        If no id is supplied an uuid id will be created before saving.'''
        conn, db = get_conn()
        for data in dataset:
            if 'id' in data:
                id_ = data['id']
            else:
                id_ = uuid.uuid4().hex
                data['id'] = id_
            conn.index(data, db, cls.__type__, id_, bulk=True)
        # refresh required after bulk index
        conn.refresh()
        return dataset
    
    @classmethod
    def delete_by_query(cls, query):
        url = str(config['ELASTIC_SEARCH_HOST'])
        loc = config['ELASTIC_SEARCH_DB'] + "/" + cls.__type__ + "/_query?q=" + query
        import httplib 
        conn = httplib.HTTPConnection(url)
        conn.request('DELETE', loc)
        resp = conn.getresponse()
        return resp.read()
        
    @classmethod
    def query(cls, q='', terms=None, facet_fields=None, flt=False, default_operator='AND', **kwargs):
        '''Perform a query on backend.

        :param q: maps to query_string parameter.
        :param terms: dictionary of terms to filter on. values should be lists.
        :param kwargs: any keyword args as per
            http://www.elasticsearch.org/guide/reference/api/search/uri-request.html
        '''
        conn, db = get_conn()
        if not q:
            ourq = pyes.query.MatchAllQuery()
        else:
            if flt:
                ourq = pyes.query.FuzzyLikeThisQuery(like_text=q,**kwargs)
            else:
                ourq = pyes.query.StringQuery(q, default_operator=default_operator)
        if terms:
            for term in terms:
                for val in terms[term]:
                    termq = pyes.query.TermQuery(term, val)
                    ourq = pyes.query.BoolQuery(must=[ourq,termq])

        ourq = ourq.search(**kwargs)
        if facet_fields:
            for item in facet_fields:
                ourq.facet.add_term_facet(item['key'], size=item.get('size',100), order=item.get('order',"count"))
        out = conn.search(ourq, db, cls.__type__)
        return out

    @classmethod
    def raw_query(self, query_string):
        if not query_string:
            msg = json.dumps({
                'error': "Query endpoint. Please provide elastic search query parameters - see http://www.elasticsearch.org/guide/reference/api/search/uri-request.html"
                })
            return msg

        host = str(config['ELASTIC_SEARCH_HOST']).rstrip('/')
        db_path = config['ELASTIC_SEARCH_DB']
        if "default_indices" in config:
            if isinstance(config["default_indices"],list) and len(config["default_indices"]) > 0:
                db_path = ",".join(config["default_indices"])
        fullpath = '/' + db_path + '/' + self.__type__ + '/_search' + '?' + query_string
        c =  httplib.HTTPConnection(host)
        c.request('GET', fullpath)
        result = c.getresponse()
        # pass through the result raw
        return result.read()


class Record(DomainObject):
    __type__ = 'record'


class Collection(DomainObject):
    __type__ = 'collection'
    
class Account(DomainObject, UserMixin):
    __type__ = 'account'

    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)

    @property
    def collections(self):
        colls = Collection.query(terms={
            'owner': [self.id]
            })
        colls = [ Collection(**item['_source']) for item in colls['hits']['hits'] ]
        return colls

