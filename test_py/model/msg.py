#coding: utf-8
import time

from tornado import gen
from tornado.escape import json_encode, json_decode

import hqby.cache


class MessageModel(object):
    def __init__(self, max_items=1000):
        self.max_items = max_items
        self.redis = hqby.cache.get_async_conn('message')

    @gen.engine
    def list(self, uid, offset, count, callback=None):
        l = yield gen.Task(self.redis.zrevrange, self._key_msgs(uid), offset, offset + count - 1, False)
        if callback:
            callback(l)

    @gen.engine
    def push(self, uid, title, msg, callback=None):
        now = time.time()
        mid = yield gen.Task(self.redis.incr, self._key_msg_id())
        k = self._key_msgs(uid)
        _ = yield gen.Task(self.redis.zadd, k, mid, '%d|%d|%s' % (mid, now, msg))
        _ = yield gen.Task(self.redis.zremrangebyrank, k, 0, -self.max_items - 1)
        k = self._key_notify_pending(uid)
        _ = yield gen.Task(self.redis.zadd, k, mid, json_encode(dict(title=title)))
        _ = yield gen.Task(self.redis.zremrangebyrank, k, 0, -self.max_items - 1)
        apple_id = yield gen.Task(self.redis.get, self._key_notify_apple_id(uid))
        if apple_id:
            yield gen.Task(self.redis.sadd, self._key_notify_apple_pending(), uid)
        if callback:
            callback(mid)

    @gen.engine
    def remove(self, uid, mid, callback=None):
        yield gen.Task(self.redis.zremrangebyscore, self._key_msgs(uid), mid, mid)
        if callback:
            callback()

    @gen.engine
    def pending(self, uid, callback=None):
        k = self._key_notify_pending(uid)
        ret = yield gen.Task(self.redis.zrange, k, 0, -1, False)
        _ = yield gen.Task(self.redis.zremrangebyrank, k, 0, -1)
        ret = [json_decode(i) for i in ret]
        if callback:
            callback(ret)

    @gen.engine
    def pending_count(self, uid, callback=None):
        k = self._key_notify_pending(uid)
        ret = yield gen.Task(self.redis.zrange, k, 0, -1, False)
        n = len(ret or [])
        if callback:
            callback(n)

    @gen.engine
    def register(self, uid, apple_id, callback=None):
        ret = yield gen.Task(self.redis.set, self._key_notify_apple_id(uid), apple_id)
        if callback:
            callback(ret)

    @gen.engine
    def unregister(self, uid, callback=None):
        apple_id = yield gen.Task(self.redis.get, self._key_notify_apple_id(uid))
        if apple_id:
            yield gen.Task(self.redis.srem, self._key_notify_apple_pending(), uid)
            yield gen.Task(self.redis.delete, self._key_notify_apple_id(uid))
        if callback:
            callback(True)

    @gen.engine
    def get_apple_id(self, uid, callback=None):
        apple_id = yield gen.Task(self.redis.get, self._key_notify_apple_id(uid))
        if callback:
            callback(apple_id)

    @gen.engine
    def _clear(self, uid, callback=None):
        ret = yield gen.Task(self.redis.delete, self._key_msgs(uid))
        ret = yield gen.Task(self.redis.delete, self._key_notify_pending(uid))
        ret = yield gen.Task(self.redis.delete, self._key_notify_apple_pending())
        if callback:
            callback(ret)

    @gen.engine
    def apple(self, callback=None):
        uid = yield gen.Task(self.redis.spop, self._key_notify_apple_pending())
        if callback:
            callback(uid)

    def _key_msgs(self, uid):
        return 'mq:uid:' + uid

    def _key_msg_id(self):
        return 'mq:msg:sn'

    def _key_notify_pending(self, uid):
        return 'mq:npnd:' + uid

    def _key_notify_apple_id(self, uid):
        return 'mq:apple:' + uid

    def _key_notify_apple_pending(self):
        return 'mq:apnd'

