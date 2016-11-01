
import requests, json, uuid
from datetime import datetime
from portality.core import app, current_user
from portality.dao import DomainObject as DomainObject
import portality.util

'''
Define models in here. They should all inherit from the DomainObject.
Look in the dao.py to learn more about the default methods available to the Domain Object.
When using portality in your own flask app, perhaps better to make your own models file somewhere and copy these examples
'''


# an example account object, which requires the further additional imports
# There is a more complex example below that also requires these imports
from werkzeug import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin

class Account(DomainObject, UserMixin):
    __type__ = 'account'

    @classmethod
    def pull_by_email(cls,email):
        res = cls.query(q='email:"' + email + '"')
        if res.get('hits',{}).get('total',0) == 1:
            return cls(**res['hits']['hits'][0]['_source'])
        else:
            return None

    @classmethod
    def pull_by_api_key(cls,api_key):
        res = cls.query(q='api_key:"' + api_key + '"')
        if res.get('hits',{}).get('total',0) == 1:
            return cls(**res['hits']['hits'][0]['_source'])
        else:
            return None

    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)

    def update(self, acc):
        if self.is_super:
            return True
        else:
            return not self.is_anonymous() and acc.id == self.id

    @property
    def is_super(self):
        return not self.is_anonymous() and self.id in app.config['SUPER_USER']

    
class Curated(DomainObject):
    __type__ = 'curated'


class Note(DomainObject):
    __type__ = 'note'

    #def save(self):
    #    if 'id' not in self.data:
    #        self.data['id'] = uuid.uuid4().hex
    #    
    #    self.data['updated_date'] = datetime.now().strftime("%Y-%m-%d %H%M")
    #
    #    if 'created_date' not in self.data:
    #        self.data['created_date'] = datetime.now().strftime("%Y-%m-%d %H%M")
    #        
    #    r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))
    #    print r

    #@classmethod
    #def about(cls, id_):
    #    '''Retrieve notes by id of record they are about'''
    #    if id_ is None:
    #        return None
    #    res = Note.query(q="about:"+id_,size=10000)
    #    return [i['_source'] for i in res['hits']['hits']]
    
    
# a special object that allows a search onto all index types - FAILS TO CREATE INSTANCES
class Everything(DomainObject):
    __type__ = 'everything'

    @classmethod
    def target(cls):
        t = 'http://' + str(app.config['ELASTIC_SEARCH_HOST']).lstrip('http://').rstrip('/') + '/'
        t += app.config['ELASTIC_SEARCH_DB'] + '/'
        return t


class Record(DomainObject):
    __type__ = 'record'

    @classmethod
    def makeid(cls):
        '''Create a new id for data object based on the idgen utility'''
        idgenerator = portality.util.idgen()
        id_ = idgenerator.next()
        while cls.pull(id_):
            id_ = idgenerator.next()
        return id_

    @classmethod
    def pull(cls, id_):
        '''Retrieve object by id.'''
        if id_ is None:
            return None
        try:
            out = requests.get(cls.target() + id_)
            if out.status_code == 404:
                return None
            else:
                # some fixes here for legacy data
                data = out.json()
                update = False
                if 'batch' in data.get('_source',{}):
                    if not isinstance(data['_source']['batch'],list):
                        data['_source']['batch'] = [data['_source']['batch']]
                        update = True
                if 'assembly' in data.get('_source',{}):
                    if data['_source']['assembly'] == '':
                        data['_source']['assembly'] = []
                        update = True
                    elif not isinstance(data['_source']['assembly'],list):
                        data['_source']['assembly'] = [data['_source']['assembly']]
                        update = True
                if 'children' in data.get('_source',{}):
                    data['_source']['children_deprecated'] = data['_source']['children']
                    del data['_source']['children']
                    update = True
                if update:
                    r = requests.post(cls.target() + id_, data=json.dumps(data['_source']))
                return cls(**data)
        except:
            return None

    def save(self):
        if 'id' in self.data:
            id_ = self.data['id'].strip()
        else:
            id_ = self.makeid()
            self.data['id'] = id_
        
        self.data['updated_date'] = datetime.now().strftime("%Y-%m-%d %H%M")

        if 'type' not in self.data:
            self.data['type'] = 'part'

        try:
            usr = current_user.id
        except:
            usr = "anonymous"

        if 'created_date' not in self.data:
            self.data['created_date'] = datetime.now().strftime("%Y-%m-%d %H%M")
            self.data['history'] = [{'date':self.data['created_date'],'user': usr,'current':'record created'}]
        else:
            if 'history' not in self.data:
                self.data['history'] = []
            previous = Record.pull(self.data['id'])
            if previous:
                for key,val in previous.data.items():
                    if key not in ['history','last_access','updated_date']:
                        if key not in self.data.keys():
                            self.data['history'].insert(0, {
                                'date': self.data['updated_date'],
                                'field': key,
                                'previous': json.dumps(val,indent=4),
                                'current': "KEY REMOVED",
                                'user': usr
                            })                        
                        elif val != self.data[key]:
                            if key == 'attachments':
                                tocurrent = "attachment list altered"
                                prev = "attachment list altered"
                            else:
                                tocurrent = json.dumps(self.data[key],indent=4)
                                prev = json.dumps(val,indent=4)
                            self.data['history'].insert(0, {
                                'date': self.data['updated_date'],
                                'field': key,
                                'previous': prev,
                                'current': tocurrent,
                                'user': usr
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
                            'user': usr
                        })

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))
    
    
    def delete(self):
        for kid in self.children:
            k = Record.pull(kid['id'])
            if not isinstance(k.data['assembly'],list):
                k.data['assembly'] = [k.data['assembly']]
            k.data['assembly'] = k.data['assembly'].remove(self.id)
            k.save()
        self.data['assembly'] = []
        self.data['obsolete'] = True
        self.save()
        return ''
    
    @property
    def children(self):
        kids = []
        if self.data['type'] == "assembly":
            res = Record.query(terms={"assembly.exact":self.id})
            if res['hits']['total'] != 0:
                kids = [i['_source'] for i in res['hits']['hits']]            
        return kids

    #@property
    #def parent(self):
    #    if 'assembly' in self.data and self.data['assembly']:
    #        parent = Record.pull(self.data['assembly'])
    #        if parent is not None:
    #            return parent
    #        else:
    #            return False
    #    else:
    #        return False

    @property
    def parents(self):
        if 'assembly' in self.data and self.data['assembly']:
            parents = []
            if 'assembly' not in self.data: self.data['assembly'] = []
            if self.data['assembly'] == '': self.data['assembly'] = []
            if not isinstance(self.data['assembly'],list):
                self.data['assembly'] = [self.data['assembly']]
            for parent in self.data['assembly']:
                rec = Record.pull(parent)
                if rec is not None:
                    parents.append(rec)
            if len(parents) != 0:
                return parents
            else:
                return False
        else:
            return False

    @property
    def notes(self):
        res = Note.query(terms={
            'about.exact': self.id
        })
        allnotes = [ Note(**item['_source']) for item in res['hits']['hits'] ]
        return allnotes
