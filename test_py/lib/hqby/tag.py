#!/usr/bin/env python
# coding: utf-8

import model.tag
from hqby.config import configs
# import logging


def age_update_tag(uid, old_age, new_age):
    if old_age == new_age:
        return
    new_tag = model.tag.get_tag_by_name(str(new_age) + u'岁')
    if not new_tag:
        new_tag = model.tag.create_tag({'name': str(new_age) + u'岁'})
        # logging.error('must create age tag first')
    return model.tag.update_tag_item(uid=uid, new_tag=new_tag['id'])


def add_item_by_tag_name(uid, name, item_id, create=False):
    tag = model.tag.get_tag_by_name(name)
    if not tag and create:
        tag = model.tag.create_tag({'name': name})
    return model.tag.add_item_tag(tag_id=tag['id'], item_id=item_id, uid=uid)


def get_tag_info(tag_id):
    tmp_tag = model.tag.get_tag(tag_id)
    if tmp_tag:
        tag = dict()
        tag['id'] = tmp_tag['id']
        tag['name'] = tmp_tag['name']
        tag['status'] = tmp_tag['status']
        tag['creator_id'] = tmp_tag['creator_id']
        return tag
    else:
        return None


def list_item_tag_ids(item_id):
    return [t['tag_id'] for t in model.tag.list_item_tags(item_id)]


def list_tag_item_ids(tag_name):
    return [t['item_id'] for t in model.tag.list_tag_items(tag_name)]


def list_item_ids_by_tag_id(tag_id, last_item, count):
    return [t['item_id'] for t in model.tag.list_tag_items_by_tag_id(tag_id, last_item, count)]


def list_tag_items(tag_id, last_item, count):
    ms = []
    for m in model.tag.list_tag_items(tag_id, last_item, count):
        del m['item_id']
        ms.append(m)
    return ms


def list_item_tags(handler, item_id):
    """
        获取某个item的tag
    """
    tag_ids = list_item_tag_ids(item_id)
    tags = []
    for i in tag_ids:
        tag = get_tag_info(i)
        if tag:
            if tag['name'] == u'0岁':  # 0 岁标签过滤掉
                continue
            tags.append({
                '_id': tag['id'],
                'name': tag['name'],
                'status': tag['status'],
                'links': [
                    handler._link('tag/%s' % tag['id'], 'tag'),
                ]
            })
    return tags
