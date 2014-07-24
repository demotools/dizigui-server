#!/usr/bin/env python
# coding: utf-8

from hqby.util import HqOrm, and_, set_, or_
import hqby.cache
from hqby.config import configs
import cPickle
import logging
import time


class Topic(HqOrm):
    """ 话题:
        - 设置消息
        - 获取用户的未读消息
        - 标记消息已读
    """
    
    _table_name = 'topic'
    _rows = [
        'id', 'user_id', 'content', 'type', 'status', 'ins_time', 'like_num', 'comment_num',  'last_comt_time', 'level', 'fix_time'
    ]
    #_db_config = configs['db_config']
    _per_page = 10

    status_ok  = 1  #可用
    status_del = 0 #删除

    type_understanding = 0 #心得

    @classmethod
    def new(cls, user_id, content, type=type_understanding, like_num=0, comment_num=0):
        """ 新建话题
        """
        if not user_id:
            return None
        data = dict(
            user_id=user_id,
            content=content,
            type=type,
            status=cls.status_ok,
            like_num=like_num,
            comment_num=comment_num,
        )
        return super(Topic, cls).new(**data)


    @classmethod
    @hqby.cache.cached('test2', 'topic-', _key='id', pickled=True, mode=configs['cache_mode'])
    def get(cls, id, fields=None):
        t = super(Topic, cls).get(id=id, fields=fields)
        return t if t else None

    @classmethod
    def find_topics(cls, user_id, page=0, order_by='fix_time desc, level desc, ins_time desc, id desc'):
        """ 获取话题
        """
        return cls.page(
            page=page,
            status=cls.status_ok,
            user_id=user_id,
            order_by=order_by,
        )


    @classmethod
    def all_topics(cls, page=0, order_by='fix_time desc, level desc, ins_time desc, id desc',callback=None):
        """ 获取所有话题
        """
        t = cls.page(
            page=page,
            status=cls.status_ok,
            order_by=order_by,
        )
        if callback:
            return callback(t)
        #return cls.page(
        #    page=page,
        #    status=cls.status_ok,
        #    order_by=order_by,
        #)
  
    @classmethod 
    @hqby.cache.cached('test2', 'topic-', _key='id', pickled=True, mode='set')
    def update_topic(cls, id, like=False, comment=False):
        """ 更新话题信息同时更新缓存 返回话题信息
        """
        dbc = hqby.db.get_conn('test2')
        if like:
            sql = "UPDATE topic SET like_num=like_num+1 WHERE id=%s"
            params = [id]
        elif comment:
            sql = "UPDATE topic SET comment_num=comment_num+1, last_comt_time = sysdate() WHERE id=%s"
            params = [id]
        else:
            logging.exception('no like or comment')
        dbc.execute(sql, *params)
        #return dbc.get("SELECT * FROM topic WHERE id = %s limit 1", id)
        return super(Topic, cls).get(id=id, fields=None)
    
    @classmethod 
    def _topic_data(cls, topic, fields=None):
        """ 专题返回格式包装
        """
        if not topic:
            return {}
        data = topic.dictify(fields=fields)
        data['topic_id'] = data['id']
        del data['id']
        #data['ins_time'] = int(data['ins_time'])
        timeArray = time.strptime(data['ins_time'], "%Y-%m-%d %H:%M:%S")
        data['ins_time'] = int(time.mktime(timeArray))
        if data['last_comt_time']:
            timestr = data['last_comt_time'].strftime("%Y-%m-%d %H:%M:%S")
            timeArray = time.strptime(timestr, "%Y-%m-%d %H:%M:%S")
            data['last_comt_time'] = int(time.mktime(timeArray))

        if data['fix_time']:
            timestr = data['fix_time'].strftime("%Y-%m-%d %H:%M:%S")
            timeArray = time.strptime(data['fix_time'], "%Y-%m-%d %H:%M:%S")
            data['fix_time'] = int(time.mktime(timeArray))

        return data



