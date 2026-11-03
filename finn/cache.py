"""Small persistent JSON cache; separate connections avoid shared-thread transactions."""
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connection():
    path = Path(os.getenv('FINN_CACHE_PATH', 'cache.db'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.execute('CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT, ts REAL)')
    try:
        with db:
            yield db
    finally:
        db.close()


def get(key, ttl=None):
    with connection() as db:
        row = db.execute('SELECT v,ts FROM kv WHERE k=?', (key,)).fetchone()
    if row and (ttl is None or time.time() - row[1] < ttl):
        return json.loads(row[0])


def put(key, value):
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO kv VALUES(?,?,?)', (key, json.dumps(value), time.time()))
    return value
