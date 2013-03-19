import os, json, UserDict, requests, uuid
from datetime import datetime
from werkzeug import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin
from artemis.core import app, current_user
import artemis.util, artemis.auth
from artemis.config import config


def makeid():
    '''Create a new id for data object based on the idgen utility'''
    idgenerator = artemis.util.idgen()
    id_ = idgenerator.next()
    while Record.get(id_):
        id_ = idgenerator.next()
    return id_
    
    
def init_db():
    mappings = config['MAPPINGS']
    for mapping in mappings:
        t = 'http://' + str(config['ELASTIC_SEARCH_HOST']).lstrip('http://').rstrip('/')
        t += '/' + config['ELASTIC_SEARCH_DB'] + '/' + mapping + '/_mapping'
        r = requests.get(t)
        if r.status_code == 404:
            r = requests.put(t, data=json.dumps(mappings[mapping]) )
            print r.text
    firstsu = config['SUPER_USER'][0]
    if not Account.get(firstsu):
        su = Account(id=config['SUPER_USER'][0])
        su.set_password(firstsu)
        su.save()
        print 'superuser account named - ' + firstsu + ' created. default password matches username. Change it.'
    curated = config['CURATED_FIELDS']
    for cur in curated:
        check = Curated.get(cur)
        if check is None:
            c = Curated(**{'id':cur,'values':['placeholder']})
            c.save()


def get_user():
    try:
        usr = current_user.id
    except:
        usr = "anonymous"
    return usr


class InvalidDAOIDException(Exception):
    pass
    

class DomainObject(UserDict.IterableUserDict):
    __type__ = None

    def __init__(self, **kwargs):
        if '_source' in kwargs:
            self.data = dict(kwargs['_source'])
            self.meta = dict(kwargs)
            del self.meta['_source']
        else:
            self.data = dict(kwargs)
            
    @classmethod
    def target(cls):
        t = 'http://' + str(config['ELASTIC_SEARCH_HOST']).lstrip('http://').rstrip('/') + '/'
        t += config['ELASTIC_SEARCH_DB'] + '/' + cls.__type__ + '/'
        return t
    
    @property
    def id(self):
        return self.data.get('id', None)
        
    @property
    def version(self):
        return self.meta.get('_version', None)

    @property
    def json(self):
        return json.dumps(self.data)

    def save(self):
        if 'id' in self.data:
            id_ = self.data['id'].strip()
        else:
            id_ = makeid()
            self.data['id'] = id_
        
        self.data['updated_date'] = datetime.now().strftime("%Y-%m-%d %H%M")

        if 'created_date' not in self.data:
            self.data['created_date'] = datetime.now().strftime("%Y-%m-%d %H%M")
            
        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))


    @classmethod
    def get(cls, id_):
        '''Retrieve object by id.'''
        if id_ is None:
            return None
        try:
            out = requests.get(cls.target() + id_)
            if out.status_code == 404:
                return None
            else:
                return cls(**out.json())
        except:
            return None

    @classmethod
    def keys(cls,mapping=False,prefix=''):
        # return a sorted list of all the keys in the index
        if not mapping:
            mapping = cls.query(endpoint='_mapping')[cls.__type__]['properties']
        keys = []
        for item in mapping:
            if mapping[item].has_key('fields'):
                for item in mapping[item]['fields'].keys():
                    if item != 'exact' and not item.startswith('_'):
                        keys.append(prefix + item + config['FACET_FIELD'])
            else:
                keys = keys + cls.keys(mapping=mapping[item]['properties'],prefix=prefix+item+'.')
        keys.sort()
        return keys
        
    @classmethod
    def query(cls, recid='', endpoint='_search', q='', terms=None, facets=None, **kwargs):
        '''Perform a query on backend.

        :param recid: needed if endpoint is about a record, e.g. mlt
        :param endpoint: default is _search, but could be _mapping, _mlt, _flt etc.
        :param q: maps to query_string parameter if string, or query dict if dict.
        :param terms: dictionary of terms to filter on. values should be lists. 
        :param facets: dict of facets to return from the query.
        :param kwargs: any keyword args as per
            http://www.elasticsearch.org/guide/reference/api/search/uri-request.html
        '''
        if recid and not recid.endswith('/'): recid += '/'
        if isinstance(q,dict):
            query = q
        elif q:
            query = {'query': {'query_string': { 'query': q }}}
        else:
            query = {'query': {'match_all': {}}}

        if facets:
            if 'facets' not in query:
                query['facets'] = {}
            for k, v in facets.items():
                query['facets'][k] = {"terms":v}

        if terms:
            boolean = {'must': [] }
            for term in terms:
                if not isinstance(terms[term],list): terms[term] = [terms[term]]
                for val in terms[term]:
                    obj = {'term': {}}
                    obj['term'][ term ] = val
                    boolean['must'].append(obj)
            if q and not isinstance(q,dict):
                boolean['must'].append( {'query_string': { 'query': q } } )
            elif q and 'query' in q:
                boolean['must'].append( query['query'] )
            query['query'] = {'bool': boolean}

        for k,v in kwargs.items():
            if k == '_from':
                query['from'] = v
            else:
                query[k] = v

        if endpoint in ['_mapping']:
            r = requests.get(cls.target() + recid + endpoint)
        else:
            r = requests.post(cls.target() + recid + endpoint, data=json.dumps(query))
        return r.json()

    def accessed(self):
        if 'last_access' not in self.data:
            self.data['last_access'] = []
        self.data['last_access'].insert(0, { 'user':get_user(), 'date':datetime.now().strftime("%Y-%m-%d %H%M") } )        
        r = requests.put(self.target() + self.data['id'], data=json.dumps(self.data))

    def delete(self):        
        r = requests.delete(self.target() + self.id)
            


