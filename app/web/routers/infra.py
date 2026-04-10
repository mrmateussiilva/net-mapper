from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from app.infra_db import init_db
from app.services.infra_service import (
    create_equipment_from_form,
    create_rack_from_form,
    get_equipment_form_options,
    get_infra_summary,
    list_equipment_with_stats,
    list_racks_with_stats,
)
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


@router.get("/equipment", response_class=HTMLResponse)
def infra_equipment(request: Request):
    init_db()
    context = {
        "title": "Infraestrutura · Equipamentos",
        "nav_items": build_nav_items("/infra"),
        "equipment": list_equipment_with_stats(),
        "message": None,
        "submitted": None,
        **get_equipment_form_options(),
    }
    return templates.TemplateResponse(request, "pages/infra_equipment.html", context)


@router.post("/equipment", response_class=HTMLResponse)
def infra_equipment_create(
    request: Request,
    name: str = Form(...),
    type_: str = Form(...),
    rack_id: str = Form(""),
    manufacturer: str = Form(""),
    model: str = Form(""),
    rack_position: str = Form(""),
    notes: str = Form(""),
):
    init_db()
    ok, message = create_equipment_from_form(
        name=name,
        type_=type_,
        rack_id=rack_id,
        manufacturer=manufacturer,
        model=model,
        rack_position=rack_position,
        notes=notes,
    )
    context = {
        "request": request,
        "equipment": list_equipment_with_stats(),
        "message": {"kind": "success" if ok else "error", "text": message},
        "submitted": {
            "name": "" if ok else name,
            "type_": "Switch" if ok else type_,
            "rack_id": "" if ok else rack_id,
            "manufacturer": "" if ok else manufacturer,
            "model": "" if ok else model,
            "rack_position": "" if ok else rack_position,
            "notes": "" if ok else notes,
        },
        **get_equipment_form_options(),
    }
    return templates.get_template("partials/infra/equipment_manager.html").render(context)
