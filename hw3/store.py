import redis

DB_HOST = "192.168.99.100"
DB_PORT = 6379


def connect(host, port):
    db = redis.StrictRedis(host=host, port=port, socket_timeout=1)
    return db


db = connect(DB_HOST, DB_PORT)


def get(key, db=db):
    return db.get(key)


def set(key, value, db=db):
    return db.set(key, value)


def cache_get(key):
    pass


def cache_set(key, value, lifetime):
    pass


