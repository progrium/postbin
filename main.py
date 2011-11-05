import wsgiref.handlers
import datetime
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from models import Bin, Post, App
from google.appengine.api import datastore_errors
from google.appengine.api import memcache
from google.appengine.api import mail
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
                db.delete(posts.fetch(100))
                time.sleep(0.1)
        except DeadlineExceededError:
            self.response.clear()
            self.response.set_status(200)

class NewPostTask(webapp.RequestHandler):
    def post(self):
        app = App.instance()
        app.total_posts += 1
        app.put()
        ip = self.request.get('ip')
        bin = self.request.get('bin')
        size = int(self.request.get('size'))
        day = datetime.datetime.now().day
        
        daily_ip_key = 'usage-%s-%s' % (day, ip)
        daily_ip_usage = memcache.get(daily_ip_key) or 0
        memcache.set(daily_ip_key, int(daily_ip_usage)+size, time=24*3600)
        if daily_ip_usage > 500000000: # about 500MB
            mail.send_mail(sender="progrium@gmail.com", to="progrium@gmail.com",
                subject="PostBin user IP over quota", body=ip)
        
        daily_bin_key = 'usage-%s-%s' % (day, bin)
        daily_bin_usage = memcache.get(daily_bin_key) or 0
        memcache.set(daily_bin_key, int(daily_bin_usage)+size, time=24*3600)
        if daily_bin_usage > 10485760: # 10MB
            obj = Bin.get_by_name(bin)
            obj.delete()

if __name__ == '__main__':
    wsgiref.handlers.CGIHandler().run(webapp.WSGIApplication([
        ('/', MainHandler), 
        ('/stats', StatsHandler), 
        ('/tasks/cleanup', CleanupTask),
        ('/tasks/newpost', NewPostTask),
        ('/blacklist', BlacklistHandler)], debug=True))
