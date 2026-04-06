import pandas as pd
import plotly.express as px
import streamlit as st

from app.data import detect_errors, safe, ign
from app.graphs import build_switch_graph, switch_radial_fig
from app.ui import go_wiki, style_status, patch_panel_html, rack_diagram_html
from app.config import TEMPLATE, CMAP

def render_wiki_switch(sw_name: str, all_df: pd.DataFrame):
    """Renders the detailed wiki page for a specific Switch."""
    grp = all_df[all_df["Switch"].astype(str).str.strip() == sw_name] if "Switch" in all_df.columns else pd.DataFrame()
    if grp.empty: 
        st.warning(f"Switch '{sw_name}' não encontrado.")
        return

    total_p = len(grp)
    active_p = (grp["Active_norm"] == "Active").sum()
    inactive_p = (grp["Active_norm"] == "Inactive/Empty").sum()
    unknown_p = (grp["Active_norm"] == "Unknown").sum()
    undoc_p = (grp["Active_norm"] == "Not Documented").sum()
    pct = active_p / max(total_p, 1) * 100
    
    decks = sorted(grp["Deck"].unique().tolist())
    racks = sorted(grp["Rack"].dropna().astype(str).unique().tolist())
    panels = sorted(grp["Optic Patch Painel"].dropna().astype(str).unique().tolist()) if "Optic Patch Painel" in grp.columns else []
    wps = sorted([w for w in grp["Wall Port"].dropna().astype(str).unique() if not ign(w)]) if "Wall Port" in grp.columns else []
    obs_vals = [o for o in grp["Observation"].dropna().astype(str).unique() if not ign(o) and o != "Observation"] if "Observation" in grp.columns else []
    
    errs = detect_errors(grp.copy(), sw_name)
    err_count = sum(len(e) for e in errs)
    gc = "#10b981" if pct > 70 else "#f59e0b" if pct > 30 else "#ef4444"

    # Header
    st.markdown(f"""
<div style="border:2px solid {gc};border-radius:16px;padding:1.4rem 1.8rem;margin-bottom:1.2rem;
            display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">
  <div>
    <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">⬡ switch</div>
    <div style="font-size:1.8rem;font-weight:800;color:#111827;margin-bottom:8px;">{sw_name}</div>
    <div>{"".join(f'<span class="badge b-purple">{d.replace("Deck ","").replace(" - ","·")}</span>' for d in decks)}
         {"".join(f'<span class="badge b-blue">{r}</span>' for r in racks[:5])}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:3rem;font-weight:900;color:{gc};line-height:1;">{pct:.0f}%</div>
    <div style="font-size:0.7rem;color:#6b7280;">utilização</div>
  </div>
</div>""", unsafe_allow_html=True)

    # KPIs
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("🔌 Total Portas", total_p)
    k2.metric("✅ Ativas", active_p)
    k3.metric("⬜ Inativas", inactive_p)
    k4.metric("❓ Desconhecidas", unknown_p)
    k5.metric("📋 Não Doc.", undoc_p)
    k6.metric("🚨 Erros", err_count)

    st.divider()
    wt1, wt2, wt3, wt4 = st.tabs(["📊 Visão Geral", "🔗 Grafo de Conexões", "🔌 Patch Panels", "📋 Todas as Portas"])

    with wt1:
        c1, c2 = st.columns([1, 2])
        with c1:
            vc = grp["Active_norm"].value_counts().reset_index()
            vc.columns = ["Status", "N"]
            fig_p = px.pie(vc, names="Status", values="N", hole=0.58, color="Status",
                           color_discrete_map=CMAP, template=TEMPLATE)
            fig_p.update_layout(height=260, margin=dict(t=10, b=0, l=0, r=0),
                                legend=dict(font=dict(size=10)))
            st.plotly_chart(fig_p, use_container_width=True)
            
        with c2:
            if panels:
                pp_ct = grp.groupby("Optic Patch Painel")["Active_norm"].apply(lambda x: (x == "Active").sum()).reset_index()
                pp_ct.columns = ["PP", "Ativas"]
                fig_pp = px.bar(pp_ct.sort_values("Ativas"), x="Ativas", y="PP", orientation="h",
                                text="Ativas", template=TEMPLATE, color="Ativas", color_continuous_scale="Greens",
                                height=max(220, len(pp_ct) * 30))
                fig_pp.update_layout(margin=dict(t=5, b=0), yaxis_title="", coloraxis_showscale=False)
                st.plotly_chart(fig_pp, use_container_width=True)

        st.markdown("#### 📋 Informações da Entidade")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"""
**Decks:** {", ".join(decks) or "—"}
**Racks:** {", ".join(racks[:6]) or "—"}""")
        m2.markdown(f"""
**Patch Panels ({len(panels)}):**
{chr(10).join(f"- {p}" for p in panels[:8]) or "—"}""")
        m3.markdown(f"""
**Wall Ports ({len(wps)}):**
{chr(10).join(f"- {w}" for w in wps[:8]) or "—"}""")

        if obs_vals:
            st.markdown(f"**Observações:** {', '.join(obs_vals[:6])}")
        if err_count > 0:
            st.warning(f"⚠️ {err_count} problemas detectados neste switch. Verifique a aba de erros.")

    with wt2:
        G_sw = build_switch_graph(sw_name, grp)
        sw_id = f"SW:{sw_name}"
        if len(G_sw.nodes) > 1:
            st.plotly_chart(switch_radial_fig(G_sw, sw_id, sw_name), use_container_width=True)
        st.markdown("#### 📋 Tabela de Conexões")
        dcols = [c for c in ["Rack", "Optic Patch Painel", "Port", "Wall Port", "Switch Port", "Active_norm", "Observation"] if c in grp.columns]
        conn_df = grp[dcols].rename(columns={"Active_norm": "Status"})
        sort_cold = "Port" if "Port" in dcols else dcols[0]
        st.dataframe(style_status(conn_df.sort_values(sort_cold)), use_container_width=True, hide_index=True, height=320)

    with wt3:
        if not panels:
            st.info("Nenhum patch panel mapeado para este switch.")
        for pp_name in panels[:20]:
            pp_rows = grp[grp["Optic Patch Painel"].astype(str) == pp_name] if "Optic Patch Painel" in grp.columns else pd.DataFrame()
            n_ports = min(max(int(pd.to_numeric(pp_rows["Port"], errors='coerce').max()) if not pp_rows.empty and pp_rows["Port"].notna().any() else 24, 24), 48)
            st.markdown(patch_panel_html(pp_rows, pp_name, n_ports), unsafe_allow_html=True)
            if st.button(f"📖 Abrir Wiki: {pp_name}", key=f"wiki_sw_pp_{pp_name}_{sw_name}"):
                go_wiki("panel", pp_name)

    with wt4:
        st.markdown(f"#### Todas as {total_p} portas do switch")
        port_cols = [c for c in ["Switch Port", "Rack", "Optic Patch Painel", "Port", "Wall Port", "Active_norm", "Observation"] if c in grp.columns]
        port_df = grp[port_cols].rename(columns={"Active_norm": "Status"})
        sort_col = "Switch Port" if "Switch Port" in port_df.columns else "Port" if "Port" in port_df.columns else port_df.columns[0]
        st.dataframe(style_status(port_df.sort_values(sort_col)), use_container_width=True, hide_index=True, height=500)


