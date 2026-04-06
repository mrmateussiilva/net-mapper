import pandas as pd
import plotly.express as px
import streamlit as st

from app.data import detect_errors
from app.config import TEMPLATE

def render_errors_view(dfs: dict):
    """Renders the global errors and inconsistencies view."""
    st.title("🚨 Erros e Inconsistências — Todos os Decks")
    
    all_issues = []
    for sh, df in dfs.items():
        all_issues.extend(detect_errors(df, sh))
        
    if all_issues:
        idf = pd.concat(all_issues, ignore_index=True)
        iss = idf.groupby(["Sheet", "Issue"]).size().reset_index(name="N")
        
        fig_e = px.bar(iss, x="N", y="Issue", color="Sheet", orientation="h", text="N",
                     template=TEMPLATE, height=max(280, len(iss) * 36),
                     color_discrete_sequence=["#10b981", "#3b82f6", "#8b5cf6"])
        fig_e.update_layout(margin=dict(t=10, b=0), yaxis_title="", legend=dict(font=dict(size=10)))
        st.plotly_chart(fig_e, use_container_width=True)
        
        by2 = idf.groupby("Issue").size().reset_index(name="N").sort_values("N", ascending=False)
        for _, ri in by2.iterrows():
            icon = '🔴' if 'duplicad' in ri['Issue'] or 'Ativo' in ri['Issue'] else '🟡'
            with st.expander(f"{icon} {ri['Issue']} — {ri['N']} ocorrências"):
                sub = idf[idf["Issue"] == ri["Issue"]]
                dcols = [c for c in ["Sheet", "Rack", "Optic Patch Painel", "Port", "Wall Port", "Switch", "Switch Port", "Active", "Observation"] if c in sub.columns]
                st.dataframe(sub[dcols], use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nenhum erro detectado!")
