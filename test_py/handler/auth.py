#!/usr/bin/env python
# coding: utf-8

import json
import hashlib
import base64
import logging
import time
import copy

from tornado.web import HTTPError, RequestHandler, asynchronous
import torndb
from tornado.escape import json_encode
from tornado.util import ObjectDict
from tornado import gen

from hqby import pk
from hqby.config import configs
from model.share import ShareModel, ShareMixin
from oauth import SinaOAuth2Mixin, TQqOAuth2Mixin, QqOAuth2Mixin
import model.action
import hqby.user
from hqby.base import BaseHandler



def url_spec(*args, **kwargs):
    return [
        #(r'/auth/sina', SinaLoginHandler, kwargs),
        #(r'/auth/tqq', TQqLoginHandler, kwargs),
        #(r'/auth/qq', QqLoginHandler, kwargs),
        #(r'/auth/qqweb', QqWebLoginHandler, kwargs),
        #(r'/auth/visit', VisitorLoginHandler, kwargs),
        #(r'/auth/test',testHandler),
        (r'/auth/third/?', ThirdAuthHandler, kwargs),
    ]

#class HqUserHandler(RequestHandler):
#
#    def post(self, **kwargs):
#        mode = kwargs.get('mode')
#        if not mode or mode not in ['register', 'login']:
#            raise HTTPError(404, 'page not found')
#        return getattr(self, '_'+mode)(**kwargs)
#
#    def _register(self, **kwargs):
#        pass
#
#    def _login(self, **kwargs):
#        pass


class BaseRequestHandler(RequestHandler):
    EXPIRES_DAYS = 30

    def write(self, chunk):
        if isinstance(chunk, dict) and self.settings.get('debug'):
            RequestHandler.write(self, json.dumps(chunk, indent=4))
        else:
            RequestHandler.write(self, chunk)

    def on_finish(self):
        """请求结束后的处理。
            如果返回的http状态码大于等于400，则记录更详细的请求日志。
        """
        if not self.settings.get('debug'):
            return
        ct = self.request.headers.get('Content-Type')
        body = self.request.body if ct and ct[:9] != 'multipart' \
                   else self.request.body[:64] + '...'
        logging.error('request detail: %s %s %s (%s) %s',
                      self.get_status(), self.request.method,
                      self.request.uri, self.request.remote_ip,
                      self.request.headers)

    def _add_links(self, d):
        d['links'] = [
            self._link('homepage', 'first'),
            self._link('randompage', 'random'),
            self._link('score/%s' % d['_id'], 'score'),
            self._link('auth/%s' % d['_id'], 'auth'),
            self._link('user/%s' % d['_id'], 'user'),
            self._link('popularize', 'popularize'), ]

    def _link(self, href, rel, **kwargs):
        d = dict(href='%s/%s' % (self.uri_prefix, href), rel='%s/relations/%s' % (self.uri_prefix, rel))
        d['class'] = 'link'
        d.update(kwargs)
        return d

    def _gen_token(self, uid, uno):
        return self.create_signed_value('token', '%s|%s' % (uid, uno))

    def _find_user(self, account):
        rs = self.db.query("SELECT * FROM users WHERE account=%s", account)
        if not rs:
            return None
        r = rs[0]
        d = copy.deepcopy(r)
        d = ObjectDict(d)
        d._id = d.id
        del d['id']
        del d['auth_time']
        del d['ins_time']
        d.user_no = str(d.user_no)
        d.token = self._gen_token(d._id, d.user_no)
        if d.ext_data:
            d.ext_data = json.loads(d.ext_data)
        d['class'] = 'user'  # TODO class是python关键字，不建议用对象属性的方法赋值
        return d

    def _update_portrait(self, account, portrait):
        self.db.execute("UPDATE users SET portrait=%s WHERE account=%s", portrait, account)

    def _output(self, user):
        d = copy.deepcopy(user)
        token = self._gen_token(d._id, d.user_no)
        d.ret_code = 0
        d.token = token
        d.user_no = str(d.user_no)
        #d.ins_time = str(d.ins_time)
        self.set_status(201)
        self.clear_cookie('token')
        self.set_cookie(
            'token', d.token, expires_days=BaseRequestHandler.EXPIRES_DAYS)
        #self._add_links(d)
        d['links'] = [
            self._link('score/%s'% d._id, 'score'),  # 成绩页
            self._link('user/edit/%s' % d._id, 'edit')  # 修改资料
        ]
        self.write(d)
        self.set_header('Content-Type', 'application/vnd.szhqby.dujing+json')
        self.set_header('Location', '%s/user/%s' % (self.uri_prefix, d._id))
        self.finish()

    def write_error(self, status_code, **kwargs):
        """异常状态码处理。
        """
        if status_code < 500:
            self._write_buffer = []
            self.set_header('Content-Type', 'application/json')
            self.finish({
                'class': 'err',
                'err_code': status_code,
                'err_msg': str(kwargs['exc_info'][1]),
            })
        else:
            return RequestHandler.write_error(self, status_code, **kwargs)


