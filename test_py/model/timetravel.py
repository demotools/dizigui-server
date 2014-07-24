#!/usr/bin/env python
# coding: utf-8

from datetime import datetime, timedelta
import hqby.db


def list_items(date_point, last_row=0, count=50):
    timetravel = datetime(
        int(date_point[0:4]), 
        int(date_point[4:6]), 
        int(date_point[6:])
    )
    dbc = hqby.db.get_conn('tonghua')
    sql = "SELECT id FROM items WHERE ins_time BETWEEN %s AND %s\
        ORDER BY id ASC LIMIT %s, %s"
    params = [timetravel, timetravel + timedelta(days = 1), last_row, count]
    rows = dbc.query(sql, *params)
    return rows

