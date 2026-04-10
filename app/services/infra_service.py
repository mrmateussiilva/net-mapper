from collections import Counter

from app.infra_db import (
    create_equipment,
    create_rack,
    list_connections_for_equipment,
    list_equipment,
    list_ports,
    list_racks,
)


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


def get_equipment_form_options() -> dict:
    """Return select options required by the equipment form."""
    return {
        "rack_options": list_racks(),
        "device_types": ["Switch", "Router", "Servidor", "Patch Panel", "Firewall", "UPS", "Outro"],
    }


def list_equipment_with_stats() -> list[dict]:
    """Return equipment enriched with port and connection counts."""
    equipment = list_equipment()
    for item in equipment:
        ports = list_ports(item["id"])
        connections = list_connections_for_equipment(item["id"])
        item["port_count"] = len(ports)
        item["connection_count"] = len(connections)
    return equipment


def create_equipment_from_form(
    name: str,
    type_: str,
    rack_id: str = "",
    manufacturer: str = "",
    model: str = "",
    rack_position: str = "",
    notes: str = "",
) -> tuple[bool, str]:
    """Validate and create equipment from a web form payload."""
    clean_name = name.strip()
    clean_type = type_.strip()
    if not clean_name:
        return False, "Nome do equipamento é obrigatório."
    if not clean_type:
        return False, "Tipo do equipamento é obrigatório."

    existing_names = {item["name"].strip().lower() for item in list_equipment()}
    if clean_name.lower() in existing_names:
        return False, f"Equipamento '{clean_name}' já existe."

    resolved_rack_id = None
    if rack_id.strip():
        try:
            resolved_rack_id = int(rack_id)
        except ValueError:
            return False, "Rack inválido."

    create_equipment(
        name=clean_name,
        type_=clean_type,
        manufacturer=manufacturer,
        model=model,
        rack_id=resolved_rack_id,
        rack_position=rack_position,
        notes=notes,
    )
    return True, f"Equipamento '{clean_name}' criado com sucesso."