def render_wiki_panel(pp_name: str, all_df: pd.DataFrame):
    """Renders the detailed wiki page for a specific Patch Panel."""
    grp = all_df[all_df["Optic Patch Painel"].astype(str).str.strip() == pp_name] if "Optic Patch Painel" in all_df.columns else pd.DataFrame()
    if grp.empty: 
        st.warning(f"Patch Panel '{pp_name}' não encontrado.")
        return
        
    total_p = len(grp)
    active_p = (grp["Active_norm"] == "Active").sum()
    pct = active_p / max(total_p, 1) * 100
    gc = "#10b981" if pct > 70 else "#f59e0b" if pct > 30 else "#ef4444"
    
    decks = sorted(grp["Deck"].unique().tolist())
    racks = sorted(grp["Rack"].dropna().astype(str).unique().tolist())
    switches = sorted([s for s in grp["Switch"].dropna().astype(str).unique() if not ign(s)]) if "Switch" in grp.columns else []
    n_ports = min(max(int(pd.to_numeric(grp["Port"], errors='coerce').max()) if grp["Port"].notna().any() else 24, 24), 48)

    st.markdown(f"""
<div style="border:2px solid {gc};border-radius:16px;padding:1.4rem 1.8rem;margin-bottom:1.2rem;
            display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">
  <div>
    <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;margin-bottom:4px;">⬡ patch panel</div>
    <div style="font-size:1.8rem;font-weight:800;color:#111827;margin-bottom:8px;">{pp_name}</div>
    <div>{"".join(f'<span class="badge b-purple">{d.replace("Deck ","").replace(" - ","·")}</span>' for d in decks)}
         {"".join(f'<span class="badge b-blue">{r}</span>' for r in racks[:4])}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:3rem;font-weight:900;color:{gc};line-height:1;">{pct:.0f}%</div>
    <div style="font-size:0.7rem;color:#6b7280;">utilização</div>
  </div>
</div>""", unsafe_allow_html=True)

    k1, k2, k3 = st.columns(3)
    k1.metric("🔢 Portas Mapeadas", total_p)
    k2.metric("✅ Ativas", active_p)
    k3.metric("🖥️ Switches", len(switches))
    st.divider()

    pt1, pt2 = st.tabs(["🔌 Painel LED", "📋 Tabela de Portas"])
    with pt1:
        st.markdown(patch_panel_html(grp, pp_name, n_ports), unsafe_allow_html=True)
        if switches:
            st.markdown("#### 🖥️ Switches conectados a este painel")
            for s in switches[:15]:
                sg = grp[grp["Switch"].astype(str).str.strip() == s] if "Switch" in grp.columns else pd.DataFrame()
                ac = int((sg["Active_norm"] == "Active").sum())
                tot2 = len(sg)
                bc = "b-green" if ac / max(tot2, 1) > 0.5 else "b-yellow"
                
                col_a, col_b = st.columns([5, 1])
                col_a.markdown(f'<span class="badge {bc}">{s}</span> <span style="font-size:0.78rem;color:#6b7280;">{ac}/{tot2} portas ativas</span>', unsafe_allow_html=True)
                if col_b.button("📖", key=f"wiki_pp_sw_{s}_{pp_name}", help=f"Abrir Wiki de {s}"):
                    go_wiki("switch", s)
                    
    with pt2:
        port_cols2 = [c for c in ["Port", "Switch", "Switch Port", "Wall Port", "Active_norm", "Observation"] if c in grp.columns]
        pdf2 = grp[port_cols2].rename(columns={"Active_norm": "Status"}).sort_values("Port")
        st.dataframe(style_status(pdf2), use_container_width=True, hide_index=True, height=420)


