# app/views/infra_view.py
# Infrastructure Wiki — CRUD views for Racks, Equipment, Ports, Connections + QR codes.
# Navigation follows the same session-state pattern used by wiki_view.py.

import io
import streamlit as st

from app.infra_db import (
    list_racks, get_rack, create_rack, update_rack, delete_rack,
    list_equipment, get_equipment, create_equipment, update_equipment, delete_equipment,
    list_ports, get_port, create_port, update_port, delete_port,
    list_connections_for_equipment, list_all_connections,
    create_connection, delete_connection,
    list_all_ports_flat,
)
from app.views.import_view import render_import_view

# ── Session-state helpers ─────────────────────────────────────────────────────

DEVICE_TYPES = ["Switch", "Router", "Servidor", "Patch Panel", "Firewall", "UPS", "Outro"]
PORT_TYPES   = ["RJ45", "SFP", "SFP+", "QSFP", "Fibra", "Console", "Outro"]
PORT_STATUSES = ["free", "active", "disabled", "unknown"]
CABLE_TYPES  = ["UTP Cat5e", "UTP Cat6", "UTP Cat6A", "Fibra OM3", "Fibra OM4", "DAC", "Outro"]


def _go_infra(page: str, **kwargs):
    """Navigate to a sub-page inside the infra module."""
    st.session_state["infra_page"] = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def _back_infra():
    """Return to the infra index."""
    st.session_state["infra_page"] = "index"
    st.session_state.pop("infra_equipment_id", None)
    st.rerun()


def _status_badge(status: str) -> str:
    cls = {
        "active":   "b-green",
        "free":     "b-gray",
        "disabled": "b-red",
        "unknown":  "b-yellow",
    }.get(status.lower(), "b-gray")
    return f'<span class="badge {cls}">{status}</span>'


# ── QR Code ───────────────────────────────────────────────────────────────────

def _generate_qr_image(equipment_id: int) -> bytes:
    """Generates a QR code PNG (bytes) pointing to this app with ?equipment_id=<id>."""
    try:
        import qrcode  # type: ignore
        from qrcode.image.styledpil import StyledPilImage  # type: ignore
    except ImportError:
        return b""

    # Build URL from current page URL so it works in any deployment
    try:
        base_url = st.context.url  # Streamlit >= 1.37
    except AttributeError:
        base_url = "http://localhost:8501"

    # Strip existing query params and append ours
    base_url = base_url.split("?")[0]
    url = f"{base_url}?equipment_id={equipment_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Equipment Detail ──────────────────────────────────────────────────────────

