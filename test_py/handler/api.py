#!/usr/bin/env python
# coding: utf-8

import logging
import re
import json

import tornado.web
import tornado.escape
from tornado.web import HTTPError

import hqby.auth
import hqby.image
import hqby.config
from model.msg import MessageModel
from model.dashboard import DashBoardModel

import model.user
from functools import wraps


def url_spec(*args, **kwargs):
    return [
        (r'/?(index)?', ApiHandler, kwargs),
    ]


def token_required(raise_error=True):
    """ 检测token修饰器
    """
    def wrap_func(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            token = self._get_token(raise_error)
            uid = token['_id'] if token else 'anonymous'
            user = model.user.get_user(user_id=uid) if token else None
            if not user and raise_error:
                raise HTTPError(404, 'Not Fount User')
            kwargs['user'] = user if user else None
            kwargs['uid'] = uid
            return func(self, *args, **kwargs)
        return wrapper
    return wrap_func
#
#
#def token_required(func):
#    """ 检测token修饰器
#    """
#    @functools.wraps(func)
#    def wrapper(self, *args, **kwargs):
#        token = self._get_token()
#        uid = token['_id']
#        user = model.user.get_user(user_id=uid)
#        if not user:
#            raise HTTPError(404, 'can not found this user')
#        kwargs['user'] = user
#        return func(self, *args, **kwargs)
#    return wrapper


class ApiHandler(tornado.web.RequestHandler):
    API_ROOT_URI = hqby.config.configs['api_base_url'] + '/'
    REL_ROOT_URI = API_ROOT_URI + 'relations/'
    IMG_ROOT_URI = hqby.config.configs['img_base_url'] + '/'
    CNT_TYPE_PREFIX = 'application/vnd.szhqby.dujing+'
    RE_CP = re.compile(r'^.*\[cp=([^\[]+)\]$')

    def _href(self, href):
        return self.API_ROOT_URI + href

    def _rel(self, rel):
        return self.REL_ROOT_URI + rel

    def _img(self, src):
        return self.IMG_ROOT_URI + src

    def _link(self, href, rel, **kargs):
        attr = dict(kargs)
        attr['href'] = self._href(href)
        attr['rel'] = self._rel(rel)
        attr['class'] = 'link'
        return attr

    def _ct(self, cntType):
        return self.CNT_TYPE_PREFIX + cntType

    @property
    def user_id(self):
        uid_uno = self.get_secure_cookie('token')
        if not uid_uno:
            return None
        uid, uno = uid_uno.split('|')
        return uid

    @property
    def user_no(self):
        uid_uno = self.get_secure_cookie('token')
        if not uid_uno:
            return None
        uid, uno = uid_uno.split('|')
        return uno

    def write(self, chunk):
        if 'error' not in self._headers:
            self.set_header('error', 0)
        #self.clear_header('test')
        if isinstance(chunk, dict) and self.settings.get('debug'):
            tornado.web.RequestHandler.write(self, json.dumps(chunk, indent=4))
        else:
            tornado.web.RequestHandler.write(self, chunk)
        if isinstance(chunk, dict):
            self.set_header('Content-Type', self._ct('json'))

    def get(self, *args, **kwargs):
        func = 'get_v' + self.get_argument('ver', '1')
        if hasattr(self, func):
            return getattr(self, func)(*args, **kwargs)
        ua = self.request.headers.get('User-Agent') or '[cp=hqby]'
        l = [
            self._link('homepage', 'first'),
            self._link('randompage', 'random'),
            self._link('auth/tqq', 'auth-tqq'),
            self._link('auth/sina', 'auth-sina'),
            self._link('auth/qq', 'auth-qq'),
            self._link('more', 'more'),
            #self._link('static/pkgs/%s/ver.js' % self._get_cp_from_ua(ua),'version'),
            {
                #'href': 'http://api.test.szhqby.com/static/pkgs/%s/th_ver.js' % self._get_cp_from_ua(ua),
                'href': 'http://api.szhqby.com/tonghua/version/ver.js',
                'class': 'link',
                'rel': 'http://api.test.szhqby.com/tonghua/relations/version'
            },
        ]
        self.write({'class': 'api_entry', 'links': l})
        self.set_header('Content-Type', self._ct('json'))
        self.set_header('Cache-Control', 'max-age=14400')

    def on_finish(self):
        """ 请求结束后的处理。
            如果返回的http状态码大于等于400，则记录更详细的请求日志。
        """
        #self.add_header('test2', 'hello')
        if not self.settings.get('debug'):
            return
        ct = self.request.headers.get('Content-Type')
        logging.error('request detail: %s %s %s (%s) %s %s',
                      self.get_status(), self.request.method,
                      self.request.uri, self.request.remote_ip,
                      self.request.headers, self.request.body[:200])

    def write_error(self, status_code, **kwargs):
        """异常状态码处理。
        """
        if 'exc_info' in kwargs:
            code = -1
            try:
                error = kwargs['exc_info'][1].log_message
                code = hqby.config.configs['error_codes'].get(error, -1)
            except (KeyError, AttributeError):
                pass
            self.set_header('error', code)
        if status_code == 403:
            self._write_buffer = []
            self.set_header('Content-Type', self._ct('json'))
            self.finish({
                'class': 'err',
                'err_code': status_code,
                'err_msg': kwargs['exc_info'][1].log_message,
                #'links': [self._link('auth', 'auth')],
            })
        elif status_code < 500:
            self._write_buffer = []
            self.set_header('Content-Type', self._ct('json'))
            self.finish({
                'class': 'err',
                'err_code': status_code,
                'err_msg': kwargs['exc_info'][1].log_message,
            })
        else:
            return tornado.web.RequestHandler.write_error(self, status_code, **kwargs)

    def _get_token(self, raise_error=True):
        """ 获取token。
            raise_error: 如果为真，没有token的时候抛出403异常，否则返回None
        """
        token = self.get_secure_cookie('token')
        if token:
            return hqby.auth.token_decode(token)
        elif raise_error:
            raise tornado.web.HTTPError(403, 'token-failed')
        else:
            return None

    def _choose_image(self, img, exp_width, key_list):
        """根据期望的宽度和key_list顺序从img中选择最合适的规格并返回。
            参考hqby.image.choose_image
        """
        if exp_width < 1:  # 小于1就是屏幕的宽度比例
            x_scr = self.request.headers.get('X-Screen', '320x480')
            exp_width = int(exp_width * int(x_scr.split('x')[0]))
        ret = hqby.image.choose_image(img, exp_width, key_list)
        if ret:
            ret['class'] = 'image'
        return ret

    def _get_cp_from_ua(self, ua):
        m = self.RE_CP.match(ua)
        if m:
            return m.group(1)
        else:
            return 'hqby'

    def get_form(self):
        """ 获取web端post表单数据, 返回字典
        """
        data = {}
        for k in self.request.arguments:
            v = self.get_arguments(k)
            data[k] = v[0] if len(v) == 1 else v
        return data
    #
    #@gen.engine
    #def _push_msg(self, from_uid, to_uid, title, msg, callback=None):
    #    if from_uid == to_uid:
    #        ret = None
    #    else:
    #        ret = yield gen.Task(MessageModel().push, to_uid, title, json.dumps(msg))
    #    if callback == self.finish:
    #        callback()
    #    elif callback:
    #        callback(ret)
    #
    #@gen.engine
    #def _notify_msg(self, from_uid, to_uid, description, callback=None):
    #    if from_uid == to_uid:
    #        ret = None
    #    else:
    #        portrait = self._choose_image(hqby.config.configs['msg_portrait'], 100, 'PORTRAIT')
    #        ret = yield gen.Task(DashBoardModel().notifyMsg, to_uid, portrait, description,
    #               self._link('msg/%s' % to_uid, 'message'))
    #    if callback == self.finish:
    #        callback()
    #    elif callback:
    #        callback(ret)
