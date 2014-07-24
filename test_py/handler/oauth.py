#!/usr/bin/env python
# coding: utf-8

import urllib
import logging
import uuid
import re

from tornado.auth import OAuth2Mixin
from tornado import httpclient
from tornado import escape

from hqby.config import configs


class SinaOAuth2Mixin(OAuth2Mixin):
    _OAUTH_AUTHORIZE_URL = "https://api.weibo.com/oauth2/authorize?"
    _OAUTH_ACCESS_TOKEN_URL = "https://api.weibo.com/oauth2/access_token?"
    _OAUTH_NO_CALLBACKS = False

    def get_authenticated_user(
        self, redirect_uri, client_id, client_secret,
        code, callback, extra_fields=None
    ):
        session = {}
        http = httpclient.AsyncHTTPClient()
        args = {
          "redirect_uri": redirect_uri,
          "client_id": client_id,
          "client_secret": client_secret,
          "code": code,
          "extra_params": {"grant_type": "authorization_code", },
        }

        fields = set(['gender', ])
        if extra_fields:
            fields.update(extra_fields)
        
        logging.error('debug detail: %s %s %s (%s) %s',
                      self.get_status(), self.request.method,
                      self.request.uri, self.request.remote_ip,
                      self.request.headers)
        logging.info('sina: %s', self._oauth_request_token_url(**args))
        http.fetch(
            self._oauth_request_token_url(**args), 
            method='POST',
            body=urllib.urlencode(args),
            callback=self.async_callback(
                self._on_access_token, redirect_uri, client_id,
                client_secret, callback, fields, session
            )
        )

    def _on_access_token(self, redirect_uri, client_id, client_secret, callback, fields, session, response):
        if response.error:
            logging.warning('sina auth error: %s' % str(response))
            callback(None)
            return

        js = response.body
        logging.info('sina: %s', js)
        args = escape.json_decode(js)
        if args.get('error_code'):
            logging.warning('sina auth error: %d, %s', args.get('error_code'), args.get('error'))
            callback(None)
            return
        session['access_token'] = args["access_token"]
        session["access_token_expires"] = args["expires_in"]
        session['open_id'] = args.get('uid')
        self.sina_request(
            path="/users/show.json",
            callback=self.async_callback(
                self._on_get_user_info, callback, session, fields
            ),
            access_token=session["access_token"],
            uid=session['open_id'],
        )

    def _on_get_user_info(self, callback, session, fields, user):
        if user is None:
            callback(None)
            return

        fieldmap = {}
        for field in fields:
            fieldmap[field] = user.get(field)

        fieldmap.update({
            "access_token": session.get("access_token"),
            "access_token_expires": session.get("access_token_expires"),
            "client_id": session.get('client_id'),
            "open_id": session.get('open_id'),
            "nick": user.get('screen_name'),
            "portrait": user.get('profile_image_url'),
        })
        callback(fieldmap)  # on_login

    def sina_request(self, path, callback, access_token=None, client_id=None, open_id=None, post_args=None, **args):
        url = "https://api.weibo.com/2" + path
        all_args = {}
        if access_token:
            all_args["access_token"] = access_token
        if open_id:
            all_args["uid"] = open_id
        all_args.update(args)

        if all_args:
            url += "?" + urllib.urlencode(all_args)
        logging.info('sina_request: %s', url)
        callback = self.async_callback(self._on_sina_request, callback)  # callback on_get_user_info(callback on_login)
        http = httpclient.AsyncHTTPClient()
        if post_args is not None:
            http.fetch(
                url, method="POST",
                body=urllib.urlencode(post_args),
                callback=callback
            )
        else:
            http.fetch(url, callback=callback)

    def _on_sina_request(self, callback, response):
        if response.error:
            logging.warning(
                "Error response %s fetching %s", 
                response.error, response.request.url
            )
            callback(None)
            return
        d = escape.json_decode(response.body)
        if d.get('error_code'):
            logging.warning(
                "sina request error: %d, %s", 
                d['error_code'], d['error']
            )
            callback(None)
            return
        callback(d)  # on_get_user_info


