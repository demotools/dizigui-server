#!/usr/bin/env python
# coding: utf-8

from hqby.util import HqOrm, and_, set_, or_
import hqby.cache
from hqby.config import configs
import cPickle
import hqby.db


class Notification(HqOrm):
    """ 推送信息表:
    """
    
    _table_name = 'notification'
    _rows = [
        'id', 'user_id', 'device', 'version', 'uuid', 'baidu_uid', 'baidu_cid']
    
    _id = 'user_id'

    @classmethod
    def new(cls, user_id, device, version, uuid, baidu_uid, baidu_cid):
        """ 新建推送信息
        """
        data = dict(
            user_id=user_id,
            device=device,
            version=version,
            uuid=uuid,
            baidu_uid=baidu_uid,
            baidu_cid=baidu_cid,
        )
        return super(Notification, cls).new(**data)


    @classmethod
    @hqby.cache.cached(configs['redis_name'], 'push-', _key='uid', pickled=True, mode=configs['cache_mode'])
    def get_notification(cls, uid, fields=None):
        #dbc = hqby.db.get_conn(configs['db_name'])
        #t = dbc.get("SELECT * FROM notification WHERE user_id = %s limit 1", uid)
        t = super(Notification, cls).get(user_id=uid, fields=fields)
        return t if t else None

 
    @classmethod 
    @hqby.cache.cached(configs['redis_name'], 'push-', _key='uid', pickled=True, mode='set')
    def update_notification(cls, uid, device, version, uuid, baidu_uid, baidu_cid):
        """ 更新推送信息同时更新缓存 返回推送信息
        """
        dbc = hqby.db.get_conn(configs['db_name'])
        sql = "UPDATE notification SET device=%s, version=%s, uuid=%s, baidu_uid=%s, baidu_cid=%s WHERE user_id=%s"
        params = [device,version,uuid,baidu_uid,baidu_cid,uid]
        dbc.execute(sql, *params)
       # return dbc.get("SELECT * FROM comment WHERE id = %s limit 1", id)
        return super(Notification, cls).get(user_id=uid, fields=None)

    @classmethod 
    def _notification_data(cls, push, fields=None):
        """ 推送信息返回格式包装
        """
        if not push:
            return {}
        data = push.dictify(fields=fields)
        data['notification_id'] = data['id']
        del data['id']
        return data

    @classmethod
    def delete_all(cls, user_id):
        key_all = 'push-' + str(user_id)
        conn = hqby.cache.get_sync_conn(configs['redis_name'])
        conn.delete(key_all)
        return 1
        


