from pathlib import Path

from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def build_nav_items(active_path: str) -> list[dict[str, str | bool]]:
    items = [
        {"href": "/", "label": "Inicio"},
        {"href": "/mapping", "label": "Mapeamento"},
        {"href": "/infra", "label": "Infraestrutura"},
    ]
    for item in items:
        item["active"] = item["href"] == active_path
    return items