class TQqOAuth2Mixin(OAuth2Mixin):
    _OAUTH_AUTHORIZE_URL = "https://open.t.qq.com/cgi-bin/oauth2/authorize?"
    _OAUTH_ACCESS_TOKEN_URL = "https://open.t.qq.com/cgi-bin/oauth2/access_token?"
    _OAUTH_NO_CALLBACKS = False

    def get_authenticated_user(
        self, redirect_uri, client_id, client_secret,
        code, callback, extra_fields = None
    ):
        session = {}
        http = httpclient.AsyncHTTPClient()
        args = {
          "redirect_uri": redirect_uri,
          "client_id": client_id,
          "client_secret": client_secret,
          "code": code,
          "extra_params": {"grant_type": "authorization_code",},
        }

        fields = set(['gender', ])
        if extra_fields:
            fields.update(extra_fields)

        logging.error('debug detail: %s %s %s (%s) %s',
                      self.get_status(), self.request.method,
                      self.request.uri, self.request.remote_ip,
                      self.request.headers)
        logging.info('tqq: %s', self._oauth_request_token_url(**args))
        http.fetch(
            self._oauth_request_token_url(**args),
            callback=self.async_callback(
                self._on_access_token, redirect_uri, client_id,
                client_secret, callback, fields, session
            )
        )

    def _on_access_token(self, redirect_uri, client_id, client_secret,
                        callback, fields, session, response):
        if response.error:
            logging.warning('tqq auth error: %s' % str(response))
            callback(None)
            return

        js = response.body
        logging.info('tqq: %s', js)
        args = {}
        tmp_args = re.split('&', js)
        for arg in tmp_args:
            key, vaule = re.split('=',arg)
            args[key] = vaule
        if args.get('error_code'):
            logging.warning('tqq auth error: %d, %s', args.get('error_code'), args.get('error'))
            callback(None)
            return
        session['access_token'] = args["access_token"]
        session["access_token_expires"] = args["expires_in"]
        session["open_id"] = args["openid"]
        self.tqq_request(
            path = "/user/info",
            callback = self.async_callback(
                self._on_get_user_info, callback, session, fields
            ),
            access_token = session["access_token"],
            open_id = args["openid"],
        )

    def _on_get_user_info(self, callback, session, fields, user):
        if user is None:
            callback(None)
            return

        fieldmap = {}
        for field in fields:
            fieldmap[field] = user.get(field)

        fieldmap.update({
            "access_token": session.get("access_token"),
            "access_token_expires": session.get("access_token_expires"),
            "client_id": session.get('client_id'),
            "open_id": user.get('openid'),
            "nick": user.get('name'),
            "portrait": user.get('head'),
        })
        callback(fieldmap)

    def tqq_request(
        self, path, callback, access_token = None,
        client_id = None, open_id = None, post_args = None, **args
    ):
        url = "https://open.t.qq.com/api" + path
        all_args = {
            'format':'json', 
            'oauth_consumer_key':configs['tqq_client_id'],
            'clientip':self.request.remote_ip,
            'oauth_version':'2.a',
        }
        if access_token:
            all_args["access_token"] = access_token
        if open_id:
            all_args["openid"] = open_id
        all_args.update(args)
        if all_args:
            url += "?" + urllib.urlencode(all_args)
        logging.info('tqq_request: %s', url)
        callback = self.async_callback(self._on_tqq_request, callback)
        http = httpclient.AsyncHTTPClient()
        if post_args is not None:
            http.fetch(
                url, 
                callback = callback
            )
        else:
            http.fetch(url, callback = callback)

    def _on_tqq_request(self, callback, response):
        if response.error:
            logging.warning(
                "Error response %s fetching %s",
                response.error, response.request.url
            )
            callback(None)
            return
        d = escape.json_decode(response.body)
        if d.get('errcode'):
            logging.warning(
                "tqq request error: %d, %s",
                d['errcode'], d['msg']
            )
            callback(None)
            return
        user = d.get('data')
        callback(user)

