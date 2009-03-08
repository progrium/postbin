import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from models import Bin

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render('templates/main.html', {}))

    def post(self):
        bin = Bin()
        bin.put()
        self.redirect('/%s' % bin.name)

if __name__ == '__main__':
    wsgiref.handlers.CGIHandler().run(webapp.WSGIApplication([('/', MainHandler)], debug=True))
