import time
from typing import Annotated

from database import Base, URLModel, UserModel, engine, get_db
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from security import decode_uid, encode_sln, hash_password, verify_password
from services import (
    count_visits,
    create_session_token,
    evict_cache_entry,
    get_url_entry_from_db,
    user_validate,
    session_user_get,
    SESSION_TTL,
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from fastapi import Depends, FastAPI, HTTPException, Request, status, Cookie

GUEST_CREATE_LIMIT = "1/second"
USER_CREATE_LIMIT = "1/second"
DEFAULT_GET_LIMIT = "3/second"

# Create database on startup for development
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URLShortener")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Serving static files from one level up in the 'frontend' folder
app.mount("/static", StaticFiles(directory="../frontend"), name="static")


@app.get("/")
def root():
    return FileResponse("../frontend/index.html")


class URLRequest(BaseModel):
    url: HttpUrl


class SignupRequest(BaseModel):
    user_name: str
    password: str


# Get all URLs in database
@app.get("/urls/", name="Get all URLs in database")
def get_all_urls(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[str, Depends(user_validate)],
):
    all_urls = db.query(URLModel).all()
    print(len(all_urls))
    return all_urls


def creation_helper(body, db, user_id=None):
    print(f"user_id : {user_id}")
    long_url_str = str(body.url)
    db_url = URLModel(l_url=long_url_str)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    # Encode and get the unique 7 digit uid
    uid = encode_sln(db_url.sln)
    db_url.uid = uid
    if user_id:
        db_url.user_id = int(user_id)
    db.commit()
    return {
        "uid": uid,
        "short_url": f"http://localhost:8000/{uid}",
        "long_url": body.url,
    }


# Create new url entry with rate limiting
@app.post("/users/shorten/", status_code=201)
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


# Query database using decoded uid with rate limiting
@app.get("/{uid}/", status_code=200)
@limiter.limit(limit_value=DEFAULT_GET_LIMIT)  # Fixed token bucket for all get calls
def get_by_uid(request: Request, uid: str):
    before = time.perf_counter()
    entry = get_url_entry_from_db(uid)
    diff = time.perf_counter() - before
    # increment the counter for uid
    count_visits(uid)
    print(f"retrieval time : {diff:.4f}")
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


# singup api
@app.post("/api/signup/", status_code=status.HTTP_201_CREATED)
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
@app.post("/api/signin/", status_code=status.HTTP_200_OK)
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
        url="/user/dashboard", status_code=status.HTTP_303_SEE_OTHER
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
    print(session_token)
    return response


@app.get("/user/dashboard")
def user_dashboard(
    user_id: Annotated[int, Depends(user_validate)],
    db: Annotated[Session, Depends(get_db)],
):
    user_data = db.query(UserModel).filter(UserModel.user_id == user_id).first()
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    username = user_data.user_name
    print(username)
    # return {f"Welcome {username}"}
    return FileResponse("../frontend/dashboard.html")
