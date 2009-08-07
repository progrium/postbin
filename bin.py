import wsgiref.handlers
from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from models import Bin, Post
import urllib
import re

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
            type = 'atom' if feed else 'html'
            self.response.out.write(template.render('templates/bin.' + type, {'bin':bin, 'posts':posts, 'request':self.request}))

    def post(self):
        bin = self._get_bin(self.request.path)
        self._record_post(bin)
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
        post.body           = self.request.body
        post.query_string   = self.request.query_string
        if use_get:
            data_source = self.request.GET
        else:
            data_source = self.request.POST
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
