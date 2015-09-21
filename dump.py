import json, requests

dumpfile = 'dump.json'
db = 'artemisv2'
tgt = 'http://localhost:9200/' + db + '/'

recs = requests.get(tgt + '_search?q=*&size=100000')

fl = open(dumpfile,'w')
fl.write(json.dumps(recs.json(),indent=4))
fl.close()

