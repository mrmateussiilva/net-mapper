# app/infra_import.py
# Pipeline de importação da planilha Safe Notos → banco infra.
# Etapas: parse → normalizar → extrair entidades → inserir no DB.

import io
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.config import SHEETS
from app.infra_db import (
    get_conn,
    create_rack, create_equipment, create_port, create_connection,
    list_racks, list_equipment, list_ports,
)

# ── Sentinelas a ignorar ──────────────────────────────────────────────────────
_IGNORE = {"XXX", "XX", "X", "EMPTY", "NAN", "?", "", "NONE", "-", "--"}


def _clean(v) -> str:
    """Converte para string stripped; retorna '' se nulo ou sentinela."""
    s = str(v).strip() if pd.notna(v) else ""
    return "" if s.upper() in _IGNORE else s


def _norm_status(v) -> str:
    """Normaliza valores da coluna Active para: active | free | unknown."""
    s = str(v).strip().upper() if pd.notna(v) else ""
    if s in ("YES", "YES, YES", "YES,YES", "YES?", "1", "ACTIVE", "YES?"):
        return "active"
    if s in ("NO", "EMPTY", ""):
        return "free"
    return "unknown"


def _infer_type(name: str) -> str:
    """Infere o tipo do equipamento pelo nome."""
    n = name.upper()
    if any(k in n for k in ("SW", "SWITCH", "CATALYST", "CISCO", "NEXUS")):
        return "Switch"
    if any(k in n for k in ("PP", "PATCH", "PAINEL")):
        return "Patch Panel"
    if any(k in n for k in ("FW", "FIRE", "FORTINET", "ASA", "PALO")):
        return "Firewall"
    if any(k in n for k in ("SRV", "SERVER", "DELL", "HP ", "NRTX")):
        return "Servidor"
    if any(k in n for k in ("RTR", "ROUTER", "ROTEADOR")):
        return "Router"
    return "Switch"  # padrão — a maioria é switch


# ── Parse da planilha ─────────────────────────────────────────────────────────

def parse_spreadsheet(file_bytes: bytes) -> Dict:
    """
    Lê o xlsx e retorna um dicionário estruturado com:
    {
      "racks": set of rack names,
      "equipment": list of dicts {name, type, rack_name, location},
      "connections": list of dicts {pp_name, pp_port, sw_name, sw_port, wall_port, status, notes, deck},
      "sheets_found": list of str,
      "warnings": list of str,
      "row_counts": dict,
    }
    """
    racks_seen: Dict[str, str] = {}      # rack_name → deck (localização)
    equip_seen: Dict[str, Dict] = {}     # equip_name → {type, rack_name, location}
    connections: List[Dict] = []
    warnings: List[str] = []
    sheets_found: List[str] = []
    row_counts: Dict[str, int] = {}
    duplicate_conns: set = set()

    xf = pd.ExcelFile(io.BytesIO(file_bytes))
    available = xf.sheet_names

    target_sheets = [s for s in SHEETS if s in available]
    if not target_sheets:
        warnings.append("Nenhuma aba esperada encontrada (Deck B - L717, Deck M - L521, Deck M - L519).")
        return {
            "racks": racks_seen, "equipment": equip_seen,
            "connections": connections, "sheets_found": sheets_found,
            "warnings": warnings, "row_counts": row_counts,
        }

    for sheet in target_sheets:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=5)
        df = df.iloc[:, 1:]
        df.columns = [str(c).strip() for c in df.columns]

        # L519 usa "1" como nome da coluna Rack
        if "1" in df.columns and "Rack" not in df.columns:
            df = df.rename(columns={"1": "Rack"})

        # Descartar linhas onde Rack == "Rack" (cabeçalho duplicado)
        if "Rack" in df.columns:
            df = df[df["Rack"].astype(str).str.strip() != "Rack"]

        # Localização = nome do sheet
        location = sheet  # ex: "Deck B - L717"

        valid_rows = 0
        for _, row in df.iterrows():
            rack1  = _clean(row.get("Rack", ""))
            rack2  = _clean(row.get("Rack2", ""))
            pp     = _clean(row.get("Optic Patch Painel", ""))
            port_n = _clean(row.get("Port", ""))
            sw     = _clean(row.get("Switch", ""))
            sw_pt  = _clean(row.get("Switch Port", ""))
            wp     = _clean(row.get("Wall Port", ""))
            active = _norm_status(row.get("Active", ""))

            # Notas: Observation + colunas unnamed
            obs_parts = []
            for col in ["Observation"] + [c for c in df.columns if "Unnamed" in c]:
                v = _clean(row.get(col, ""))
                operational_tags = {"FEITO", "CH", "OK", "?", "DUVIDA"}
                if v and v.upper() not in operational_tags:
                    obs_parts.append(v)
            notes = " | ".join(obs_parts) if obs_parts else ""

            # Registrar racks
            if rack1:
                racks_seen.setdefault(rack1, location)
            if rack2:
                racks_seen.setdefault(rack2, location)

            # Registrar patch panel como equipamento (rack1)
            if pp and pp.upper() not in _IGNORE:
                if pp not in equip_seen:
                    equip_seen[pp] = {
                        "name": pp,
                        "type": "Patch Panel",
                        "rack_name": rack1 or None,
                        "location": location,
                    }

            # Registrar switch como equipamento (rack2)
            if sw and sw.upper() not in _IGNORE:
                if sw not in equip_seen:
                    equip_seen[sw] = {
                        "name": sw,
                        "type": _infer_type(sw),
                        "rack_name": rack2 or None,
                        "location": location,
                    }

            # Só criar conexão se tiver pp + port + switch + switch port
            if pp and port_n and sw and sw_pt:
                conn_key = (pp, str(port_n), sw, str(sw_pt))
                if conn_key not in duplicate_conns:
                    duplicate_conns.add(conn_key)
                    connections.append({
                        "pp_name":   pp,
                        "pp_port":   str(port_n),
                        "sw_name":   sw,
                        "sw_port":   str(sw_pt),
                        "wall_port": wp,
                        "status":    active,
                        "notes":     notes,
                        "deck":      location,
                    })
                    valid_rows += 1

        sheets_found.append(sheet)
        row_counts[sheet] = valid_rows

    return {
        "racks":        racks_seen,
        "equipment":    equip_seen,
        "connections":  connections,
        "sheets_found": sheets_found,
        "warnings":     warnings,
        "row_counts":   row_counts,
    }


