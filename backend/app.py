from database import Base, engine
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routers import urls

from fastapi import FastAPI

# crate database on startup for development
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URLShortener")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(urls.router)


@app.get("/")
def root():
    return FileResponse("static/index.html")
