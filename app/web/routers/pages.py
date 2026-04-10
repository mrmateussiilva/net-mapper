from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
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
            "nav_items": [
                {"href": "/", "label": "Inicio"},
                {"href": "/mapping", "label": "Mapeamento", "disabled": True},
                {"href": "/infra", "label": "Infraestrutura", "disabled": True},
            ],
        },
    )

