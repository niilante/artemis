import json, requests, uuid

dumpfile = 'dump.json'
db = 'artemisv2'
tgt = 'http://localhost:9200/' + db + '/'

fls = json.load(open(dumpfile,'r'))

types = {}

for rc in fls['hits']['hits']:
    if rc['_index'] == db:
        rec = rc['_source']
        if 'updated_date' in rec: rec['updated_date'] = rec['updated_date'].replace(':','')
        if 'created_date' in rec: rec['created_date'] = rec['created_date'].replace(':','')
        if rc['_type'] == 'record' and 'type' not in rec: rec['type'] = 'part'
        if rc['_type'] not in types.keys(): types[rc['_type']] = 0
        types[rc['_type']] += 1
        if rc['_type'] == 'curated':
            for val in rec.get('values',[]):
                trec = {
                    'type': rec['id'],
                    'value': val,
                    'id': uuid.uuid4().hex
                }
                r = requests.post(tgt + rc['_type'] + '/' + trec['id'], data=json.dumps(trec))
        else:
            r = requests.post(tgt + rc['_type'] + '/' + rc['_id'], data=json.dumps(rec))
        if r.status_code != 201: print r.status_code, r.text
    
for k in types.keys():
    print 'loaded', types[k], k
