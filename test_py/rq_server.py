import redis
#from lib.hqby.config import configs
from rq import Worker, Queue, Connection
from lib.baidu_pusher.Channel import *

listen = ['high', 'default', 'low']

#redis_conf = configs['redis']['test2']
#redis_host = redis_conf['host']
#redis_port = redis_conf['port']
redis_host = "localhost"
redis_port = 6379
#redis_url = 'redis://' + redis_host + ':' + redis_port
#conn = redis.from_url(redis_url)
conn = redis.StrictRedis(host=redis_host, port=redis_port, db=0)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
