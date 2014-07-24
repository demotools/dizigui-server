#!/usr/bin/env python
# coding: utf-8

import hqby.db


def create_feedback(uid, data):
    """创建反馈信息
    """
    max_try = 3
    dbc = hqby.db.get_conn('tonghua')
    for i in range(max_try):
        try:
            dbc.execute(
                "INSERT INTO feedbacks (user_id, data, ins_time)"
                "VALUES (%s, %s, now())",
                uid, data
            )
        except Exception as ex:
            if ex[0] == 1062:
                continue
            else:
                raise ex
        break
    else:
        raise Exception('Feedback Error', 'unable to create feedback')
    return


def list_feedback(last_row=0, count=50):
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT * FROM feedbacks ORDER BY id DESC LIMIT %s,%s"
    params = [last_row, count]
    rows = dbc.query(sql, *params)
    results = []
    for row in rows:
        results.append({
            'id': row['id'],
            'data': row['data'],
            'ins_time': row['ins_time'].isoformat(),
        })
    return results
