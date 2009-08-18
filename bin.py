import wsgiref.handlers
from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from models import Bin, Post
import urllib
import re
import hashlib
from cgi import FieldStorage

class BinHandler(webapp.RequestHandler):
    def get(self):
        path = self.request.path
        if path[-1] == '/':
            self.redirect(path[:-1])
        path, feed = re.subn(r'^(.+)\/feed$', r'\1', path)
        bin = self._get_bin(path)
        if self.request.query_string:
            self._record_post(bin, True)
            self.redirect('/%s' % bin.name)
        else:
            posts = bin.post_set.order('-created').fetch(50)
            self.response.out.write(template.render('templates/bin.%s' % ('atom' if feed else 'html'), 
                {'bin':bin, 'posts':posts, 'request':self.request}))

    def post(self):
        bin = self._get_bin(self.request.path)
        self._record_post(bin)
        # TODO: This should maybe be a header thing
        if 'http://' in self.request.query_string:
            urlfetch.fetch(url=self.request.query_string.replace('http://', 'http://hookah.webhooks.org/'),
                            payload=urllib.urlencode(self.request.POST.items()), method='POST')
        self.redirect('/%s' % bin.name)
    
    def head(self):
        bin = self._get_bin(self.request.path)
        if self.request.query_string:
            self._record_post(bin, True)
        else:
            self._record_post(bin)

    def _record_post(self, bin, use_get=False):
        post = Post(bin=bin, remote_addr=self.request.remote_addr)
        post.headers        = dict(self.request.headers)
        try:
            post.body           = self.request.body
        except UnicodeDecodeError:
            #post.body_binary    = self.request.body
            pass
        post.query_string   = self.request.query_string
        data_source = self.request.GET if use_get else self.request.POST
        for k in data_source.keys():
            if isinstance(data_source[k], FieldStorage):
                file_body = data_source[k].file.read()
                data_source[k] = {
                    'file_name': data_source[k].filename,
                    'file_extension': data_source[k].filename.split('.')[-1],
                    'file_digest': hashlib.md5(file_body).hexdigest(),
                    'file_size': round(len(file_body) / 1024.0, 1),
                }
        post.form_data      = [[k,v] for k,v in data_source.items()]
        post.put()

    def _get_bin(self, path):
        name = path.replace('/', '')
        bin = Bin.all().filter('name =', name).get()
        if bin:
            return bin
        else:
            self.redirect('/')


if __name__ == '__main__':
    wsgiref.handlers.CGIHandler().run(webapp.WSGIApplication([('/.*', BinHandler)], debug=True))
