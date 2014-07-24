#!/usr/bin/env python
# coding: utf-8

import json
import time
import hqby.db
from hqby.config import configs, _start_time, _end_time, _per_day
import model.item
import model.comment
import model.action
import model.timetravel
import model.tag
import hqby.tag

import datetime


def item_initialization(params, img, audio, ip):
    item = dict()
    item['note'] = params['note']
    item['user_id'] = img['user_id']
    item['ip'] = ip
    item['img_type'] = img['img_type']
    item['audio_type'] = audio['type']
    item['audio_len'] = audio['len']
    return item


def get_by_id(handler, item_id):
    """  原始数据, 解包数据库
    """
    tmp_item = model.item.get_item(item_id)
    if not tmp_item:
        return None
    tmp_user = model.user.get_user(user_id=tmp_item['user_id'])
    if not tmp_user:
        return None
    else:
        now = datetime.datetime.now()
        if now < _end_time and tmp_item['ins_time'] > _start_time:
            tmp_item['love'] += (now-tmp_item['ins_time']).days * _per_day
        row = {}
        item_tags = hqby.tag.list_item_tags(handler, tmp_item['id']) if not tmp_item['guess'] else []
        tmp_item['image'] = json.loads(tmp_item['image'])
        row['book_image'] = tmp_item['image'] if tmp_item['type'] == 'book' else [tmp_item['image'], ]
        row['image'] = row['book_image'][0]
        row['id'] = tmp_item['id']
        row['user_id'] = tmp_item['user_id']
        row['user_nick'] = tmp_user['nick']
        row['user_portrait'] = tmp_user['portrait']
        row['user_age'] = tmp_user['age']
        row['user_type'] = tmp_user['user_type']
        row['type'] = tmp_item['type']
        row['img_type'] = tmp_item['img_type']
        row['audio'] = json.loads(tmp_item['audio'])
        row['audio_type'] = tmp_item['audio_type']
        row['audio_len'] = tmp_item['audio_len']
        row['audio_play'] = tmp_item['audio_play']
        row['note'] = tmp_item['note']
        row['love'] = tmp_item['love']
        row['collect'] = tmp_item['collect']
        row['star_level'] = tmp_item['star_level']
        row['guess'] = tmp_item['guess']
        row['tags'] = item_tags
        row['comment'] = model.comment.count_by_item(item_id=row['id'])
        row['ins_timestamp'] = long(time.mktime(tmp_item['ins_time'].timetuple()))
        row['ins_time'] = tmp_item['ins_time']
        return row


## todo remove
#def front_item_data(handler, item=None, item_id=None, size=3.0/3.2):
#    """ item 返回前端数据统一包装
#    """
#    if not handler:
#        return {}
#    if not item and item_id:
#        item = get_by_id(handler, item_id)
#    item_image = item['image']
#    if isinstance(item_image, (unicode, str)):
#        item_image = json.loads(item_image)
#    if isinstance(item['audio'], (unicode, str)):
#        item['audio'] = json.loads(item['audio'])
#    if item['type'] == 'book':
#        imgs = []
#        raw_imgs = []
#        for i in item_image:
#            imgs.append(handler._choose_image(i, size, 'WATERFALL'))
#            raw_imgs.append(handler._choose_image(i, size, 'RAW'))
#        item['book_image'] = imgs
#        item['book_raw_image'] = raw_imgs
#        item['image'] = imgs[0]
#        item['raw_image'] = raw_imgs[0]
#    else:
#        item['book_image'] = []
#        item['book_raw_image'] = []
#        item['image'] = handler._choose_image(item_image, size, 'WATERFALL')
#        item['raw_image'] = handler._choose_image(item_image, size, 'RAW')
#
#    # add use message
#    if 'user_nick' not in item:
#        tmp_user = model.user.get_user(user_id=item['user_id'])
#        if not tmp_user:
#            return None
#        item['user_nick'] = tmp_user['nick']
#        item['user_portrait'] = tmp_user['portrait']
#        item['user_age'] = tmp_user['age']
#        item['user_type'] = tmp_user['user_type']
#    item_data = {
#        '_id': item['id'],
#        'class': 'item',
#        'user_id': item['user_id'],
#        'user_nick': item['user_nick'],
#        'user_portrait': item['user_portrait'],
#        'user_age': item['user_age'],
#        'user_type': item['user_type'],
#        'note': item['note'],
#        'ins_timestamp': item.get('ins_timestamp') or long(time.mktime(item['ins_time'].timetuple())),
#        'love': item['love'],
#        'collect': item['collect'],
#        'comment': item.get('comment') or model.comment.count_by_item(item_id=item['id']),
#        'img_type': item['img_type'],
#        'image': item['image'],
#        'type': item['type'],
#        'raw_image': item['raw_image'],  # 原图
#        'audio': item['audio'],
#        'audio_type': item['audio_type'],
#        'audio_len': item['audio_len'],
#        'audio_play': item['audio_play'],
#        'star_level': item['star_level'],
#        'guess': item['guess'],
#        'tags': item.get('tags') or (hqby.tag.list_item_tags(handler, item['id']) if not item['guess'] else []),
#        'links': [
#            handler._link('item/%s' % item['id'], 'item'),
#            handler._link('item/%s/love' % item['id'], 'love'),
#            handler._link('item/%s/collect' % item['id'], 'collect'),
#            handler._link('item/%s/share' % item['id'], 'share'),
#            handler._link('item/%s/play' % item['id'], 'play'),
#            handler._link('comment/%s' % item['id'], 'comment'),
#            handler._link('user/%s' % item['user_id'], 'owner'),
#            handler._link('user2/%s' % item['user_id'], 'owner2'),
#        ]
#    }
#    return item_data


