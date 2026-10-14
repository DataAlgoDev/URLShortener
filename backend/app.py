from database import Base, engine
from routers import urls

from fastapi import FastAPI

# crate database on startup for development
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URLShortener")

app.include_router(urls.router)


@app.get("/")
def root():
    return {"message": "Welcome to URLShortener"}
