import pandas as pd
import streamlit as st

from app.data import ign
from app.ui import go_wiki, style_status

def render_spotlight_view(all_df: pd.DataFrame):
    """Renders the global search spotlight."""
    st.title("🔍 Spotlight — Busca Universal")
    st.caption("Busque qualquer coisa: nome de switch, rack, patch panel, wall port, observação...")
    
    query = st.text_input("Buscar...", placeholder="ex: SW01, 423RQ005, FIREWALL, CCTV...", label_visibility="collapsed")
    
    if query:
        q = query.lower()
        mask = all_df.astype(str).apply(lambda col: col.str.lower().str.contains(q, na=False)).any(axis=1)
        results = all_df[mask].drop_duplicates().head(40)
        
        st.caption(f"{len(results)} resultados")
        if results.empty:
            st.info("Nenhum resultado encontrado.")
        else:
            show_cols = [c for c in ["Deck", "Rack", "Optic Patch Painel", "Port", "Wall Port", "Switch", "Switch Port", "Active_norm", "Observation"] if c in results.columns]
            ren = results[show_cols].rename(columns={"Active_norm": "Status"})
            st.dataframe(style_status(ren), use_container_width=True, hide_index=True, height=500)
            
            # Quick wiki links
            st.divider()
            st.markdown("**Ir direto para a ficha:**")
            
            if "Switch" in results.columns:
                sws = sorted(set(s for s in results["Switch"].dropna().astype(str) if not ign(s) and q in s.lower()))
                for s in sws[:5]:
                    if st.button(f"📖 Switch: {s}", key=f"spot_sw_{s}"):
                        go_wiki("switch", s)
                        
            if "Optic Patch Painel" in results.columns:
                pps = sorted(set(p for p in results["Optic Patch Painel"].dropna().astype(str) if not ign(p) and q in p.lower()))
                for p in pps[:5]:
                    if st.button(f"📖 Patch Panel: {p}", key=f"spot_pp_{p}"):
                        go_wiki("panel", p)
                        
            racks = sorted(set(r for r in results["Rack"].dropna().astype(str) if q in r.lower()))
            for r in racks[:5]:
                if st.button(f"📖 Rack: {r}", key=f"spot_rk_{r}"):
                    go_wiki("rack", r)
