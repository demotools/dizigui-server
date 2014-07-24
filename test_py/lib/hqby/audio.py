#!/usr/bin/env python
# coding: utf-8

import os
import binascii
import json
import re
from tornado.web import HTTPError
import logging

# from PIL import Image

import hqby.pk
import hqby.db
from hqby.config import configs
from tools import tools


def save_audio(audio, audio_type, audio_len, pre_path, pre_url, mid_path):
    """保存临时音频
    """
    sub_path = '%s.%s' % (mid_path, audio_type)
    audio_file = os.path.join(pre_path, *sub_path.split('/'))
    if not os.path.exists(os.path.dirname(audio_file)):
        os.makedirs(os.path.dirname(audio_file))
    audio.seek(0)
    with open(audio_file, 'wb') as f:
        f.write(audio.read())
    info = {
        'src': '%s/%s?%s' % (pre_url, sub_path, file_crc(audio_file)),
        'type': audio_type,
        'len': audio_len,
    }
    return info


def id_to_subdir(id, dir_len=2):
    """获取音频子目录
    """
    dirs = []
    audio_dir = str(int(id) // (10 ** dir_len))
    prefix = len(audio_dir) % dir_len
    if prefix > 0:
        audio_dir = '0' * (dir_len - prefix) + audio_dir
    for i in range(len(audio_dir) // dir_len):
        dirs.append(audio_dir[i * dir_len:(i + 1) * dir_len])
    return '/'.join(dirs)


def file_crc(file_path):
    """计算文件的crc
    """
    f = open(file_path, 'rb')
    crc = binascii.crc32(f.read())
    f.close()
    return '%08x' % (crc & 0xffffffff)


def create_temp_audio(audio_file, audio_type, audio_len, user_id):
    """生成临时音频
    """
    # todo: check file size and dimensions?
    max_try = 3
    dbc = hqby.db.get_conn(configs['db_name'])
    for i in range(max_try):
        id = hqby.pk.gen_id(8)
        try:
            dbc.execute(
                "insert into temp_audios (id, user_id, type, len, ins_time) "
                "values (%s, %s, %s, %s, sysdate())",
                #"values (%s, %s, %s, %s, unix_timestamp())",
                id, user_id, audio_type, audio_len)
        except Exception as ex:
            if ex[0] == 1062:  # duplicated id
                continue
            else:
                raise ex
        break
    else:
        raise Exception('Audio Error', 'unable to create temp audio id')
    audio = save_audio(
        audio_file,
        audio_type,
        audio_len,
        configs['audio_base_path'],
        configs['audio_base_url'],
        'temp/' + id
    )
    audio['id'] = id
    dbc.execute(
        "update temp_audios set audio = %s where id = %s",
        json.dumps(audio), id)
    return audio


def get_temp_audio(id):
    """获取临时音频
    """
    dbc = hqby.db.get_conn(configs['db_name'])
    audio = dbc.get("select * from temp_audios where id = %s", id)
    if not audio:
        raise HTTPError(500, 'Temp Audio not found')
    audio['audio'] = json.loads(audio['audio'])
    return audio


def move_temp_audio(audio, pre_path, pre_url, mid_path, new_id=None):
    """移动临时音频
    """
    # info = {}
    # 利用正则表达式解析src来获得文件名和扩展名
    re_pattern = configs['audio_base_url'] + '\/(\S+)\?'
    tmp_path_re = re.compile(re_pattern)

    absolute_url = audio['audio']['src']
    tmp_path = tmp_path_re.match(absolute_url).group(1)
    tmp_file = os.path.join(configs['audio_base_path'], *tmp_path.split('/'))
    extension = tmp_path.split('.')[-1]
    sub_path = '%s/%s.%s' % (mid_path, audio['id'], extension)
    audio_file = os.path.join(pre_path, *sub_path.split('/'))
    if not os.path.exists(os.path.dirname(audio_file)):
        os.makedirs(os.path.dirname(audio_file))
    os.rename(tmp_file, audio_file)
    # convert amr to mp3
    try:
        audio_thread = tools.AudioConvertThread(audio_file)
        audio_thread.start()
    except Exception as ex:
        logging.error('[Error]: convert amr failed-%s' % str(ex))
    info = {
        'src': '%s/%s?%s' % (pre_url, sub_path, file_crc(audio_file)),
    }
    dbc = hqby.db.get_conn(configs['db_name'])
    dbc.execute("delete from temp_audios where id = %s", audio['id'])
    if new_id:
        info['id'] = new_id
    return info


