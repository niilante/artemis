import os
import urllib2
from copy import deepcopy
import unicodedata
import httplib
import json

from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
from flask.views import View, MethodView
from flaskext.login import login_user, current_user

import artemis.dao
from artemis.config import config
import artemis.iomanager
from artemis.core import app, login_manager
from artemis.view.account import blueprint as account
from artemis import auth

app.register_blueprint(account, url_prefix='/account')


# NB: the decorator appears to kill the function for normal usage
@login_manager.user_loader
def load_account_for_login_manager(userid):
    out = artemis.dao.Account.get(userid)
    return out

@app.context_processor
def set_current_user():
    """ Set some template context globals. """
    return dict(current_user=current_user)

@app.before_request
def standard_authentication():
    """Check remote_user on a per-request basis."""
    remote_user = request.headers.get('REMOTE_USER', '')
    if remote_user:
        user = artemis.dao.Account.get(remote_user)
        if user:
            login_user(user, remember=False)
    # add a check for provision of api key
    elif 'api_key' in request.values:
        res = artemis.dao.Account.query(q='api_key:"' + request.values['api_key'] + '"')['hits']['hits']
        if len(res) == 1:
            user = artemis.dao.Account.get(res[0]['_source']['id'])
            if user:
                login_user(user, remember=False)


@app.route('/')
def home():
    # get list of available collections
    try:
        result = artemis.dao.Collection.query(q="*",sort={"created":{"order":"desc"}})
        if result["hits"]["total"] != 0:
            colls = [i["_source"]  for i in result["hits"]["hits"]]
    except:
        colls = None
        counts = None
    return render_template('home/index.html', colls=colls, upload=config["allow_upload"] )

@app.route('/account/<user>')
def account(user):
    if hasattr(current_user,'id'):
        if user == current_user.id:
            return render_template('account/view.html',current_user=current_user)

    flash('You are not that user. Or you are not logged in.')
    return redirect('/account/login')


@app.route('/help')
@app.route('/help/<path:path>')
def content(path=''):
    return render_template('help/index.html', page=path)


@app.route('/record/<path:path>', methods=['GET','POST'])
@app.route('/record/<path:path>/<rectype>', methods=['GET','POST'])
def record(path,rectype=''):
    # POSTs do updates, creates, deletes of records
    if request.method == "POST":
        #if not auth.collection.create(current_user, None):
        #    abort(401)
        if 'delete' in request.values:
            host = str(config['ELASTIC_SEARCH_HOST']).rstrip('/')
            db_name = config['ELASTIC_SEARCH_DB']
            fullpath = '/' + db_name + '/record/' + path
            c =  httplib.HTTPConnection(host)
            c.request('DELETE', fullpath)
            c.getresponse()
            resp = make_response( '{"id":"' + path + '","deleted":"yes"}' )
            resp.mimetype = "application/json"
            return resp
        
        # if not deleting, do the create / update    
        newrecord = request.json
        action = "updated"
        if path == "create":
            if 'id' in newrecord:
                if artemis.dao.Record.get(newrecord['id']):
                    flash('Sorry. That record ID already exists.')
                    return redirect('/record/create')
            action = "new"
        recobj = artemis.dao.Record(**newrecord)
        recobj.save()
        # TODO: should pass a better success / failure output
        resp = make_response( '{"id":"' + recobj.id + '","action":"' + action + '"}' )
        resp.mimetype = "application/json"
        return resp

        
    # otherwise do the GET of the record
    JSON = False
    if path.endswith(".json") or request.values.get('format',"") == "json":
        path = path.replace(".json","")
        JSON = True

    res = artemis.dao.Record.query(q='id:"' + path + '"')

    if path == "create":
        #if not auth.collection.create(current_user, None):
        #    abort(401)
        return render_template('create.html',rectype=rectype)
    elif res["hits"]["total"] == 0:
        abort(404)
    elif JSON:
        return outputJSON(results=res, record=True)
    elif res["hits"]["total"] != 1:
        io = artemis.iomanager.IOManager(res)
        return render_template('record.html', io=io, multiple=True)
    else:
        io = artemis.iomanager.IOManager(res)
        #coll = artemis.dao.Collection.get(io.set()[0]['collection'][0])
        #if coll and auth.collection.update(current_user, coll) and config["allow_edit"] == "YES":
        #    edit = True
        #else:
        #    edit = False
        return render_template('record.html', io=io, edit=True)


