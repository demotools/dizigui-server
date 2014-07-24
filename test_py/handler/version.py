#!/usr/bin/env python
# coding: utf-8

from tornado.web import HTTPError
from tornado.escape import json_decode

import handler.api


def url_spec(**kwargs):
    return [
        (r'/version/?', VersionHandler, kwargs),
    ]


class VersionHandler(handler.api.ApiHandler):
    """ 安卓版本更新
    """

    def get(self, **kwargs):
        info = {}
        info['version'] = '1.1'
        info['url'] = 'http://img.dujing.com/ReadingClassicsApp.apk'
        info['msg'] = '检测到最新版本，请及时更新！'
        self.write(info)

