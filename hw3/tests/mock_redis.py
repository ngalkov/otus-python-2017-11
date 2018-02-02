import datetime
import time

import redis


class MockRedis(object):
    def __init__(self, error=False):
        self.error = error  # for mocking redis-py error
        self.storage = {}

    def set(self, key, value, ex=None):
        if self.error:
            raise redis.RedisError
        expired_at = None
        if ex is not None:
            expired_at = datetime.datetime.now() + datetime.timedelta(seconds=ex)
        self.storage[key] = [value, expired_at]
        return True

    def get(self, key):
        if self.error:
            raise redis.RedisError
        value = self.storage.get(key, None)
        if value is None:
            return None
        # redis-py returns byte string from Redis - so return value should be encoded into byte string for mocking
        if value[1] is None:
            return value[0].encode()
        if value[1] > datetime.datetime.now():
            return value[0].encode()
        else:
            del self.storage[key]
            return None


if __name__ == "__main__":
    r = MockRedis()
    r.set("ключ", "значение", ex=1)
    if r.get("ключ").decode() != "значение":
        print("set() errror")
    time.sleep(1)
    if not r.get("ключ") is None:
        print("set(ex) errror")
    if not r.get("no_key") is None:
        print("no key errror")

    r = MockRedis(error=True)
    try:
        r.set("key", "value")
        print("raise redis.RedisError on set() error")
    except redis.RedisError:
        pass
        try:
            r.get("key")
            print("raise redis.RedisError on get() error")
        except redis.RedisError:
            pass
    print("Tests done.")
