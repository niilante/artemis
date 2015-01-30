
from flask import Blueprint, request, abort, render_template, make_response, flash, send_file, redirect
from flask.ext.login import current_user

from datetime import datetime
import json, StringIO, time

import portality.util as util
from portality.core import app
import portality.models as models

from portality.view.stream import stream


blueprint = Blueprint('record', __name__)


@blueprint.route('/create/<rectype>', methods=['GET','POST'])
def create(rectype):
    if current_user.is_anonymous():
        abort(401)

    if request.method == "GET":
        if rectype == 'batch':
            idgenerator = util.idgen('batch')
            batchid = idgenerator.next()
        else:
            batchid = None
        return render_template(
            'create.html', 
            rectype=rectype, 
            batchid=batchid, 
            obsoletes = [i['_source'] for i in models.Record.query(terms={'obsolete':True},size=100000).get('hits',{}).get('hits',{})],
            assemblies = [i['_source'] for i in models.Record.query(terms={'type':'assembly'},size=100000).get('hits',{}).get('hits',{})]
        )

    elif request.method == "POST":
        received = request.json if request.json else request.values
        record = {}
        for key, val in received.items():
            if key not in ['submit','howmany']:
                record[key] = val
        if self.rectype == "batch":
            create = int(received['howmany'])
        else:
            create = 1
        count = 0
        recids = []
        while count < create:
            count = count + 1
            recobj = models.Record(**record)
            recobj.save()
            recids.append(recobj.id)

        time.sleep(1)
        if self.rectype == "batch":
            flash('Your batch has been created. The parts in the batch are shown below.')
            return redirect('/batch/' + record['batch'])
        else:
            flash('Your new record has been created')
            return redirect('/record/' + recids[0])

        
@blueprint.route('/edit/batch')
@blueprint.route('/edit/batch/<bid>', methods=['GET','POST'])
def batchedit(bid=None):
    if current_user.is_anonymous(): abort(401)
        
    if request.method == "GET":
        if bid is None:
            return render_template(
                'batchedit.html', 
                bid=bid,
                batches=stream(key='batch',raw=True,size=1000000),
                keys={}
            )

        else:
            recs = models.Record.query(q='batch.exact:"'+str(bid)+'"',size=1000000)
            keys = {}
            for rec in [i['_source'] for i in recs.get('hits',{}).get('hits',[])]:
                for key in rec.keys():
                    if key not in ['notes','attachments','created_date','batch','updated_date','last_access','id','history','type']:
                        if key not in keys.keys():
                            keys[key] = []
                        if not isinstance(rec[key],list):rec[key] = [rec[key]]
                        for val in rec[key]:
                            if val not in keys[key]:
                                keys[key].append(val)
                
            return render_template(
                'batchedit.html', 
                bid=bid,
                batchsize=recs.get('hits',{}).get('total',0),
                batches=[],
                keys=keys
            )

    elif request.method == "POST":
        received = request.json if request.json else request.values
        recs = models.Record.query(q='batch.exact:"' + bid + '"', size=1000000)
        updated = 0
        for rc in recs.get('hits',{}).get('hits',[]):
            rid = rc['_source']['id']
            rec = models.Record.pull(rid)
            for key, val in received.items():
                if key not in ['submit']:
                    rec.data[key] = val
            rec.save()
            updated += 1

        time.sleep(1)
        flash(str(updated) + ' records in this batch have been updated. The parts in the batch are shown below.')
        return redirect('/batch/' + bid)


@blueprint.route('/<rid>', methods=['GET','POST','DELETE'])
def rec(rid):
    res = models.Record.pull(rid)

    if res is None:
        abort(404)
    elif request.method == "DELETE" or request.method == 'POST' and request.values.get('submit',False) == 'Delete':
        if current_user.is_anonymous():
            abort(401)
        flash('record ' + res.id + ' obsolete')
        res.delete()
        return redirect('/')

    elif request.method == "POST":
        if current_user.is_anonymous(): abort(401)
        newdata = request.json if request.json else request.values
        for k, v in newdata.items():
            if v.startswith("{u'"):
                if k in res.data.keys():
                    del res.data[k]
                dd = json.loads(v.replace("u'","'").replace("'",'"'))
                for l, m in dd.items():
                    if len(m) > 0:
                        res.data[k + '_' + l] = m
            elif k not in ['submit']:
                res.data[k] = v
        res.save()

    else:
        res.accessed()

    return render_template(
        'record.html', 
        batches=stream(key='batch',raw=True,size=1000000),
        record=res
    )


