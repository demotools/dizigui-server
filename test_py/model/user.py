#!/usr/bin/env python
# coding: utf-8

import json
import hqby.db
import hqby.cache
from hqby.config import configs
from hashlib import md5
import torndb
import logging

_admins = {
    'hqadmin': True,
}


def find_zombie_users():
    """ 系统僵尸用户, auth_type=zombie
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = 'select * from users where auth_type=%s'
    params = ['zombie', ]
    return dbc.query(sql, *params)


def create_user(user):
    """ 新建一个用户
    """
    dbc = hqby.db.get_conn('test2')
    for i in range(3):
        try:
            uid = dbc.execute(
            "INSERT INTO users (id, account, passwd, auth_type, bind_sina, bind_tqq, bind_qq, portrait, nick,auth_time)"
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, sysdate())",
            user['id'], user['account'], user['passwd'], user['auth_type'], user['bind_sina'], user['bind_tqq'],
            user['bind_qq'], user['portrait'], user['nick']
            )
            break
        except torndb.IntegrityError as e:
            if e[1].find("for key 'account'") >= 0:
                return 'dup'
            else:
                logging.exception('insert error id=%s account=%s', uid, user['account'])
    return uid


def get_admin(account, pwd):
    """ 管理员:
        account: hqadmin
        pwd: adminhq
    """
    dbc = hqby.db.get_conn('tonghua')
    pwd = md5(pwd).hexdigest()
    if not _admins.get(account):
        return None
    sql = 'select * from users where account=%s and passwd=%s limit 1'
    params = [account, pwd]
    admin = dbc.get(sql, *params)
    return admin


@hqby.cache.cached('test2', 'user-', _key='user_id', pickled=True, mode=configs['cache_mode'])
def get_user(user_id):
    dbc = hqby.db.get_conn('test2')
    user = dbc.get("SELECT * FROM users WHERE id = %s limit 1", user_id)
    return user


def register_user(user_id, email, nick, passwd):
    dbc = hqby.db.get_conn('tonghua')
    sql = 'INSERT INTO users (id, account, passwd, nick) VALUES (%s, %s, %s, %s)'
    return dbc.execute_lastrowid(sql, user_id, email, passwd, nick)


@hqby.cache.cached('test2', 'user-', _key='user_id', pickled=True, mode='set')
def update_user(user_id, portrait, nick, age, phone, email):
    """ 更新用户信息同时更新缓存 返回用户信息
    """
    dbc = hqby.db.get_conn('test2')
    sql = "UPDATE users SET portrait=%s, nick=%s, age=%s, phone=%s, email=%s WHERE id=%s"
    params = [portrait, nick, age, phone, email, user_id]
    dbc.execute(sql, *params)
    return dbc.get("SELECT * FROM users WHERE id = %s limit 1", user_id)


def get_some_users(last_uno=0, count=500):
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT * FROM users ORDER BY user_no DESC LIMIT %s"
    params = [count]
    if last_uno:
        sql = sql.replace(' ORDER ', ' WHERE user_no < %s ORDER ')
        params.insert(-1, last_uno)
    return dbc.query(sql, *params)


def upgrade_user(user_id, grade):
    dbc = hqby.db.get_conn('tonghua')
    sql = "UPDATE users SET user_type=%s WHERE id=%s"
    params = [grade, user_id]
    return dbc.execute(sql, *params)


def find_total_user():
    dbc = hqby.db.get_conn('tonghua')
    rows = dbc.query("SHOW TABLE STATUS WHERE name='users'")
    return rows[0]['Rows']


def stat_type_user(auth_type='sina'):
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT count(id) FROM users WHERE auth_type=%s"
    params = [auth_type]
    num = dbc.query(sql, *params)
    return num[0].get('count(id)', 0) if num else 0


def get_bind_info(uid):
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT * FROM users WHERE id = %s"
    params = [uid]
    return dbc.get(sql, *params)


def check_existed_bdinfo(bd_info):
    dbc = hqby.db.get_conn('tonghua')
    sql = "UPDATE users SET baidu_uid='', baidu_cid='' \
           WHERE baidu_uid=%s AND baidu_cid=%s"
    params = [bd_info['bd_uid'], bd_info['bd_cid']]
    return dbc.execute(sql, *params)


def bind_bdinfo(uid, bd_info):
    dbc = hqby.db.get_conn('tonghua')
    sql = "UPDATE users SET baidu_uid=%s, baidu_cid=%s\
           WHERE id = %s"
    params = [bd_info['bd_uid'], bd_info['bd_cid'], uid]
    return dbc.execute(sql, *params)


def bind_iosinfo(uid, ios_info):
    dbc = hqby.db.get_conn('tonghua')
    sql = 'UPDATE users SET iphone_id=%s WHERE id=%s'
    params = [ios_info['iphone_id'], uid]
    return dbc.execute(sql, *params)


def clear_existed_iosinfo(ios_info):
    dbc = hqby.db.get_conn('tonghua')
    sql = "UPDATE users SET iphone_id='' WHERE iphone_id=%s"
    return dbc.execute(sql, ios_info['iphone_id'])


def top_users(limit):
    dbc = hqby.db.get_conn('tonghua')
    sql = 'select users.*, top_users.status, top_users.created from top_users join users on top_users.user_id=users.id \
           where top_users.status=1 order by top_users.created desc limit %s'
    params = [limit, ]
    return dbc.query(sql, *params)


def user_works(user_id):
    """ 获取用户的精选作品, item3, book2
    """
    item_limit = 3
    book_limit = 2
    dbc = hqby.db.get_conn('tonghua')
    sql = '(select * from items where user_id=%s and type=%s and status=1 order by star_level desc limit %s) union all \
           (select * from items where user_id=%s and type=%s and status=1 order by star_level desc limit %s)'
    params = [user_id, 'item', item_limit, user_id, 'book', book_limit]
    return dbc.query(sql, *params)
