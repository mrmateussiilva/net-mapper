# app/infra_db.py
# Persistence layer for the rack infrastructure wiki.
# Uses the existing cabling.db SQLite file — tables are prefixed with infra_
# to avoid any collision with future uses of the same database.

import os
import sqlite3
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# On Streamlit Cloud the working dir is read-only; use a writable tmp dir as fallback.
# Locally we keep using cabling.db in the project root (existing file).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
_LOCAL_DB = os.path.join(_PROJECT_ROOT, "cabling.db")

def _get_db_path() -> str:
    """Returns a writable path for the SQLite database."""
    # Prefer the local project file when writable (local dev)
    if os.access(_PROJECT_ROOT, os.W_OK):
        return _LOCAL_DB
    # Fallback: system temp directory (Streamlit Cloud, etc.)
    return os.path.join(tempfile.gettempdir(), "cabling_infra.db")

_DB_PATH = _get_db_path()


def get_conn() -> sqlite3.Connection:
    """Returns a sqlite3 connection with row_factory set to dict-like rows."""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Creates all infra tables if they don't exist. Safe to call repeatedly."""
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS infra_racks (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            location TEXT,
            notes    TEXT
        );

        CREATE TABLE IF NOT EXISTS infra_equipment (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            type          TEXT NOT NULL,
            manufacturer  TEXT,
            model         TEXT,
            rack_id       INTEGER REFERENCES infra_racks(id) ON DELETE SET NULL,
            rack_position TEXT,
            notes         TEXT
        );

        CREATE TABLE IF NOT EXISTS infra_ports (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL REFERENCES infra_equipment(id) ON DELETE CASCADE,
            port_name    TEXT NOT NULL,
            port_type    TEXT,
            status       TEXT DEFAULT 'free',
            notes        TEXT
        );

        CREATE TABLE IF NOT EXISTS infra_connections (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            source_port_id      INTEGER NOT NULL REFERENCES infra_ports(id) ON DELETE CASCADE,
            destination_port_id INTEGER NOT NULL REFERENCES infra_ports(id) ON DELETE CASCADE,
            cable_type          TEXT,
            notes               TEXT
        );
    """)
    conn.commit()
    conn.close()


# ── Racks ──────────────────────────────────────────────────────────────────────

def list_racks() -> List[Dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM infra_racks ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_rack(rack_id: int) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM infra_racks WHERE id = ?", (rack_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_rack(name: str, location: str = "", notes: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO infra_racks (name, location, notes) VALUES (?, ?, ?)",
        (name.strip(), location.strip(), notes.strip()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_rack(rack_id: int, name: str, location: str, notes: str) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE infra_racks SET name=?, location=?, notes=? WHERE id=?",
        (name.strip(), location.strip(), notes.strip(), rack_id),
    )
    conn.commit()
    conn.close()


def delete_rack(rack_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM infra_racks WHERE id = ?", (rack_id,))
    conn.commit()
    conn.close()


# ── Equipment ─────────────────────────────────────────────────────────────────

def list_equipment(rack_id: Optional[int] = None) -> List[Dict]:
    conn = get_conn()
    if rack_id is not None:
        rows = conn.execute(
            "SELECT e.*, r.name as rack_name FROM infra_equipment e "
            "LEFT JOIN infra_racks r ON e.rack_id = r.id "
            "WHERE e.rack_id = ? ORDER BY e.name",
            (rack_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT e.*, r.name as rack_name FROM infra_equipment e "
            "LEFT JOIN infra_racks r ON e.rack_id = r.id ORDER BY e.name"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_equipment(equipment_id: int) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute(
        "SELECT e.*, r.name as rack_name, r.location as rack_location "
        "FROM infra_equipment e LEFT JOIN infra_racks r ON e.rack_id = r.id "
        "WHERE e.id = ?",
        (equipment_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_equipment(
    name: str,
    type_: str,
    manufacturer: str = "",
    model: str = "",
    rack_id: Optional[int] = None,
    rack_position: str = "",
    notes: str = "",
) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO infra_equipment (name, type, manufacturer, model, rack_id, rack_position, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name.strip(), type_.strip(), manufacturer.strip(), model.strip(), rack_id, rack_position.strip(), notes.strip()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_equipment(
    equipment_id: int,
    name: str,
    type_: str,
    manufacturer: str,
    model: str,
    rack_id: Optional[int],
    rack_position: str,
    notes: str,
) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE infra_equipment SET name=?, type=?, manufacturer=?, model=?, rack_id=?, rack_position=?, notes=? "
        "WHERE id=?",
        (name.strip(), type_.strip(), manufacturer.strip(), model.strip(), rack_id, rack_position.strip(), notes.strip(), equipment_id),
    )
    conn.commit()
    conn.close()


def delete_equipment(equipment_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM infra_equipment WHERE id = ?", (equipment_id,))
    conn.commit()
    conn.close()


# ── Ports ──────────────────────────────────────────────────────────────────────

def list_ports(equipment_id: int) -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM infra_ports WHERE equipment_id = ? ORDER BY port_name",
        (equipment_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_port(port_id: int) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM infra_ports WHERE id = ?", (port_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_port(
    equipment_id: int,
    port_name: str,
    port_type: str = "",
    status: str = "free",
    notes: str = "",
) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO infra_ports (equipment_id, port_name, port_type, status, notes) VALUES (?, ?, ?, ?, ?)",
        (equipment_id, port_name.strip(), port_type.strip(), status.strip(), notes.strip()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_port(port_id: int, port_name: str, port_type: str, status: str, notes: str) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE infra_ports SET port_name=?, port_type=?, status=?, notes=? WHERE id=?",
        (port_name.strip(), port_type.strip(), status.strip(), notes.strip(), port_id),
    )
    conn.commit()
    conn.close()


def delete_port(port_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM infra_ports WHERE id = ?", (port_id,))
    conn.commit()
    conn.close()


# ── Connections ────────────────────────────────────────────────────────────────

def list_connections_for_equipment(equipment_id: int) -> List[Dict]:
    """Returns all connections where either endpoint belongs to the given equipment."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            c.id,
            c.cable_type,
            c.notes,

            sp.id        AS src_port_id,
            sp.port_name AS src_port_name,
            sp.port_type AS src_port_type,
            se.id        AS src_equip_id,
            se.name      AS src_equip_name,

            dp.id        AS dst_port_id,
            dp.port_name AS dst_port_name,
            dp.port_type AS dst_port_type,
            de.id        AS dst_equip_id,
            de.name      AS dst_equip_name

        FROM infra_connections c
        JOIN infra_ports sp ON c.source_port_id = sp.id
        JOIN infra_ports dp ON c.destination_port_id = dp.id
        JOIN infra_equipment se ON sp.equipment_id = se.id
        JOIN infra_equipment de ON dp.equipment_id = de.id
        WHERE se.id = ? OR de.id = ?
        ORDER BY sp.port_name
    """, (equipment_id, equipment_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_all_connections() -> List[Dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            c.id, c.cable_type, c.notes,
            sp.port_name AS src_port_name, se.name AS src_equip_name,
            dp.port_name AS dst_port_name, de.name AS dst_equip_name
        FROM infra_connections c
        JOIN infra_ports sp ON c.source_port_id = sp.id
        JOIN infra_ports dp ON c.destination_port_id = dp.id
        JOIN infra_equipment se ON sp.equipment_id = se.id
        JOIN infra_equipment de ON dp.equipment_id = de.id
        ORDER BY se.name, sp.port_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_connection(
    source_port_id: int,
    destination_port_id: int,
    cable_type: str = "",
    notes: str = "",
) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO infra_connections (source_port_id, destination_port_id, cable_type, notes) VALUES (?, ?, ?, ?)",
        (source_port_id, destination_port_id, cable_type.strip(), notes.strip()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def delete_connection(connection_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM infra_connections WHERE id = ?", (connection_id,))
    conn.commit()
    conn.close()


def list_all_ports_flat() -> List[Dict]:
    """Returns all ports with their equipment name — used to populate connection dropdowns."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT p.id, p.port_name, p.port_type, p.status, e.id as equipment_id, e.name as equipment_name "
        "FROM infra_ports p JOIN infra_equipment e ON p.equipment_id = e.id ORDER BY e.name, p.port_name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
