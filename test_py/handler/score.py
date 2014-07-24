#!/usr/bin/env python
# coding: utf-8

from tornado.web import HTTPError

import handler.api
import hqby.item
import hqby.user
import model.action
from hqby.config import configs
import hqby.db
import time


def url_spec(**kwargs):
    return [
        (r'/score/?(?P<uid>[a-zA-Z0-9\-_]{8})?', ScoreHandler, kwargs),
        #(r'/score/(?P<mode>(?:current)|(?:record))/?(?P<page>\d+)?/?', UserScoreHandler, kwargs),
    ]

class ScoreHandler(handler.api.ApiHandler):
    def get(self, **kwargs):
        token = self._get_token()
        score_uid = kwargs.get('uid')
        visit_uid = token['_id']
        self.write("score_uid = %s and visit_uid = %s"%(score_uid,visit_uid))
        self.set_status(200)

    def post(self, **kwargs):
        token = self._get_token()
        score_uid = kwargs.get('uid')
        visit_uid = token['_id']
        if score_uid != visit_uid:
            raise HTTPError(404, 'can not found this user')
        #params = json_decode(self.request.body)
        a = int(self.get_argument("words_num"))
        b = int(self.get_argument("read_times"))
        c = int(self.get_argument("learn_len"))
        dbc = hqby.db.get_conn('test2')
        user_score = dbc.get("SELECT * FROM score WHERE user_id = %s limit 1", score_uid)
        if user_score:
            a = user_score['words_num'] + a
            b = user_score['read_times'] + b
            c = user_score['learn_len'] + c
            sql = "UPDATE score SET words_num=%s, read_times=%s, Learn_len=%s WHERE user_id=%s"
            params = [a, b, c, score_uid]
            dbc.execute(sql, *params)
        else:
            for i in range(3):
                try:
                    #self.write("a = %d,b = %d,c = %d"%(a,b,c))
                    dbc.execute(
                        "INSERT INTO score (user_id, words_num, read_times, learn_len)" "VALUES (%s,%s,%s,%s)",
                        score_uid, a, b, c)
                    break
                except Exception as ex:
                    raise ex
                    break
        #d = dbc.get("SELECT * FROM score WHERE user_id = %s limit 1", score_uid)
        #del d['updated']
        d = {}
        d['user_id'] = score_uid
        d['words_num'] = a
        d['read_times'] = b
        d['learn_len'] = c
        self.write(d)
        self.set_status(200)

    def _links(self, uid, last_row=0, count=10):
        return [
            self._link('score/%s' % uid, 'first'),
            ]