class RegisterMixin(object):
    def _try_gen(self, user):
        ret = copy.deepcopy(user)
        for i in range(3):
            _id = self._gen_id()
            try:
                ret.user_no = self.db.execute_lastrowid(
                    "INSERT INTO users (id, account, passwd, auth_type, bind_sina, bind_tqq, bind_qq, portrait, nick,last_login_ip,\
                    auth_time)"
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, sysdate())",
                    _id, ret.account,
                    self._sha1(ret.account.lower(), ret.passwd),
                    ret.auth_type, ret.bind_sina,
                    ret.bind_tqq, ret.bind_qq,
                    ret.portrait, ret.nick ,ret.last_login_ip
                )
                ret.user_no = str(ret.user_no)
                ret._id = _id
                ret.token = self._gen_token(ret._id, ret.user_no)
                ret.ext_data = {}
                ret['class'] = 'user'
                break
            except torndb.IntegrityError as e:
                if e[1].find("for key 'account'") >= 0:
                    return 'dup'
                else:
                    logging.exception(
                        'insert error id=%s account=%s', ret._id, ret.account)
        return ret

    def _gen_id(self, n=8):
        """
            产生随机化的用户id, 增加检测重复的机制
        """
        uid = pk.gen_id(n)
        while hqby.user.get_user_info(uid):
            logging.warning('ha has gen the same id!!!!')
            uid = pk.gen_id(n)
        return uid

    def _sha1(self, *arg):
        return hashlib.sha1(''.join(arg)).hexdigest()

    @gen.engine
    def _on_bind(self, uid, user, auth_type):
        if not user:
            raise HTTPError(403)
        sm = ShareModel()
        t = time.time() + int(user.get('access_token_expires'))
        ret = yield gen.Task(  # 记录用户的三方帐号信息到缓存中
            sm.update,
            uid,
            auth_type,
            open_id=user.get('open_id'),
            access_token=user.get('access_token'),
            access_token_expires=t,
        )

class ThirdAuthHandler(BaseHandler,BaseRequestHandler, RegisterMixin):
    def initialize(self, db, uri_prefix):
        self.db = db
        self.uri_prefix = uri_prefix
    def get(self):
        self.write("Hello, test a login!")

    """ 三方登录, 客户端验证
    """

    def post(self):
        """ 传入参数:
            auth_type, open_id, nick, access_token, portrait, access_token_expires
        """
        data = self.phone_data(required=('auth_type', 'open_id', 'access_token', 'nick'))
        portrait = data.portrait or configs['dujing_default_portrait']
        device = data.device or ''  # 登录设备名称, 字符串
        if data.auth_type not in hqby.base.auth_types:
            raise HTTPError(400, '[Bad Request]: bad auth type')
        data.ip = self.ip
        account = data.auth_type + '@' + hashlib.md5(data.open_id).hexdigest()
        nick = data.nick or '佚名'
        auth_type = data.auth_type
        binds = {'sina':0, 'tqq':0, 'qq':0}
        binds[auth_type] = 1
        u = self._find_user(account)
        if not u:
            u = ObjectDict(
                account=account, passwd=self._gen_id(20),
                auth_type=auth_type, user_type=0,
                bind_sina=binds['sina'], bind_tqq=binds['tqq'], bind_qq=binds['qq'],
                portrait=portrait, nick=nick,last_login_ip=data.ip,
                baidu_uid='', baidu_cid=''
            )
            u = self._try_gen(u)
            if not u:
                raise HTTPError(500)
        self._on_bind(u._id, data, auth_type)
        self._output(u)  # 返回用户, 写入cookie finish request

