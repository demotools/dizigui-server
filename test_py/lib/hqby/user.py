#!/usr/bin/env python
# coding: utf-8

import json
import time
import model.user
from model.notification import Notification
from hqby.config import configs

def get_user_info(uid, user=None):
    """
        用户额外的信息保存-ext_data: 包括 - phone, address, email, qq, intro
    """
    tmp_user = model.user.get_user(user_id=uid) if not user else user
    if tmp_user:
        user = dict()
        user['_id'] = tmp_user['id']
        user['user_no'] = tmp_user['user_no']
        user['user_type'] = tmp_user['user_type']
        user['nick'] = tmp_user['nick']
        user['age'] = tmp_user['age']
        user['portrait'] = tmp_user['portrait']
        user['phone'] = tmp_user['phone']
        user['email'] = tmp_user['email']
        return user
    else:
        return None


def update_user(user_id, portrait, nick, age, phone, email):
    return model.user.update_user(user_id, portrait, nick, age, phone, email)



def get_bind_info(uid):
    #n = Notification.delete_all(uid)     #测试删除缓存
    #return {}
    push = Notification.get_notification(uid)
    if push:
        push = Notification._notification_data(push)
        #push['notification_id'] = push['id']
        #del push['id']
        return push
    return {}


def update_bdinfo(bd_info):
    push = Notification.update_notification(bd_info['uid'], bd_info['device'], bd_info['version'], bd_info['uuid'], bd_info['baidu_uid'], bd_info['baidu_cid'])
    return Notification._notification_data(push)


def bind_bdinfo(bd_info):
    push = Notification.new(bd_info['uid'], bd_info['device'], bd_info['version'], bd_info['uuid'], bd_info['baidu_uid'], bd_info['baidu_cid'])
    return Notification._notification_data(push)

