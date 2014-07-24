#!/usr/bin/env python
# coding: utf-8

import json
import random
from datetime import date, datetime, timedelta
import hqby.db
import hqby.cache
from hqby.config import configs
from hqby.util import _rebuild_argv, list_to_sql

_rows = [
    'id', 'image', 'type', 'img_type', 'audio', 'org_audio', 'audio_type', 'audio_len', 'note',
    'user_id', 'ip', 'ins_time', 'love', 'share', 'audio_play', 'collect', 'star_level', 'guess', 'status'
]


def find_user_works(uid, type='item', page=0, per_page=15):
    dbc = hqby.db.get_conn('tonghua')
    sql = 'select ' + list_to_sql(_rows) + ' from items where type=%s and status=1 and ' \
                                           'user_id=%s order by ins_time desc limit %s, %s'
    params = [type, uid, page*per_page, per_page]
    return dbc.query(sql, *params)


def get_day_items(beg, end=None):
    if not end:
        end = datetime.now()
    dbc = hqby.db.get_conn('tonghua')
    sql = 'select id, type from items where ins_time >= %s and ins_time <= %s and status=1 order by id desc'
    params = [beg, end]
    return dbc.query(sql, *params)


def find_week_items(w=2):
    t_time = datetime.now() - timedelta(days=w*7)
    dbc = hqby.db.get_conn('tonghua')
    sql = 'select id, type from items where ins_time >= %s and status=1 order by id desc'
    return dbc.query(sql, *[t_time, ])


def find_books(page=0, per_page=10):
    dbc = hqby.db.get_conn('tonghua')
    sql = 'select' + list_to_sql(_rows) + 'from items where type="book" and status=1 order by id desc limit %s, %s'
    params = [page*per_page, per_page]
    return dbc.query(sql, *params)


def get_book_pages(per_page=10):
    dbc = hqby.db.get_conn('tonghua')
    sql = 'select count(id) from items where type="book" and status=1'
    sum_b = dbc.get(sql)['count(id)']
    ps = sum_b*1.0/per_page
    if ps > int(ps):
        ps = int(ps) + 1
    return int(ps)


def create_item(item):
    """
    创建item
    """

    max_try = 3
    default_guess = 0
    dbc = hqby.db.get_conn('tonghua')
    for i in range(max_try):
        try:
            dbc.execute(
                "INSERT INTO items (image, img_type, \
                    audio, org_audio, audio_type, audio_len, \
                    note, user_id, ip, ins_time, guess, type)"
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s, %s)",
                json.dumps(item['image']), item['img_type'],
                json.dumps(item['audio']), json.dumps(item['audio']), item['audio_type'],
                item['audio_len'],
                item['note'],
                item['user_id'], item['ip'], default_guess,
                item['type'],
            )
            item_id = dbc.execute("SELECT LAST_INSERT_ID();")
        except Exception as ex:
            if ex[0] == 1062:
                continue
            else:
                raise ex
        break
    else:
        raise Exception('Item Error', 'unable to create item')
    item['item_id'] = item_id
    return item


def get_first_item_date():
    """ 获取第一个item的插入时间
    """
    dbc = hqby.db.get_conn('tonghua')
    rows = dbc.query("SELECT ins_time FROM items ORDER BY id ASC LIMIT 1")
    if rows:
        item_date = rows[0]['ins_time']
        first_item_date = date(
            item_date.year,
            item_date.month,
            item_date.day
        )
    else:
        first_item_date = date.today()
    return first_item_date


