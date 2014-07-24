# coding: utf-8
""" 配置模块，负责加载配置，并供其它模块使用
"""

from tornado import options
import datetime

version = 2.0

API_BASE_URI = 'http://api.dujing.com'
IMG_BASE_URI = 'http://img.dujing.com'
#IMG_BASE_URI = 'http://192.168.2.29:8888/static/img.dujing.szhqby.com'
AUD_BASE_URI = 'http://aud.dujing.com'
PORTRAIT_URI = 'http://img.test.szhqby.com/dujing/img/portrait/none.png'

TEST_MODE = False  # 测试模式, 禁用cache, 更改数据库

DB_NAME = 'test2' if not TEST_MODE else 'tonghua2'
TEST_DB_NAME = 'tonghua2'
APP_REDIS_NAME = 'test2'

_start_time = datetime.datetime(year=2014, month=5, day=29, hour=15, minute=0, second=0)
_end_time = datetime.datetime(year=2015, month=10, day=8, hour=19, minute=0, second=0)
_per_day = 2

ERROR_CODES = {
    'token-failed': 1,  # token 失效
    'audio too long': 2,  # 上传音频文件长度过长
    'can not found this user': 3,  # 找不到用户
    'audio io error': 4,  # 音频错误
    'user update error': 5,
}

configs = {
    'debug': True,
    'db_name': DB_NAME,
    'test_db_name': TEST_DB_NAME,
    #'max_book_images': 5,  # 绘本最大图片数量 超过截断
    'test_mode': TEST_MODE,
    'api_base_url': API_BASE_URI,
    'cache_mode': 'get' if not TEST_MODE else 'db',  # values: get, set, delete, db
    'cookie_secret': 'hqby',
    'error_codes': ERROR_CODES,
    'dujing_default_portrait': PORTRAIT_URI,
    'db_config': {'host': 'localhost', 'database': DB_NAME, 'user': 'root','pre_exe': ('SET NAMES utf8mb4', )},
    'db': {
        DB_NAME: {'host': 'localhost', 'database': DB_NAME, 'user': 'root'},
        'tonghua2': {'host': 'localhost', 'database': TEST_DB_NAME, 'user': 'root'},
    },
    'img_base_url': IMG_BASE_URI,
    'img_base_path': '/Users/hqby/Desktop/test_py/static/img',
    'audio_base_url': AUD_BASE_URI,
    'audio_base_path': '/Users/hqby/Desktop/test_py/static/aud',
    'redis_name': APP_REDIS_NAME,
    'redis': {
         APP_REDIS_NAME : {'host': 'localhost', 'port': 6379},
    },
    'mq_secret': 'hqby',
    'user2roles': {
        '1000': 'editor',
    },
    'acl': {
        'editor': {
            'allow': {'/oa/item': '*', }
        }
    },
    'max_query_rows': 99,
    #'sina_client_id': '4148264515',
    #'sina_client_secret': 'd25bc39469452ce29899a0a341bd7a85',
    'sina_client_id': '994790506',
    'sina_client_secret': '2a5040392ee98d1a727f6d2f51c1c9d2',
    #'tqq_client_id': '801333915',
    #'tqq_client_secret': '3ae855ce1a28c717bbfce3fb884aabb2',
    #'qq_client_id': '100450630',
    #'qq_client_secret': 'effc357bb9e29bae5456669c0c4fdb6f',
    'tqq_client_id': '801479150',
    'tqq_client_secret': 'fc2d0cf8d2b4430872e22b7716dd5ff6',
    'qq_client_id': '101022156',
    'qq_client_secret': '94985e7295ab3bc9de813c85d53925e0',
    'action_scores': {
        'register': 0,
        'publish': 5,
        'remove': -5,
        'love': 2,
        'comment': 0,
    },
}

th_mail_configs = {
    'mail_to': [
        'jacky@szhqby.com',
        'shadow@szhqby.com',
    ],
    'mail_host': 'smtp.126.com',
    'mail_user': 'hqbytonghua',
    'mail_pass': 'hqbyth',
    'mail_postfix': '126.com',
}

baidu_push_configs = {
    'apiKey': 'rTDqgdEgdkDV2Gkx3zdGrtOr',
    'secretKey': '7TFW8QuUm2tsFRh2R9q1rOGQqZKSty89',
}


def load_py_file(path):
    if not path:
        return
    execfile(path, {}, configs)
    
options.define('port', default=8888, help='server listening port', type=int)
options.define('conf', default=None, help='configuration file', type=str)
options.parse_command_line()
load_py_file(options.options['conf'])
configs['port'] = options.options['port']
