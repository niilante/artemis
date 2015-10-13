import json, csv, time

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models

blueprint = Blueprint('imports', __name__)


@blueprint.route('/', methods=['POST'])
def index(model=None, deleteall=False):
    if current_user.is_anonymous() or not current_user.is_super:
        abort(401)
        
    if request.method == 'POST':
#        try:
        records = []
        if "csv" in request.files.get('upfile').filename:
            upfile = request.files.get('upfile')
            reader = csv.DictReader( upfile )
            records = [ row for row in reader ]
            sourcetype = "csv"
        elif "json" in request.files.get('upfile').filename:
            upfile = request.files.get('upfile')
            records = json.load(upfile)
            sourcetype = "json"

        if model is None:
            #model = request.form.get('model',None)
            model = 'record'
            if model is None:
                flash("You must specify what sort of records you are trying to upload.")
                return render_template('leaps/admin/import.html')

        klass = getattr(models, model[0].capitalize() + model[1:] )

        if (deleteall or request.values.get('deleteall',False)):
            klass.delete_all()

        if model.lower() == 'record':
            total = len(records)
            chunk = 500
            pos = 0
            while pos < total:
                if pos + chunk < total:
                    to = pos + chunk
                else:
                    to = total
                recs = []
                for rec in records[pos:to]:
                    if 'id' in rec and len(rec['id']) > 1:
                        old = models.Record().pull(rec['id'])
                        if old is None: old = models.Record()
                        for k in rec.keys():
                            old.data[k] = rec[k]
                        recs.append(old.data)
                    else:
                        rid = models.Record.makeid()
                        print "rid ", rid
                        rec['id'] = rid
                        recs.append(rec)
                klass().bulk(recs)
                pos += chunk
                time.sleep(1)

        else:
            klass().bulk(records)
        
        time.sleep(1)
        checklen = klass.query(q="*")['hits']['total']
        
        flash(str(len(records)) + " records have been imported, and there are now " + str(checklen) + " records.")
        return redirect('search')

#        except:
#            flash("There was an error importing your records. Please try again.")
#            return render_template('leaps/admin/import.html', model=model)
