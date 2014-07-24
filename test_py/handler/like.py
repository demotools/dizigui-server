#!/usr/bin/env python
# coding: utf-8

from tornado.web import HTTPError

import handler.api
from model.topic import Topic
from model.comment import Comment
import model.like
import hqby.user
from model.message import Message


def url_spec(**kwargs):
    return [
        #(r'/like/(?P<mode>(?:topic/(?P<topic_id>\d+))|(?:comment/(?P<comment_id>\d+)))?', LikeHandler, kwargs),
        (r'/like/(?P<mode>(?:topic)|(?:comment))/(?P<item_id>\d+)', LikeHandler, kwargs),

    ]


class LikeHandler(handler.api.ApiHandler):

    @handler.api.token_required(True)
    def get(self, **kwargs):
        uid = kwargs['uid']
        mode = kwargs['mode']
        item_id = int(kwargs['item_id'])
        user = hqby.user.get_user_info(uid=uid)
        if not user:
            raise HTTPError(403, 'can not found this user')
        if mode not in ['topic','comment']:
            raise HTTPError(400,'type not topic or comment')
        if mode == 'topic':          
            #如果赞的是心得 先从缓存中找赞  没赞过的话就新建赞
            key = "0"+uid+str(item_id)
            zan = model.like.get_zan(uid,item_id,0,key)
            if not zan:             
                #更新心得里的like_num  新建赞  新建msg 
                item = Topic.update_topic(item_id, True, False)
                item_data = Topic._topic_data(item)
                zan = {'user_id':str(uid),'item_id':item_data['topic_id'],'item_type':0}
                zan = model.like.create_like(zan)
                msg = self.create_msg('TL', user, item_data)
                self.write({'status':1,'type':mode,'like_num':item_data['like_num'],'uid':uid,'like_id':zan['id'],'msg':msg})
            else:
                self.write({'status':0,'type':mode,'msg':'already liked'})
        elif mode == 'comment':       
            #如果赞的是评论 先从缓存中找赞  没赞过的话就新建赞
            key = "1"+uid+str(item_id)
            zan = model.like.get_zan(uid,item_id,1,key)
            if not zan:
                item = Comment.update_comment(item_id,True)
                zan = {'user_id':str(uid),'item_id':item['id'],'item_type':1}
                zan = model.like.create_like(zan)
                msg = self.create_msg('CL', user, item)
                self.write({'status':1,'type':mode,'like_num':item['like_num'],'uid':uid,'like_id':zan['id'],'msg':msg})
            else:
                self.write({'status':0,'type':mode,'msg':'already liked'})
        return

    def create_msg(self, msg_type, user, item):  #建立消息
        to_uid = item['user_id']
        uid = user['_id']
        if uid == to_uid: #如果赞的是自己  不存消息
            return {}
        if msg_type == 'TL':
            m_type = "心得"
            content = user['nick'] + "赞了你的"+m_type + "  \"%s\""%item['content']
        if msg_type == 'CL':
            m_type = "评论"
            if item['c_type'] == 'audio':
                content = user['nick'] + "赞了你的语音"+m_type
            else:
                content = user['nick'] + "赞了你的"+m_type + "  \"%s\""%item['content'] 
        msg = Message.set_message(to_uid, msg_type, uid, content, item['topic_id'])
        msg = Message._msg_data(msg)
        return msg



          
