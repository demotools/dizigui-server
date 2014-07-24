#!/usr/bin/env python
# coding: utf-8

from tornado.web import HTTPError
from tornado.escape import json_decode

import handler.api
import hqby.user
import model.user

def url_spec(**kwargs):
    return [
        (r'/bdinfo/?', BDinfoHandler),
    ]


class BDinfoHandler(handler.api.ApiHandler):

    def post(self, *args, **kwargs):
        token = self._get_token()
        uid = token['_id']
        if not(model.user.get_user(user_id=uid)):
            raise HTTPError(404, 'can not found this user')
        params = json_decode(self.request.body)
        params['uid'] = uid
        push = hqby.user.get_bind_info(uid)
        if push:
            push = hqby.user.update_bdinfo(params)
        else:
            push = hqby.user.bind_bdinfo(params)
        bd_info = {}
        if push:
            bd_info['msg'] = 'push info saved'
            bd_info['status'] = 1
        else:
            bd_info['msg'] = 'update err'
            bd_info['status'] = 0
        self.write(bd_info)
        self.set_status(201)
    
    def get(self, *args, **kwargs):
        token = self._get_token()
        uid = token['_id']
        if not(model.user.get_user(user_id=uid)):
            raise HTTPError(404, 'can not found this user')
        bd_info = {}
        #bd_info = hqby.user.get_bind_info(uid)
        bd_info.update(hqby.user.get_bind_info(uid))
        if not bd_info:
            bd_info['status'] = 0
            bd_info['msg'] = 'no record'
        else:
            bd_info['status'] = 1
        self.write(bd_info)
        self.set_status(200)


class BindHandler(handler.api.ApiHandler):

    def post(self, *args, **kwargs):
        token = self._get_token()
        uid = token['_id']
        mode = kwargs.get('mode', 'baidu')
        if not(model.user.get_user(user_id=uid)):
            raise HTTPError(404, 'can not found this user')
        params = json_decode(self.request.body)
        bind_info = dict()
        bind_info['_id'] = uid
        if mode == 'ios':
            bind_info['iphone_id'] = params['iphone_id']
            hqby.user.clear_iosinfo(bind_info)  # 清理掉已经被使用的iphone_id<保证唯一性>
            hqby.user.bind_iosinfo(uid, bind_info)
        elif mode == 'baidu':
            bind_info['bd_uid'] = params['bd_uid']
            bind_info['bd_cid'] = params['bd_cid']
            hqby.user.check_bdinfo(bind_info)
            hqby.user.bind_bdinfo(uid, bind_info)
        else:
            raise HTTPError(404, 'error request')
        self.write(bind_info)
        self.set_status(201)
    
    def get(self, *args, **kwargs):
        token = self._get_token()
        uid = token['_id']
        mode = kwargs.get('mode', 'baidu')
        if not(model.user.get_user(user_id=uid)):
            raise HTTPError(404, 'can not found this user')
        bind_info = dict()
        bind_info['_id'] = uid
        info = hqby.user.get_bind_info(uid) or dict.fromkeys(['iphone_id', 'bd_uid', 'bd_cid'], '')
        bind_info.update(info)
        if mode == 'ios':
            del bind_info['bd_uid']
            del bind_info['bd_cid']
        elif mode == 'baidu':
            del bind_info['iphone_id']
        else:
            raise HTTPError(404, 'error request')
        self.write(bind_info)
        self.set_status(200)