def render_equipment_detail(equipment_id: int):
    """Full documentation page for a single piece of equipment."""
    eq = get_equipment(equipment_id)
    if not eq:
        st.error("Equipamento não encontrado.")
        return

    ports = list_ports(equipment_id)
    connections = list_connections_for_equipment(equipment_id)

    # Build a quick-lookup: port_id → connection row (with remote side)
    connected_ports: dict = {}
    for conn in connections:
        if conn["src_equip_id"] == equipment_id:
            connected_ports[conn["src_port_id"]] = {
                "remote_equip": conn["dst_equip_name"],
                "remote_port":  conn["dst_port_name"],
                "cable_type":   conn["cable_type"] or "—",
                "notes":        conn["notes"] or "",
            }
        else:
            connected_ports[conn["dst_port_id"]] = {
                "remote_equip": conn["src_equip_name"],
                "remote_port":  conn["src_port_name"],
                "cable_type":   conn["cable_type"] or "—",
                "notes":        conn["notes"] or "",
            }

    active_count = sum(1 for p in ports if p["status"] == "active")
    total_ports = len(ports)
    pct = active_count / max(total_ports, 1) * 100
    gc = "#10b981" if pct > 70 else "#f59e0b" if pct > 30 else "#ef4444"

    # ── Header card ──
    rack_info = eq.get("rack_name") or "—"
    if eq.get("rack_location"):
        rack_info += f" · {eq['rack_location']}"

    st.markdown(f"""
<div style="border:2px solid {gc};border-radius:16px;padding:1.4rem 1.8rem;margin-bottom:1.2rem;
        display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">
  <div>
    <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">
      ⬡ {eq.get('type','equipamento')}
    </div>
    <div style="font-size:1.8rem;font-weight:800;color:#111827;margin-bottom:8px;">{eq['name']}</div>
    <div>
      <span class="badge b-blue">{eq.get('manufacturer') or '—'}</span>
      <span class="badge b-purple">{eq.get('model') or '—'}</span>
      <span class="badge b-gray">Rack: {rack_info}</span>
      {"<span class='badge b-gray'>Pos: " + eq['rack_position'] + "</span>" if eq.get('rack_position') else ""}
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:3rem;font-weight:900;color:{gc};line-height:1;">{pct:.0f}%</div>
    <div style="font-size:0.7rem;color:#6b7280;">portas ativas</div>
  </div>
</div>""", unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🔌 Total Portas", total_ports)
    k2.metric("✅ Ativas", active_count)
    k3.metric("🔗 Conexões", len(connections))
    k4.metric("⬜ Livres", sum(1 for p in ports if p["status"] == "free"))

    st.divider()

    tab_ports, tab_notes, tab_qr = st.tabs(["📋 Portas & Conexões", "📝 Notas", "📷 QR Code"])

    # ── Tab: Ports & Connections ──
    with tab_ports:
        if not ports:
            st.info("Nenhuma porta cadastrada. Use o gerenciador para adicionar portas.")
        else:
            rows_display = []
            for p in ports:
                remote = connected_ports.get(p["id"])
                rows_display.append({
                    "Porta":         p["port_name"],
                    "Tipo":          p["port_type"] or "—",
                    "Status":        p["status"],
                    "Conectado a":   f"{remote['remote_equip']} · {remote['remote_port']}" if remote else "—",
                    "Cabo":          remote["cable_type"] if remote else "—",
                    "Notas":         p["notes"] or (remote["notes"] if remote else "") or "—",
                })

            import pandas as pd
            pdf = pd.DataFrame(rows_display)

            def _color_status(val):
                m = {"active": "background-color:#d1fae5;color:#065f46",
                     "free":   "background-color:#f3f4f6;color:#6b7280",
                     "disabled":"background-color:#fee2e2;color:#991b1b",
                     "unknown":"background-color:#fef3c7;color:#92400e"}
                return m.get(val, "")

            styled = pdf.style.map(_color_status, subset=["Status"])
            st.dataframe(styled, use_container_width=True, hide_index=True, height=400)

    # ── Tab: Notes ──
    with tab_notes:
        notes_text = eq.get("notes") or ""
        if notes_text:
            st.markdown(notes_text)
        else:
            st.info("Sem notas cadastradas para este equipamento.")

        st.divider()
        col_edit = st.columns([1, 3])[0]
        if col_edit.button("✏️ Editar equipamento", key=f"det_edit_{equipment_id}"):
            _go_infra("edit_equipment", infra_equipment_id=equipment_id)

    # ── Tab: QR Code ──
    with tab_qr:
        try:
            base_url = st.context.url
        except AttributeError:
            base_url = "http://localhost:8501"
        base_url = base_url.split("?")[0]
        url = f"{base_url}?equipment_id={equipment_id}"

        st.markdown(f"**URL de acesso direto:**")
        st.code(url)
        st.caption("Escaneie o QR abaixo para acessar diretamente esta documentação.")

        qr_bytes = _generate_qr_image(equipment_id)
        if qr_bytes:
            st.image(qr_bytes, caption=f"QR · {eq['name']}", width=240)

            st.download_button(
                label="⬇️ Baixar QR Code (PNG)",
                data=qr_bytes,
                file_name=f"qr_{eq['name'].replace(' ', '_')}.png",
                mime="image/png",
                key=f"dl_qr_{equipment_id}",
            )
        else:
            st.warning("Biblioteca `qrcode` não instalada. Execute: `pip install qrcode[pil]`")


# ── Rack Manager ──────────────────────────────────────────────────────────────

def render_rack_manager():
    """CRUD page for racks."""
    st.subheader("🗄️ Gerenciar Racks")

    racks = list_racks()

    # Form to create a new rack
    with st.expander("➕ Adicionar novo rack", expanded=not racks):
        with st.form("form_new_rack", clear_on_submit=True):
            c1, c2 = st.columns(2)
            r_name = c1.text_input("Nome *", placeholder="Rack A")
            r_loc  = c2.text_input("Localização", placeholder="Sala de TI · Andar 3")
            r_notes = st.text_area("Notas", height=80)
            submitted = st.form_submit_button("Salvar rack")
            if submitted:
                if not r_name.strip():
                    st.error("Nome é obrigatório.")
                else:
                    create_rack(r_name, r_loc, r_notes)
                    st.success(f"Rack '{r_name}' criado.")
                    st.rerun()

    # List existing racks
    if not racks:
        st.info("Nenhum rack cadastrado ainda.")
        return

    st.markdown(f"**{len(racks)} rack(s) cadastrado(s)**")
    for rack in racks:
        with st.expander(f"🗄️ {rack['name']}  ·  {rack.get('location') or '—'}", expanded=False):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                with st.form(f"form_edit_rack_{rack['id']}", clear_on_submit=False):
                    ec1, ec2 = st.columns(2)
                    e_name  = ec1.text_input("Nome", value=rack["name"], key=f"rname_{rack['id']}")
                    e_loc   = ec2.text_input("Localização", value=rack.get("location") or "", key=f"rloc_{rack['id']}")
                    e_notes = st.text_area("Notas", value=rack.get("notes") or "", key=f"rnotes_{rack['id']}", height=70)
                    if st.form_submit_button("💾 Salvar alterações"):
                        update_rack(rack["id"], e_name, e_loc, e_notes)
                        st.success("Rack atualizado.")
                        st.rerun()
            with col_b:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if st.button("🗑️ Excluir", key=f"del_rack_{rack['id']}",
                             help="Atenção: equipamentos neste rack não serão excluídos."):
                    delete_rack(rack["id"])
                    st.warning(f"Rack '{rack['name']}' excluído.")
                    st.rerun()

            # Show equipment count in this rack
            equips = list_equipment(rack["id"])
            if equips:
                st.caption(f"{len(equips)} equipamento(s) neste rack: " + ", ".join(e["name"] for e in equips[:8]))


# ── Equipment Manager ─────────────────────────────────────────────────────────

def render_equipment_manager():
    """CRUD page for equipment, with a link to the detail/port management pages."""
    st.subheader("📟 Gerenciar Equipamentos")

    racks = list_racks()
    rack_map = {r["id"]: r["name"] for r in racks}
    rack_options = {r["name"]: r["id"] for r in racks}

    all_equip = list_equipment()

    with st.expander("➕ Adicionar novo equipamento", expanded=not all_equip):
        with st.form("form_new_equip", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            eq_name  = c1.text_input("Nome *", placeholder="SW-CORE-01")
            eq_type  = c2.selectbox("Tipo *", DEVICE_TYPES)
            eq_mfg   = c3.text_input("Fabricante", placeholder="Cisco")

            c4, c5, c6 = st.columns(3)
            eq_model = c4.text_input("Modelo", placeholder="Catalyst 2960")
            eq_rack  = c5.selectbox("Rack", ["— (sem rack)"] + list(rack_options.keys()))
            eq_pos   = c6.text_input("Posição no rack", placeholder="U12")

            eq_notes = st.text_area("Notas", height=70)
            submitted = st.form_submit_button("Salvar equipamento")
            if submitted:
                if not eq_name.strip():
                    st.error("Nome é obrigatório.")
                else:
                    rid = rack_options.get(eq_rack) if eq_rack != "— (sem rack)" else None
                    new_id = create_equipment(eq_name, eq_type, eq_mfg, eq_model, rid, eq_pos, eq_notes)
                    st.success(f"Equipamento '{eq_name}' criado com ID {new_id}.")
                    st.rerun()

    if not all_equip:
        st.info("Nenhum equipamento cadastrado ainda.")
        return

    # Search / filter
    search = st.text_input("🔍 Filtrar equipamentos...", placeholder="nome, tipo, fabricante...")
    filtered = [e for e in all_equip if not search or search.lower() in (
        e["name"] + e.get("type","") + (e.get("manufacturer") or "") + (rack_map.get(e["rack_id"]) or "")
    ).lower()]

    st.caption(f"{len(filtered)} equipamento(s)")

    for eq in filtered:
        rack_label = rack_map.get(eq["rack_id"], "—") if eq.get("rack_id") else "—"
        port_count = len(list_ports(eq["id"]))

        col_h, col_btn = st.columns([7, 1])
        col_h.markdown(
            f'<span class="badge b-blue">{eq["type"]}</span> '
            f'<strong>{eq["name"]}</strong> &nbsp; <span style="color:#6b7280;font-size:0.8rem;">'
            f'Rack: {rack_label} · {port_count} porta(s)</span>',
            unsafe_allow_html=True,
        )
        if col_btn.button("📄 Ficha", key=f"btn_det_{eq['id']}", help="Ver documentação completa"):
            _go_infra("equipment_detail", infra_equipment_id=eq["id"])

        with st.expander(f"✏️ Editar · {eq['name']}", expanded=False):
            ed1, ed2, ed3 = st.columns(3)
            with st.form(f"form_edit_eq_{eq['id']}"):
                fe1, fe2, fe3 = st.columns(3)
                fe_name  = fe1.text_input("Nome", value=eq["name"], key=f"ename_{eq['id']}")
                fe_type  = fe2.selectbox("Tipo", DEVICE_TYPES,
                                         index=DEVICE_TYPES.index(eq["type"]) if eq["type"] in DEVICE_TYPES else 0,
                                         key=f"etype_{eq['id']}")
                fe_mfg   = fe3.text_input("Fabricante", value=eq.get("manufacturer") or "", key=f"emfg_{eq['id']}")

                fe4, fe5, fe6 = st.columns(3)
                fe_model = fe4.text_input("Modelo", value=eq.get("model") or "", key=f"emodel_{eq['id']}")
                rack_idx = 0
                rack_names_list = ["— (sem rack)"] + list(rack_options.keys())
                if eq.get("rack_id") and eq["rack_id"] in rack_map:
                    try:
                        rack_idx = rack_names_list.index(rack_map[eq["rack_id"]])
                    except ValueError:
                        rack_idx = 0
                fe_rack  = fe5.selectbox("Rack", rack_names_list, index=rack_idx, key=f"erack_{eq['id']}")
                fe_pos   = fe6.text_input("Posição", value=eq.get("rack_position") or "", key=f"epos_{eq['id']}")
                fe_notes = st.text_area("Notas", value=eq.get("notes") or "", key=f"enotes_{eq['id']}", height=70)

                col_save, col_del = st.columns([3, 1])
                if col_save.form_submit_button("💾 Salvar"):
                    rid2 = rack_options.get(fe_rack) if fe_rack != "— (sem rack)" else None
                    update_equipment(eq["id"], fe_name, fe_type, fe_mfg, fe_model, rid2, fe_pos, fe_notes)
                    st.success("Atualizado.")
                    st.rerun()
                if col_del.form_submit_button("🗑️ Excluir", help="Exclui também todas as portas e conexões."):
                    delete_equipment(eq["id"])
                    st.warning(f"'{eq['name']}' excluído.")
                    st.rerun()


# ── Port Manager ──────────────────────────────────────────────────────────────

def render_port_manager():
    """CRUD page for ports. User selects an equipment first, then manages its ports."""
    st.subheader("🔌 Gerenciar Portas")

    all_equip = list_equipment()
    if not all_equip:
        st.info("Cadastre equipamentos antes de gerenciar portas.")
        return

    eq_options = {f"{e['name']} ({e.get('type','')})": e["id"] for e in all_equip}
    selected_label = st.selectbox("Selecionar equipamento:", list(eq_options.keys()))
    eq_id = eq_options[selected_label]
    eq = get_equipment(eq_id)

    ports = list_ports(eq_id)

    st.markdown(f"**{len(ports)} porta(s)** cadastrada(s) em **{eq['name']}**")

    # Bulk-add shortcut
    with st.expander("➕ Adicionar porta(s)"):
        with st.form("form_add_ports", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            p_name   = c1.text_input("Nome da porta *", placeholder="Gi0/1")
            p_type   = c2.selectbox("Tipo", PORT_TYPES)
            p_status = c3.selectbox("Status", PORT_STATUSES)
            p_notes  = st.text_input("Notas", placeholder="uplink, firewall...")

            # Optional: bulk range
            st.markdown("**Ou adicionar em lote:**")
            bc1, bc2, bc3 = st.columns(3)
            prefix = bc1.text_input("Prefixo", placeholder="Gi0/", key="bulk_prefix")
            start  = bc2.number_input("De", min_value=0, value=1, step=1, key="bulk_start")
            end    = bc3.number_input("Até", min_value=0, value=24, step=1, key="bulk_end")

            submitted = st.form_submit_button("Adicionar")
            if submitted:
                if prefix.strip() and end >= start:
                    for i in range(int(start), int(end) + 1):
                        create_port(eq_id, f"{prefix.strip()}{i}", p_type, p_status, p_notes)
                    st.success(f"{int(end) - int(start) + 1} porta(s) adicionada(s).")
                    st.rerun()
                elif p_name.strip():
                    create_port(eq_id, p_name.strip(), p_type, p_status, p_notes)
                    st.success(f"Porta '{p_name}' adicionada.")
                    st.rerun()
                else:
                    st.error("Informe o nome da porta ou preencha campos de lote.")

    if not ports:
        return

    # Show port table with inline status edit
    import pandas as pd
    pdf = pd.DataFrame(ports)[["id", "port_name", "port_type", "status", "notes"]]
    pdf.columns = ["ID", "Porta", "Tipo", "Status", "Notas"]
    st.dataframe(pdf, use_container_width=True, hide_index=True, height=300)

    # Delete a port
    with st.expander("🗑️ Excluir porta"):
        port_del_options = {f"{p['port_name']} ({p['status']})": p["id"] for p in ports}
        del_sel = st.selectbox("Porta a excluir:", list(port_del_options.keys()), key="del_port_sel")
        if st.button("Confirmar exclusão", key="confirm_del_port"):
            delete_port(port_del_options[del_sel])
            st.warning(f"Porta '{del_sel}' excluída.")
            st.rerun()


# ── Connection Manager ────────────────────────────────────────────────────────

def render_connection_manager():
    """CRUD page for port-to-port connections."""
    st.subheader("🔗 Gerenciar Conexões")

    all_ports = list_all_ports_flat()
    if len(all_ports) < 2:
        st.info("Cadastre pelo menos 2 portas em equipamentos diferentes para criar conexões.")
        return

    port_options = {f"{p['equipment_name']} · {p['port_name']} ({p['port_type'] or 'N/A'})": p["id"] for p in all_ports}
    port_labels = list(port_options.keys())

    with st.expander("➕ Nova conexão", expanded=True):
        with st.form("form_new_conn", clear_on_submit=True):
            c1, c2 = st.columns(2)
            src_label = c1.selectbox("Origem (porta):", port_labels, key="conn_src")
            dst_label = c2.selectbox("Destino (porta):", port_labels, key="conn_dst")

            c3, c4 = st.columns(2)
            cable    = c3.selectbox("Tipo de cabo:", ["—"] + CABLE_TYPES)
            c_notes  = c4.text_input("Notas", placeholder="uplink, VLAN 100...")

            submitted = st.form_submit_button("Criar conexão")
            if submitted:
                src_id = port_options[src_label]
                dst_id = port_options[dst_label]
                if src_id == dst_id:
                    st.error("Origem e destino não podem ser a mesma porta.")
                else:
                    create_connection(src_id, dst_id, cable if cable != "—" else "", c_notes)
                    st.success("Conexão criada.")
                    st.rerun()

    # List existing connections
    all_conns = list_all_connections()
    if not all_conns:
        st.info("Nenhuma conexão cadastrada ainda.")
        return

    st.markdown(f"**{len(all_conns)} conexão(ões) cadastrada(s)**")

    import pandas as pd
    conn_rows = []
    for c in all_conns:
        conn_rows.append({
            "ID":       c["id"],
            "Origem":   f"{c['src_equip_name']} · {c['src_port_name']}",
            "Destino":  f"{c['dst_equip_name']} · {c['dst_port_name']}",
            "Cabo":     c["cable_type"] or "—",
            "Notas":    c["notes"] or "—",
        })
    cdf = pd.DataFrame(conn_rows)
    st.dataframe(cdf, use_container_width=True, hide_index=True, height=320)

    with st.expander("🗑️ Excluir conexão"):
        del_conn_options = {f"#{c['ID']}  {c['Origem']} → {c['Destino']}": c["ID"] for c in conn_rows}
        del_conn_sel = st.selectbox("Selecionar:", list(del_conn_options.keys()), key="del_conn_sel")
        if st.button("Confirmar exclusão", key="confirm_del_conn"):
            delete_connection(del_conn_options[del_conn_sel])
            st.warning("Conexão excluída.")
            st.rerun()


# ── Infra Index ───────────────────────────────────────────────────────────────

def render_infra_index():
    """Overview page: stats summary + equipment cards grid."""
    st.title("🏭 Infraestrutura — Wiki de Equipamentos")
    st.caption("Documentação viva de racks, equipamentos, portas e conexões.")

    racks  = list_racks()
    equips = list_equipment()
    all_ports = list_all_ports_flat()
    all_conns = list_all_connections()

    # KPI row
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🗄️ Racks", len(racks))
    k2.metric("📟 Equipamentos", len(equips))
    k3.metric("🔌 Portas", len(all_ports))
    k4.metric("🔗 Conexões", len(all_conns))

    if not equips:
        st.divider()
        st.info("Nenhum equipamento cadastrado. Use os gerenciadores na barra lateral para começar.")
        return

    st.divider()

    # Search
    search = st.text_input("🔍 Buscar equipamento...", placeholder="nome, tipo, rack, fabricante...")

    filtered = [
        e for e in equips
        if not search or search.lower() in (
            e["name"] + e.get("type","") + (e.get("manufacturer") or "") + (e.get("rack_name") or "")
        ).lower()
    ]

    st.caption(f"{len(filtered)} equipamento(s)")

    cols_n = 3
    for i in range(0, len(filtered), cols_n):
        cols = st.columns(cols_n)
        for j, col in enumerate(cols):
            if i + j >= len(filtered):
                break
            eq = filtered[i + j]
            ports = list_ports(eq["id"])
            active_p = sum(1 for p in ports if p["status"] == "active")
            total_p  = len(ports)
            conn_p   = len(list_connections_for_equipment(eq["id"]))
            pct2 = active_p / max(total_p, 1) * 100
            gc2  = "#10b981" if pct2 > 70 else "#f59e0b" if pct2 > 30 else "#ef4444" if total_p > 0 else "#9ca3af"

            with col:
                st.markdown(f"""
<div class="wiki-card" style="border-left:4px solid {gc2};">
  <div style="font-size:0.68rem;color:#9ca3af;text-transform:uppercase;margin-bottom:4px;">
    📟 {eq.get('type', 'Equipamento')}
  </div>
  <div style="font-weight:700;font-size:0.95rem;color:#111827;margin-bottom:6px;word-break:break-all;">
    {eq['name']}
  </div>
  <div style="font-size:0.78rem;color:#6b7280;margin-bottom:8px;">
    {eq.get('manufacturer') or ''} {eq.get('model') or ''}<br>
    Rack: {eq.get('rack_name') or '—'} {('· ' + eq['rack_position']) if eq.get('rack_position') else ''}
  </div>
  <div class="stat-row">
    <div class="stat-pill"><strong style="color:{gc2};">{active_p}</strong><span>ativas</span></div>
    <div class="stat-pill"><strong style="color:#6b7280;">{total_p}</strong><span>portas</span></div>
    <div class="stat-pill"><strong style="color:#3b82f6;">{conn_p}</strong><span>conexões</span></div>
  </div>
</div>""", unsafe_allow_html=True)
                if st.button("Ver ficha →", key=f"idx_det_{eq['id']}_{i}_{j}"):
                    _go_infra("equipment_detail", infra_equipment_id=eq["id"])


# ── Main Router ───────────────────────────────────────────────────────────────

def render_infra():
    """Top-level router for the Infraestrutura module."""

    # Check for QR deep-link: ?equipment_id=<id>
    params = st.query_params
    if "equipment_id" in params and st.session_state.get("infra_page") in (None, "index"):
        try:
            eid = int(params["equipment_id"])
            st.session_state["infra_page"] = "equipment_detail"
            st.session_state["infra_equipment_id"] = eid
            # Clear param so refresh doesn't keep redirecting
            st.query_params.clear()
        except (ValueError, TypeError):
            pass

    page = st.session_state.get("infra_page", "index")

    # Sub-nav in sidebar for the infra section
    with st.sidebar:
        st.divider()
        st.markdown("**📂 Infraestrutura**")
        sub = st.radio(
            "Gerenciadores",
            ["📋 Visão Geral", "🗄️ Racks", "📟 Equipamentos", "🔌 Portas", "🔗 Conexões", "📥 Importar"],
            key="infra_sub_nav",
            label_visibility="collapsed",
        )

    # If user clicks a sub-nav item, override the drill-down page
    if sub == "📋 Visão Geral" and page not in ("equipment_detail", "edit_equipment"):
        page = "index"
    elif sub == "🗄️ Racks":
        page = "racks"
    elif sub == "📟 Equipamentos" and page not in ("equipment_detail", "edit_equipment"):
        page = "equipment"
    elif sub == "🔌 Portas":
        page = "ports"
    elif sub == "🔗 Conexões":
        page = "connections"
    elif sub == "📥 Importar":
        page = "import"

    # Back button for detail pages
    if page in ("equipment_detail", "edit_equipment"):
        col_back, col_bc = st.columns([1, 10])
        if col_back.button("← Voltar", key="infra_back"):
            st.session_state["infra_page"] = "index"
            st.session_state.pop("infra_equipment_id", None)
            st.rerun()

        eq_id = st.session_state.get("infra_equipment_id")
        eq    = get_equipment(eq_id) if eq_id else None
        label = eq["name"] if eq else str(eq_id)
        col_bc.markdown(
            f'<div class="breadcrumb">🏭 Infraestrutura / 📟 Equipamento / <span>{label}</span></div>',
            unsafe_allow_html=True,
        )
        st.divider()

    # Route
    if page == "index":
        render_infra_index()
    elif page == "racks":
        render_rack_manager()
    elif page == "equipment":
        render_equipment_manager()
    elif page == "ports":
        render_port_manager()
    elif page == "connections":
        render_connection_manager()
    elif page == "import":
        render_import_view()
    elif page == "equipment_detail":
        eq_id = st.session_state.get("infra_equipment_id")
        if eq_id:
            render_equipment_detail(eq_id)
        else:
            st.error("Nenhum equipamento selecionado.")
            _back_infra()
    else:
        render_infra_index()
