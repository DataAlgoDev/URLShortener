import logging
import sys
import time
from pathlib import Path
from typing import Annotated

from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from redis.exceptions import RedisError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import Base, URLModel, UserModel, engine, get_db
from backend.security import decode_uid, encode_sln, hash_password, verify_password
from backend.services import (
    SESSION_TTL,
    count_visits,
    create_session_token,
    delete_session,
    evict_cache_entry,
    get_url_entry_from_db,
    redis_client,
    session_user_get,
    user_validate,
)
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True,  # Overrides Gunicorn's default log suppression
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/"
BASE_DIR = Path(__file__).resolve().parent  # points to /app/backend
FRONTEND_DIR = BASE_DIR.parent / "frontend"  # points to /app/frontend

GUEST_CREATE_LIMIT = "1/second"
USER_CREATE_LIMIT = "1/second"
DEFAULT_GET_LIMIT = "3/second"


class URLRequest(BaseModel):
    url: HttpUrl


class SignupRequest(BaseModel):
    user_name: str
    password: str


# Create database on startup for development
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URLShortener")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Serving static files from one level up in the 'frontend' folder
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def root():
    return FileResponse(f"{FRONTEND_DIR}/index.html")


# Get all URLs in database
@app.get("/urls/", name="Get all URLs in database")
def get_all_urls(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[str, Depends(user_validate)],
):
    all_urls = db.query(URLModel).all()
    logger.info("%s", len(all_urls))
    return all_urls


# Create new url entry with rate limiting
@app.post("/users/shorten/", status_code=status.HTTP_201_CREATED)
@limiter.limit(USER_CREATE_LIMIT)
def user_shorten_url(
    request: Request,
    body: URLRequest,
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[int, Depends(session_user_get)],
):
    return creation_helper(body, db, user_id=user_id)


# Create new url entry with rate limiting
@app.post("/guest/shorten/", status_code=201)
@limiter.limit(GUEST_CREATE_LIMIT)
def guest_shorten_url(
    request: Request,
    body: URLRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return creation_helper(body, db)


@app.post("/users/signup/", status_code=status.HTTP_201_CREATED)
def sign_up(
    request: Request, body: SignupRequest, db: Annotated[Session, Depends(get_db)]
):
    # check is username exists
    resp = db.query(UserModel).filter(UserModel.user_name == body.user_name).first()
    if resp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User Exists"
        )
    obj = UserModel(user_name=body.user_name, hashed_pwd=hash_password(body.password))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# login api
@app.post("/users/signin/", status_code=status.HTTP_200_OK)
def sign_in(body: SignupRequest, db: Annotated[Session, Depends(get_db)]):
    # raise error if username / combination doesnt exist
    user_name = body.user_name
    user_password = body.password
    resp = db.query(UserModel).filter(UserModel.user_name == user_name).first()
    if not resp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not verify_password(user_password, resp.hashed_pwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username / Password is not correct",
        )
    user_id = resp.user_id
    # create a session token and store in hash
    session_token = create_session_token(user_id)
    # return with http only cookie
    response = RedirectResponse(
        url="/users/dashboard/", status_code=status.HTTP_303_SEE_OTHER
    )
    # redirect to user page
    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        secure=False,  # needs https
        samesite="lax",
        max_age=SESSION_TTL,
    )
    return response


@app.get("/users/dashboard/", status_code=200)
def user_dashboard(user_id: Annotated[int, Depends(user_validate)]):
    return FileResponse(f"{FRONTEND_DIR}/dashboard.html")


@app.post("/users/logout/", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(
    response: Response,
    session_id: Annotated[str | None, Cookie()] = None,
):
    if session_id:
        # Evict the session key directly from Redis
        delete_session(session_id)

    # Always clear the cookie from the browser regardless of session state
    response.delete_cookie(key="session_id", path="/", httponly=True, samesite="lax")
    return {}


@app.get("/api/me/", status_code=status.HTTP_200_OK)
def get_user_data(
    user_id: Annotated[int, Depends(user_validate)],
    db: Annotated[Session, Depends(get_db)],
):
    user_info = (
        db.query(URLModel)
        .filter(URLModel.user_id == user_id)
        .order_by(URLModel.clicks.desc())
        .all()
    )
    user_data = db.query(UserModel).filter(UserModel.user_id == user_id).first()
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    username = user_data.user_name

    return username, user_info


# Query database using decoded uid with rate limiting
@app.get("/{uid}/", status_code=status.HTTP_200_OK)
@limiter.limit(limit_value=DEFAULT_GET_LIMIT)  # Fixed token bucket for all get calls
def get_by_uid(request: Request, uid: str):
    before = time.perf_counter()
    entry = get_url_entry_from_db(uid)
    diff = time.perf_counter() - before
    # increment the counter for uid
    count_visits(uid)
    logger.info(f"URL retrieval time : {diff:.4f}")
    return entry


## Delete entry requires user validation
@app.delete("/api/{uid}/", status_code=status.HTTP_200_OK)
def delete_by_uid(
    request: Request,
    uid: str,
    db: Annotated[Session, Depends(get_db)],
    userid: Annotated[str, Depends(user_validate)],
):
    sln = decode_uid(uid)
    entry = db.get(URLModel, sln)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="UID not found"
        )
    db.delete(entry)
    db.commit()
    # Removes stale entry from cache
    evict_cache_entry(uid)
    return {"message": f"Successfully deleted URL with uid '{uid}'"}


@app.get("/health", status_code=status.HTTP_200_OK)
def readiness_check(response: Response, db: Annotated[Session, Depends(get_db)]):
    is_healthy = True
    health_status = {"status": "healthy", "dependencies": {}}
    # Postgres
    try:
        db.execute(text("SELECT 1"))
        health_status["dependencies"]["postgres"] = {"status": "up"}
    except SQLAlchemyError as sqlal_err:
        is_healthy = False
        health_status["dependencies"]["postgres"] = {
            "status": "down",
            "error": str(sqlal_err),
        }
        logger.error("Error occurred while checking postgres db : %s", sqlal_err)
    except Exception as e:
        logger.exception("Unexpected error occurred! : %s", e)  # noqa: TRY401
    # redis
    try:
        if redis_client.ping():
            health_status["dependencies"]["redis"] = {"status": "up"}
        else:
            raise ConnectionError("Ping Failed")
    except ConnectionError as conn_err:
        is_healthy = False
        health_status["dependencies"]["redis"] = {
            "status": "down",
            "error": str(conn_err),
        }
    except RedisError as redis_err:
        logger.error("Error while checking redis status :%s", redis_err)
        is_healthy = False
        health_status["dependencies"]["redis"] = {
            "status": "down",
            "error": str(redis_err),
        }
    except Exception as e:
        logger.exception("Unexpected error occurred! : %s", e)  # noqa: TRY401
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        health_status["status"] = "unhealthy"
        logger.error("One or more dependencies are not healthy! : %s", health_status)
    return health_status


#### Helpers ####
def creation_helper(body, db, user_id=None):
    long_url_str = str(body.url)
    db_url = URLModel(l_url=long_url_str)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    # Encode and get the unique 7 digit uid
    uid = encode_sln(db_url.sln)
    short_url = f"{BASE_URL}{uid}"
    db_url.uid = uid
    db_url.s_url = short_url
    if user_id:
        db_url.user_id = int(user_id)
    db.commit()
    return {
        "uid": uid,
        "short_url": f"http://localhost:8000/{uid}",
        "long_url": body.url,
    }