## todo remove
#def list_tag_items(handler, tag_name):
#    """ 根据标签名称 取得标签对应的item列表
#    """
#    item_ids = hqby.tag.list_tag_item_ids(tag_name)
#    items = []
#    for i in item_ids:
#        item = hqby.item.get_by_id(handler, i)
#        if item:
#            items.append(front_item_data(handler, item, size=3.0/3.2))
#    return items


def get_item_info(handler, item_id=0, item=None, size=3.0/3.2, fields=None, uid=None):
    """ item 数据包装
    """
    item = item or model.item.get_item(item_id, fields=fields)
    if not item:
        return None
    if not fields:
        fields = item.keys()
        # 额外的属性
        fields.extend(['user_nick', 'comment', 'tags', 'raw_image', 'user_portrait',
                       'user_age', 'user_type', 'book_image', 'book_raw_image'])
    # json load json_data
    if 'audio' in fields:
        item['audio'] = json.loads(item['audio'])
    if 'image' in fields:
        item['image'] = json.loads(item['image'])
        item['book_image'] = item['image'] if item['type'] == 'book' else [item['image'], ]
        imgs = []
        raw_imgs = []
        for i in item['book_image']:
            imgs.append(handler._choose_image(i, size, 'WATERFALL'))
            raw_imgs.append(handler._choose_image(i, size, 'RAW'))
        item['book_image'] = imgs
        item['book_raw_image'] = raw_imgs
        item['image'] = imgs[0]
        item['raw_image'] = raw_imgs[0]
    # add use message
    if 'user_nick' in fields:
        tmp_user = model.user.get_user(user_id=item['user_id'])
        if not tmp_user:
            return None
        item['user_nick'] = tmp_user['nick']
        item['user_portrait'] = tmp_user['portrait']
        item['user_age'] = tmp_user['age']
        item['user_type'] = tmp_user['user_type']
    if 'comment' in fields:
        item['comment'] = model.comment.count_by_item(item_id=item['id'])
    if 'tags' in fields:
        item['tags'] = hqby.tag.list_item_tags(handler, item['id']) if not item['guess'] else []
    # 活动
    if 'love' in fields:
        now = datetime.datetime.now()
        if now < _end_time and item['ins_time'] > _start_time:
            item['love'] += (now-item['ins_time']).days * _per_day
    item_data = dict()
    if 'ins_time' in fields:
        item_data['ins_timestamp'] = long(time.mktime(item['ins_time'].timetuple()))
    for attr in fields:
        if attr in item:
            item_data[attr] = item[attr]
    # 通用属性
    item_data['_id'] = item['id']
    item_data['class'] = 'item'
    item_data['links'] = [
        handler._link('item/%s' % item['id'], 'item'),
        handler._link('item/%s/love' % item['id'], 'love'),
        handler._link('item/%s/collect' % item['id'], 'collect'),
        handler._link('item/%s/share' % item['id'], 'share'),
        handler._link('item/%s/play' % item['id'], 'play'),
        handler._link('comment/%s' % item['id'], 'comment'),
    ]
    if 'user_id' in fields:
        item_data['links'].append(handler._link('user/%s' % item['user_id'], 'owner'))
        item_data['links'].append(handler._link('user2/%s' % item['user_id'], 'owner2'))
    if 'ins_time' in item_data:
        del item_data['ins_time']
    if uid:
        loved_items = model.action.get_loved_items(uid) if uid != 'anonymous' else []
        item_data['had_loved'] = 1 if item_data['_id'] in loved_items else 0
    return item_data


