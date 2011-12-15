import json, urllib2
from copy import deepcopy
import operator, unicodedata
import artemis.dao
import artemis.config
import re

class IOManager(object):
    def __init__(self, results, args={}, showkeys='', showfacets="", incollection=False, implicit_key="", implicit_value="", path="", showopts=""):
        self.results = results
        self.args = args
        self.showopts = showopts
        self.showkeys = showkeys
        self.showfacets = showfacets
        self.incollection = incollection
        self.implicit_key = implicit_key
        self.implicit_value = implicit_value
        self.path = path
        #self.facet_fields = args.get('facet_fields','')
        self.config = artemis.config.Config()
        self.result_display = self.config.result_display
        self.facet_fields = self.config.facet_fields

        '''check for specific settings related to this collection, if in a collection'''
        if self.incollection:
            if 'display_settings' in self.incollection:
                if 'result_display' in self.incollection['display_settings']:
                    self.result_display = self.incollection['display_settings']['result_display']
                if 'facet_fields' in self.incollection['display_settings']:
                    self.facet_fields = self.incollection['display_settings']['facet_fields']

        self.facet_values = {}
        if 'facets' in self.results:
            for facet,data in self.results['facets'].items():
                self.facet_values[facet.replace(self.config.facet_field,'')] = data["terms"]
        

    def get_q(self):
        return self.args.get('q','')
    
    def get_safe_terms_object(self):
        terms = {}
        for term in self.args["terms"]:
            if term.replace(self.config.facet_field,'') not in self.path:
                theterm = '['
                for i in self.args['terms'][term]:
                    theterm += '"' + i + '",'
                theterm = theterm[:-1]
                theterm += ']'
                terms[term.replace(self.config.facet_field,'')] = theterm
        return terms    

    def get_path_params(self,myargs):
        param = '/' + self.path + '?' if (self.path != '') else self.config.base_url + '?'
        if 'q' in myargs:
            param += 'q=' + myargs['q'] + '&'
        if 'terms' in myargs:
            for term in myargs['terms']:
                if term.replace(self.config.facet_field,'') not in self.path:
                    val = '[' + ",".join(urllib2.quote('"{0}"'.format(i.encode('utf-8'))) for i in myargs['terms'][term]) + ']'
                    param += term.replace(self.config.facet_field,'') + '=' + val + '&'
        if self.showkeys:
            param += 'showkeys=' + self.showkeys + '&'
        if self.showfacets:
            param += 'showfacets=' + self.showfacets + '&'
        return param

    def get_add_url(self, field, value):
        myargs = deepcopy(self.args)
        field += self.config.facet_field
        if myargs['terms'].has_key(field):
            if value not in myargs['terms'][field]:
                myargs['terms'][field].append(value)
        else:
            myargs['terms'][field] = [value]
        return self.get_path_params(myargs)
        
    def get_delete_url(self, field, value=None):
        myargs = deepcopy(self.args)
        if value is not None:
            field += self.config.facet_field
            myargs['terms'][field].remove(value)
            if len(myargs['terms'][field]) == 0:
                del myargs['terms'][field]
        else:
            del myargs['terms'][field]
        return self.get_path_params(myargs)


    def in_args(self, facet, value):
        return self.args['terms'].has_key(facet + self.config.facet_field) and value in self.args['terms'][facet + self.config.facet_field]
            
    '''get all currently available keys in ES, and see if they are searchable'''
    def get_keys(self):
        self.seenkey = []
        self.keys = []
        for record in self.set():
            for key in record.keys():
                if key not in self.seenkey:
                    if isinstance(record[key],basestring):
                        self.keys.append({"key":key,"sortable":True})
                    else:
                        self.keys.append({"key":key,"sortable":False})
                        if not isinstance(record[key],list):
                            record[key] = [record[key]]
                        for each in record[key]:
                            if isinstance(each,dict):
                                for thing in each.keys():
                                    if key+'.'+thing not in self.seenkey:
                                        if isinstance(each[thing],basestring):
                                            self.keys.append({"key":key+'.'+thing,"sortable":True})
                                        else:
                                            self.keys.append({"key":key+'.'+thing,"sortable":False})
                                        self.seenkey.append(key+'.'+thing)
                    self.seenkey.append(key)
        self.keys.sort(key=lambda x: x['key'])
        return self.keys
    
    '''get keys to show on results'''
    def get_showkeys(self,format="string"):
        if format == "string":
            if not self.showkeys:
                return "";
            return self.showkeys
        else:
            if not self.showkeys:
                return []
            return [i for i in self.showkeys.split(',')]

    def get_showfacets(self,format="string"):
        if not self.showfacets:
            self.showfacets = ""
            for item in self.facet_fields:
                self.showfacets += item['key'] + ','
            self.showfacets = self.showfacets.strip(',')
        if format == "string":
            if not self.showfacets:
                return "";
            return self.showfacets
        else:
            if not self.showfacets:
                return []
            return [i for i in self.showfacets.split(',')]

    def get_rpp_options(self):
        return self.config.results_per_page_options

    def numFound(self):
        return int(self.results['hits']['total'])

    def page_size(self):
        return int(self.args.get("size",10))

    def paging_range(self):
        return ( self.numFound() / self.page_size() ) + 1

    def sorted_by(self):
        if "sort" in self.args:
            return self.args["sort"].keys()[0].replace(self.config.facet_field,"")
        return ""

    def sort_order(self):
        if "sort" in self.args:
            return self.args["sort"][self.args["sort"].keys()[0]]["order"]
        return ""
        
    def start(self):
        return int(self.args.get('start',0))

    def set(self):
        '''Return list of search result items'''
        return [rec['_source'] for rec in self.results['hits']['hits']]


    def get_str(self, result, field, raw=False):
        res = result.get(field,"")
        if not res:
            return ""
        if self.config.display_value_functions.has_key(field) and not raw:
            d = self.config.display_value_functions[field]
            func_name = d.keys()[0]
            args = d[func_name]
            args["field"] = field
            if self.incollection:
                args["incollection"] = self.incollection
            args["path"] = self.path
            func = globals()[func_name]
            return func(res, args)
        else:
            if isinstance(res,list):
                if isinstance(res[0],dict):
                    out = ""
                    for item in res:
                        if item.get('id','').startswith('http'):
                            theid = '<a href="' + item['id'] + '">' + item['id'] + '</a>'
                        else:
                            theid = item.get('id','')
                        out += item.get('type','') + ": " + theid + "<br />"
                    return out
                else:
                    return ','.join(str(res))
            else:
                return res
        return res
        
    def get_meta(self):
        if self.incollection:
            meta = '<p><a href="/'
            meta += self.path + '.json?size=' + str(self.incollection['records'])
            meta += '">Download this collection</a><br />'
            meta += 'This collection was created by <a href="/account/' + self.incollection['owner'] + '">' + self.incollection['owner'] + '</a><br />'
            if "source" in self.incollection and self.incollection['source']:
                meta += 'The source of this collection is <a href="'
                meta += self.incollection["source"] + '">' + self.incollection["source"] + '</a>.<br /> '
            if "modified" in self.incollection:
                meta += 'This collection was last updated on ' + self.incollection["modified"] + '. '
            return meta
        else:
            return ""

    def get_children(self):
        res = artemis.dao.Record.query(q='assembly:"' + self.set()[0]['id'] + '"')
        if res['hits']['total'] != 0:
            return [i['_source'] for i in res['hits']['hits']]
        else:
            return None


    def get_record_version(self,recordid):
        record = artemis.dao.Record.get(recordid)
        if not record:
            record = artemis.dao.Collection.get(recordid)
        return record.version

    def get_record_as_table(self,which=0):
        return self.tablify(self.set()[which])
        
    def tablify(self,thing):
        if not thing:
            return ""
        try:
            s = '<table>'
            for key,val in thing.iteritems():
                s += '<tr><td><strong>' + key + '</strong></td><td>' + self.tablify(val) + '</td></tr>'
            s += '</table>'
        except:
            if isinstance(thing,list):
                s = '<table>'
                for item in thing:
                    s += '<tr><td>' + self.tablify(item) + '</tr></td>'
                s += '</table>'
            else:
                s = thing
        return s


def collectionify(value, dict):
    # for the given value, make it a link to a collection facet URL
    coll = artemis.dao.Collection.get(value[0])
    if coll:
        return '<a href="/' + coll['owner'] + "/" + value[0] + '" alt="go to collection '  + value[0] + '" title="go to collection '  + value[0] + '">' + value[0] + '</a>'
    else:
        return value

def searchify(value, dict):
    # for the given value, make it a link to a search of the value
    return '<a href="?q=' + value + '" alt="search for ' + value + '" title="search for ' + value + '">' + value + '</a>'


