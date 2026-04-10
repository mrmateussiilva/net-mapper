from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from app.infra_db import init_db
from app.services.infra_service import create_rack_from_form, get_infra_summary, list_racks_with_stats
from app.web.deps import build_nav_items, templates


router = APIRouter(prefix="/infra")


@router.get("", response_class=HTMLResponse)
def infra_index(request: Request):
    init_db()
    summary = get_infra_summary()

    return templates.TemplateResponse(
        request,
        "pages/infra_index.html",
        {
            "title": "Infraestrutura",
            "nav_items": build_nav_items("/infra"),
            "summary": summary,
        },
    )


@router.get("/racks", response_class=HTMLResponse)
def infra_racks(request: Request):
    init_db()
    context = {
        "title": "Infraestrutura · Racks",
        "nav_items": build_nav_items("/infra"),
        "racks": list_racks_with_stats(),
        "message": None,
        "submitted": None,
    }
    return templates.TemplateResponse(request, "pages/infra_racks.html", context)


@router.post("/racks", response_class=HTMLResponse)
def infra_racks_create(
    request: Request,
    name: str = Form(...),
    location: str = Form(""),
    notes: str = Form(""),
):
    init_db()
    ok, message = create_rack_from_form(name, location, notes)
    context = {
        "request": request,
        "racks": list_racks_with_stats(),
        "message": {"kind": "success" if ok else "error", "text": message},
        "submitted": {"name": "" if ok else name, "location": "" if ok else location, "notes": "" if ok else notes},
    }
    return templates.get_template("partials/infra/racks_manager.html").render(context)
