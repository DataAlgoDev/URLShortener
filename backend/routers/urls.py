import time
from typing import Annotated

from database import get_db
from models import URLModel
from pydantic import BaseModel, HttpUrl
from services import decode_uid, encode_sln, get_url_entry_from_db
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="", tags=["URLs"])


class URLRequest(BaseModel):
    url: HttpUrl
    # Future feature - On demand deduplication O(logN)
    # dedup: bool = False


# get all urls in database
@router.get("/urls/")
def get_all_urls(db: Annotated[Session, Depends(get_db)]):
    all_urls = db.query(URLModel).all()
    print(all_urls, len(all_urls))
    return all_urls


# create new url entry with duplicates allowed : O(1)
@router.post("/shorten/", status_code=201)
def shorten_url(request: URLRequest, db: Annotated[Session, Depends(get_db)]):
    long_url_str = str(request.url)
    db_url = URLModel(l_url=long_url_str)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    # encode and get the unique 7 digit uid
    uid = encode_sln(db_url.sln)
    db_url.uid = uid
    db.commit()
    return {
        "uid": uid,
        "short_url": f"http://localhost:8000/{uid}",
        "long_url": request.url,
    }


# query database using decoded uid : O(1)
@router.get("/{uid}/", status_code=200)
def get_by_uid(uid: str):
    before = time.perf_counter()
    # check the uid in cache before doing any additional compute
    entry = get_url_entry_from_db(uid)

    diff = time.perf_counter() - before
    print(f"retrieval time : {diff:.4f}")
    return entry


# entries are stateless and need not to be deleted for now
@router.delete("/{uid}/", status_code=204)
def delete_by_uid(uid: str, db: Annotated[Session, Depends(get_db)]):
    sln = decode_uid(uid)
    entry = db.get(URLModel, sln)
    if not entry:
        raise HTTPException(status_code=404, detail="UID not found")
    db.delete(entry)
    db.commit()
    return {"message": f"Successfully deleted URL with uid '{uid}'"}
