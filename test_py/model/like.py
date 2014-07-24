#!/usr/bin/env python
# coding: utf-8

import json
import hqby.db
import hqby.cache
from hqby.config import configs
from hashlib import md5
import torndb
import logging


def create_like(zan):
    """ 新建一个赞
    """
    dbc = hqby.db.get_conn(configs['db_name'])
    for i in range(3):
        try:
            lid = dbc.execute(
            "INSERT INTO zan (user_id, item_id ,item_type)"
            "VALUES (%s, %s, %s)",
            zan['user_id'], zan['item_id'], zan['item_type']
            )
            break
        except torndb.IntegrityError as e:
            if e[1].find("for key 'account'") >= 0:
                return 'dup'
            else:
                logging.exception('insert error id=%s account=%s', uid, user['account'])
    key = str(zan['item_type'])+zan['user_id']+str(zan['item_id'])
    return get_zan(zan['user_id'],zan['item_id'],zan['item_type'], key)

@hqby.cache.cached('test2', 'like-', _key='key', pickled=True, mode=configs['cache_mode'])
def get_zan(user_id, item_id, item_type, key):
    dbc = hqby.db.get_conn(configs['db_name'])
    zan = dbc.get("SELECT * FROM zan WHERE user_id = %s and item_id = %s and item_type = %s limit 1", user_id, item_id, item_type)
    return zan


