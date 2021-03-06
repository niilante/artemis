
from flask import Flask, request, abort, render_template, make_response, redirect, flash, session
from flask.views import View
from flask.ext.login import login_user, current_user

import json, time, datetime, math, uuid

import portality.models as models
from portality.core import app, login_manager

from portality.view.stream import stream as rawstream

from portality.view.query import blueprint as query
from portality.view.stream import blueprint as stream
from portality.view.account import blueprint as account
from portality.view.record import blueprint as record
from portality.view.export import blueprint as export
from portality.view.imports import blueprint as imports


app.register_blueprint(query, url_prefix='/query')
app.register_blueprint(stream, url_prefix='/stream')
app.register_blueprint(account, url_prefix='/account')
app.register_blueprint(record, url_prefix='/record')
app.register_blueprint(export, url_prefix='/export')
app.register_blueprint(imports, url_prefix='/import')


@login_manager.user_loader
def load_account_for_login_manager(userid):
    out = models.Account.pull(userid)
    return out

@app.context_processor
def set_current_context():
    """ Set some template context globals. """
    fields = {}
    f = [i['_source'] for i in models.Curated.query(size=10000).get('hits',{}).get('hits',{})]
    for rec in f:
        if rec.get('type',False) and rec['type'] not in fields.keys(): fields[rec['type']] = []
        if rec.get('type',False) and rec.get('value',False) and rec['value'] not in fields[rec['type']]: fields[rec['type']].append(rec['value'])
    if 'staff' not in fields: fields['staff'] = []
    accs = models.Account.query(q='*',size=1000000)
    for i in accs.get('hits',{}).get('hits',[]):
        if i['_source']['id'] not in fields['staff']:
            fields['staff'].append(i['_source']['id'])
    fields['staff'].sort()
    return dict(current_user=current_user, app=app, curatedfields=fields)

@app.before_request
def standard_authentication():
    """Check remote_user on a per-request basis."""
    remote_user = request.headers.get('REMOTE_USER', '')
    if request.json:
        vals = request.json
    else:
        vals = request.values
    if remote_user:
        user = models.Account.pull(remote_user)
        if user is not None:
            login_user(user, remember=False)
            session.permanent = True
    # add a check for provision of api key
    elif 'api_key' in vals:
        res = models.Account.query(q='api_key:"' + vals['api_key'] + '"')['hits']['hits']
        if len(res) == 1:
            user = models.Account.pull(res[0]['_source']['id'])
            if user is not None:
                login_user(user, remember=False)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(401)
def unauthorised(e):
    flash('Sorry, you must be logged in to view that page', 'warning')
    return redirect('/account/login')
        

@app.route('/help')
@app.route('/help/<path:path>')
def content(path=''):
    return render_template('help/index.html', page=path)


@app.route('/')
def home():
    recenttype = 'generic'
    try:
        try:
            res = models.Record.query(q = 'history.user.exact:"' + current_user.id + '"', sort={'history.date.exact':{'order':'desc'}})
            recenttype = 'user'
        except:
            res = models.Record.query(sort={'created_date.exact':{'order':'desc'}})
    except:
        res = models.Record.query()
    return render_template(
        'home/index.html',
        assemblies = models.Record.query(terms={'type':'assembly'})['hits']['total'],
        records = models.Record.query(terms={'type':'part'})['hits']['total'],
        recent = [i['_source'] for i in res.get('hits',{}).get('hits',[])],
        recenttype = recenttype
    )



@app.route('/search')
@app.route('/search/obsolete')
@app.route('/search/<batch>')
@app.route('/batch/<batch>')
@app.route('/assembly/<assembly>')
@app.route('/type/part')
@app.route('/type/assembly')
def search(batch=False,assembly=False):
    if 'obsolete' in request.path:
        obsolete = True
    else:
        obsolete = False
    dates = rawstream(key='created_date',size=10000,raw=True)
    datevals = []
    for d in dates:
        dd = math.floor(d/1000)
        dp = datetime.datetime.fromtimestamp(dd).strftime('%Y-%m-%d')
        if dp not in datevals: datevals.append(dp)
    if 'type' in request.path and 'part' in request.path:
        tp = 'part'
    elif 'type' in request.path and 'assembly' in request.path:
        tp = 'assembly'
    else:
        tp = False
    return render_template('search/index.html', obsolete=obsolete, datevals=datevals, batch=batch, assembly=assembly, type=tp)

    
# set the route for receiving new notes
# TODO update this so that notes cascade into sub batches and assemblies, and subsub batches etc, when chosen to apply to more than just the current record
@app.route('/note', methods=['GET','POST'])
@app.route('/note/<nid>', methods=['GET','POST','DELETE'])
def note(nid=''):
    if request.method == 'POST':
        cascade = False;
        if 'assembly' in request.json: cascade = True
        if 'batch' in request.json:
            res = models.Record.query(terms={"batch.exact":request.json['batch']},size=10000)
            for r in [i['_source'] for i in res['hits']['hits']]:
                rec = models.Record.pull(r['id'])
                rec.addnote(request.json,cascade)
        else:
            rec = models.Record.pull(request.json['about'])
            rec.addnote(request.json,cascade)

        time.sleep(1)
        return ""

    elif request.method == 'DELETE':
        note = models.Note.pull(nid)
        note.delete()
        return ""

    else:
        thenote = models.Note.pull(nid)
        if thenote:
            resp = make_response( json.dumps(thenote.data, sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            abort(404)


@app.route('/admin', methods=['GET'])
@app.route('/admin/<cid>', methods=['GET','POST','DELETE'])
def admin(cid=False):
    if current_user.is_anonymous() or not current_user.is_super:
        abort(401)

    if cid:
        if cid == 'create':
            cur = models.Curated()
        else:
            cur = models.Curated.pull(cid)
            if cur is None: abort(404)

    if not cid:
        return render_template('admin/index.html')
    elif request.method == 'GET':
        return render_template('admin/edit.html', cur=cur)
    elif request.method == 'DELETE' or request.method == 'POST' and request.values.get('submit','') == 'Delete':
        cur.delete()
        flash('Curated value deleted')
        return render_template('admin/index.html')
    elif request.method == 'POST' and request.values.get('submit','') == 'Replace':
        old = models.Curated.pull(request.values['replace'])
        oldval = old.data['value']
        newval = cur.data['value']
        valtype = cur.data['type']
        # do a query here for all records with this value in the relevant curated field slot, and switch the value
        res = models.Record.query(q=valtype+".exact:'" + oldval + "'", fields='id', size=10000)
        counter = 0
        for rid in [i['fields']['id'] for i in res.get('hits',{}).get('hits',[])]:
            rec = models.Record.pull(rid)
            rec.data[valtype] = newval
            rec.save()
            counter += 1
        old.delete()
        flash(str(counter) + ' records have been altered, and ' + oldval + ' has been removed from curated ' + valtype + ' values.')
        return render_template('admin/edit.html', cur=cur)
    elif request.method == 'POST':
        values = request.json if request.json else request.values
        for k,v in values.items():
            if k not in ['submit']:
                cur.data[k] = v
        cur.save()
        flash('Record updated')
        return render_template('admin/edit.html', cur=cur)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=app.config['DEBUG'], port=app.config['PORT'])

