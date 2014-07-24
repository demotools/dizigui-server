#coding: utf-8
import time

from tornado import gen
from tornado.escape import json_encode, json_decode

import hqby.cache
from hqby.config import configs


class DashBoardModel(object):
    MAX_ITEMS = 100
    EVENT_ID_MSG = '__MSG'
    EVENT_ID_ALL = '__ALL'

    def __init__(self):
        self.redis = hqby.cache.get_async_conn('message')

    def list(self, uid=None, offset=0, count=30, callback=None):
        if uid is None:
            if callback: callback([])
        else:
            offset = int(offset or 0)
            count = int(count or 30)
            count = min(self.MAX_ITEMS, count)
            self._list(uid, offset, count, callback)

    def listAll(self, offset=0, count=30, callback=None):
        self.list(self.EVENT_ID_ALL, offset, count, callback)

    def notify(self, dest_uid, src_uid, portrait, name, description, images, address, link, now=None, callback=None):
        if now is None:
            now = time.time()
        event_id = src_uid
        event_data = dict(
            portrait=portrait,
            name=name,
            description=description,
            images=images,
            link=link,
            timestamp=int(now),
        )
        self._notify(dest_uid, event_id, event_data, callback)

    def notifyAll(self, src_uid, portrait, name, description, images, address, link, now=time.time(), callback=None):
        self.notify(self.EVENT_ID_ALL, src_uid, portrait, name, description, images, address, link, now, callback)

    def notifyMsg(self, dest_uid, portrait, description, link, now=None, callback=None):
        if now is None:
            now = time.time()
        event_id = self.EVENT_ID_MSG
        event_dict = dict(
            portrait=portrait,
            name=u'\u6d88\u606f',
            description=description,
            images=[],
            link=link,
            timestamp=int(now),
        )
        self._notify(dest_uid, event_id, event_dict, callback)

    @gen.engine
    def reset(self, dest_uid, src_uid, callback=None):
        yield gen.Task(self.redis.hset, self._unread_key(dest_uid), src_uid, 0)
        if callback:
            callback()

    @gen.engine
    def resetMsg(self, dest_uid, callback=None):
        yield gen.Task(self.redis.hset, self._unread_key(dest_uid), self.EVENT_ID_MSG, 0)
        if callback:
            callback()

    @gen.engine
    def remove(self, dest_uid, src_uid, callback=None):
        uid = dest_uid
        event_id = src_uid
        _ = yield gen.Task(self.redis.hdel, self._unread_key(uid), event_id)
        _ = yield gen.Task(self.redis.hdel, self._hash_key(uid), event_id)
        _ = yield gen.Task(self.redis.zrem, self._sset_key(uid), event_id)
        if callback:
            callback(event_id)

    @gen.engine
    def all_len(self, callback=None):
        n = yield gen.Task(self.redis.hlen, self._hash_key(self.EVENT_ID_ALL))
        if callback:
            callback(n)

    @gen.engine
    def _list(self, uid=None, offset=0, count=30, callback=None):
        ret = []
        l = yield gen.Task(self.redis.zrevrange, self._sset_key(uid), offset, offset + count - 1, False)
        d = yield gen.Task(self.redis.hmget, self._hash_key(uid), l)
        n = yield gen.Task(self.redis.hmget, self._unread_key(uid), l)
        for i in l:
            event_dict = json_decode(d[i])
            event_dict['unread'] = int(n[i] or 0)
            ret.append(event_dict)
        if callback:
            callback(ret)

    @gen.engine
    def _notify(self, uid, event_id, event_dict, callback=None):
        now = int(event_dict.get('timestamp') or time.time())
        event_dict['class'] = 'event'
        _ = yield gen.Task(self.redis.hincrby, self._unread_key(uid), event_id, 1)
        js = json_encode(event_dict)
        _ = yield gen.Task(self.redis.hset, self._hash_key(uid), event_id, js)
        _ = yield gen.Task(self.redis.zadd, self._sset_key(uid), now, event_id)
        if callback:
            callback(event_id)

    @gen.engine
    def _clear(self, uid, callback=None):
        for i in [uid, self.EVENT_ID_MSG, self.EVENT_ID_ALL]:
            ret = yield gen.Task(self.redis.delete, self._hash_key(i))
            ret = yield gen.Task(self.redis.delete, self._sset_key(i))
            ret = yield gen.Task(self.redis.delete, self._unread_key(i))
        if callback:
            callback(ret)

    def _hash_key(self, uid):
        return 'dbrd:h:' + uid

    def _sset_key(self, uid):
        return 'dbrd:s:' + uid

    def _unread_key(self, uid):
        return 'dbrd:n:' + uid
