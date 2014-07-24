#!/usr/bin/env python
# coding: utf-8

import sys
reload(sys)
sys.setdefaultencoding('utf-8') #当出现编码错误如UnicodeDecodeError: 'ascii' codec can't decode byte 时 用这三行

import json
import time
from tornado.web import HTTPError
from tornado.escape import json_decode
from tornado import gen
from tornado.web import asynchronous

import handler.api
from model.topic import Topic
from model.comment import Comment
import model.user
from hqby.config import configs, baidu_push_configs
import hqby.user
import model.like
from model.message import Message

from lib.baidu_pusher.Channel import *  #这里要加lib. 因为对于系统库rq来说并不知道baidu_pusher在哪，不像本程序内在dujing.py中声明过
import rq_client


def url_spec(**kwargs):
    return [
        #(r'/topic/(?P<page>\d+)?', AllTopicHandler, kwargs),
        (r'/comment/?(?P<topic_id>\d+)?/?(?P<page>\d+)?', CommentHandler, kwargs),
    ]



class CommentHandler(handler.api.ApiHandler):

    @asynchronous
    @gen.engine
    def get(self, **kwargs):
        """
        话题的评论
        """
        token = self._get_token(False)
        uid = token['_id'] if token else '0'
        tid = kwargs.get('topic_id')
        page = kwargs.get('page')
        page = int(page) if page else 0
        #comments = Comment.find_comment(topic_id=tid,page=page)
        comments = yield gen.Task(Comment.find_comment,tid,page)
        _all = [self._check_data(t,uid) for t in comments] if comments else []
        data = {
            'class': 'comments',
            'topic_id':tid,
            'comments': _all,
            'next_page':page+1,
            }
        self.write(data)
        self.set_status(200)
        self.finish()

    def post(self, **kwargs):
        """
            新建一个评论 需要用户登录
        """
        token = self._get_token()
        uid = token['_id']
        user = hqby.user.get_user_info(uid=uid)
        if not user:
            raise HTTPError(403, 'can not found this user')
        try:
            params = json_decode(self.request.body)
        except ValueError:
            params = self.get_form()
        comment_type = params.get('comment_type', False)
        self.check_comment_type(comment_type)
        self.check_topic(params['topic_id'])
        params['user_id'] = uid
        # 添加一个新的评论
        comm = self.create_comment(params,comment_type)
       # self.write('haha = %s'%comm)
        #return
        data = self._comment_data(comm)
        data['is_liked'] = 0
        topic = Topic.update_topic(data['topic_id'],False,True)
        topic_data = Topic._topic_data(topic)
        if data['to_user_id']:
            to_uid = data['to_user_id']
            msg_type = 'CC'
            content = user['nick'] + '回复了你的评论 ' 
        else:
            to_uid = topic_data['user_id']
            msg_type = 'TC'
            content = user['nick'] + "评论了你的心得 " + "  \"%s\""%topic_data['content'] 
        if uid != to_uid:
            msg = Message.set_message(to_uid, msg_type, uid, content, topic_data['topic_id']) #link_id 是topic的id
            msg = Message._msg_data(msg)
        else:
            msg = 'you reply yourself'
         #给被回复者发送通知
        baidu_apiKey = baidu_push_configs['apiKey']
        baidu_secretKey = baidu_push_configs['secretKey']
        bind_info = hqby.user.get_bind_info(to_uid)
        baidu_uid, baidu_cid = bind_info.get('baidu_uid'), bind_info.get('baidu_cid')
        if baidu_uid and baidu_cid and uid != to_uid:
            message = {
                'title': '读经',
                'description': '%s回复了你，快去看看吧' % user['nick'].encode('utf8'),
                'open_type': 2,
                "aps": {
                    "alert": '%s回复了你，快去看看吧' % user['nick'].encode('utf8'),
	                "sound":"",
                	"badge":0
                    },
                }
            message = json.dumps(message)
            message_key = "sys"
            c = Channel(baidu_apiKey, baidu_secretKey, arr_curlOpts=dict(TIMEOUT=3, CONNECTTIMEOUT=5))
            push_type = 1   # 1-单个人, 2-一群人, 3-全部人
            optional = dict()
            optional[Channel.USER_ID] = baidu_uid
            optional[Channel.CHANNEL_ID] = int(baidu_cid)
            optional[Channel.MESSAGE_TYPE] = 1    # 0-消息, 1-通知
            optional['device_types'] = [3, 4]      # 4-ios, 3-安卓, 5-wp设备, 2-pc, 1-浏览器
            optional['deploy_status'] = 1 if configs['debug'] else 2     # 1-开发, 2-生产
            #job = c.pushMessage(push_type, message, message_key, optional)
            job = rq_client.default_queue.enqueue(c.pushMessage, push_type, message, message_key, optional)
            #logging.info('log for baidu pusher: %s', str(job))
        self.write({'comment':data,'topic':topic_data,'msg':msg})
        self.set_status(200)
        self.set_header('Content-Type', self._ct('json'))

    def check_topic(self, item_id):
        if not item_id:
            raise HTTPError(404)
        item_id = int(item_id)
        i = Topic.get(item_id)
        if not i:
            raise HTTPError(404, 'can not found item with id=%d' % item_id)

    def check_comment_type(self, refer_type):
        if not refer_type:
            raise HTTPError(400, 'missing param comment_type')
        if not (refer_type == 'txt' or refer_type == 'audio'):
            raise HTTPError(400, 'unknown comment type')

    def create_comment(self, params, comment_type):
        if comment_type == 'txt':
            if not params.get('content', False):
                raise HTTPError(403, 'there is not data')
            comment = Comment.new(**params)
        if comment_type == 'audio':
            audio = hqby.audio.get_temp_audio(params['audio_id'])
            info = hqby.audio.move_temp_audio(
                audio, configs['audio_base_path'],
                configs['audio_base_url'],
                hqby.audio.id_to_subdir(params['topic_id'])
            )
            #info['src'] = info['src'].encode('utf-8')
            info['audio_len'] = audio['len']
            info['type'] = audio['type']
            params['content'] = json.dumps(info)
            del params['audio_id']
            comment = Comment.new(**params)
        return comment

    def _comment_data(self, comm, fields=None):
        """ 评论返回格式包装
        """
        data = Comment._comment_data(comm)
        user = hqby.user.get_user_info(uid=data['user_id'])
        data['user'] = user
        to_user = {}
        if data['to_user_id']:
            to_user = hqby.user.get_user_info(uid=data['to_user_id'])
        data['to_user'] = to_user
        return data

    def _check_data(self, comm, uid):  #检查评论是否被赞过
        data = self._comment_data(comm)
        key = "1"+uid+str(data['comment_id'])
        zan = model.like.get_zan(uid,data['comment_id'],1,key)
        data['is_liked'] = 0 if not zan else 1
        return data