@app.route('/search')
@app.route('/<path:path>')
def search(path=''):
    io = dosearch(path.replace(".json",""),'Record')
    if path.endswith(".json") or request.values.get('format',"") == "json":
        if io.incollection:
            return outputJSON(results=io.results, coll=io.incollection['id'])
        else:
            return outputJSON(results=io.results)
    else:
        #edit = False
        #if io.incollection:
        #    if auth.collection.update(current_user, io.incollection):
        #        edit = True
        return render_template('search/index.html', io=io, edit=True, coll=io.incollection)

def dosearch(path,searchtype='Record'):
    showkeys = request.values.get('showkeys',None)
    showfacets = request.values.get('showfacets',None)
    args = {"terms":{}}
    if 'from' in request.values:
        args['start'] = request.values.get('from')
    if 'size' in request.values:
        args['size'] = request.values.get('size')
    if 'sort' in request.values:
        if request.values.get("sort") != "..." and request.values.get("sort") != "":
            args['sort'] = {request.values.get('sort') : {"order" : request.values.get('order','asc')}}
    if 'default_operator' in request.values:
        args['default_operator'] = request.values['default_operator']
    if 'q' in request.values:
        if len(request.values.get('q')) > 0:
            args['q'] = request.values.get('q')
            args['q'] = args['q'].replace('!','')
            if '"' in args['q'] and args['q'].count('"')%2 != 0:
                args['q'] = args['q'].replace('"','')
            if ' OR ' in request.values['q']:
                args['default_operator'] = 'OR'
            if ' AND ' in request.values['q']:
                args['default_operator'] = 'AND'
        
    incollection = {}
    implicit_key = False
    implicit_value = False
    if path != '' and not path.startswith("search"):
        path = path.strip()
        if path.endswith("/"):
            path = path[:-1]
        bits = path.split('/')
        if len(bits) == 2:
            # if first bit is a user ID then this is a collection
            if artemis.dao.Account.get(bits[0]):
                incollection = artemis.dao.Collection.get(bits[1])
                bits[0] = 'collection'
            implicit_key = bits[0]
            implicit_value = bits[1]

    args['facet_fields'] = []
    try:
        facets = incollection['display_settings']['facet_fields']
    except:
        facets = config["facet_fields"]
    print showfacets
    for key,item in enumerate(facets):
        if showfacets:
            if item['key'] not in showfacets.split(','):
                del facets[key]
        new = { "key": item['key']+config["facet_field"], "size": item.get('size',100), "order": item.get('order','count') }
        args['facet_fields'].append(new)
    if showfacets:
        for item in showfacets.split(','):
            if item and item+config["facet_field"] not in [i['key'] for i in args['facet_fields']]:
                args['facet_fields'].append({ "key": item+config["facet_field"], "size": "100", "order": "count" })
                facets.append({ "key": item, "size": "100", "order": "count" })
    for param in request.values:
        if param in [i['key'].replace(config['facet_field'],'') for i in args['facet_fields']]:
            vals = json.loads(unicodedata.normalize('NFKD',urllib2.unquote(request.values.get(param))).encode('utf-8','ignore'))
            args['terms'][param + config['facet_field']] = vals
    if implicit_key:
        args['terms'][implicit_key+config["facet_field"]] = [implicit_value]


    if searchtype == 'Record':
        results = artemis.dao.Record.query(**args)
    else:
        results = artemis.dao.Collection.query(**args)
    return artemis.iomanager.IOManager(results, args, showkeys, showfacets, incollection, implicit_key, implicit_value, path, request.values.get('showopts',''))

def outputJSON(results, coll=None, record=False, collection=False):
    '''build a JSON response, with metadata unless specifically asked to suppress'''
    # TODO: in some circumstances, people data should be added to collections too.
    out = {"metadata":{}}
    if coll:
        out['metadata'] = artemis.dao.Collection.query(q='"'+coll+'"')['hits']['hits'][0]['_source']
    out['metadata']['query'] = request.base_url + '?' + request.query_string
    if request.values.get('facets','') and results['facets']:
        out['facets'] = results['facets']
    out['metadata']['from'] = request.values.get('from',0)
    out['metadata']['size'] = request.values.get('size',10)

    if collection:
        out = dict(**results)
    else:
        out['records'] = [i['_source'] for i in results['hits']['hits']]

    # if a single record meta default is false
    if record and len(out['records']) == 1 and not request.values.get('meta',False):
        out = out['records'][0]

    # if a search result meta default is true
    meta = request.values.get('meta',True)
    if meta == "False" or meta == "false" or meta == "no" or meta == "No" or meta == 0:
        meta = False
    if not record and not meta:
        out = out['records']

    resp = make_response( json.dumps(out, sort_keys=True, indent=4) )
    resp.mimetype = "application/json"
    return resp

if __name__ == "__main__":
    artemis.dao.init_db()
    app.run(host='0.0.0.0', port=5004, debug=True)

