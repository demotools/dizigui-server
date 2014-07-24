#!/usr/bin/env python
# coding: utf-8

import hqby.db


def create_tag(tag):
    max_try = 3
    dbc = hqby.db.get_conn('tonghua')
    for i in range(max_try):  # 插入标签名称的唯一性由数据库限制
        try:
            tag_id = dbc.execute(
                'INSERT INTO tag (name, status, created, creator_id)\
                 VALUES (%s, 1, now(), 0)',
                tag['name']
            )
            #tag_id = dbc.execute('SELECT LAST_INSERT_ID();')
        except Exception as ex:
            if ex[0] == 1062:
                continue
            else:
                raise ex
        break
    else:
        raise Exception('Create tag error', 'unable to create tag')
    tag['tag_id'] = tag_id
    tag['id'] = tag_id
    return tag


def add_item_tag(item_id, tag_id, uid=0):
    """ 为item添加一个标签
    """
    max_try = 3
    dbc = hqby.db.get_conn('tonghua')
    errs = []
    for i in range(max_try):  # 插入数据的唯一性由数据库限制
        try:
            _id = dbc.execute(
                'INSERT INTO tag_item (item_id, tag_id, uid)\
                 VALUES (%s, %s, %s)',
                item_id, tag_id, uid
            )
            #_id = dbc.execute('SELECT LAST_INSERT_ID();')
        except Exception as ex:
            if ex[0] == 1062:
                errs.append(str(ex))
                continue
            else:
                raise ex
        break
    else:
        raise Exception('Create item_tag error', ', '.join(errs))
    return {'id': _id, 'item_id': item_id, 'tag_id': tag_id, 'uid': uid}


def add_item_tags(item_id, tag_ids):
    """ 为item添加多个标签
    """
    if not tag_ids:
        return
    adds = []
    for i in tag_ids:
        try:
            adds.append(add_item_tag(item_id, i))
        except Exception:
            pass
    return adds


def list_item_tags(item_id):
    """ 获取某个item的标签id列表
    """
    dbc = hqby.db.get_conn('tonghua')
    return dbc.query(
        "SELECT tag_id FROM tag_item WHERE item_id = %s",
        item_id
    )


def del_item_tags(item_id):
    """
        根据item_id 删除item tag
    """
    dbc = hqby.db.get_conn('tonghua')
    return dbc.execute(
        "DELETE FROM tag_item WHERE item_id=%s",
        item_id
    )


def list_tag_items(tag_name):
    """ 根据标签名称 获取使用了某个标签的item的id列表
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = 'SELECT tag_item.item_id FROM tag, tag_item WHERE tag.id = tag_item.tag_id \
          AND tag.name = %s AND tag.status = true'
    return dbc.query(sql, tag_name)


def list_tag_items_by_tag_id(tag_id, last_item=0, count=10):
    """ 根据tag_id 获取使用了某个标签的item的id列表
    """
    dbc = hqby.db.get_conn('tonghua')
    # sql = 'SELECT item_id FROM tag_item WHERE tag_id=%s ORDER BY item_id DESC LIMIT %s'
    sql = 'SELECT a.item_id FROM tag_item a left join items b on b.id=a.item_id WHERE a.tag_id=%s AND \
           b.status=1 ORDER BY item_id DESC LIMIT %s'
    params = [tag_id, count]
    if last_item:
        sql = sql.replace('ORDER', 'AND item_id<%s ORDER')
        params.insert(1, last_item)
    return dbc.query(sql, *params)


def get_tag_by_name(tag_name):
    dbc = hqby.db.get_conn('test2')
    return dbc.get('SELECT * FROM tag WHERE name = %s AND status = true', tag_name)


def get_tag(tag_id):
    """ 取一个标签对象
    """
    dbc = hqby.db.get_conn('tonghua')
    return dbc.get('SELECT * FROM tag WHERE id = %s AND status = true', tag_id)


def update_tag_item(id='', uid='', new_tag=0, new_item=0):
    if (not id and not uid) or (not new_tag and not new_item):
        return
    sql = 'UPDATE tag_item set ' + ('tag_id' if new_tag else 'item_id') + '=%s WHERE ' + ('id=%s' if id else 'uid=%s')
    dbc = hqby.db.get_conn('tonghua')
    params = []
    params.append(new_tag if new_tag else new_item)
    params.append(id if id else uid)
    return dbc.execute(sql, *params)


def list_tag_items(tag_id, last_item=0, count=10):
    """
        根据tag_id 获取使用标签的items
    """
    dbc = hqby.db.get_conn('tonghua')
    sql = 'SELECT items.*, tag_item.item_id FROM tag_item JOIN items ON items.id=tag_item.item_id  \
           WHERE tag_item.tag_id=%s AND items.status=1 AND items.guess=0 ORDER BY item_id DESC limit %s'
    params = [tag_id, count]
    if last_item:
        sql = sql.replace('ORDER', 'AND item_id<%s ORDER ')
        params.insert(1, last_item)
    return dbc.query(sql, *params)