# ── Execução do Import ────────────────────────────────────────────────────────

def execute_import(parsed: Dict, skip_existing: bool = True) -> Dict:
    """
    Insere as entidades extraídas no banco.
    Retorna um relatório com contagens de inserções e erros.
    """
    report = {
        "racks_created": 0,
        "racks_skipped": 0,
        "equip_created": 0,
        "equip_skipped": 0,
        "ports_created": 0,
        "conns_created": 0,
        "conns_skipped": 0,
        "errors": [],
    }

    # ── 1. Racks ──
    existing_racks = {r["name"]: r["id"] for r in list_racks()}
    rack_id_map: Dict[str, int] = dict(existing_racks)

    for rack_name, location in parsed["racks"].items():
        if rack_name in existing_racks and skip_existing:
            report["racks_skipped"] += 1
            continue
        try:
            new_id = create_rack(rack_name, location=location)
            rack_id_map[rack_name] = new_id
            report["racks_created"] += 1
        except Exception as e:
            report["errors"].append(f"Rack '{rack_name}': {e}")

    # ── 2. Equipment ──
    existing_equip = {e["name"]: e["id"] for e in list_equipment()}
    equip_id_map: Dict[str, int] = dict(existing_equip)

    for eq_name, eq_data in parsed["equipment"].items():
        if eq_name in existing_equip and skip_existing:
            report["equip_skipped"] += 1
            continue
        try:
            rack_id = rack_id_map.get(eq_data["rack_name"]) if eq_data.get("rack_name") else None
            new_id = create_equipment(
                name=eq_name,
                type_=eq_data["type"],
                rack_id=rack_id,
                notes=f"Importado de: {eq_data['location']}",
            )
            equip_id_map[eq_name] = new_id
            report["equip_created"] += 1
        except Exception as e:
            report["errors"].append(f"Equip '{eq_name}': {e}")

    # ── 3. Ports + Connections ──
    # Cache: equip_id → set of port_names already created
    port_cache: Dict[int, Dict[str, int]] = {}  # equip_id → {port_name → port_id}

    def _get_or_create_port(equip_id: int, port_name: str, status: str = "free") -> Optional[int]:
        if equip_id not in port_cache:
            existing = {p["port_name"]: p["id"] for p in list_ports(equip_id)}
            port_cache[equip_id] = existing
        if port_name in port_cache[equip_id]:
            return port_cache[equip_id][port_name]
        try:
            new_id = create_port(equip_id, port_name, port_type="", status=status)
            port_cache[equip_id][port_name] = new_id
            report["ports_created"] += 1
            return new_id
        except Exception as e:
            report["errors"].append(f"Port '{port_name}' equip_id={equip_id}: {e}")
            return None

    # Track already-inserted connections to avoid dupes within this run
    conn_set: set = set()

    for conn in parsed["connections"]:
        pp_id = equip_id_map.get(conn["pp_name"])
        sw_id = equip_id_map.get(conn["sw_name"])

        if not pp_id or not sw_id:
            report["conns_skipped"] += 1
            continue

        pp_port_id = _get_or_create_port(pp_id, conn["pp_port"], conn["status"])
        sw_port_id = _get_or_create_port(sw_id, conn["sw_port"], conn["status"])

        if not pp_port_id or not sw_port_id:
            report["conns_skipped"] += 1
            continue

        conn_key = (pp_port_id, sw_port_id)
        if conn_key in conn_set:
            report["conns_skipped"] += 1
            continue
        conn_set.add(conn_key)

        notes_parts = []
        if conn.get("wall_port"):
            notes_parts.append(f"Wall Port: {conn['wall_port']}")
        if conn.get("notes"):
            notes_parts.append(conn["notes"])
        if conn.get("deck"):
            notes_parts.append(f"Deck: {conn['deck']}")

        try:
            create_connection(
                source_port_id=pp_port_id,
                destination_port_id=sw_port_id,
                cable_type="Fibra",
                notes=" | ".join(notes_parts),
            )
            report["conns_created"] += 1
        except Exception as e:
            report["errors"].append(f"Conn {conn['pp_name']}:{conn['pp_port']} → {conn['sw_name']}:{conn['sw_port']}: {e}")
            report["conns_skipped"] += 1

    return report
