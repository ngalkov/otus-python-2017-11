import redis
import functools

# Redis address
HOST = "192.168.99.100"
PORT = 6379

TIMEOUT = 3
MAX_ATTEMPT = 3

# db and db_cache can be different. Set the same for now
try:
    db = redis.StrictRedis(host=HOST, port=PORT, socket_timeout=TIMEOUT)
except:
    db = None

db_cache = db


def repeat_command(max_attempt=MAX_ATTEMPT, exc=None):
    # Decorator. Trying to execute decorated function and return this function result
    # On error repeat function max_attempt times. If no success raise exception exc or return None.
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempt):
                try:
                    return func(*args, **kwargs)
                except:
                    pass
            if exc:
                raise exc
            else:
                return None
        return wrapper
    return decorator


class Store(object):
    # redis-py does all encoding-decoding when communicate to Redis,
    # but return value is byte string so it needs to be decoded
    def __init__(self, db=db, db_cache=db_cache):
        self.db = db
        self.db_cache = db_cache

    @repeat_command(exc=OSError)
    def set(self, key, value):
        if self.db is None:
            raise OSError
        return self.db.set(key, value)

    @repeat_command(exc=OSError)
    def get(self, key):
        if self.db is None:
            raise OSError
        result = self.db.get(key)
        if result is None:
            return None
        else:
            return result.decode()

    @repeat_command()
    def cache_set(self, key, value, lifetime):
        if self.db_cache is None:
            return None
        return self.db_cache.set(key, value, ex=lifetime)

    @repeat_command()
    def cache_get(self, key):
        if self.db_cache is None:
            return None
        result = self.db_cache.get(key)
        if result is None:
            return None
        else:
            return result.decode()



