
from datetime import datetime
import cStringIO as StringIO
import json, string

from flask import Blueprint, request, send_file

import portality.models as models


blueprint = Blueprint('export', __name__)


@blueprint.route('/', methods=['GET','POST'])
def index():
    query = json.loads(request.values.get('source','{"query":{"match_all":{}}}'))

    keys = request.form.keys()
    keys = []
    records = []
    s = models.Record.query(q=query)
    for i in s.get('hits',{}).get('hits',[]): 
        records.append(i['_source'])
        for key in i['_source'].keys():
            if key not in keys and key not in ['history','attachments','last_access']:
                keys.append(key)

    # TODO: do some key ordering here if required
    #if 'x' in keys:
    #    keys.remove('x')
    #    keys = ['x'] + keys

    return download_csv(records,keys)

def fixify(strng):
    newstr = ''
    allowed = string.lowercase + string.uppercase + "@!%&*()_-+=;:~#./?[]{}, '" + '0123456789'
    for part in strng:
        if part == '\n':
            newstr += '  '
        elif part in allowed:
            newstr += part
    return newstr

def download_csv(recordlist,keys):
    # make a csv string of the records
    csvdata = StringIO.StringIO()
    firstrecord = True
    for record in recordlist:
        # for the first one, put the keys on the first line, otherwise just newline
        if firstrecord:
            fk = True
            for key in keys:
                if fk:
                    fk = False
                else:
                    csvdata.write(',')
                csvdata.write('"' + key + '"')
            csvdata.write('\n')
            firstrecord = False
        else:
            csvdata.write('\n')
        # and then add each record as a line with the keys as chosen by the user
        firstkey = True
        for key in keys:
            if firstkey:
                firstkey = False
            else:
                csvdata.write(',')
            if key in record.keys():
                if isinstance(record[key],bool):
                    if record[key]:
                        tidykey = "true"
                    else:
                        tidykey = "false"
                elif isinstance(record[key],list):
                    tidykey = ",".join(record[key])
                elif isinstance(record[key],dict):
                    tidykey = "OBJECT CANNOT BE EXPORTED"
                else:
                    tidykey = fixify(record[key].replace('"',"'"))
                csvdata.write('"' + tidykey + '"')
            else:
                csvdata.write('""')
    # dump to the browser as a csv attachment
    csvdata.seek(0)
    return send_file(
        csvdata, 
        mimetype='text/csv',
         attachment_filename="export_" + datetime.now().strftime("%d%m%Y%H%M") + ".csv",
        as_attachment=True
    )


