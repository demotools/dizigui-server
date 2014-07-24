#!/usr/bin/env python
# coding: utf-8

import hqby.db
from hqby.config import configs
from tornado.web import HTTPError

from hqby.util import HqOrm
from model.score import Score  # 积分记录
import hqby.cache
import logging


def find_user_action(score_uid):
    """查找是否存在该用户的积分记录
    """
    dbc = hqby.db.get_conn('tonghua')
    tmp_user_action = dbc.query(
        "SELECT id FROM user_actions WHERE score_uid = %s LIMIT 1",
        score_uid
    )
    return True if tmp_user_action else False


def get_latest_score(score_uid):
    """
        获取用户最新积分
    """
    us = Score.get(user_id=score_uid)
    return (us.total, us.current) if us else (0, 0)
    # dbc = hqby.db.get_conn('tonghua')
    # result = dbc.query(
    #     "SELECT * FROM user_actions WHERE score_uid = %s ORDER BY id DESC",
    #     score_uid
    # )
    # if not result:
    #     total_score, hand_score = 0, 0
    # else:
    #     total_score, hand_score = result[0]['total_score'], result[0]['hand_score']
    # return total_score, hand_score


def register(actor_uid, score_uid, item_id):
    """记录注册时的行为，并初始化积分为0，此时item_id为-1
    """
    dbc = hqby.db.get_conn('tonghua')
    action = 'register'
    max_try = 3
    for i in range(max_try):
        try:
            dbc.execute(
                "INSERT INTO user_actions ( \
                    actor_uid, action, score_uid, \
                    item_id, ins_time) "
                "VALUES (%s, %s, %s, %s, now())",
                actor_uid, action, score_uid, item_id
            )
        except Exception as ex:
            raise ex
        break
    else:
        raise Exception('Table user_actions Error', 'unable to create user register action')
    # 初始化积分记录
    Score.init_score(user_id=score_uid)


def publish(actor_uid, score_uid, item_id):
    """记录发布行为，并增加相应积分
    """
    dbc = hqby.db.get_conn('tonghua')
    action = 'publish'
    total_score, hand_score = get_latest_score(score_uid)
    add_score = configs['action_scores']['publish']
    max_try = 3
    for i in range(max_try):
        try:
            dbc.execute(
                "INSERT INTO user_actions ( \
                    actor_uid, action, score_uid, \
                    total_score, hand_score, \
                    item_id, ins_time) "
                "VALUES (%s, %s, %s, %s, %s, %s, now())",
                actor_uid, action, score_uid,
                total_score + add_score, hand_score + add_score,
                item_id
            )
        except Exception as ex:
            raise ex
        break
    else:
        raise Exception('Table user_actions Error', 'unable to create user publish action')
    # 记录积分
    Score.add(score=add_score, user_id=score_uid)


def love_and_share(actor_uid, score_uid, item_id):
    """ 记录喜欢和分享行为，并增加相应积分
    """
    dbc = hqby.db.get_conn('tonghua')
    action = 'love'
    total_score, hand_score = get_latest_score(score_uid)
    add_score = configs['action_scores']['love']

    sql = "SELECT id FROM user_actions \
            WHERE actor_uid=%s AND action=%s \
            AND score_uid=%s AND item_id=%s LIMIT 1"
    params = [actor_uid, 'love', score_uid, item_id]
    tmp_result = dbc.query(sql, *params)
    if tmp_result:
        return False

    max_try = 3
    for i in range(max_try):
        try:
            dbc.execute(
                "INSERT INTO user_actions ( \
                    actor_uid, action, score_uid, \
                    total_score, hand_score, \
                    item_id, ins_time) "
                "VALUES (%s, %s, %s, %s, %s, %s, now())",
                actor_uid, action, score_uid,
                total_score + add_score, hand_score + add_score,
                item_id
            )
        except Exception as ex:
            raise ex
        break
    else:
        raise Exception('Table user_actions Error', 'unable to create user love action')
    Score.add(score=add_score, user_id=score_uid)
    # update cache
    get_loved_items(actor_uid, mode='set')
    return True


def comment(actor_uid, score_uid, item_id, comment_id):
    """记录评论行为，并增加相应积分
    """
    dbc = hqby.db.get_conn('tonghua')
    action = 'comment'
    total_score, hand_score = get_latest_score(score_uid)
    add_score = configs['action_scores']['comment']
    max_try = 3
    for i in range(max_try):
        try:
            dbc.execute(
                "INSERT INTO user_actions ( \
                    actor_uid, action, score_uid, \
                    total_score, hand_score, \
                    item_id, comment_id, ins_time) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, now())",
                actor_uid, action, score_uid,
                total_score + add_score, hand_score + add_score,
                item_id, comment_id
            )
        except Exception as ex:
            raise ex
        break
    else:
        raise Exception('Table user_actions Error', 'unable to create user comment action')
    try:
        conn = hqby.cache.get_sync_conn('tonghua')
        key = 'item-comment-count-' + str(item_id)
        #value = conn.get(key)
        #if value:
        #    value = int(value) + 1
        #else:
        value = dbc.query("SELECT count(id) FROM comments WHERE item_id = %s", item_id)[0].get('count(id)', 0)
        conn.set(key, value)
        logging.info('[Cache Update]: success-%s' % key)
    except Exception as ex:
        logging.error('[Cache update]: error-%s-%s' % (key, str(ex)))
    return Score.add(score=add_score, user_id=score_uid)


