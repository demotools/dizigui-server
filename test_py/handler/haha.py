import tornado.ioloop
import tornado.web
import MySQLdb



def url_spec(**kwargs):
    return  [
            (r'/haha/?([\w\-]+)?', MainHandler),
            ]

class MainHandler(tornado.web.RequestHandler):
    def get(self):
       # user_id =str(kwargs.get('uid'))
       # self.write("Hello, loard %s!"%user_id)
        self.write("great caesar!!!")


