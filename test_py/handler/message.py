#!/usr/bin/env python
# coding: utf-8

""" 消息接口
"""

from tornado.web import HTTPError
import time
import json
from tornado.escape import json_decode

import handler.api
from model.message import Message
from model.topic import Topic
import model.user
import hqby.item
from hqby.config import configs


def url_spec(**kwargs):
    return [
        (r'/message/(?P<type>(?:delete)|(?:all)|(?:number))/?(?P<page>\d+)?/?$',
         MessageHandler, kwargs),
        (r'/message/(?P<type>(?:read))/(?P<msg_id>\d+)/?', MessageHandler, kwargs),
    ]


class MessageHandler(handler.api.ApiHandler):

    @handler.api.token_required()
    def get(self, **kwargs):
        """ 获取各种类型的未读消息, 未读消息数量, 全部的未读消息
        """
        type = kwargs.get('type')
        if not type or type not in ['delete', 'number', 'all']:
            raise HTTPError(400, 'type err')
        page = kwargs.get('page') or 0
        if type == 'number':
            data = self._msg_number(user_id=kwargs['uid'])
        elif type == 'delete':
            data = self._delete_all(user_id=kwargs['uid'])
        else:
            data = self._get_msgs(user_id=kwargs['uid'], type=type, page=page)
        self.write(data)
        self.set_status(201)

    @handler.api.token_required()
    def post(self, **kwargs):
        """  接口: 1. 标记消息为已读-read
                  2. 设置系统消息-sys
        """
        type = kwargs.get('type')
        msg_id = kwargs.get('msg_id')
       # self.write({'read msg_id':msg_id})
       # return
        if type == 'read' and msg_id:
            result = Message.mark_read(user_id=kwargs['uid'], msg_id=msg_id)
        elif type == 'sys' and (kwargs['uid'] == 'admin' or configs['test_mode']):  # todo 系统用户才能设置系统消息
            data = json_decode(self.request.body)
            content = data.get('content')
            if content:
                result = Message.set_message(type=Message._type_sys, content=content)
        else:
            raise HTTPError(404, 'not support post method or user not support')
        self.write(result.dictify())
        self.set_status(201)

    def _get_msgs(self, user_id, type, page=0):
        """ 获取用户的未读消息
        """
        page = int(page) if page is not None else page
        msgs = Message.get_message(user_id=user_id, type=type, page=page)
        datas = []
        for m in msgs:
            data = self._msg_data(m)
            if data:
                datas.append(data)
        return {
            'class': 'message',
            'msgs': datas,
            'type': type,
            'next_page': str(page+1)
            }

    def _msg_number(self, user_id):
        """ 获取用户未读消息数量
        """
        #return str(Message.unread_num(user_id=user_id))
        return {
            'class': 'number',
            'number': Message.unread_num(user_id=user_id)
        }

    def _delete_all(self, user_id):
        """删除用户所有未读信息
        """
        n = Message.delete_all(user_id=user_id)
        if n ==0:
            status = 1
        else:
            status = 0
        return {
            'class': 'delete',
            'status': status
        }

    def _msg_data(self, msg):
        """ 统一返回格式 - 带上 comment, item
        """
        data = Message._msg_data(msg)
        if data['link_id']:
            topic = Topic.get(data['link_id'])
            topic = Topic._topic_data(topic)
            data['topic'] = topic
            tmp_user = model.user.get_user(user_id=topic['user_id'])  # 消息来源用户
            if not tmp_user:
                return None
            data['topic_user'] = {
                'id': tmp_user['id'],
                'nick': tmp_user['nick'],
                'portrait': tmp_user['portrait'],
                'type': tmp_user['user_type'],
                } if tmp_user else {}
        if data['from_uid']:
            tmp_user = model.user.get_user(user_id=data['from_uid'])  # 消息来源用户
            if not tmp_user:
                return None
            data['from_user'] = {
                'id': tmp_user['id'],
                'nick': tmp_user['nick'],
                'portrait': tmp_user['portrait'],
                'type': tmp_user['user_type'],
                } if tmp_user else {}
        data['class'] = 'message'
        return data
