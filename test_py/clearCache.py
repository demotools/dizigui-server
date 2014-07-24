import hqby.cache
from hqby.config import configs
import cPickle
import hqby.db


def main():
    key_push = 'push-' + str(user_id)
    conn = hqby.cache.get_sync_conn(configs['redis_name'])
    conn.delete(key_push)

if __name__ == '__main__':
    main()
