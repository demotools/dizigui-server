#!/usr/bin/env python
# coding: utf-8

from hqby.util import HqOrm, and_, set_, or_
import hqby.cache
from hqby.config import configs
import cPickle
import logging
import time


class Message(HqOrm):
    """ 消息系统支持:
        - 设置消息
        - 获取用户的未读消息
        - 标记消息已读
    """

    _table_name = 'message'
    _rows = ['id', 'user_id', 'from_uid', 'type', 'content', 'status', 'link_id', 'ins_time']

    _status_unread = 0  # 未读消息
    _status_read = 1
    _status_del = 2 #删除消息

    _type_TC = 'TC'  #心得被回复
    _type_TL = 'TL'  #心得被赞
    _type_CC = 'CC'  #回复被回复
    _type_CL = 'CL'  #回复被赞
    _type_TS = 'TS'  #心得被分享
    _type_sys = 'sys'  #系统消息

    _types = ['TC', 'TL', 'CC', 'CL', 'TS', 'sys']

    _cache_key = 'message-%s-%s'
    _cache = not configs['test_mode']

    _per_page = 20

    @classmethod
    def set_message(cls, user_id, msg_type, from_uid='', content='', link_id=0, status=_status_unread):
        """ 新建消息 - 指定类型
        """
        if msg_type not in cls._types:
            return 'type not right'
        if (msg_type != 'sys' and link_id == 0):
            return 'link_id   missing'
        msg = cls.new(
            user_id=user_id,
            from_uid=from_uid,
            type=msg_type,
            content=content,
            status=status,
            link_id=link_id,
        )
        if cls._cache:  # cache
            #key_type = cls._cache_key % (user_id, type)
            key_all = cls._cache_key % (user_id, 'all')
            conn = hqby.cache.get_sync_conn(configs['redis_name'])
            # 更新缓存
            #type_msgs = conn.get(key_type)
            all_msgs = conn.get(key_all)
            try:
                #if type_msgs and msg:
                #    conn.set(key_type, cPickle.dumps(cPickle.loads(type_msgs).append(msg)))
                #    logging.info('[Cache Update]: Success > %s' % key_type)
                if all_msgs and msg:
                    conn.set(key_all, cPickle.dumps(cPickle.loads(all_msgs).append(msg)))
                    logging.info('[Cache Update]: Success > %s' % key_all)
            except Exception as ex:  # 有异常 清空缓存
                logging.error('[Cache Update]: Error > ' + str(ex))
                #conn.delete(key_type)
                conn.delete(key_all)
        return msg

    @classmethod
    def get_message(cls, user_id, type='all', page=0):
        """  获取用户的未读消息, 缓存分页支持. page=None 获取全部的未读消息
        """
        key = cls._cache_key % (user_id, type)
        conn = hqby.cache.get_sync_conn(configs['redis_name'])
        try:
            messages = conn.get(key) if cls._cache else None
            if messages:
                messages = cPickle.loads(messages)
                logging.info('[Cache Get]: Success > ' + key)
        except Exception as ex:
            logging.error('[Cache Get]: Error > ' + str(ex))
            messages = None
        if not messages or not cls._cache:
            param = dict(
                status=cls._status_unread,
                order_by='ins_time desc',
            )
            if type != 'all':
                param['type'] = type
                param['user_id'] = user_id
            elif type == 'all':
                param['user_id'] = user_id
            alls = cls.find(**param)
            usermsgs = []
            for msg in alls:
                # 进行重组排序 写入缓存
                usermsgs.append(msg)
            messages = usermsgs
            if cls._cache:
                conn.set(key, cPickle.dumps(messages))
                logging.info('[Cache Set]: Success > ' + key)
        return messages[page*cls._per_page: (page+1)*cls._per_page] if page is not None else messages

    @classmethod
    def unread_num(cls, user_id):
        """ 获取某个用户的未读消息数量
        """
        return len(cls.get_message(user_id=user_id, page=None))

    @classmethod
    def mark_read(cls, user_id, msg_id):
        """ 标记消息为已读
        """
        msg = cls.get(id=msg_id, status=cls._status_unread)
        if not msg:
            return
        if msg.user_id == user_id:
            msg.status = cls._status_read
            data = msg.save()
        # 更新缓存
        if cls._cache:
            #key_type = cls._cache_key % (user_id, msg.type)
            key_all = cls._cache_key % (user_id, 'all')
            conn = hqby.cache.get_sync_conn(configs['redis_name'])
           # type_msgs = conn.get(key_type)
            all_msgs = conn.get(key_all)
            try:
                #if type_msgs:
                #    type_msgs = [m for m in cPickle.loads(type_msgs) if int(m.id) != int(msg_id)]
                #    conn.set(key_type, cPickle.dumps(type_msgs))
                #     logging.info('[Cache Update]: Success > ' + str(key_type))
                if all_msgs:
                    all_msgs = [m for m in cPickle.loads(all_msgs) if int(m.id) != int(msg_id)]
                    conn.set(key_all, cPickle.dumps(all_msgs))
                    logging.info('[Cache Update]: Success > ' + str(key_all))
            except Exception as ex:
                logging.error('[Cache Update]: Error > ' + str(ex))
                conn.delete(key_all)
                #conn.delete(key_type)
        return data

    @classmethod
    def delete_all(cls, user_id):
        n = cls.unread_num(user_id)
        if n != 0:
            cls.cls_update(set_(status=cls._status_read), and_(user_id=user_id))
            if cls._cache:
                key_all = cls._cache_key % (user_id, 'all')
                conn = hqby.cache.get_sync_conn(configs['redis_name'])
                conn.delete(key_all)
        return cls.unread_num(user_id)


    @classmethod 
    def _msg_data(cls, msg, fields=None):
        """ 消息返回格式包装
        """
        if not msg:
            return {}
        data = msg.dictify(fields=fields)
        data['msg_id'] = data['id']
        del data['id']
        timeArray = time.strptime(data['ins_time'], "%Y-%m-%d %H:%M:%S")
        data['ins_time'] = int(time.mktime(timeArray))
        return data
