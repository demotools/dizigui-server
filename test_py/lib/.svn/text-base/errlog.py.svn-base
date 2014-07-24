# coding: utf-8

import os
# import binascii
# import json
# import tempfile
# import re


import hqby.pk
from hqby.config import configs


def create_errlog(file_name, tmp_file):
    """生成错误日志
    """
    log_path = configs['log_base_path']
    log_file = os.path.join(log_path,file_name)
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    with open(log_file,'w') as f:
        f.write(tmp_file.read())

def get_errlog(last_id=0):
    """获取日志文件列表
    """
    log_path = configs['log_base_path']
    file_list = os.popen('ls -t %s' %log_path)
    tmp_list = []
    for file in file_list:
        tmp_list.append(file.rstrip('\n'))
    try:
        file_name = os.path.join(log_path, tmp_list[last_id])
    except IndexError as ex:
        file_name = ""
    finally:
        return file_name
