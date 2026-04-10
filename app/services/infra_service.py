from collections import Counter

from app.infra_db import create_rack, list_equipment, list_ports, list_racks, list_connections_for_equipment


def get_infra_summary() -> dict:
    """Build a lightweight summary for the infra landing page."""
    racks = list_racks()
    equipment = list_equipment()
    ports = sum(len(list_ports(item["id"])) for item in equipment)
    connections = sum(len(list_connections_for_equipment(item["id"])) for item in equipment)
    return {
        "racks": len(racks),
        "equipment": len(equipment),
        "ports": ports,
        "connections": connections // 2 if connections else 0,
        "equipment_preview": equipment[:8],
    }


def list_racks_with_stats() -> list[dict]:
    """Return racks enriched with equipment counts for listing pages."""
    racks = list_racks()
    equipment = list_equipment()
    by_rack = Counter(item.get("rack_name") for item in equipment if item.get("rack_name"))

    for rack in racks:
        rack["equipment_count"] = by_rack.get(rack["name"], 0)
    return racks


def create_rack_from_form(name: str, location: str = "", notes: str = "") -> tuple[bool, str]:
    """Validate and create a rack from a web form payload."""
    clean_name = name.strip()
    if not clean_name:
        return False, "Nome do rack é obrigatório."

    existing_names = {rack["name"].strip().lower() for rack in list_racks()}
    if clean_name.lower() in existing_names:
        return False, f"Rack '{clean_name}' já existe."

    create_rack(clean_name, location=location, notes=notes)
    return True, f"Rack '{clean_name}' criado com sucesso."
