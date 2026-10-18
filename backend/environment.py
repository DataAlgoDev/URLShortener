import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "../.env")


def validate_secret(name: str, fallback: str | None = None) -> str:
    value = os.getenv(name)
    if not value and not fallback:
        raise ValueError(
            f"Unable to set environment variable! for : {name}, and empty fallback"
        )
    return value if value else fallback


DATABASE_URL = validate_secret("DATABASE_URL")

SECRET_SALT = validate_secret("SECRET_SALT", "DEFAULT-SALT")

REDIS_URL = validate_secret("REDIS_URL", "redis://redis:6379/0")
