import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def validate_secrets(variable, name):
    if not variable:
        raise ValueError(f"Unable to find environment variable! : {name}")


DATABASE_URL = os.getenv("DATABASE_URL")
validate_secrets(DATABASE_URL, "DATABASE_URL")

SECRET_SALT = os.getenv("SECRET_SALT")
validate_secrets(SECRET_SALT, "SECRET_SALT")
