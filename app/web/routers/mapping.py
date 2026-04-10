from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.services.mapping_service import load_and_process_data
from app.web.deps import build_nav_items, templates


router = APIRouter(prefix="/mapping")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_XLSX = PROJECT_ROOT / "Network Mapping - Safe Notos.xlsx"


@router.get("", response_class=HTMLResponse)
def mapping_index(request: Request):
    summary = None
    if DEFAULT_XLSX.exists():
        file_bytes = DEFAULT_XLSX.read_bytes()
        dfs, all_df = load_and_process_data(file_bytes)
        deck_rows = []
        for deck_name, df in dfs.items():
            deck_rows.append(
                {
                    "name": deck_name,
                    "rows": len(df),
                    "active": int((df.get("Active_norm") == "Active").sum()),
                    "unknown": int((df.get("Active_norm") == "Unknown").sum()),
                }
            )

        summary = {
            "source_name": DEFAULT_XLSX.name,
            "total_rows": len(all_df),
            "switches": len(set(all_df.get("Switch", []).dropna().astype(str))) if "Switch" in all_df.columns else 0,
            "decks": deck_rows,
        }

    return templates.TemplateResponse(
        request,
        "pages/mapping_index.html",
        {
            "title": "Mapeamento",
            "nav_items": build_nav_items("/mapping"),
            "summary": summary,
        },
    )
