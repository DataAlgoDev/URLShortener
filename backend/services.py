import random
import time
from collections import defaultdict
from threading import Thread, Lock

from cachetools import LRUCache
from environment import SECRET_SALT
from database import SessionLocal, URLModel
from sqids import Sqids

from fastapi import HTTPException

_buffer_lock = Lock()
_cache_lock = Lock()

_click_counter = defaultdict(int)
lru_cache = LRUCache(maxsize=100)


# create sqids object
def get_sqids(secret_salt=SECRET_SALT) -> Sqids:
    alphanum = list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    rng = random.Random(secret_salt)
    rng.shuffle(alphanum)
    alphanum = "".join(alphanum)
    return Sqids(alphabet=alphanum, min_length=7)


# encode the given serial number to uid string
def encode_sln(serial_no: int) -> str:
    sqids = get_sqids()
    uid = sqids.encode([serial_no])
    if not uid or len(uid) > 7:
        raise HTTPException(status_code=503, detail="UID went out of bounds!")
    return uid


# decode the given string uid to serial number
def decode_uid(uid: str) -> int:
    sqids = get_sqids()
    decoded = sqids.decode(uid)
    if not decoded:
        raise HTTPException(status_code=404, detail="Invalid short URL")
    return decoded[0]


# gets entry from lru cache in case of a cache hit else queries db
def get_url_entry_from_db(uid: str):
    with _cache_lock:
        if uid in lru_cache:
            return lru_cache[uid]
    sln = decode_uid(uid)
    db = SessionLocal()
    try:
        entry = db.get(URLModel, sln)
        if not entry:
            raise HTTPException(status_code=404, detail="URL not found")
        with _cache_lock:
            lru_cache[uid] = entry
        return entry
    finally:
        db.close()


def evict_cache_entry(uid):
    with _cache_lock:
        if uid in lru_cache:
            del lru_cache[uid]


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
