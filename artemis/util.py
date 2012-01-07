import re
import os
from unicodedata import normalize
from functools import wraps

def jsonp(f):
    """Wraps JSONified output for JSONP"""
    from flask import request, current_app
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f(*args,**kwargs).data) + ')'
            return current_app.response_class(content, mimetype='application/javascript')
        else:
            return f(*args, **kwargs)
    return decorated_function


# derived from http://flask.pocoo.org/snippets/5/ (public domain)
# changed delimiter to _ instead of - due to ES search problem on the -
_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
def slugify(text, delim=u'_'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


def idgen():
    if not os.path.exists('lastintid'):
        storedlastint = open('lastintid','w')
        storedlastint.write('0')
        storedlastint.close()
    while True:
        storedlastint = open('lastintid','r+')
        lastint = int(storedlastint.read())
        storedlastint.seek(0)
        storedlastint.truncate()
        thisint = lastint + 1
        storedlastint.write(str(thisint))
        storedlastint.close()
        nextid = str(hex(thisint))[2:]
        while len(nextid) < 5:
            nextid = '0' + nextid
        yield nextid
