from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.web.deps import build_nav_items, templates


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/home.html",
        {
            "title": "Migracao FastAPI + HTMX",
            "nav_items": build_nav_items("/"),
        },
    )
