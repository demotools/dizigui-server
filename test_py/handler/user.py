#!/usr/bin/env python
# coding: utf-8


from tornado.web import HTTPError
from tornado.escape import json_decode

import handler.api
import hqby.item
import hqby.user
import hqby.tag
from hqby.config import configs

import model.item
import tornado.ioloop
import tornado.web

def url_spec(**kwargs):
    return [
        (r'/user/edit/?(?P<uid>[a-zA-Z0-9\-_]{8})?/?(?P<last_row>\d+)?/?(?P<count>\d+)?', UserHandler, kwargs),
       # (r'/user2/?(?P<uid2>[a-zA-Z0-9\-_]{8})?/?(?P<last_row>\d+)?/?(?P<count>\d+)?', User2Handler, kwargs),
       # (r'/user/top/?(?P<num>\d{1,2})?/?', TopUsersHandler, kwargs),
        #(r'/token/test', TokenHandler, kwargs),
       # (r'/user/(?P<uid>[\w\-_]{8})/works/?$', UserWorksHandler, kwargs),
       # (r'/user/(?P<uid>[\w\-_]{8})/(?P<mode>(?:items)|(?:books))/?(?P<page>\d+)?/?', UserPageHandler, kwargs),
    ]

class UserHandler2(tornado.web.RequestHandler):
    def get(self, **kwargs):
        self.write("hello my user!")




class UserHandler(handler.api.ApiHandler):
    def get(self, **kwargs):
        token = self._get_token(False)
        actor_uid = str(kwargs.get('uid'))  # change unicode to str
        visit_uid = token['_id'] if token else 'anonymous'
        visit_uid = str(visit_uid)
        last_row = int(kwargs.get('last_row') or 0)
        count = int(kwargs.get('count') or 10)
        user = hqby.user.get_user_info(uid=actor_uid)
        if not user:
            raise HTTPError(404, 'can not found this user')
        user['edit'] = 1 if actor_uid == visit_uid else 0
        #user['publish_total'] = hqby.user. \
           # get_publish_total(actor_uid=actor_uid)
       # user['actions'] = hqby.user.get_user_action(self, actor_uid=actor_uid, visit_uid=visit_uid, last_row=last_row, count=count)
        user['links'] = self._links(actor_uid, last_row, count)
        self.write(user)
        #self.write("usr_id = %s"%user['_id'])
        self.set_status(200)

    def put(self, **kwargs):
        token = self._get_token()
        uid = token['_id']
        #self.write("token uid = %s"%uid)
        #return
        url_uid = str(kwargs.get('uid'))  # change unicode to str
        if uid != url_uid:
            raise HTTPError(403, 'user update error')
        user = hqby.user.get_user_info(uid=uid)
        if not user:
            raise HTTPError(404, 'can not found this user')
        params = json_decode(self.request.body)
        if not params.get('portrait_id', False):
            portrait = user['portrait']
        else:
            portrait = hqby.image.get_temp_image(params['portrait_id'])
            mid_path = '%s/%s/%s' % ('portrait', hqby.image.id_to_subdir(user['user_no']), user['_id'])
            info = hqby.image.move_temp_image(
                portrait,
                configs['img_base_path'],
                configs['img_base_url'],
                mid_path
            )
            portrait = info['100x100']['src']
        age = params.get('age', user['age'])
        try:
            # 检测age字段的合法性
            assert int(age) in range(0, 100)
        except (AssertionError, ValueError, TypeError):
            age = user['age']
        if not params.get('nick', False):
            params['nick'] = user['nick']
        if not params.get('phone', False):
            params['phone'] = user['phone']
        if not params.get('email', False):
            params['email'] = user['email']
        user = hqby.user.update_user(
            user_id=uid,
            portrait=portrait,
            nick=params['nick'],
            age=age,
            phone = params['phone'],
            email = params['email']
            )
        user = hqby.user.get_user_info(uid=uid, user=user)
        self.write(user)
        self.set_status(200)

    post = put

    def _links(self, uid, last_row=0, count=10):
        return [
            self._link('user/%s' % uid, 'first'),
            self._link('user/%s/%s/%s' % (uid, last_row + count, count), 'next'),
        ]
