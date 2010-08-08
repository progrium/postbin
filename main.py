import wsgiref.handlers
import datetime
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from models import Bin, Post, App
from google.appengine.api import datastore_errors
from google.appengine.runtime import DeadlineExceededError
import time, yaml

class MainHandler(webapp.RequestHandler):
    def get(self):
        app = App.instance()
        self.response.out.write(template.render('templates/main.html', locals()))

    def post(self):
        bin = Bin()
        bin.put()
        self.redirect('/%s' % bin.name)

class StatsHandler(webapp.RequestHandler):
    def get(self):
        posts = Post.all().order('-size').fetch(20)
        try:
            current_post = None
            for post in posts:
                current_post = post
                bin = post.bin
            self.response.out.write(template.render('templates/stats.html', locals()))
        except datastore_errors.Error, e:
            if e.args[0] == "ReferenceProperty failed to be resolved":
                current_post.delete()
                self.redirect('/stats')

class BlacklistHandler(webapp.RequestHandler):
    def get(self):
        blacklist = yaml.load(open('dos.yaml').read())
        blacklist = [(b['subnet'], b['description'].split(' - ')) for b in blacklist['blacklist']]
        self.response.out.write(template.render('templates/blacklist.html', locals()))

class CleanupTask(webapp.RequestHandler):
    def get(self):
        posts = Post.all().filter('created <', datetime.datetime.now() - datetime.timedelta(days=90))
        assert posts.count()
        try:
            while True:
                db.delete(posts.fetch(500))
                time.sleep(0.1)
        except DeadlineExceededError:
            self.response.clear()
            self.response.set_status(200)

class NewPostTask(webapp.RequestHandler):
    def post(self):
        app = App.instance()
        app.total_posts += 1
        app.put()

if __name__ == '__main__':
    wsgiref.handlers.CGIHandler().run(webapp.WSGIApplication([
        ('/', MainHandler), 
        ('/stats', StatsHandler), 
        ('/tasks/cleanup', CleanupTask),
        ('/tasks/newpost', NewPostTask),
        ('/blacklist', BlacklistHandler)], debug=True))
