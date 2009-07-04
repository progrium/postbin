import time, yaml
from google.appengine.ext import db
from google.appengine.api import datastore_types
from django.utils import simplejson

def baseN(num,b,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])
    
class ObjectProperty(db.Property):
    data_type = datastore_types.Text
    def get_value_for_datastore(self, model_instance):
        value = super(ObjectProperty, self).get_value_for_datastore(model_instance)
        return db.Text(self._deflate(value))
    def validate(self, value):
        return self._inflate(value)
    def make_value_from_datastore(self, value):
        return self._inflate(value)
    def _inflate(self, value):
        if value is None:
            return {}
        if isinstance(value, basestring):
            return simplejson.loads(value)
        return value
    def _deflate(self, value):
        return simplejson.dumps(value)

class Bin(db.Model):
    name = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        kwargs['name'] = kwargs.get('name', baseN(abs(hash(time.time())), 36))
        super(Bin, self).__init__(*args, **kwargs)
        
        
class Post(db.Model):
    bin = db.ReferenceProperty(Bin)
    created = db.DateTimeProperty(auto_now_add=True)
    remote_addr = db.StringProperty(required=True)
    headers = ObjectProperty()
    query_string = db.StringProperty()
    form_data = ObjectProperty()
    body = db.TextProperty()
    
    def id(self):
        return baseN(abs(hash(self.created)), 36)[0:6]

    def __iter__(self):
        out = []
        if self.form_data:
            if hasattr(self.form_data, 'items'):
                items = self.form_data.items()
            else:
                items = self.form_data
            for k,v in items:
                try:
                    outval = simplejson.dumps(simplejson.loads(v), sort_keys=True, indent=2)
                except ValueError:
                    outval = v
                out.append((k, outval))
        else:
            out = (('body', self.body),)

        return iter(sorted(out))

    def __str__(self):
        return '\n'.join("%s = %s" % (k,v) for k,v in self)
