from urllib import urlopen, urlencode
import md5
import os, re
from unicodedata import normalize
from functools import wraps
from flask import request, current_app


def jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f(*args,**kwargs).data) + ')'
            return current_app.response_class(content, mimetype='application/javascript')
        else:
            return f(*args, **kwargs)
    return decorated_function


# derived from http://flask.pocoo.org/snippets/45/ (pd) and customised
def request_wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    if best == 'application/json' and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']:
        best = True
    else:
        best = False
    if request.values.get('format','').lower() == 'json' or request.path.endswith(".json"):
        best = True
    return best
        

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


# generate an ID as per artemis specification
def idgen(idtype='id'):
    if idtype == 'id':
        filename = 'lastidid'
    else:
        filename = 'lastidbatch'
    if not os.path.exists(filename):
        storedlastid = open(filename,'w')
        storedlastid.write('00000')
        storedlastid.close()

    allowed = ['0','1','2','3','4','5','6','7','8','9','A','C','E','F','G','H','J','K','L','M','N','P','R','T','V','W','X','Y']

    while True:
        storedlastid = open(filename,'r+')
        lastid = storedlastid.read()
        storedlastid.seek(0)
        storedlastid.truncate()

        tripover = False
        thisid = ''
        for index, letter in enumerate(reversed(lastid)):
            next = ''
            if index == 0 or tripover:
                tripover = False
                position = ''
                for pos, item in enumerate(allowed):
                    if item == letter:
                        position = pos
                if position == len(allowed) - 1:
                    next = allowed[0]
                    tripover = True
                else:
                    next = allowed[position + 1]
                thisid = str(next) + str(thisid)
            else:
                thisid = str(letter) + str(thisid)
            
        while len(thisid) < 5:
            thisid = '0' + str(thisid)

        storedlastid.write(str(thisid))
        storedlastid.close()

        yield thisid


# get gravatar for email address
def get_gravatar(email, size=None, default=None, border=None):
    email = email.lower().strip()
    hash = md5.md5(email).hexdigest()
    args = {'gravatar_id':hash}
    if size and 1 <= int(size) <= 512:
        args['size'] = size
    if default: args['default'] = default
    if border: args['border'] = border

    url = 'http://www.gravatar.com/avatar.php?' + urlencode(args)

    response = urlopen(url)
    image = response.read()
    response.close()

    return image

