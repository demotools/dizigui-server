#!/usr/bin/env python

import os.path
import sys
import os

os.environ['PYTHON_EGG_CACHE'] = '/tmp'

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib', 'poster-0.8.1-py2.6.egg'))

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

import hqby.db
import hqby.cache
from hqby.config import configs
from handler import auth

class Application(tornado.web.Application):
    def __init__(self):
        uri_prefix = configs['api_base_url']
        db = hqby.db.get_conn(configs['db_name'])
        handlers = []
        handler_mods = [
            'haha',
            'gaga',
            'user',
            'image',
            'audio',
            'score',
            'topic',
            'like',
            'comment',
            'message',
            'bdinfo',
            'version',
                    ]
        for i in handler_mods:
            m = __import__('handler.' + i, fromlist=['url_spec'])
            handlers.extend(m.url_spec())
        handlers.extend(
            auth.url_spec(db=db, uri_prefix=uri_prefix))

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            cookie_secret=configs['cookie_secret'],
            autoescape=None,
            debug=configs['debug'],
            sina_client_id=configs['sina_client_id'],
            sina_client_secret=configs['sina_client_secret'],
            tqq_client_id=configs['tqq_client_id'],
            tqq_client_secret=configs['tqq_client_secret'],
            qq_client_id=configs['qq_client_id'],
            qq_client_secret=configs['qq_client_secret'],
        )
        tornado.web.Application.__init__(self, handlers, **settings)

def main():
    http_server = tornado.httpserver.HTTPServer(Application(), xheaders=True)
    http_server.listen(configs['port'])
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