def get_user_action(actor_uid, last_row, count):
    """ 获取用户的行为记录
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT * FROM user_actions \
           WHERE actor_uid = %s AND item_id <> -1 \
           GROUP BY actor_uid,action,score_uid,item_id \
           ORDER BY id DESC LIMIT %s,%s"
    params = [actor_uid, last_row, count]
    return dbc.query(sql, *params)


def get_user_action_and_items(actor_uid, last_row, count, type=None):
    """ 获取用户的行为记录
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT user_actions.*, items.image, items.img_type, items.user_id AS owner, items.status, items.love, \
           items.type FROM user_actions \
           JOIN items ON items.id=user_actions.item_id WHERE items.status=1 AND user_actions.actor_uid=%s \
           AND user_actions.item_id!=-1 ORDER BY id DESC LIMIT %s,%s"
    params = [actor_uid, last_row, count]
    if type and type in ('book', 'item'):
        sql = sql.replace('ORDER', 'AND items.type=%s ORDER')
        params.insert(1, type)
    return dbc.query(sql, *params)


def get_user_score(score_uid, last_row, count):
    """ 获取用户的积分记录
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT * FROM user_actions \
           WHERE score_uid = %s AND (action = 'publish' OR action = 'love')\
           ORDER BY id DESC LIMIT %s,%s"
    params = [score_uid, last_row, count]
    score_records = dbc.query(sql, *params)
    return score_records


def get_publish_total(actor_uid):
    """计算用户发布的总数
    """
    dbc = hqby.db.get_conn('tonghua')
    params = [actor_uid]
    sql = "SELECT * FROM user_actions \
           WHERE actor_uid = %s AND action = 'publish'"
    rows = dbc.query(sql, *params)
    return len(rows)


@hqby.cache.cached('tonghua', 'user-love-items-', _key='actor_uid', pickled=True, mode=configs['cache_mode'])
def get_loved_items(actor_uid, mode=configs['cache_mode']):
    """ 获取用户喜欢过的item_id
    """
    dbc = hqby.db.get_conn('tonghua')
    params = [actor_uid]
    sql = "SELECT item_id FROM user_actions WHERE actor_uid = %s AND action = 'love'"
    rows = dbc.query(sql, *params)
    return set([row['item_id'] for row in rows])


def del_by_item_id(item_id):
    """根据item_id删除用户行为
    """
    dbc = hqby.db.get_conn('tonghua')
    #找到publish该item的记录，取得item_owner
    result = dbc.query(
        "SELECT * FROM user_actions WHERE item_id=%s",
        item_id
    )
    # 对结果行为进行分数的统计, 统计该item总共获取到的积分
    item_score = 0
    for ac in result:
        if ac['action'] != 'remove':
            item_score += configs['action_scores'][ac['action']]
    if result:
        item_owner = result[0]['actor_uid']
    else:
        raise HTTPError(404, 'can not found this item')
    #获取item_owner最新积分
    total_score, hand_score = get_latest_score(item_owner)
    #记录remove行为，并减少相应积分，注意此时item_id为-1
    action = 'remove'
    add_score = -item_score  # configs['action_scores']['remove']
    max_try = 3
    for i in range(max_try):
        try:
            dbc.execute(
                "INSERT INTO user_actions ( \
                    actor_uid, action, score_uid, \
                    total_score, hand_score, \
                    item_id, ins_time) "
                "VALUES (%s, %s, %s, %s, %s, %s, now())",
                item_owner, action, item_owner,
                total_score, hand_score + add_score,
                -1
            )
        except Exception as ex:
            raise ex
        break
    else:
        raise Exception('Table user_actions Error', 'unable to create user remove action')
    # 在action表中删除与该item有关的记录
    sql = "DELETE FROM user_actions WHERE item_id = %s"
    params = [item_id]
    dbc.execute(sql, *params)
    # 消减积分
    Score.add(score=add_score, user_id=item_owner)


def del_by_comment_id(comment_id):
    """根据comment_id删除用户行为
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "DELETE FROM user_actions WHERE comment_id = %s"
    params = [comment_id]
    dbc.execute(sql, *params)


def find_action_users(item_id, action=None):
    """ 获取针对item的全部行为的用户以及特定行为的用户 - 没有做重复过滤 handler层进行处理
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = 'SELECT users.portrait, users.user_type, users.id, user_actions.actor_uid, user_actions.item_id,  \
           user_actions.action FROM user_actions JOIN users ON user_actions.actor_uid=users.id  \
           WHERE user_actions.item_id=%s'
    if action:
        sql += ' AND user_actions.action=%s'
    sql += ' LIMIT 20'
    params = [item_id, ] if not action else [item_id, action]
    return dbc.query(sql, *params)


def get_user_score_record(user_id, page=0, per_page=15):
    """ 获取用户的积分记录 - 新接口
    """
    dbc = hqby.db.get_conn('tonghua')
    beg = page * per_page
    sql = "SELECT * FROM user_actions \
           WHERE score_uid = %s AND (action = 'publish' OR action = 'love')\
           ORDER BY id DESC LIMIT %s OFFSET %s"
    params = [user_id, per_page, beg]
    return dbc.query(sql, *params)