class SinaLoginHandler(BaseRequestHandler, SinaOAuth2Mixin, RegisterMixin):
    def initialize(self, db, uri_prefix):
        self.db = db
        self.uri_prefix = uri_prefix

    @asynchronous
    def get(self):
        redirect_uri = self.uri_prefix + '/auth/sina'  # 回调url
        if self.get_argument("code", False):  # 回调后会带上code
            self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.settings["sina_client_id"],
                client_secret=self.settings["sina_client_secret"],
                code=self.get_argument("code"),
                callback=self.async_callback(self._on_login)
            )
            return

        if self.settings.get('debug') and self.get_argument('test', '') == 'henry':
            user = ObjectDict(
                open_id='1234',
                nick='henry',
                portrait=configs['tonghua_default_portrait'],
                access_token='atkn',
                access_token_expires=time.time()+3600)
            self._on_login(user)
            return

        self.authorize_redirect(  # 初次请求, 直接跳转, 进行验证
            redirect_uri=redirect_uri,
            client_id=self.settings["sina_client_id"],
            extra_params={
                "response_type": "code",
                "display": "mobile",
            },
        )

    def _on_login(self, user):
        if not user:
            raise HTTPError(403)
        account = 'sina@' + hashlib.md5(user['open_id']).hexdigest()
        nick = user['nick'] or '佚名'
        auth_type = 'sina'
        (bind_sina, bind_tqq, bind_qq) = (1, 0, 0)
        portrait = user['portrait'] or configs['tonghua_default_portrait']
        u = self._find_user(account)
        if not u:
            u = ObjectDict(
                account=account, passwd=self._gen_id(20),
                auth_type=auth_type, user_type=0,
                bind_sina=bind_sina, bind_tqq=bind_tqq, bind_qq = bind_qq,
                portrait=portrait, nick=nick,
                baidu_uid='', baidu_cid=''
            )
            u = self._try_gen(u)
            if not u:
                raise HTTPError(500)
        self._on_bind(u._id, user, auth_type)  # 记录三方信息到缓存
        logging.info('bind sina: %s %s', u._id, user)
        # 记录注册行为, 初始化积分记录
       # had_user_action = model.action.find_user_action(score_uid=u._id)
       # if not had_user_action:
        #    model.action.register(actor_uid=u._id, score_uid=u._id, item_id=-1)
         #   logging.info('register action from %s', u._id)
        self._output(u)  # 返回用户, 写入cookie finish request


class TQqLoginHandler(BaseRequestHandler, TQqOAuth2Mixin, RegisterMixin):
    def initialize(self, db, uri_prefix):
        self.db = db
        self.uri_prefix = uri_prefix

    @asynchronous
    def get(self):
        redirect_uri = self.uri_prefix + '/auth/tqq'
        if self.get_argument("code", False):
            self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.settings["tqq_client_id"],
                client_secret=self.settings["tqq_client_secret"],
                code=self.get_argument("code"),
                callback=self.async_callback(self._on_login)
            )
            return

        if self.settings.get('debug') and self.get_argument('test', '') == 'henry':
            user = ObjectDict(
                open_id='1234',
                nick='henry',
                portrait=configs['tonghua_default_portrait'],
                access_token='atkn',
                access_token_expires=time.time()+3600)
            self._on_login(user)
            return

        self.authorize_redirect(
            redirect_uri = redirect_uri,
            client_id = self.settings["tqq_client_id"],
            extra_params = {
                "response_type": "code",
                "display": "mobile",
            },
        )

    def _on_login(self, user):
        if not user:
            raise HTTPError(403)
        account = 'tqq@' + hashlib.md5(user['open_id']).hexdigest()
        nick = user['nick'] or '佚名'
        auth_type = 'tqq'
        (bind_sina, bind_tqq, bind_qq) = (0, 1, 0)
        if user['portrait']:
            portrait = user['portrait'] + "/100"
        else:
            portrait = configs['tonghua_default_portrait']
        u = self._find_user(account)
        if not u:
            u = ObjectDict(
                account=account, passwd=self._gen_id(20),
                auth_type=auth_type, user_type=0,
                bind_sina=bind_sina, bind_tqq=bind_tqq, bind_qq=bind_qq,
                portrait=portrait, nick=nick,
                baidu_uid='', baidu_cid=''
            )
            u = self._try_gen(u)
            if not u:
                raise HTTPError(500)
        self._on_bind(u._id, user, auth_type)
        logging.info('bind tqq: %s %s', u._id, user)
        had_user_action = model.action.find_user_action(u._id)
        if not had_user_action:
            model.action.register(actor_uid=u._id, score_uid=u._id, item_id=-1)
            logging.info('register action from %s', u._id)
        self._output(u)


