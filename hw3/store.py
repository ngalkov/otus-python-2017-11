import redis
import socket

# Redis address
HOST = "192.168.99.100"
PORT = 6379

TIMEOUT = 3
MAX_ATTEMPT = 3

# db and db_cache can be different. Set the same for now
db = redis.StrictRedis(host=HOST, port=PORT, socket_timeout=TIMEOUT)
db_cache = db


class Store(object):
    # redis-py does all encoding-decoding when communicate to Redis,
    # but return value is byte string so it needs to be decoded
    def __init__(self, db=db, db_cache=db_cache):
        self.db = db
        self.db_cache = db_cache

    def set(self, key, value):
        for attempt in range(MAX_ATTEMPT):
            try:
                return self.db.set(key, value)
            except redis.RedisError:
                pass
        raise OSError

    def get(self, key):
        for attempt in range(MAX_ATTEMPT):
            try:
                result = self.db.get(key)
                if result is None:
                    return None
                else:
                    return result.decode()
            except redis.RedisError:
                pass
        raise OSError

    def cache_set(self, key, lifetime, value):
        for attempt in range(MAX_ATTEMPT):
            try:
                return self.db_cache.set(key, value, ex=lifetime)
            except redis.RedisError:
                pass
        return None

    def cache_get(self, key):
        for attempt in range(MAX_ATTEMPT):
            try:
                result = self.db_cache.get(key)
                if result is None:
                    return None
                else:
                    return result.decode()
            except redis.RedisError:
                pass
        return None



