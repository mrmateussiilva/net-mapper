import pandas as pd
import streamlit as st

from app.config import SHEETS
from app.graphs import global_3d_fig
from app.data import ign

def render_grafo3d(all_df: pd.DataFrame):
    """Renders the 3D topology graph page."""
    st.title("🌐 Topologia 3D da Rede")
    st.caption("Arraste para rotacionar · Scroll para zoom · Hover nos nós para detalhes")
    
    deck_f = st.multiselect("Filtrar Deck", SHEETS, default=SHEETS)
    if "Active_norm" not in all_df.columns:
        st.warning("Dados de status de portal indisponíveis.")
        return
        
    filt = all_df[(all_df["Active_norm"] == "Active") & (all_df["Deck"].isin(deck_f))]
    
    if not filt.empty:
        c1, c2, c3 = st.columns(3)
        sw_ct = len(set(v for v in filt.get("Switch", pd.Series(dtype=str)).dropna().astype(str) if not ign(v))) if "Switch" in filt.columns else 0
        pp_ct = len(set(v for v in filt.get("Optic Patch Painel", pd.Series(dtype=str)).dropna().astype(str) if not ign(v))) if "Optic Patch Painel" in filt.columns else 0
        rk_ct = filt["Rack"].nunique() if "Rack" in filt.columns else 0
        
        c1.metric("🖥️ Switches", sw_ct)
        c2.metric("🔌 Patch Panels", pp_ct)
        c3.metric("📦 Racks", rk_ct)
        
        try:
            fig = global_3d_fig(filt)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar grafo 3D: {e}")
    else:
        st.info("Nenhuma porta ativa encontrada para o(s) deck(s) selecionado(s).")
