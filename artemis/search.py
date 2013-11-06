
from flask import Flask, request, redirect, abort, make_response
from flask import render_template, flash, send_file
import artemis.dao
from artemis import auth
from datetime import datetime
from copy import deepcopy
import json, httplib, StringIO, time
from artemis.config import config
import artemis.util as util


class Search(object):

    def __init__(self,path,current_user):
        self.path = path.replace(".json","")
        self.current_user = current_user

        self.search_options = {
            'sharesave_link': False,
            'search_url': '/query?',
            'search_index': 'elasticsearch',
            'paging': { 'from': 0, 'size': 10 },
            'predefined_filters': {},
            'facets': config['search_facet_fields'],
            'result_display': config['search_result_display']
        }

        self.parts = self.path.strip('/').split('/')

        self.values = {}
        self.values['assembly'] = [i['_source'] for i in artemis.dao.Record.query(terms={'type':'assembly'},size=100000).get('hits',{}).get('hits',{})]
        self.values['user'] = [i['_source'] for i in artemis.dao.Account.query().get('hits',{}).get('hits',{})]


    def find(self):
        if artemis.dao.Account.get(self.parts[0]):
            if len(self.parts) == 1:
                return self.account() # user account
        elif self.parts[0] == 'record':
            self.path = ''
            self.rectype = ''
            self.pcid = ''
            if len(self.parts) > 1:
                self.path = self.parts[1]
            if len(self.parts) > 2:
                self.rectype = self.parts[2]
            if len(self.parts) > 3:
                self.pcid = self.parts[3]
            if self.path == 'create':
                return self.create()
            elif self.rectype == 'parent':
                return self.parent()
            elif self.rectype == 'children':
                return self.children()
            elif self.rectype == 'attachments':
                return self.attachments()
            else:
                return self.record()
        elif len(self.parts) == 1:
            if self.parts[0] != 'search':
                self.search_options['q'] = self.parts[0]
            return self.default() # get search result of implicit search term
        elif len(self.parts) == 2:
            return self.implicit_facet() # get search result of implicit facet filter
        else:
            abort(404)


    def default(self):
        if util.request_wants_json():
            res = artemis.dao.Record.query()
            resp = make_response( json.dumps([i['_source'] for i in res['hits']['hits']], sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            return render_template('search/index.html', 
                current_user=self.current_user, 
                search_options=json.dumps(self.search_options), 
                collection=None
            )
        

    def implicit_facet(self):
        self.search_options['predefined_filters'][self.parts[0]+config['FACET_FIELD']] = {'term':{self.parts[0]+config['FACET_FIELD']:self.parts[1]}}
        # remove the implicit facet from facets
        for count,facet in enumerate(self.search_options['facets']):
            if facet['field'] == self.parts[0]+config['FACET_FIELD']:
                del self.search_options['facets'][count]
        if util.request_wants_json():
            res = artemis.dao.Record.query(terms=self.search_options['predefined_filters'])
            resp = make_response( json.dumps([i['_source'] for i in res['hits']['hits']], sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            return render_template('search/index.html', 
                current_user=self.current_user, 
                search_options=json.dumps(self.search_options), 
                collection=None, 
                implicit=self.parts[0]+': ' + self.parts[1]
            )


    def record(self):
        res = artemis.dao.Record.get(self.path)

        if request.method == "DELETE" or request.method == 'POST' and request.values.get('submit',False) == 'Delete':
            flash('record ' + res.id + ' deleted')
            res.delete()
            return redirect('/')

        elif request.method == "POST":
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
            opts = deepcopy(self.search_options)
            notes = artemis.dao.Note.about(res.id)
            return render_template(
                'record.html', 
                record=res, 
                search_options=json.dumps(opts), 
                notes=notes,
                recordstring=json.dumps(res.data,indent=4), 
                edit=True,
                values=self.values
            )
                    
        else:
            if not res:
                abort(404)
            else:
                res.update_access_record()
                opts = deepcopy(self.search_options)
                notes = artemis.dao.Note.about(res.id)
                opts['result_display'][0][1]['pre'] = '<a onclick="doupdate(\''
                opts['result_display'][0][1]['post'] = '\')" href="javascript: return null;">'
                if res.data.get('type','') == "assembly":
                    opts['predefined_filters'] = {'type.exact':{'term':{'type.exact':'part'}}}
                else:
                    opts['predefined_filters'] = {'type.exact':{'term':{'type.exact':'assembly'}}}
                for att in res.data.get('attachments',[]):
                    att['attachment'] = ''
                return render_template(
                    'record.html', 
                    record=res, 
                    search_options=json.dumps(opts), 
                    notes=notes,
                    recordstring=json.dumps(res.data,indent=4), 
                    edit=True,
                    values=self.values
                )

    
    def create(self):
        if request.method == "GET":
            if self.rectype == "batch":
                idgenerator = util.idgen('batch')
                batchid = idgenerator.next()
            else:
                batchid = None
            return render_template('create.html', rectype=self.rectype, batchid=batchid, values=self.values)

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
                recobj = artemis.dao.Record(**record)
                recobj.save()
                recids.append(recobj.id)

            time.sleep(1)
            if self.rectype == "batch":
                flash('Your batch has been created. The parts in the batch are shown below.')
                return redirect('/batch/' + record['batch'])
            else:
                flash('Your new record has been created')
                return redirect('/record/' + recids[0])
            
            
    def parent(self):
        res = artemis.dao.Record.get(self.path)
        if not res:
            abort(404)
            
        if request.method == 'GET':
            resp = make_response( res.parent.json )
            resp.mimetype = "application/json"
            return resp
        elif request.method == 'POST':
            if self.pcid:
                res.data['assembly'] = self.pcid
                res.save()
                # update the parent assembly too
                ass = artemis.dao.Record.get(self.pcid)
                if 'children' not in ass.data: ass.data['children'] = []
                ass.data['children'].append(self.path)
                ass.save()
                return ""
            else:
                abort(404)
        elif request.method == 'DELETE':
            # update the parent assembly too
            ass = artemis.dao.Record.get(res.data['assembly'])
            if 'children' not in ass.data: ass.data['children'] = []
            if self.path in ass.data['children']:
                ass.data['children'].remove(self.path)
            ass.save()
            res.data['assembly'] = ''
            res.save()
            return ""


    def children(self):
        if request.method == 'GET':
            if self.pcid:
                res = artemis.dao.Record.get(self.pcid)
                output = res.json
            else:
                res = artemis.dao.Record.get(self.path)
                output = res.children
        elif request.method == 'POST':
            if self.pcid:
                c = artemis.dao.Record.get(self.pcid)
                c.data['assembly'] = self.path
                c.save()
                # update the parent assembly too
                ass = artemis.dao.Record.get(self.path)
                if 'children' not in ass.data: ass.data['children'] = []
                ass.data['children'].append(self.pcid)
                ass.save()
                return ""
            else:
                abort(404)
        elif request.method == 'DELETE':
            try:
                if self.pcid:
                    children_ids = [self.pcid]
                    # update the parent assembly too
                    if 'children' not in res.data: res.data['children'] = []
                    if self.pcid in res.data['children']:
                        res.data['children'].remove(self.pcid)
                    res.save()
                else:
                    res = artemis.dao.Record.get(self.path)
                    children_ids = [i['id'] for i in res.children]
                    res.data['children'] = []
                    res.save()
                for kid in children_ids:
                    c = artemis.dao.Record.get(kid)
                    c.data['assembly'] = ''
                    c.save()
                return ""
            except:
                abort(404)

        resp = make_response( output )
        resp.mimetype = "application/json"
        return resp


    def attachments(self):
        if request.method == 'GET':
            if self.pcid:
                res = artemis.dao.Record.get(self.path)
                for att in res.data['attachments']:
                    if att['filename'] == self.pcid:
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
                res = artemis.dao.Record.get(self.path)
                resp = make_response( json.dumps(res.data['attachments']) )
                resp.mimetype = "application/json"
                return resp
        elif request.method == 'POST':
            upfile = request.files.get('upfile')
            content = upfile.read()
            encoded = content.encode("base64")
            newatt = {
                "attachment": encoded,
                "filename": upfile.filename,
                "description": request.values.get('description',""),
                "test_type": request.values.get('test_type',""),
                "test_date": request.values.get('test_date',""),
                "tested_by": request.values.get("tested_by",""),
                "user": self.current_user.id,
                "date": datetime.now().strftime("%Y-%m-%d %H%M")
            }
            res = artemis.dao.Record.get(self.path)
            if 'attachments' not in res.data:
                res.data['attachments'] = []
            res.data['attachments'].insert(0, newatt)
            res.save()
            if res.data.get('type','') == 'assembly':
                for kid in res.children:
                    k = artemis.dao.Record.get(kid['id'])
                    if 'attachments' not in k.data:
                        k.data['attachments'] = []
                    k.data['attachments'].insert(0, newatt)
                    k.save()
            return redirect('/record/' + res.id)
        elif request.method == 'DELETE':
            try:
                res = artemis.dao.Record.get(self.path)
                if self.pcid:
                    count = 0
                    for att in res.data['attachments']:
                        count += 1
                        if att['filename'] == self.pcid:
                            del res.data['attachments'][count]
                else:
                    res.data['attachments'] = []
                res.save()
                return ""
            except:
                abort(404)


    def account(self):
        self.search_options['predefined_filters']['owner'+config['FACET_FIELD']] = self.parts[0]
        acc = artemis.dao.Account.get(self.parts[0])

        if request.method == 'DELETE':
            if not auth.user.update(self.current_user,acc):
                abort(401)
            if acc: acc.delete()
            return ''
        elif request.method == 'POST':
            if not auth.user.update(self.current_user,acc):
                abort(401)
            info = request.json
            if info.get('_id',False):
                if info['_id'] != self.parts[0]:
                    acc = artemis.dao.Account.get(info['_id'])
                else:
                    info['api_key'] = acc.data['api_key']
                    info['created_date'] = acc.data['created_date']
                    info['collection'] = acc.data['collection']
                    info['owner'] = acc.data['collection']
            acc.data = info
            if 'password' in info and not info['password'].startswith('sha1'):
                acc.set_password(info['password'])
            acc.save()
            resp = make_response( json.dumps(acc.data, sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            if util.request_wants_json():
                if not auth.user.update(self.current_user,acc):
                    abort(401)
                resp = make_response( json.dumps(acc.data, sort_keys=True, indent=4) )
                resp.mimetype = "application/json"
                return resp
            else:
                admin = True if auth.user.update(self.current_user,acc) else False
                recordcount = artemis.dao.Record.query(terms={'owner':acc.id})['hits']['total']
                return render_template('account/view.html', 
                    current_user=self.current_user, 
                    search_options=json.dumps(self.search_options), 
                    record=json.dumps(acc.data), 
                    recordcount=recordcount,
                    admin=admin,
                    account=acc,
                    superuser=auth.user.is_super(self.current_user)
                )



