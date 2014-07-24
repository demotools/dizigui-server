# coding: utf-8
"""Cache工具。

用法1：
    import hqby.cache
    conn = hqby.cache.get_sync_conn('mobile')
    conn.set('13812345678', 'username')
    uname = conn.get('13812345678')

用法2：
    import hqby.cache
    @hqyb.cache.SyncCache('/j2/mobile/data/', 300)
    def get_mobile_user(mobile):
        ...
        return uname
    def update_mobile_user(mobile):
        ...
        get_mobile_user._del_cache(mobile)
        # get_mobile_user._clr_cache()
"""

import hashlib
import cPickle
import inspect

import redis
import tornadoredis

from hqby.config import configs
from functools import wraps
from inspect import getcallargs
import logging


_SYNC_CONNS_ = {}
_ASYNC_CONNS_ = {}
_IO_LOOP_ = None


def get_sync_conn(id):
    if id in _SYNC_CONNS_:
        return _SYNC_CONNS_[id]
    _SYNC_CONNS_[id] = conn = redis.Redis(**configs['redis'][id])
    return conn


def get_async_conn(id):
    if id in _ASYNC_CONNS_:
        return _ASYNC_CONNS_[id]
    _ASYNC_CONNS_[id] = conn = tornadoredis.Client(
        io_loop=_IO_LOOP_, **configs['redis'][id])
    conn.connect()
    return conn


def set_ioloop(ioloop):
    global _IO_LOOP_
    while _ASYNC_CONNS_:
        _ASYNC_CONNS_.popitem()[1].disconnect()
    _IO_LOOP_ = ioloop


def gen_key(prefix, args, kwargs):
    key = prefix + ','.join([str(i) for i in args]) \
                 + ','.join([(str(i), str(j)) for i, j in kwargs.items()])
    if len(key) > 200:
        key = prefix + hashlib.md5(key).hexdigest()
    return key


class SyncCache(object):

    def __init__(self, conn_id, prefix_key, ttl=None):
        self.conn_id = conn_id
        self.prefix_key = prefix_key
        self.ttl = ttl

    def __call__(self, func):
        self.func = func
        self.skip_self_arg = (inspect.getargspec(func).args[:1] == ['self'])
        def deco_func(*args, **kwargs):
            return self.call_func(*args, **kwargs)
        setattr(deco_func, '_del_cache', self._del_cache)
        setattr(deco_func, '_clr_cache', self._clr_cache)
        return deco_func

    def call_func(self, *args, **kwargs):
        key = gen_key(self.prefix_key, args[1:], kwargs) if self.skip_self_arg \
                else gen_key(self.prefix_key, args, kwargs)
        conn = get_sync_conn(self.conn_id)
        ret = conn.get(key)
        if ret:
            return cPickle.loads(ret)
        ret = self.func(*args, **kwargs)
        if self.ttl == None:
            conn.set(key, cPickle.dumps(ret))
        else:
            conn.setex(key, cPickle.dumps(ret), self.ttl)
        return ret

    def _del_cache(self, *args, **kwargs):
        key = gen_key(self.prefix_key, args, kwargs)
        get_sync_conn(self.conn_id).delete(key)

    def _clr_cache(self, *args, **kwargs):
        key = gen_key(self.prefix_key, args, kwargs)
        conn = get_sync_conn(self.conn_id)
        keys = conn.keys(key + '*')
        if keys:
            conn.delete(*keys)


def id_cache(conn_id, key):
    def deco_func(func):
        id = func()
        conn = get_sync_conn(conn_id)
        id2 = int(conn.get(key) or 0)
        if id > id2:
            conn.set(key, id)

        def call_func():
            return conn.incr(key) - 1
        return call_func
    return deco_func


def cached(conn_id, key_, _key, pickled=False, mode=configs['cache_mode']):  # 装饰器参数
    """" 缓存装饰器:
         _key(额外唯一标识key的参数名称-必须在kwargs中指定该值) 如:_key='id', 则kwargs中必须有id的值
         cache(是否使用缓存)
         key = 装饰器前缀key + kwargs.get(_key)
         mode: get, set, delete, db. default is get
    """""
    def func_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):  # 函数参数
            args_dict = getcallargs(func, *args, **kwargs)
            key_add = args_dict.get(_key)
            key = key_ + str(key_add) if key_add else None
            cache_mode = args_dict.get('mode', mode)
            assert cache_mode in set(['db', 'get', 'set', 'delete'])
            value = None
            conn = None
            try:
                if cache_mode != 'db':
                    conn = get_sync_conn(conn_id)
                    if cache_mode == 'get':  # get
                        value = conn.get(key) if key else None
                        if pickled and value:
                            value = cPickle.loads(value)
                    elif cache_mode == 'delete':  # delete
                        conn.delete(key)
                        logging.info('[Cache Delete]: %s' % key)
            except Exception as ex:
                logging.error('[Cache Error]: %s - %s' % (key, str(ex)))
                value = None
                conn = None
            if value:
                logging.info('[Cache Get]: %s' % key)
                return value
            value = func(*args, **kwargs)  # db
            redis_value = cPickle.dumps(value) if value and pickled else value
            if cache_mode == 'set' or cache_mode == 'get' and conn:  # set
                if redis_value:
                    conn.set(key, redis_value)
                    logging.info('[Cache Set]: %s' % key)
                else:  # 清除缓存
                    conn.delete(key)
                    logging.info('[Cache Delete]: %s - remove not use data' % key)
            return value
        return wrapper
    return func_wrapper
