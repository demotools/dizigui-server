#!/usr/bin/env python
# coding: utf-8

from hqby.util import HqOrm, and_, set_, or_
import hqby.cache
from hqby.config import configs
import cPickle
import logging
import time
import json

class Comment(HqOrm):
    """ 评论:
    """
    
    _table_name = 'comment'
    _rows = [
        'id', 'user_id', 'topic_id', 'c_type', 'content', 'status', 'to_user_id', 'like_num', 'ins_time']
    #_db_config = configs['db_config']
    _per_page = 10

    status_ok  = 1  #可用
    status_del = 0 #删除

    @classmethod
    def new(cls, user_id, topic_id, comment_type, content, to_user_id=0, like_num=0):
        """ 新建话题
        """
        data = dict(
            user_id=user_id,
            topic_id=topic_id,
            c_type=comment_type,
            content=content,
            status=cls.status_ok,
            to_user_id=to_user_id,
            like_num=like_num,
        )
        return super(Comment, cls).new(**data)


    @classmethod
    @hqby.cache.cached('test2', 'comment-', _key='id', pickled=True, mode=configs['cache_mode'])
    def get(cls, id, fields=None):
        t = super(Comment, cls).get(id=id, fields=fields)
        return t if t.status else None

    @classmethod
    def find_comment(cls, topic_id, page=0, order_by='ins_time desc, id desc',callback=None):
        """ 获取评论
        """
        c = cls.page(
            page=page,
            status=cls.status_ok,
            topic_id=topic_id,
            order_by=order_by,
        )

        if callback:
            return callback(c)
     
    @classmethod 
    @hqby.cache.cached('test2', 'comment-', _key='id', pickled=True, mode='set')
    def update_comment(cls, id, like=False):
        """ 更新评论信息同时更新缓存 返回评论信息
        """
        dbc = hqby.db.get_conn('test2')
        if like:
            sql = "UPDATE comment SET like_num=like_num+1 WHERE id=%s"
            params = [id]
        else:
            logging.exception('like err')
        dbc.execute(sql, *params)
        return dbc.get("SELECT * FROM comment WHERE id = %s limit 1", id)

    @classmethod 
    def _comment_data(cls, comm, fields=None):
        """ 评论返回格式包装
        """
        if not comm:
            return {}
        data = comm.dictify(fields=fields)
        data['comment_id'] = data['id']
        del data['id']
        #data['ins_time'] = int(data['ins_time'])
        timeArray = time.strptime(data['ins_time'], "%Y-%m-%d %H:%M:%S")
        data['ins_time'] = int(time.mktime(timeArray))
        data['content'] = json.loads(data['content']) if data['c_type'] == 'audio' else data['content']
        return data