class Record(DomainObject):
    __type__ = 'record'
    
    def update_access_record(self):
        return self.accessed()
    

    def save(self):
        if 'id' in self.data:
            id_ = self.data['id'].strip()
        else:
            id_ = makeid()
            self.data['id'] = id_
        
        self.data['updated_date'] = datetime.now().strftime("%Y-%m-%d %H%M")

        if 'type' not in self.data:
            self.data['type'] = 'part'

        if 'created_date' not in self.data:
            self.data['created_date'] = datetime.now().strftime("%Y-%m-%d %H%M")
            self.data['history'] = [{'date':self.data['created_date'],'user': get_user(),'current':'record created'}]
        else:
            if 'history' not in self.data:
                self.data['history'] = []
            previous = Record.get(self.data['id'])
            if previous:
                for key,val in previous.data.items():
                    if key not in ['history','last_access','updated_date']:
                        if val != self.data[key]:
                            if key == 'attachments':
                                tocurrent = "attachment list altered"
                            else:
                                tocurrent = json.dumps(self.data[key],indent=4)
                            self.data['history'].insert(0, {
                                'date': self.data['updated_date'],
                                'field': key,
                                'previous': json.dumps(val,indent=4),
                                'current': tocurrent,
                                'user': get_user()
                            })
                for key in self.data.keys():
                    if key not in previous.data.keys() and key not in ['history']:
                        if key == 'attachments':
                            tocurrent = "attachment list altered"
                        else:
                            tocurrent = json.dumps(self.data[key],indent=4)
                        self.data['history'].insert(0, {
                            'date': self.data['updated_date'],
                            'field': key,
                            'previous': '',
                            'current': tocurrent,
                            'user': get_user()
                        })

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))
    
    
    def delete(self):
        for kid in self.children:
            k = Record.get(kid['id'])
            k.data['assembly'] = ''
            k.save()
        r = requests.delete(self.target() + self.id)
        return ''
    
    @property
    def children(self):
        kids = []
        if self.data['type'] == "assembly":
            res = Record.query(terms={"assembly.exact":self.id})
            if res['hits']['total'] != 0:
                kids = [i['_source'] for i in res['hits']['hits']]            
        return kids

    '''@property
    def attachments(self):
        atts = self.data['attachments']
        if self.data['type'] == "part":
            if self.parent:
                atts = atts + self.parent['attachments']
        return atts'''

    @property
    def parent(self):
        if 'assembly' in self.data and self.data['assembly']:
            parent = Record.get(self.data['assembly'])
            if parent:
                return parent
            else:
                return False
        else:
            return False

    @property
    def notes(self):
        res = Note.query(terms={
            'owner': [self.id]
        })
        allnotes = [ Note(**item['_source']) for item in res['hits']['hits'] ]
        return allnotes
                    

class Curated(DomainObject):
    __type__ = 'curated'


class Note(DomainObject):
    __type__ = 'note'

    def delete(self):
        url = str(config['ELASTIC_SEARCH_HOST'])
        loc = config['ELASTIC_SEARCH_DB'] + "/" + self.__type__ + "/" + self.id
        conn = httplib.HTTPConnection(url)
        conn.request('DELETE', loc)
        resp = conn.getresponse()
        return ''

    @classmethod
    def about(cls, id_):
        '''Retrieve notes by id of record they are about'''
        if id_ is None:
            return None
        res = Note.query(q="about:"+id_)
        return [i['_source'] for i in res['hits']['hits']]

    
class Account(DomainObject, UserMixin):
    __type__ = 'account'

    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)

    @property
    def is_super(self):
        return artemis.auth.user.is_super(self)
    
    def delete(self):
        url = str(config['ELASTIC_SEARCH_HOST'])
        loc = config['ELASTIC_SEARCH_DB'] + "/" + self.__type__ + "/" + self.id
        conn = httplib.HTTPConnection(url)
        conn.request('DELETE', loc)
        resp = conn.getresponse()
        for note in self.notes:
            note.delete()

