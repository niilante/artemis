import json, requests

dumpfile = 'dump.json'
db = 'artemisv2'
tgt = 'http://localhost:9200/' + db + '/'

fls = json.load(open(dumpfile,'r'))

types = {}

for rc in fls['hits']['hits']:
    if rc['_index'] == db:
        rec = rc['_source']
        if rc['_type'] not in types.keys(): types[rc['_type']] = 0
        types[rc['_type']] += 1
        requests.post(tgt + rc['_type'] + '/' + rc['_id'], data=json.dumps(rec))
    
for k in types.keys():
    print 'loaded', types[k], k