def render_wiki_rack(rack_name: str, all_df: pd.DataFrame):
    """Renders the detailed wiki page for a specific Rack."""
    grp = all_df[all_df["Rack"].astype(str).str.strip() == rack_name]
    if grp.empty: 
        st.warning(f"Rack '{rack_name}' não encontrado.")
        return
        
    total_p = len(grp)
    active_p = (grp["Active_norm"] == "Active").sum()
    pct = active_p / max(total_p, 1) * 100
    gc = "#10b981" if pct > 70 else "#f59e0b" if pct > 30 else "#ef4444"
    
    decks = sorted(grp["Deck"].unique().tolist())
    panels = sorted(grp["Optic Patch Painel"].dropna().astype(str).unique().tolist()) if "Optic Patch Painel" in grp.columns else []
    switches = sorted([s for s in grp["Switch"].dropna().astype(str).unique() if not ign(s)]) if "Switch" in grp.columns else []

    st.markdown(f"""
<div style="border:2px solid {gc};border-radius:16px;padding:1.4rem 1.8rem;margin-bottom:1.2rem;
            display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">
  <div>
    <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;margin-bottom:4px;">⬡ rack</div>
    <div style="font-size:1.8rem;font-weight:800;color:#111827;margin-bottom:8px;">{rack_name}</div>
    <div>{"".join(f'<span class="badge b-purple">{d.replace("Deck ","").replace(" - ","·")}</span>' for d in decks)}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:3rem;font-weight:900;color:{gc};line-height:1;">{pct:.0f}%</div>
    <div style="font-size:0.7rem;color:#6b7280;">utilização</div>
  </div>
</div>""", unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🔌 Portas", total_p)
    k2.metric("✅ Ativas", active_p)
    k3.metric("📦 Patch Panels", len(panels))
    k4.metric("🖥️ Switches", len(switches))
    st.divider()

    rt1, rt2 = st.tabs(["🏗️ Diagrama", "🔗 Entidades Conectadas"])
    with rt1:
        st.markdown(rack_diagram_html(grp, rack_name), unsafe_allow_html=True)
    with rt2:
        c1r, c2r = st.columns(2)
        with c1r:
            st.markdown("#### 🔌 Patch Panels")
            for pp in panels[:30]:
                pp_grp = grp[grp["Optic Patch Painel"].astype(str) == pp] if "Optic Patch Painel" in grp.columns else pd.DataFrame()
                ac = int((pp_grp["Active_norm"] == "Active").sum())
                tot2 = len(pp_grp)
                pct2 = ac / max(tot2, 1)
                bc = "b-green" if pct2 > 0.5 else "b-yellow" if pct2 > 0.2 else "b-red"
                
                col_a, col_b = st.columns([5, 1])
                col_a.markdown(f'<span class="badge {bc}">{pp}</span> <span style="font-size:0.78rem;color:#6b7280;">{ac}/{tot2} ativas ({pct2*100:.0f}%)</span>', unsafe_allow_html=True)
                if col_b.button("📖", key=f"wiki_rk_pp_{pp}_{rack_name}", help=f"Wiki: {pp}"):
                    go_wiki("panel", pp)
                    
        with c2r:
            st.markdown("#### 🖥️ Switches")
            for sw in switches[:30]:
                sw_grp = grp[grp["Switch"].astype(str).str.strip() == sw] if "Switch" in grp.columns else pd.DataFrame()
                ac = int((sw_grp["Active_norm"] == "Active").sum())
                tot2 = len(sw_grp)
                pct2 = ac / max(tot2, 1)
                bc = "b-green" if pct2 > 0.5 else "b-yellow" if pct2 > 0.2 else "b-red"
                
                col_a, col_b = st.columns([5, 1])
                col_a.markdown(f'<span class="badge {bc}">{sw}</span> <span style="font-size:0.78rem;color:#6b7280;">{ac}/{tot2} ativas ({pct2*100:.0f}%)</span>', unsafe_allow_html=True)
                if col_b.button("📖", key=f"wiki_rk_sw_{sw}_{rack_name}", help=f"Wiki: {sw}"):
                    go_wiki("switch", sw)


def render_wiki_index(all_df: pd.DataFrame):
    """Renders the main Wiki index page with search and grid."""
    st.title("📖 Wiki — Entidades da Rede")
    st.caption("Clique em qualquer entidade para ver sua ficha completa com portas, conexões e grafo.")

    wiki_q = st.text_input("🔍 Buscar entidade...", "", placeholder="ex: SW01, 423RQ005, PP03...")

    def entity_grid(entity_type, names, get_group_fn, badge_class, icon):
        filt = [n for n in names if wiki_q.lower() in n.lower()] if wiki_q else names
        st.caption(f"{len(filt)} entidades")
        cols_n = 3
        for i in range(0, min(len(filt), 90), cols_n):
            cols = st.columns(cols_n)
            for j, col in enumerate(cols):
                if i + j >= len(filt): break
                name = filt[i + j]
                grp2 = get_group_fn(name)
                ac2 = int((grp2["Active_norm"] == "Active").sum())
                tot2 = len(grp2)
                ina2 = int((grp2["Active_norm"] == "Inactive/Empty").sum())
                unk2 = int((grp2["Active_norm"] == "Unknown").sum())
                pct2 = ac2 / max(tot2, 1) * 100
                gc2 = "#10b981" if pct2 > 70 else "#f59e0b" if pct2 > 30 else "#ef4444"
                
                with col:
                    st.markdown(f"""
<div class="wiki-card" style="border-left:4px solid {gc2};">
  <div style="font-size:0.68rem;color:#9ca3af;text-transform:uppercase;margin-bottom:4px;">{icon} {entity_type}</div>
  <div style="font-weight:700;font-size:0.95rem;color:#111827;margin-bottom:8px;word-break:break-all;">{name}</div>
  <div class="stat-row">
    <div class="stat-pill"><strong style="color:{gc2};">{ac2}</strong><span>ativas</span></div>
    <div class="stat-pill"><strong style="color:#6b7280;">{ina2}</strong><span>inativas</span></div>
    <div class="stat-pill"><strong style="color:#f59e0b;">{unk2}</strong><span>desc.</span></div>
    <div class="stat-pill"><strong style="color:{gc2};">{pct2:.0f}%</strong><span>uso</span></div>
  </div>
</div>""", unsafe_allow_html=True)
                    if st.button("Abrir ficha →", key=f"wiki_grid_{entity_type}_{name}_{i}_{j}"):
                        go_wiki(entity_type, name)

    tabs_w = st.tabs(["🖥️ Switches", "📦 Racks", "🔌 Patch Panels"])

    with tabs_w[0]:
        if "Switch" in all_df.columns:
            sw_names_all = sorted([s for s in all_df["Switch"].dropna().astype(str).unique() if not ign(s)])
            entity_grid("switch", sw_names_all, lambda n: all_df[all_df["Switch"].astype(str).str.strip() == n], "b-green", "🖥️")

    with tabs_w[1]:
        rack_names_all = sorted(all_df["Rack"].dropna().astype(str).unique().tolist())
        entity_grid("rack", rack_names_all, lambda n: all_df[all_df["Rack"].astype(str).str.strip() == n], "b-purple", "📦")

    with tabs_w[2]:
        if "Optic Patch Painel" in all_df.columns:
            pp_names_all = sorted(all_df["Optic Patch Painel"].dropna().astype(str).unique().tolist())
            entity_grid("panel", pp_names_all, lambda n: all_df[all_df["Optic Patch Painel"].astype(str).str.strip() == n], "b-blue", "🔌")


def render_wiki(all_df: pd.DataFrame):
    """Main Wiki router."""
    if st.session_state.get("wiki_type"):
        col_back, col_bc = st.columns([1, 10])
        if col_back.button("← Voltar"):
            st.session_state.wiki_type = None
            st.session_state.wiki_name = None
            st.rerun()
            
        type_label = {"switch": "Switch", "panel": "Patch Panel", "rack": "Rack"}.get(st.session_state.wiki_type, "")
        col_bc.markdown(f'<div class="breadcrumb">📖 Wiki / {type_label} / <span>{st.session_state.wiki_name}</span></div>', unsafe_allow_html=True)
        st.divider()
        
        if st.session_state.wiki_type == "switch":
            render_wiki_switch(st.session_state.wiki_name, all_df)
        elif st.session_state.wiki_type == "panel":
            render_wiki_panel(st.session_state.wiki_name, all_df)
        elif st.session_state.wiki_type == "rack":
            render_wiki_rack(st.session_state.wiki_name, all_df)
    else:
        render_wiki_index(all_df)
