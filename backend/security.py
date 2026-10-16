import random

import bcrypt
from environment import SECRET_SALT
from sqids import Sqids

from fastapi import HTTPException


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


def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt directly."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a stored bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )
