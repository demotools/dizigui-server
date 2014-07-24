#coding: utf-8
import time
import urllib
import logging

from poster.encode import multipart_encode, MultipartParam
from tornado import gen
from tornado import httpclient
from tornado.escape import json_decode

import hqby.cache
from hqby.config import configs
from model.share import ShareModel


class FriendMixin(object):
    @gen.engine
    def add_friend(self, uid, target, th_uid, th_name, callback=None):
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
        if target in ['sina']:
            getattr(self, '_friend4'+ target)(data, th_uid, th_name, callback)
        if target in ['tqq']:
            getattr(self, '_friend4'+ target)(data, th_uid, th_name, callback)

    def _friend4sina(self, data, th_uid, th_name, callback):
        http = httpclient.AsyncHTTPClient()
        callback = self.async_callback(self._on_friend4sina, callback)
        post_args = {
            'access_token': data['access_token'],
            'uid':th_uid,
            'screen_name':th_name,
        }
        body=urllib.urlencode(post_args)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        http.fetch('https://api.weibo.com/2/friendships/create.json', method='POST', body=body, headers=headers, callback=callback)

    def _on_friend4sina(self, callback, response):
        logging.error("add friend for sina: response = %s", response)
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

    '''
    def _share2tqq(self, data, txt, cnt_type, img, callback):
        http = httpclient.AsyncHTTPClient()
        callback = self.async_callback(self._on_share2tqq, callback)
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
    '''
