import time
from collections import defaultdict
from threading import Lock, Thread

from cachetools import LRUCache
from database import SessionLocal, URLModel
from security import decode_uid

from fastapi import Cookie, HTTPException, status

_buffer_lock = Lock()
_cache_lock = Lock()

_click_counter = defaultdict(int)
url_cache = LRUCache(maxsize=100)
# stores sessionID(str) as key and userID(int), expiration(float) as values
session_store: dict[str, tuple[int, float]] = {}


# gets entry from lru cache in case of a cache hit else queries db
def get_url_entry_from_db(uid: str):
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
    with _cache_lock:
        if uid in url_cache:
            del url_cache[uid]


def count_visits(uid):
    with _buffer_lock:
        _click_counter[uid] += 1


def _bg_count_flush():
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


# Returns userID from a valid session else raises error
def user_validate(session_id: str | None = Cookie(default=None)) -> str:
    values = session_store.get(session_id)
    if not values or values[1] < time.time():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login",
        )
    return values[0]
