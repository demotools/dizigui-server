# coding: utf8
# 基础request封装, 约定:
# 记录用户: 安全cookie保存用户id, key(token), cache保存用户对象(使用cpickle.dumps序列化对象), 每次更新用户信息需要及时更新缓存
# 登录: 在config中设置登录url, 需要登录才能访问的接口需要添加login_required()修饰器即可, 默认web模式


from tornado.web import RequestHandler, MissingArgumentError, HTTPError
from tornado.escape import json_decode, url_unescape
from urlparse import parse_qsl
import cPickle
from functools import wraps
from copy import deepcopy
import json
import logging

import cache
from config import configs

auth_types = [  # 三方登录平台支持类型
        'sina', 'qq', 'tqq'
    ]

def login_required(mode='phone'):
    """ 用户修饰器
    """
    def wrap_func(func):
        @wraps(func)
        def wrapper(handler, *args, **kwargs):
            if not handler.user:
                if mode == 'web':
                    return handler.redirect(handler.get_login_url())
                else:
                    raise HTTPError(401, '[Unauthorized]: Login required')
            return func(handler, *args, **kwargs)
        return wrapper
    return wrap_func


class RequestData(dict):
    """  请求数据对象
    """
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return None

    def __setattr__(self, key, value):
        self[key] = value

    def validate(self, required=None):
        """ 请求数据验证方法
        """
        if required:
            for key in required:
                if not self[key]:
                    raise HTTPError(400, '[Bad Request]: request data illegal',  reason='Bad-Request')
        return True


##基础封装RequestHandler
class BaseHandler(RequestHandler):

    _messages = []

    API_ROOT_URI = configs['api_base_url'] + '/'
    CNT_TYPE_PREFIX = 'application/vnd.szhqby.dujing+'  # add app-name to custom it

    def _href(self, href):
        return self.API_ROOT_URI + href

    def _link(self, href, key, **kwargs):
        attr = dict(kwargs)
        attr['href'] = self._href(href)
        attr['key'] = key
        return attr

    def _ct(self, cntType):
        return self.CNT_TYPE_PREFIX + cntType

    def get_current_user(self):
        """ 获取当前用户, 优先从redis获取
        """
        uid = self.get_secure_cookie('token')
        if not uid:
            return None
        try:
            user = cache.get_sync_conn(configs['redis_name']).get('uid-%s' % uid)
            if user:
                user = cPickle.loads(user)
        except Exception as ex:
            logging.error('[Cache Get]: (Error) %s' % str(ex))
            user = None
        return user # or User.get(id=uid)

    def get_login_url(self):
        return configs['web_login_url'] + '?next=' + self.request.uri

    def phone_data(self, required=None):
        """ phone 请求数据获取, 返回参数对象
        """
        data = self.request.body
        if not data:
            raise HTTPError(400, '[Bad Request]: request body data not found')
        try:
            data = json_decode(data)
        except ValueError:  # 非json数据, 尝试encode url获取
            logging.warning('[Warning Request]: request data not json type')
            try:
                data = url_unescape(data)
                data = dict(parse_qsl(data))
            except Exception as ex:
                raise HTTPError(400, '[Bad Request]: request data illegal %s' % str(ex))
        rdata = RequestData(data)
        rdata.validate(required)  # 数据验证
        return rdata

    def request_data(self, required=None, phone=True):
        return self.phone_data(required=required) if phone else self.request.arguments

    def form_data(self):
        """ web 端 获取表单全部数据 - 字典
        """
        data = {}
        for k in self.request.arguments:
            v = self.get_arguments(k)
            data[k] = v[0] if len(v) == 1 else v
        return data

    def login(self, user, expires_days=None, expires=None):
        """ 用户登录, 写入cookie-token, 用户对象保存到缓存
        """
        if not user:
            return
        if not expires and not expires_days:
            expires_days = configs['cookie_expires_days']
        self.clear_cookie('token')
        self.set_secure_cookie('token', str(user.id), expires_days=expires_days, expires=expires)
        cache.get_sync_conn(configs['redis_name']).set('uid-%s' % user.id, cPickle.dumps(user))
        self.current_user = user  # 设置用户

    def logout(self, user=None):
        user = user or self.user
        self.clear_cookie('token')
        if user:
            cache.get_sync_conn(configs['redis_name']).delete('uid-%s' % user.id)

    def get_args(self, key, default='', data_type=unicode):
        """ 获取post或者get数据的某个参数
        """
        try:
            data = self.get_argument(key)
            if callable(data_type):
                return data_type(data)
            return data
        except MissingArgumentError:
            return default

    def get_template_namespace(self):
        """ 添加额外的模板变量, 默认有:
         handler=self,
         request=self.request,
         current_user=self.current_user,
         locale=self.locale,
          _=self.locale.translate,
         static_url=self.static_url,
         xsrf_form_html=self.xsrf_form_html,
         reverse_url=self.reverse_url
        """
        msg = deepcopy(self._messages)
        add_names = dict(
            messages=msg,
        )
        self.clear_message()
        name = super(BaseHandler, self).get_template_namespace()
        name.update(add_names)
        return name

    def clear_message(self):
        while self._messages:
            self._messages.pop()

    def add_message(self, msg):
        """ 添加一条消息, 提供给模板使用
        """
        self.clear_message()
        self._messages.append(msg)

    @property
    def user(self):
        """ 当前用户对象
        """
        return self.current_user

    @property
    def ip(self):
        return self.request.headers.get('X-Real-Ip', self.request.remote_ip)

    def write(self, chunk):
        if isinstance(chunk, dict) and self.settings.get('debug'):
            RequestHandler.write(self, json.dumps(chunk, indent=4))
        else:
            RequestHandler.write(self, chunk)
        if isinstance(chunk, dict):
            self.set_header('Content-Type', self._ct('json'))

    def write_error(self, status_code, **kwargs):
        """ 异常状态码处理
        """
        if 'exc_info' in kwargs:  # 设置错误码
            code = -1
            try:
                error = kwargs['exc_info'][1].log_message
                code = configs['error_codes'].get(error, -1)
                self.set_header('error-msg', unicode(error))
            except (KeyError, AttributeError):
                pass
            self.set_header('error', code)
        return super(BaseHandler, self).write_error(status_code, **kwargs)