@blueprint.route('/<rid>/parent', methods=['GET','DELETE'])
@blueprint.route('/<rid>/parent/<pid>', methods=['GET','POST','DELETE'])
def parent(rid, pid=False):
    res = models.Record.pull(rid)
    if res is None:
        abort(404)
    elif request.method == 'GET':
        resp = make_response( res.parent.json )
        resp.mimetype = "application/json"
        return resp
    elif request.method == 'POST' and pid:
        if current_user.is_anonymous(): abort(401)
        res.data['assembly'] = pid
        res.save()
        return ""
    elif request.method == 'DELETE':
        if current_user.is_anonymous(): abort(401)
        res.data['assembly'] = ''
        res.save()
        return ""

    
@blueprint.route('/<rid>/children', methods=['GET','DELETE'])
@blueprint.route('/<rid>/children/<cid>', methods=['GET','POST','DELETE'])
def children(rid,cid=False):
    res = models.Record.pull(rid)
    if res is None: abort(404)
    if request.method == 'GET':
        if cid:
            resc = models.Record.pull(cid)
            output = resc.json
        else:
            output = json.dumps(res.children)
    elif request.method == 'POST':
        if current_user.is_anonymous(): abort(401)
        c = models.Record.pull(cid)
        c.data['assembly'] = rid
        c.save()
        return ""
    elif request.method == 'DELETE':
        if current_user.is_anonymous(): abort(401)
        try:
            if cid:
                children_ids = [cid]
            else:
                children_ids = [i['id'] for i in res.children]
            for kid in children_ids:
                c = models.Record.pull(kid)
                c.data['assembly'] = ''
                c.save()
            return ""
        except:
            abort(404)

    resp = make_response( output )
    resp.mimetype = "application/json"
    return resp


@blueprint.route('/<rid>/attachments', methods=['GET','POST'])
@blueprint.route('/<rid>/attachments/<aid>', methods=['GET','POST'])
def attachments(rid,aid=False):
    res = models.Record.pull(rid)
    if res is None: abort(404)
    if request.method == 'GET':
        if aid:
            res = models.Record.pull(rid)
            for att in res.data['attachments']:
                if att['filename'] == aid:
                    thefile = att['attachment'].decode("base64")
                    strio = StringIO.StringIO()
                    strio.write(thefile)
                    strio.seek(0)
                    return send_file(
                        strio, 
                        attachment_filename=att['filename'],
                        as_attachment=True
                    )
        else:
            resp = make_response( json.dumps(res.data['attachments']) )
            resp.mimetype = "application/json"
            return resp
    elif request.method == 'POST':
        if current_user.is_anonymous(): abort(401)
        upfile = request.files.get('upfile')
        content = upfile.read()
        encoded = content.encode("base64")
        newatt = {
            "attachment": encoded,
            "filename": upfile.filename,
            "description": request.values.get('description',""),
            "test_type": request.values.get('test_type',""),
            "test_date": request.values.get('test_date',""),
            "test_status": request.values.get('test_status',""),
            "tested_by": request.values.get("tested_by",""),
            "user": current_user.id,
            "date": datetime.now().strftime("%Y-%m-%d %H%M")
        }
        if 'attachments' not in res.data: res.data['attachments'] = []
        res.data['attachments'].insert(0, newatt)
        if newatt['test_status'] == 'Pass':
            if 'overall_test_status' not in res.data:
                res.data['overall_test_status'] = 'allpass'
            elif res.data['overall_test_status'] == 'lastfail':
                res.data['overall_test_status'] = 'somefail'
        else:
            res.data['overall_test_status'] = 'lastfail'
            
        res.save()
        if res.data.get('type','') == 'assembly':
            for kid in res.children:
                k = models.Record.pull(kid['id'])
                if 'attachments' not in k.data:
                    k.data['attachments'] = []
                k.data['attachments'].insert(0, newatt)
                k.save()
        return redirect('/record/' + res.id)
    elif request.method == 'DELETE':
        if current_user.is_anonymous(): abort(401)
        try:
            if aid:
                count = 0
                for att in res.data['attachments']:
                    count += 1
                    if att['filename'] == aid:
                        del res.data['attachments'][count]
            else:
                res.data['attachments'] = []
            res.save()
            return ""
        except:
            abort(404)