class QqLoginHandler(BaseRequestHandler, QqOAuth2Mixin, RegisterMixin):
    def initialize(self, db, uri_prefix):
        self.db = db
        self.uri_prefix = uri_prefix

    @asynchronous
    def get(self):
        redirect_uri = self.uri_prefix + '/auth/qq'
        if self.get_argument("code", False):
            self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.settings["qq_client_id"],
                client_secret=self.settings["qq_client_secret"],
                code=self.get_argument("code"),
                callback=self.async_callback(self._on_login))
            return

        if self.settings.get('debug') and self.get_argument('test', '') == 'henry':
            user = ObjectDict(
                open_id='1234', nick='henry',
                portrait=configs['tonghua_default_portrait'],
                access_token='atkn',
                access_token_expires=time.time()+3600)
            self._on_login(user)
            return

        self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=self.settings["qq_client_id"],
            extra_params={
                "scope": "get_user_info,add_share",
                "response_type": "code",
                "display": "mobile"
            },
        )

    def _on_login(self, user):
        if not user:
            raise HTTPError(403)
        account = 'qq@' + hashlib.md5(user['open_id']).hexdigest()
        nick = user['nick'] or '佚名'
        auth_type = 'qq'
        (bind_sina, bind_tqq, bind_qq) = (0, 0, 1)
        portrait = user['portrait'] or configs['tonghua_default_portrait']
        u = self._find_user(account)
        if not u:
            u = ObjectDict(
                account=account, passwd=self._gen_id(20),
                auth_type=auth_type, user_type=0,
                bind_sina=bind_sina, bind_tqq=bind_tqq, bind_qq=bind_qq,
                portrait=portrait, nick=nick,
                baidu_uid='', baidu_cid=''
            )
            u = self._try_gen(u)
            if not u:
                raise HTTPError(500)
        self._on_bind(u._id, user, auth_type)
        logging.info('bind qq: %s %s', u._id, user)
        had_user_action = model.action.find_user_action(score_uid=u._id)
        if not had_user_action:
            model.action.register(actor_uid=u._id, score_uid=u._id, item_id=-1)
            logging.info('register action from %s', u._id)
        self._output(u)


class QqWebLoginHandler(BaseRequestHandler, QqOAuth2Mixin, RegisterMixin):
    def initialize(self, db, uri_prefix):
        self.db = db
        self.uri_prefix = uri_prefix

    @asynchronous
    def get(self):
        redirect_uri = self.uri_prefix + '/auth/qqweb'
        if self.get_argument("code", False):
            self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=self.settings["qq_client_id"],
                client_secret=self.settings["qq_client_secret"],
                code=self.get_argument("code"),
                callback=self.async_callback(self._on_login))
            return

        if self.settings.get('debug') and self.get_argument('test', '') == 'henry':
            user = ObjectDict(open_id='1234', nick='henry',
                              portrait=configs['tonghua_default_portrait'],
                              access_token='atkn',
                              access_token_expires=time.time()+3600)
            self._on_login(user)
            return

        self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=self.settings["qq_client_id"],
            extra_params={
                "scope": "get_user_info,add_share",
                "response_type": "code",
                "display": "mobile"
            },
        )

    def _on_login(self, user):
        if not user:
            raise HTTPError(403)
        account = 'qq@' + hashlib.md5(user['open_id']).hexdigest()
        nick = user['nick'] or '佚名'
        auth_type = 'qq'
        (bind_sina, bind_tqq, bind_qq) = (0, 0, 1)
        portrait = user['portrait'] or configs['tonghua_default_portrait']
        u = self._find_user(account)
        if not u:
            u = ObjectDict(
                account=account, passwd=self._gen_id(20),
                auth_type=auth_type, user_type=0,
                bind_sina=bind_sina, bind_tqq=bind_tqq, bind_qq=bind_qq,
                portrait=portrait, nick=nick,
                baidu_uid='', baidu_cid=''
            )
            u = self._try_gen(u)
            if not u:
                raise HTTPError(500)
        self._on_bind(u._id, user, auth_type)
        logging.info('bind qq: %s %s', u._id, user)
        had_user_action = model.action.find_user_action(score_uid=u._id)
        if not had_user_action:
            model.action.register(actor_uid=u._id, score_uid=u._id, item_id=-1)
            logging.info('register action from %s', u._id)
        self._output(u)

    def _output(self, user):
        token = self._gen_token(user._id, user.user_no)
        self.set_cookie('token', token, domain='imtonghua.com', expires_days=BaseRequestHandler.EXPIRES_DAYS)
        v = json_encode(dict(user_no=user.user_no, nick=user.nick))
        self.set_cookie('user', base64.b64encode(v), domain='imtonghua.com')
        self.render('../templates/qqweb.html', nick=user.nick)
        #self.redirect('http://www.imtonghua.com/')


class VisitorLoginHandler(BaseRequestHandler):
    def initialize(self, db, uri_prefix):
        self.db = db
        self.uri_prefix = uri_prefix

    def get(self):
        d = ObjectDict(
            token='',
            nick=u'游客',
            portrait=configs['tonghua_default_portrait'],
        )
        self.set_status(200)
        self._add_links(d)
        self.write(d)

    def _add_links(self, d):
        d['links'] = [
            self._link('homepage' , 'first'),
            self._link('randompage' , 'random'),
            ]