def get_last_nostar_item_id(type=None):
    """获取第一次访问starpage时，时间线上第一个item的id
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT id FROM items WHERE star_level=0 AND status=1 ORDER BY id DESC LIMIT 1"
    parm = []
    if type is not None:
        sql = sql.replace('status=1', 'status=1 AND type=%s ')
        parm = [type]
    rows = dbc.query(sql, *parm)
    return rows[0]['id'] if rows else 0


#@hqby.cache.cached('tonghua', 'items', _key='item_id', pickled=True, mode=configs['cache_mode'])
def get_item(item_id, fields=None):
    """ 根据id获取item
    """
    fields = _rows if not fields else fields
    #assert set(fields).issubset(set(_rows))
    dbc = hqby.db.get_conn('tonghua')
    sql = 'SELECT %s FROM items WHERE id="%s" AND status=1 LIMIT 1' % (list_to_sql(fields), item_id)
    return dbc.get(sql)


def get_max_id():
    """ 获取最后一个item的ID
    """
    dbc = hqby.db.get_conn('tonghua')
    rows = dbc.query("SELECT id FROM items WHERE status = 1 ORDER BY id DESC LIMIT 1")
    return rows[0]['id'] if rows else 0


def find_total_item():
    """ 统计item总数
    """
    dbc = hqby.db.get_conn('tonghua')
    #rows = dbc.query("SHOW TABLE STATUS WHERE name='items'")
    result = dbc.query("select count(id) from items where status=1")
    return result[0]['count(id)'] if result else 0


def get_item_owner(item_id):
    """ 获取指定item所有者的UID
    """
    dbc = hqby.db.get_conn('tonghua')
    return dbc.get("SELECT user_id FROM items WHERE id = %s AND status = 1 limit 1", item_id).get('user_id')


def list_items(last_id=0, count=10):
    """ 获取可用的item
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT id FROM items WHERE status = 1 ORDER BY id DESC LIMIT %s"
    params = [count]
    if last_id:
        sql = sql.replace(' ORDER ', ' AND id < %s ORDER ')
        params.insert(-1, last_id)
    return dbc.query(sql, *params)


def list_star_items(last_id=0, count=10):
    """
       展示含有star的items
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT id FROM items WHERE star_level > 0 AND status = 1 ORDER BY id DESC LIMIT %s"
    params = [count]
    if last_id:
        sql = sql.replace(' ORDER ', ' AND id < %s ORDER ')
        params.insert(-1, last_id)
    return dbc.query(sql, *params)


def list_starshow_items(last_row=0, count=50, type=None):
    """
        供starshow页面使用
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT id FROM items WHERE star_level > 0 AND status=1 ORDER BY star_level DESC, id DESC LIMIT %s"
    params = [count]
    if type is not None:
        sql = sql.replace('status=1', 'status=1 AND type=%s ')
        params.insert(0, type)
    if last_row:
        sql = sql.replace(' LIMIT %s', ' LIMIT %s,%s')
        params.insert(-1, last_row)
    return dbc.query(sql, *params)


def list_nostar_items(last_id=0, count=10, type=None):
    """ 供starmanage页面使用
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT id FROM items WHERE star_level = 0 AND status=1 ORDER BY id DESC LIMIT %s"
    params = [count]
    if type is not None:
        sql = sql.replace('status=1', 'status=1 AND type=%s ')
        params.insert(0, type)
    if last_id:
        sql = sql.replace(' ORDER ', ' AND id < %s ORDER ')
        params.insert(-1, last_id)
    return dbc.query(sql, *params)


def get_today_nostar_items(type=None):
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT id FROM items WHERE star_level = 0 AND ins_time > %s AND status=1 AND type=%s ORDER BY id DESC"
    tmp_today = date.today()
    tmp_datetime = datetime(tmp_today.year, tmp_today.month, tmp_today.day)
    params = [tmp_datetime]
    if type is not None:
        sql = sql.replace('status=1', 'status=1 AND type=%s ')
        params.append(type)
    return dbc.query(sql, *params)


#todo ins_time > today ???
def get_today_star_items(type=None):
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT" + list_to_sql(_rows) + "FROM items WHERE star_level > 0 AND ins_time > %s AND status=1 " \
                                          "ORDER BY id DESC"
    tmp_today = date.today()
    #tmp_datetime = datetime(tmp_today.year, tmp_today.month, tmp_today.day)
    params = [tmp_today]
    if type is not None:
        sql = sql.replace('status=1', 'status=1 AND type=%s ')
        params.append(type)
    return dbc.query(sql, *params)


def get_star_items(last_row=0, count=10, type=None):
    """ 按照level排序的item列表
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "select" + list_to_sql(_rows) + 'from items where star_level>0 and status=1 order by star_level desc,id desc \
          limit %s'
    params = [count, ]
    if type:
        sql = sql.replace('status=1', 'status=1 and type=%s ')
        params.insert(0, type)
    if last_row:
        sql = sql.replace('limit %s', 'limit %s,%s')
        params.insert(-1, last_row)  # last_row 是偏移量, 插入倒数第二位
    return dbc.query(sql, *params)


