#!/usr/bin/env python
# coding: utf-8

import json
import time
from tornado.web import HTTPError
from tornado.escape import json_decode
from tornado import gen
from tornado.web import asynchronous


import handler.api
from model.topic import Topic
import model.user
from hqby.config import configs
import hqby.user
import model.like


def url_spec(**kwargs):
    return [
        (r'/topic/(?P<page>\d+)?', AllTopicHandler, kwargs),
        (r'/topic/?(?P<uid>[a-zA-Z0-9\-_]{8})?/?(?P<page>\d+)?', TopicHandler, kwargs),
    ]



class TopicHandler(handler.api.ApiHandler):

    def get(self, **kwargs):
        """
        我的专题
        """
        #token = self.get_secure_cookie('token')
        #self.write('token = %s'%token)
        #return
        token = self._get_token()
        uid = token['_id']
        url_uid = str(kwargs.get('uid'))  # change unicode to str
        if uid != url_uid:
            raise HTTPError(403, 'not the user in token')
        user = hqby.user.get_user_info(uid=uid)
        if not user:
            raise HTTPError(403, 'can not found this user')
        topic_id = kwargs.get('topic_id')
        page = kwargs.get('page')
        page = int(page) if page else 0
        topics = Topic.find_topics(user_id=uid,page=page)
        _all = [self._topic_data(t,uid) for t in topics] if topics else []
        data = {
            'class': 'my_topics',
            'topics': _all,
            'next_page':page+1,
            }
        self.write(data)
        self.set_status(200)

    def post(self, **kwargs):
        """
            新建一个话题 需要用户登录
        """
        token = self._get_token(False)
        uid = token['_id']
        url_uid = str(kwargs.get('uid'))  # change unicode to str
        if uid != url_uid:
            raise HTTPError(403, 'not the user in token')
        user = hqby.user.get_user_info(uid=uid)
        if not user:
            raise HTTPError(403, 'can not found this user')
        try:
            params = json_decode(self.request.body)
        except ValueError:
            params = self.get_form()
        params['user_id'] = uid
        # 添加一个新的专题
        topic = Topic.new(**params)
        data = Topic._topic_data(topic)
        self.write(data)
        self.set_status(200)

    
   
    def _topic_data(self, topic, uid):
        """ 所有专题返回格式包装
        """
        data = self._check_data(topic,uid)
        user = hqby.user.get_user_info(uid=data['user_id'])
        data['user'] = user
        return data

    def _check_data(self, topic, uid):      #检查心得是否被赞过
        data = Topic._topic_data(topic)
        key = "0"+uid+str(data['topic_id'])
        zan = model.like.get_zan(uid,data['topic_id'],0,key)
        data['is_liked'] = 0 if not zan else 1
        return data

    def _items_topic(self, size=3.0/3.2, **kwargs):
        page = kwargs.get('page', 0)
        topic_id = kwargs.get('topic_id')
        if not topic_id:
            return []
        #item_ids = TopicItem.find_item_ids(topic_id=topic_id, page=page)
        #fitems = []
        topic = Topic.get(id=topic_id)
        if not topic:
            return {}
        pre_topics = [self._topic_data(topic=t, fields=['name', 'id', 'image', 'cover', 'intro_img']) for t in topic.get_pre(limit=4)] if not page else []
        items = TopicItem.topic_items(topic_id=topic_id, page=page)
        items = [hqby.item.get_item_info(self, item=item, size=size) for item in items]
        data = {
            'class': 'topic-items',
            'items': items,
            'pre_topics': pre_topics,
            'links': [
                self._link('topic/items/%s' % (topic_id, ), 'first'),
                self._link('topic/items/%s/%s' % (topic_id, page+1, ), 'next'),
            ]
        }
        return data

class AllTopicHandler(TopicHandler):

    @asynchronous
    @gen.engine
    def get(self, **kwargs):
        """
        所有的专题
        """
        token = self._get_token(False)
        uid = token['_id'] if token else '0'
        page = kwargs.get('page')
        page = int(page) if page else 0
        topics = yield gen.Task(Topic.all_topics,page=page)
        _all = [self._topic_data(t,uid) for t in topics] if topics else []
        data = {
            'class': 'all_topics',
            'topics': _all,
            'next_page':page+1,
            }
        self.write(data)
        self.set_status(200)
        self.finish()

        #topics = Topic.all_topics(page=page)
        #_all = [self._topic_data(t,uid) for t in topics] if topics else []
        #data = {
        #    'class': 'all_topics',
        #    'topics': _all,
        #    'next_page':page+1,
        #    }
        #self.write(data)
        #self.set_status(200)
        #self.finish()

