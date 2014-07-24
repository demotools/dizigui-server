#coding: utf-8
import time
import urllib
import logging

from poster.encode import multipart_encode, MultipartParam
from tornado import gen
from tornado import httpclient
from tornado.escape import json_encode, json_decode

import hqby.cache
from hqby.config import configs


class ShareMixin(object):
    @gen.engine
    def share(self, uid, target, txt, img_uri=None, callback=None):
        sm = ShareModel()
        if target not in sm.TARGET_ALL:
            if callback:
                callback(False)
            return
        data = yield gen.Task(sm.access_token, uid, target)
        if data is None or data['access_token_expires'] < time.time() + 180:
            if callback:
                callback(False)
            return
        if target in ['tqq','sina']:
            if img_uri and img_uri[:7].lower() == 'http://':
                http = httpclient.AsyncHTTPClient()
                callback = self.async_callback(self._on_img, data, txt, callback)
                http.fetch(img_uri, method='GET', callback=callback)
            else:
                getattr(self, '_share2'+ target)(data, txt, '', None, callback)
        if target in ['qq']:
            getattr(self, '_share2'+ target)(data, txt, '', img_uri, callback)

    def _on_img(self, data, txt, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                                        response.request.url)
            if callback:
                callback(False)
            return
        getattr(self, '_share2'+ data['target'])(data, txt, response.headers.get('Content-Type', 'application/octet-stream'), response.body, callback)

    def _share2tqq(self, data, txt, cnt_type, img, callback):
        http = httpclient.AsyncHTTPClient()
        callback = self.async_callback(self._on_share2tqq, callback)
        if img is None:
            post_args = {
                'oauth_consumer_key': configs['tqq_client_id'],
                'access_token': data['access_token'],
                'openid': data['open_id'],
                'clientip': self.request.remote_ip,
                'oauth_version': '2.a',
                'scope': 'all',
                'format': 'json',
                'content': txt,
            }
            body = urllib.urlencode(post_args)
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            http.fetch('https://open.t.qq.com/api/t/add', method='POST', body=body, callback=callback)
        else:
            post_args = [
                ('oauth_consumer_key', configs['tqq_client_id']),
                ('access_token', data['access_token']),
                ('openid', data['open_id']),
                ('clientip', self.request.remote_ip),
                ('oauth_version', '2.a'),
                ('scope', 'all'),
                ('format', 'json'),
                ('content', txt),
                MultipartParam('pic', img, filetype=cnt_type, filename='pic'),
            ]
            body, headers = multipart_encode(post_args)
            body = "".join(body)
            logging.info("share to tqq: headers = %s", headers)
            http.fetch('https://open.t.qq.com/api/t/add_pic', method='POST', body=body, headers=headers, callback=callback)

    def _on_share2tqq(self, callback, response):
        logging.info("share to tqq: response = %s", response)
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                                        response.request.url)
            if callback:
                callback(False)
            return
        js = json_decode(response.body)
        if js['errcode'] != 0:
            logging.warning("Error response %s fetching %s", response.error,
                                        response.body)
        callback(js['errcode'] == 0)

    def _share2sina(self, data, txt, cnt_type, img, callback):
        http = httpclient.AsyncHTTPClient()
        callback = self.async_callback(self._on_share2sina, callback)
        if img is None:
            post_args = {
                'access_token': data['access_token'],
                'status': txt,
            }
            body=urllib.urlencode(post_args)
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            http.fetch('https://api.weibo.com/2/statuses/update.json', method='POST', body=body, headers=headers, callback=callback)
        else:
            post_args = [
                ('access_token', data['access_token']),
                ('status', txt),
                MultipartParam('pic', img, filetype=cnt_type, filename='pic'),
            ]
            body, headers = multipart_encode(post_args)
            body = "".join(body)
            logging.info("share to sina: headers = %s", headers)
            http.fetch('https://upload.api.weibo.com/2/statuses/upload.json', method='POST', body=body, headers=headers, callback=callback)

    def _on_share2sina(self, callback, response):
        logging.error("share to sina: response = %s", response)
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                                        response.request.url)
            if callback:
                callback(False)
            return
        js = json_decode(response.body)
        if 'error_code' in js:
            logging.warning("Error response %s fetching %s", response.error,
                                        response.body)
        callback('error_code' not in js)

    def _share2qq(self, data, txt, cnt_type, img, callback):
        http = httpclient.AsyncHTTPClient()
        callback = self.async_callback(self._on_share2qq, callback)
        img = img.split('?')[0]
        post_args = {
            'oauth_consumer_key': configs['qq_client_id'],
            'access_token': data['access_token'],
            'openid': data['open_id'],
            'format': 'json',
            'comment': txt,
            'images': img,
            'title': '童说童画分享',
            'url': 'http://www.imtonghua.com/',
            'site': '童说童画',
            'fromurl': 'http://www.imtonghua.com/',
            'nswb': 1,
        }
        body = urllib.urlencode(post_args)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        logging.info("share to qq: headers = %s", headers)
        http.fetch('https://graph.qq.com/share/add_share', method='POST', body=body, callback=callback)

    def _on_share2qq(self, callback, response):
        logging.info("share to qq: response = %s", response)
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                                        response.request.url)
            if callback:
                callback(False)
            return
        js = json_decode(response.body)
        if js['ret'] != 0:
            logging.warning("Error response %s fetching %s", response.error,
                                        response.body)
        callback(js['ret'] == 0)

class ShareModel(object):
    TARGET_TQQ = 'tqq'
    TARGET_SINA = 'sina'
    TARGET_QQ = 'qq'
    TARGET_ALL = set([TARGET_TQQ, TARGET_SINA, TARGET_QQ])

    def __init__(self):
        self.redis = hqby.cache.get_async_conn('test2')

    @gen.engine
    def targets(self, uid, callback=None):
        ret = yield gen.Task(self.redis.hgetall, self._key(uid))
        for k in ret:
            v = json_decode(ret[k])
            ret[k] = dict(uid=uid, target=k, open_id=v.get('oid'), access_token=v.get('at'), access_token_expires=v.get('ate'))
        for k in self.TARGET_ALL:
            if k not in ret:
                ret[k] = self._dump(uid, k)
        if callback:
            callback(ret)

    @gen.engine
    def update(self, uid, target, open_id=None, access_token=None, access_token_expires=None, callback=None):
        ''' 记录用户的openid, access_token到redis中
        '''
        if target not in self.TARGET_ALL:
            if callback:
                callback(False)
            return
        d = dict(oid=open_id, at=access_token, ate=access_token_expires)
        yield gen.Task(self.redis.hset, self._key(uid), target, json_encode(d))
        if callback:
            callback(True)

    @gen.engine
    def access_token(self, uid, target, callback=None):
        ''' 获取用户的三方分享信息
        '''
        if target not in self.TARGET_ALL:
            if callback:
                callback(None)
            return
        ret = yield gen.Task(self.redis.hget, self._key(uid), target)
        if  ret:
            ret = json_decode(ret)
        else:
            ret = {}
        ret = dict(uid=uid, target=target, open_id=ret.get('oid'), access_token=ret.get('at'), access_token_expires=ret.get('ate'))
        if callback:
            callback(ret)

    def _dump(self, uid, target):
        return dict(uid=uid, target=target, open_id=None, access_token=None, access_token_expires=None)

    @gen.engine
    def _clear(self, uid, callback=None):
        yield gen.Task(self.redis.delete, self._key(uid))
        if callback:
            callback()

    def _key(self, uid):
        return 'tonghua/shr:' + uid

