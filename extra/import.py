import httplib
import csv
import json

es_url = "localhost:9200"
es_path = "/artemis/record"

f = open('pms_parts','r')
reader = csv.DictReader(f, delimiter = '\t', quotechar = '"')

for row in reader:
    row['type'] = "part"
    c =  httplib.HTTPConnection(es_url)
    c.request('POST', es_path + '/' + row['id'], json.dumps(row))
    result = c.getresponse()
    print result.status, result.reason
    
f.close()

