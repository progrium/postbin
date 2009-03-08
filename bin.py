import wsgiref.handlers
from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from models import Bin, Post

class BinHandler(webapp.RequestHandler):
    def get(self):
        bin = self._get_bin()
        posts = bin.post_set.order('-created').fetch(50)
        request = self.request
        self.response.out.write(template.render('templates/bin.html', {'bin':bin, 'posts':posts, 'request':request}))

    def post(self):
        bin = self._get_bin()
        post = Post(bin=bin, remote_addr=self.request.remote_addr)
        post.headers        = dict(self.request.headers)
        post.body           = self.request.body
        post.query_string   = self.request.query_string
        post.form_data      = dict(self.request.POST)
        post.put()
        self.redirect('/%s' % bin.name)
        
    def _get_bin(self):
        name = self.request.path[1:]
        bin = Bin.all().filter('name =', name).get()
        if bin:
            return bin
        else:
            self.redirect('/')


if __name__ == '__main__':
    wsgiref.handlers.CGIHandler().run(webapp.WSGIApplication([('/.*', BinHandler)], debug=True))
