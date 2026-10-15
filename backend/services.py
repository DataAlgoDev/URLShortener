import random
from functools import lru_cache

from config import SECRET_SALT
from database import SessionLocal, URLModel
from sqids import Sqids

from fastapi import HTTPException


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


@lru_cache(maxsize=100)
def get_url_entry_from_db(uid: str):
    sln = decode_uid(uid)
    db = SessionLocal()
    try:
        entry = db.get(URLModel, sln)
        if not entry:
            raise HTTPException(status_code=404, detail="URL not found")
        return entry
    finally:
        db.close()
