import json

from flask import Flask, jsonify, json, request, redirect, abort, make_response
from flask import render_template, flash
from flask.views import View, MethodView
from flask.ext.login import login_user, current_user

import artemis.dao
import artemis.util as util
from artemis.config import config
from artemis.core import app, login_manager
from artemis.view.account import blueprint as account
from artemis import auth


app.register_blueprint(account, url_prefix='/account')

@login_manager.user_loader
def load_account_for_login_manager(userid):
    out = artemis.dao.Account.get(userid)
    return out

@app.context_processor
def set_current_user():
    """ Set some template context globals. """
    fields = {}
    f = [i['_source'] for i in artemis.dao.Curated().query(size=10000).get('hits',{}).get('hits',{})]
    for rec in f:
        fields[rec['id']] = ",".join(rec['values'])
    return dict(current_user=current_user, curatedfields=fields)

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


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(401)
def page_not_found(e):
    return render_template('401.html'), 401


@app.route('/query/<path:path>', methods=['GET','POST'])
@app.route('/query/', methods=['GET','POST'])
@app.route('/query', methods=['GET','POST'])
def query(path='Record'):
    pathparts = path.split('/')
    subpath = pathparts[0]
    if subpath.lower() == 'account':
        abort(401)
    klass = getattr(artemis.dao, subpath[0].capitalize() + subpath[1:] )
    qs = request.query_string
    if request.method == "POST":
        qs += "&source=" + json.dumps(dict(request.form).keys()[-1])
    if len(pathparts) > 1 and pathparts[1] == '_mapping':
        resp = make_response( json.dumps(klass().get_mapping()) )
    else:
        resp = make_response( klass().raw_query(qs) )
    resp.mimetype = "application/json"
    return resp
        

@app.route('/help')
@app.route('/help/<path:path>')
def content(path=''):
    return render_template('help/index.html', page=path)


@app.route('/')
def home():
    try:
        res = artemis.dao.Record.query(sort={'created_date':{'order':'desc'}})
    except:
        res = artemis.dao.Record.query()
    return render_template(
        'home/index.html',
        assemblies = artemis.dao.Record.query(terms={'type':'assembly'})['hits']['total'],
        records = artemis.dao.Record.query(terms={'type':'part'})['hits']['total'],
        recent = [i['_source'] for i in res['hits']['hits']]
    )


@app.route('/users')
@app.route('/users.json')
def users():
    if current_user.is_anonymous() or not current_user.is_super:
        abort(401)
    users = artemis.dao.Account.query(sort={'id':{'order':'asc'}},size=1000000)
    if users['hits']['total'] != 0:
        accs = [artemis.dao.Account.get(i['_source']['id']) for i in users['hits']['hits']]
        # explicitly mapped to ensure no leakage of sensitive data. augment as necessary
        users = []
        for acc in accs:
            user = {"id":acc["id"]}
            users.append(user)
    if util.request_wants_json():
        resp = make_response( json.dumps(users, sort_keys=True, indent=4) )
        resp.mimetype = "application/json"
        return resp
    else:
        return render_template('account/users.html',users=users)

    
# set the route for receiving new notes
@app.route('/note', methods=['GET','POST'])
@app.route('/note/<nid>', methods=['GET','POST','DELETE'])
def note(nid=''):
    if request.method == 'POST':
        newnote = artemis.dao.Note()
        newnote.data = request.json
        newnote.save()
        return redirect('/note/' + newnote.id)

    elif request.method == 'DELETE':
        note = artemis.dao.Note.get(nid)
        note.delete()
        return ""

    else:
        thenote = artemis.dao.Note.get(nid)
        if thenote:
            resp = make_response( json.dumps(thenote.data, sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            abort(404)


# set th route for admin functions
@app.route('/admin', methods=['GET','POST'])
@app.route('/admin/', methods=['GET','POST'])
def admin():
    if current_user.is_anonymous() or not current_user.is_super:
        abort(401)

    if request.method == 'GET':
        return render_template('admin/index.html')
    elif request.method == 'POST':
        key = request.json['key']
        values = request.json['values']
        curlist = artemis.dao.Curated.get(key)
        curlist.data['values'] = values
        curlist.save()
        return ""


# this is a catch-all that allows us to present everything as a search
# such as /implicit_facet_key/implicit_facet_value
# and any thing else passed as a search
@app.route('/<path:path>', methods=['GET','POST','DELETE'])
def default(path):
    import artemis.search
    searcher = artemis.search.Search(path=path,current_user=current_user)
    return searcher.find()


if __name__ == "__main__":
    artemis.dao.init_db()
    app.run(host='0.0.0.0', debug=config['debug'], port=config['port'])