def get_pre_star_items(last_row=0, count=10, type=None):
    """ 获取手机首页的展示内容
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT" + list_to_sql(_rows) + "FROM items WHERE star_level > 0 AND ins_time < %s AND status=1 \
           ORDER BY star_level DESC, id DESC LIMIT %s"
    tmp_today = date.today()
    #tmp_datetime = datetime(tmp_today.year, tmp_today.month, tmp_today.day)
    params = [tmp_today, count]
    if type is not None:
        sql = sql.replace('status=1', 'status=1 AND type=%s ')
        params.insert(1, type)
    if last_row:
        sql = sql.replace(' LIMIT %s', ' LIMIT %s,%s')
        params.insert(-1, last_row)
    return dbc.query(sql, *params)


def get_nostar_items(last_id=0, count=10, type=None):
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT" + list_to_sql(_rows) + "FROM items WHERE star_level = 0 AND status=1 ORDER BY id DESC LIMIT %s"
    params = [count]
    if type:
        sql = sql.replace('status=1', 'status=1 AND type=%s')
        params.insert(0, type)
    if last_id != 0:
        sql = sql.replace(' ORDER ', ' AND id < %s ORDER ')
        params.insert(-1, last_id)
    return dbc.query(sql, *params)


def random_choose(count=10):
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT id FROM items WHERE status = 1 ORDER BY id DESC"
    rows = dbc.query(sql)
    shuffle_rows = rows
    random.shuffle(shuffle_rows)
    return shuffle_rows[0: count] if shuffle_rows else []


def del_by_item_id(item_id):
    """根据item_id删除item
    """
    dbc = hqby.db.get_conn('tonghua')
    # sql = "DELETE FROM items WHERE id = %s"
    sql = "UPDATE items SET status = 0 WHERE id = %s"
    params = [item_id]
    return dbc.execute(sql, *params)


def add_star_by_id(item_id):
    """ 将item的星级设置为1，进入推荐内容
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "UPDATE items SET star_level=1 WHERE id=%s"
    params = [item_id]
    return dbc.execute(sql, *params)


def update_star_by_id(item_id, star):
    """根据推荐指数更新数据库
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = "UPDATE items SET star_level=%s WHERE id=%s"
    params = [star, item_id]
    return dbc.execute(sql, *params)


def set_item_audio(item_id, audio=None, revert=False):
    """ 设置item的播放语音, 提供恢复接口
    """
    dbc = hqby.db.get_conn('tonghua')
    if revert:
        item = dbc.get('SELECT * from items WHERE id=%s', item_id)
        audio = item['org_audio'] if item else None
    if audio is None:
        return
    sql = 'UPDATE items SET audio=%s WHERE id=%s'
    params = [audio, item_id]
    return dbc.execute(sql, *params)


def set_item_guess(item_id, guess=1):
    """ 设置以及取消设置猜图
    """
    dbc = hqby.db.get_conn('tonghua')
    if int(guess) not in [0, 1]:
        guess = 1
    if guess:
        audio = 'guess_audio'
    else:
        item = dbc.get('SELECT org_audio from items WHERE id=%s', item_id)
        audio = item['org_audio'] if item else None
    if not audio:
        return
    sql = 'UPDATE items SET guess=%s, audio=%s WHERE id=%s'
    params = [guess, audio, item_id]
    return dbc.execute(sql, *params)


# todo 改善性能
def get_top_itembooks(limit=10):
    """ 随机获取5幅绘本
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = 'SELECT' + list_to_sql(_rows) + 'from items WHERE type=%s AND status=1 ORDER BY rand() LIMIT %s'
    params = ['book', limit]
    return dbc.query(sql, *params)
