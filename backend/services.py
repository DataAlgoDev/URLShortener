import secrets
import time
from collections import defaultdict
from threading import Lock, Thread

import redis
from cachetools import LRUCache
from database import SessionLocal, URLModel
from security import decode_uid

from fastapi import Cookie, HTTPException

TOKEN_BYTES = 32
SESSION_TTL = 60
SESSION_STORE_SIZE = 2

_buffer_lock = Lock()
_cache_lock = Lock()

_click_counter = defaultdict(int)
url_cache = LRUCache(maxsize=100)

redis_client = redis.Redis(host="localhost", port=6379, db=0)


def get_url_entry_from_db(uid: str):
    """Gets entry from lru cache in case of a cache hit else queries db"""
    with _cache_lock:
        if uid in url_cache:
            return url_cache[uid]
    sln = decode_uid(uid)
    db = SessionLocal()
    try:
        entry = db.get(URLModel, sln)
        if not entry:
            raise HTTPException(status_code=404, detail="URL not found")
        with _cache_lock:
            url_cache[uid] = entry
        return entry
    finally:
        db.close()


def evict_cache_entry(uid):
    """Remove url entry from cache"""
    with _cache_lock:
        if uid in url_cache:
            del url_cache[uid]


def count_visits(uid):
    """Counts number of visits on a short link"""
    with _buffer_lock:
        _click_counter[uid] += 1


def _bg_count_flush():
    """Flush link click counts to database at time time intervals"""
    while True:
        time.sleep(5)
        with _buffer_lock:
            if not _click_counter:
                continue
            local_counts = dict(_click_counter)
            _click_counter.clear()
        db = SessionLocal()
        try:
            for uid, count in local_counts.items():
                sln = decode_uid(uid)
                entry = db.get(URLModel, sln)
                if entry:
                    entry.clicks += count
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error flushing URL analytics! {e}")
            # Emergency roll back to global
            with _buffer_lock:
                for uid, count in local_counts.items():
                    _click_counter[uid] += count
        finally:
            db.close()


flusher_thread = Thread(target=_bg_count_flush, daemon=True)
flusher_thread.start()


# returns user_id of a session
def session_user_get(session_id=Cookie(default=None)) -> int | None:
    """Returns session id"""
    return None if not session_id else int(redis_client.get(f"session:{session_id}"))


# Returns whether a user session exists of not
def user_validate(session_id=Cookie(default=None)) -> str:
    """Check if the user is authenticated"""
    print(session_id)
    user_id = redis_client.get(f"session:{session_id}")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized user")
    return int(user_id)


def create_session_token(user_id: int) -> str:
    """Generate a new secret session id"""
    new_token = secrets.token_hex(TOKEN_BYTES)
    redis_client.setex(f"session:{new_token}", SESSION_TTL, user_id)
    return new_token


def delete_session(session_id):
    """Delete a session id from Redis"""
    redis_client.delete(f"session:{session_id}")
