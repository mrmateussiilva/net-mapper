import pandas as pd
import plotly.express as px
import streamlit as st

from app.config import SHEETS, TEMPLATE, CMAP
from app.data import hascol
from app.ui import rack_diagram_html, patch_panel_html, go_wiki

def render_racks_view(dfs: dict):
    """Renders the physical Racks overview."""
    st.title("🏗️ Racks Físicos — Diagrama U-slot")
    
    deck_sel = st.selectbox("Deck", SHEETS)
    if deck_sel not in dfs:
        st.warning("Deck selecionado não encontrado na base de dados.")
        return
        
    df_rack = dfs[deck_sel]
    if "Rack" not in df_rack.columns:
        st.warning("Informação de Rack indisponível para este deck.")
        return
        
    rack_names = sorted(df_rack["Rack"].dropna().astype(str).unique())
    if not rack_names:
        st.info("Nenhum rack mapeado neste deck.")
        return
        
    rack_sel = st.selectbox("Rack", rack_names)
    rack_df2 = df_rack[df_rack["Rack"].astype(str) == rack_sel]
    
    if not rack_df2.empty and "Active_norm" in rack_df2.columns:
        total_u = len(rack_df2)
        active_u = (rack_df2["Active_norm"] == "Active").sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("U-slots (Portas listadas)", total_u)
        c2.metric("✅ Ativos", active_u)
        c3.metric("📊 Utilização", f"{active_u/max(total_u,1)*100:.0f}%")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown(rack_diagram_html(rack_df2, rack_sel), unsafe_allow_html=True)
            
        with col2:
            vc = rack_df2["Active_norm"].value_counts().reset_index()
            vc.columns = ["S", "N"]
            fig_r = px.pie(vc, names="S", values="N", hole=0.55, color="S", color_discrete_map=CMAP, template=TEMPLATE)
            fig_r.update_layout(height=280, margin=dict(t=10, b=0))
            st.plotly_chart(fig_r, use_container_width=True)
            
            if hascol(rack_df2, "Optic Patch Painel"):
                pp_b = rack_df2.groupby("Optic Patch Painel")["Active_norm"].apply(lambda x: (x == "Active").sum()).reset_index()
                pp_b.columns = ["PP", "Ativas"]
                if not pp_b.empty:
                    fig_pp = px.bar(pp_b, x="Ativas", y="PP", orientation="h", text="Ativas", template=TEMPLATE,
                                  color="Ativas", color_continuous_scale="Greens", height=max(200, len(pp_b) * 24))
                    fig_pp.update_layout(margin=dict(t=5, b=0), yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
                    st.plotly_chart(fig_pp, use_container_width=True)


def render_patch_panels_view(dfs: dict):
    """Renders the standard Patch Panels visualizer view."""
    st.title("🔌 Patch Panels — Visualização de Portas")
    st.caption("Cada círculo = uma porta física · 🟢 ativo · ⚫ vazio · 🟡 desconhecido · 🔴 não doc. · Hover para detalhes")
    
    deck_pp = st.selectbox("Deck", SHEETS, key="pp_deck")
    if deck_pp not in dfs:
        st.warning("Deck selecionado não encontrado.")
        return
        
    df_pp = dfs[deck_pp]
    pp_search = st.text_input("Filtrar patch panel", "")
    
    pp_names = sorted(df_pp["Optic Patch Painel"].dropna().astype(str).unique()) if "Optic Patch Painel" in df_pp.columns else []
    if pp_search: 
        pp_names = [p for p in pp_names if pp_search.lower() in p.lower()]
        
    st.caption(f"{len(pp_names)} patch panels")
    
    for pp_name in pp_names[:30]:
        pp_rows = df_pp[df_pp["Optic Patch Painel"].astype(str) == pp_name]
        try:
            max_port = int(pd.to_numeric(pp_rows["Port"], errors='coerce').max())
            n_ports = min(max(max_port if pp_rows["Port"].notna().any() else 24, 24), 48)
        except Exception:
            n_ports = 24
            
        st.markdown(patch_panel_html(pp_rows, pp_name, n_ports=n_ports), unsafe_allow_html=True)
        
        if st.button(f"📖 Abrir Wiki: {pp_name}", key=f"pp_wiki_{pp_name}"):
            go_wiki("panel", pp_name)
