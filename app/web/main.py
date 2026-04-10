from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.routers.pages import router as pages_router


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


app = FastAPI(title="Network Mapping", version="0.1.0")
app.include_router(pages_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

