import tornado.ioloop
import tornado.web
import MySQLdb



def url_spec(**kwargs):
    return [
            (r'/gaga', MainHandler),
            ]

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, loard gaga!")