def list_items_by_tag_id(handler, tag_id, last_item=0, count=50, uid=None):
    """ 根据标签id 取得标签对应的item列表
    """
    count = min(configs['max_query_rows'], count)
    return [get_item_info(handler, item=item, size=3.0/3.2, uid=uid) for item in
            hqby.tag.list_tag_items(tag_id, last_item, count)]


#todo remov
def waterfall_ids(handler, ids, size=3.0/3.2):
    """ 瀑布流辅助方法
    """
    ds = []
    for iid in ids:
        data = get_item_info(handler, item_id=iid, size=size)
        if data:
            ds.append(data)
    return ds


def waterfall_items(handler, items, uid, size=3.0/3.2):
    ds = []
    for item in items:
        data = get_item_info(handler, item=item, size=size, uid=uid)
        if data:
            ds.append(data)
    return ds


def list_items(last_id=0, count=50):
    count = min(configs['max_query_rows'], count)
    rows = model.item.list_items(last_id, count)
    return [i['id'] for i in rows]


def list_star_items(last_id=0, count=50):
    count = min(configs['max_query_rows'], count)
    rows = model.item.list_star_items(last_id, count)
    return [i['id'] for i in rows]


def list_starshow_items(last_row=0, count=50, type=None):
    """供starshow页面使用
    """
    count = min(configs['max_query_rows'], count)
    rows = model.item.list_starshow_items(last_row, count, type=type)
    return [i['id'] for i in rows]


def list_nostar_items(last_id=0, count=50, type=None):
    """供starmanage页面使用
    """
    count = min(configs['max_query_rows'], count)
    rows = model.item.list_nostar_items(last_id, count, type=type)
    return [i['id'] for i in rows]


def get_last_nostar_item_id(type=None):
    """供第一次访问starpage时生成next链接使用
    """
    row = model.item.get_last_nostar_item_id(type=type)
    num = int(row)
    return num


def get_today_nostar_items(type=None):
    return model.item.get_today_nostar_items(type=type)


def get_today_star_items(type=None):
    return model.item.get_today_star_items(type=type)


def get_pre_star_items(last_row=0, count=10, type=None):
    return model.item.get_pre_star_items(last_row, count, type=type)


def get_nostar_items(last_id=0, count=10, type=None):
    return model.item.get_nostar_items(last_id, count, type=type)


def random_choose(count=10):
    count = min(configs['max_query_rows'], count)
    rows = model.item.random_choose(count)
    return [i['id'] for i in rows]


def timetravel_items(date_point, last_row=0, count=50):
    count = min(configs['max_query_rows'], count)
    rows = model.timetravel.list_items(date_point, last_row, count)
    return [i['id'] for i in rows]


def del_by_id(item_id):
    model.item.del_by_item_id(item_id)
    model.comment.del_by_item_id(item_id)
    model.action.del_by_item_id(item_id)
    return


def add_star_by_id(item_id):
    model.item.add_star_by_id(item_id)
    return


def update_star_by_id(item_id, star):
    model.item.update_star_by_id(item_id, star)
    return


def set_item_audio(item_id, audio=None, revert=False):
    model.item.set_item_audio(item_id, audio, revert)
    return


def set_item_guess(item_id, guess=1):
    model.item.set_item_guess(item_id, guess)
    return


def top_books(handler, limit=10):
    tops = model.item.get_top_itembooks(limit=limit)
    return [get_item_info(handler, item=i, size=3.0/3.2) for i in tops]

