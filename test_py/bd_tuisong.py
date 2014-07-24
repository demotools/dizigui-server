#!/usr/bin/env python
# coding: utf-8

import json

from lib.hqby.config import baidu_push_configs
from lib.baidu_pusher.Channel import *
import rq_client
import logging

#TODO 发送请求到百度云推送
#baidu_apiKey = '4CFw1RCNUBQm9OjVwRFBveiL' #baidu_push_configs['apiKey']
#baidu_secretKey = 'ZILGPQrQRGYDaSzQACVlGFLKQmD4gA5f' #baidu_push_configs['secretKey']
baidu_apiKey = baidu_push_configs['apiKey']
baidu_secretKey = baidu_push_configs['secretKey']
#print baidu_apiKey
#print baidu_secretKey
#给item所有者发送通知
#baidu_uid, baidu_cid = hqby.user.get_bdinfo(item_owner)
# baidu_uid = '779641056846633466'
# baidu_cid = '4688168318454031429'
#baidu_uid = '954305684295460271'
#baidu_cid = '4793070047889914437'
#baidu_uid = '1005653614289383804'
#baidu_cid = '5580036389805052339'
#baidu_uid = '1121081431634052844'
#baidu_cid = '4504441413945146247'
message = {
    'title': '童说童画',
    'description': 'huaua',
    'open_type': 2,
    "aps": {
	"alert":"Message From Baidu Push",
	"sound":"",
	"badge":0
	},
}
message = json.dumps(message)
message_key = "sys"
c = Channel(baidu_apiKey, baidu_secretKey, arr_curlOpts=dict(TIMEOUT=3, CONNECTTIMEOUT=5))
push_type = 1  # 1-单个人, 2-一群人, 3-全部人
optional = dict()
optional[Channel.USER_ID] = 1089119974920956848
optional[Channel.CHANNEL_ID] = 4303185885256703539
optional[Channel.MESSAGE_TYPE] = 1  # 0-消息, 1-通知
optional[Channel.DEVICE_TYPE] = 3  # 4-ios, 3-安卓, 5-wp设备, 2-pc, 1-浏览器
# optional['push_type'] = 3
# optional['device_types'] = [3, 4]
optional['deploy_status'] = 1  # 1-开发, 2-生产
ret = None
#ret = c.pushMessage(push_type, message, message_key, optional)
#ret = yield gen.Task(c.pushMessage, push_type, message, message_key, optional)
job = rq_client.default_queue.enqueue(c.pushMessage, push_type, message, message_key, optional)
print optional
print job
logging.info('log for baidu pusher: %s', str(job))