class QqOAuth2Mixin(OAuth2Mixin):
    _OAUTH_AUTHORIZE_URL = "https://graph.qq.com/oauth2.0/authorize?"
    _OAUTH_ACCESS_TOKEN_URL = "https://graph.qq.com/oauth2.0/token?"
    _OAUTH_NO_CALLBACKS = False

    def get_authenticated_user(self, redirect_uri, client_id, client_secret,
                              code, callback, extra_fields=None):
        session = {}
        session['state'] = uuid.uuid4()
        http = httpclient.AsyncHTTPClient()
        args = {
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "extra_params": {"grant_type": "authorization_code", "state": session['state']},
        }

        fields = set(['gender', ])
        if extra_fields:
            fields.update(extra_fields)

        logging.info('request token uri: %s', self._oauth_request_token_url(**args))
        http.fetch(
            self._oauth_request_token_url(**args),
            self.async_callback(
                self._on_access_token, 
                redirect_uri, client_id,
                client_secret, callback, fields, session
            )
        )

    def _on_access_token(self, redirect_uri, client_id, client_secret,
                        callback, fields, session, response):
        if response.error:
            logging.warning('qq auth error: %s' % str(response))
            callback(None)
            return

        js = response.body
        logging.info('resp: %s', js)
        if js.startswith('callback('):
            js = js[9:-3].strip()
            args = escape.json_decode(js)
        else:
            args = escape.parse_qs_bytes(escape.native_str(js))
        if 'error' in args:
            logging.warning('qq auth get open_id error: %d, %s',
                 args['error'], args['error_description'])
            callback(None)
            return

        session['access_token'] = args["access_token"][-1]
        session["access_token_expires"] = args.get("expires_in")[-1]
        http = httpclient.AsyncHTTPClient()
        callback = self.async_callback(
            self._on_get_open_id, callback, fields, session)
        url = 'https://graph.qq.com/oauth2.0/me?' + urllib.urlencode(
            {'access_token': session['access_token']})
        http.fetch(url, callback=callback)

    def _on_get_open_id(self, callback, fields, session, response):
        if response.error:
            logging.warning('qq auth get open_id error: %s', str(response))
            callback(None)
            return
        logging.debug('get open id return: %s', str(response))
        js = response.body
        logging.info('open id resp: %s', js)
        if js.startswith('callback('):
            js = js[9:-3].strip()
        args = escape.json_decode(js)
        if 'error' in args:
            logging.warning('qq auth get open_id error: %d, %s',
                 args['error'], args['error_description'])
            callback(None)
            return
        session['client_id'] = args['client_id']
        session['open_id'] = args['openid']
        self.qq_request(
            path="/user/get_user_info",
            callback=self.async_callback(
                self._on_get_user_info, callback, session, fields),
            access_token=session["access_token"],
            client_id=session["client_id"],
            openid=session['open_id'],
        )

    def _on_get_user_info(self, callback, session, fields, user):
        if user is None:
            callback(None)
            return

        fieldmap = {}
        for field in fields:
            fieldmap[field] = user.get(field)

        fieldmap.update({
            "access_token": session.get("access_token"),
            "access_token_expires": session.get("access_token_expires"),
            "client_id": session.get('client_id'),
            "open_id": session.get('open_id'),
            "nick": user.get('nickname'),
            "portrait": user.get('figureurl_2'),
        })
        callback(fieldmap)

    def qq_request(self, path, callback, access_token=None, client_id=None, open_id=None,
                           post_args=None, **args):
        url = "https://graph.qq.com" + path
        all_args = {}
        if access_token:
            all_args["access_token"] = access_token
        if client_id:
            all_args['oauth_consumer_key'] = client_id
        if open_id:
            all_args["openid"] = open_id
        all_args.update(args)

        if all_args:
            url += "?" + urllib.urlencode(all_args)
        logging.info('qq_request uri: %s', url)
        callback = self.async_callback(self._on_qq_request, callback)
        http = httpclient.AsyncHTTPClient()
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, callback=callback)

    def _on_qq_request(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                            response.request.url)
            callback(None)
            return
        d = escape.json_decode(response.body)
        if 'ret' in d and d['ret']:
            logging.warning("qq request error: %s", response.body)
            callback(None)
            return
        callback(escape.json_decode(response.body))


