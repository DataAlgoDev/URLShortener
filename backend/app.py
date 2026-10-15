import time
from typing import Annotated

from database import Base, URLModel, engine, get_db
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from services import (
    count_visits,
    decode_uid,
    encode_sln,
    evict_cache_entry,
    get_url_entry_from_db,
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from fastapi import Depends, FastAPI, HTTPException, Request

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


# Get all URLs in database
@app.get("/urls/")
def get_all_urls(db: Annotated[Session, Depends(get_db)]):
    all_urls = db.query(URLModel).all()
    print(all_urls, len(all_urls))
    return all_urls


# Create new url entry with rate limiting
@app.post("/shorten/", status_code=201)
@limiter.limit("1/second")  # Token bucket capacity
def shorten_url(
    request: Request, body: URLRequest, db: Annotated[Session, Depends(get_db)]
):
    long_url_str = str(body.url)
    db_url = URLModel(l_url=long_url_str)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)

    # Encode and get the unique 7 digit uid
    uid = encode_sln(db_url.sln)
    db_url.uid = uid
    db.commit()
    return {
        "uid": uid,
        "short_url": f"http://localhost:8000/{uid}",
        "long_url": body.url,
    }


# Query database using decoded uid with rate limiting
@app.get("/{uid}/", status_code=200)
@limiter.limit("3/second")
def get_by_uid(request: Request, uid: str):
    before = time.perf_counter()
    entry = get_url_entry_from_db(uid)
    diff = time.perf_counter() - before
    # increment the counter for uid
    count_visits(uid)
    print(f"retrieval time : {diff:.4f}")
    return entry


# Delete entry
@app.delete("/{uid}/", status_code=200)
def delete_by_uid(uid: str, db: Annotated[Session, Depends(get_db)]):
    sln = decode_uid(uid)
    entry = db.get(URLModel, sln)
    if not entry:
        raise HTTPException(status_code=404, detail="UID not found")
    db.delete(entry)
    db.commit()
    # Removes stale entry from cache
    evict_cache_entry(uid)
    return {"message": f"Successfully deleted URL with uid '{uid}'"}
