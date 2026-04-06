import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..data import health_score, hascol, ign
from ..config import TEMPLATE

def render_dashboard(dfs: dict, all_df: pd.DataFrame):
    """Renders the main dashboard view with consolidated metrics and charts."""
    st.title("🔌 Network Mapping — Safe Notos")
    st.caption("Dashboard consolidado · 3 decks · cabeamento estruturado")

    total = sum(len(d) for d in dfs.values())
    active = sum((d.get("Active_norm") == "Active").sum() for d in dfs.values()) if total > 0 else 0
    inactive = sum((d.get("Active_norm") == "Inactive/Empty").sum() for d in dfs.values()) if total > 0 else 0
    unknown = sum((d.get("Active_norm") == "Unknown").sum() for d in dfs.values()) if total > 0 else 0
    undoc = sum((d.get("Active_norm") == "Not Documented").sum() for d in dfs.values()) if total > 0 else 0
    
    n_sw = len(set(v for v in all_df.get("Switch", pd.Series(dtype=str)).dropna().astype(str) if not ign(v))) if "Switch" in all_df.columns else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("🔌 Total Portas", f"{total:,}")
    c2.metric("✅ Ativas", f"{active:,}", f"{active/total*100:.1f}%" if total else "0%")
    c3.metric("⬜ Inativas", f"{inactive:,}", f"{inactive/total*100:.1f}%" if total else "0%")
    c4.metric("❓ Desconhecidas", f"{unknown:,}", f"{unknown/total*100:.1f}%" if total else "0%")
    c5.metric("📋 Não Doc.", f"{undoc:,}", f"{undoc/total*100:.1f}%" if total else "0%")
    c6.metric("🖥️ Switches", f"{n_sw:,}")

    st.divider()

    # Health scores
    st.subheader("📊 Network Health Score por Deck")
    hcols = st.columns(len(dfs) if len(dfs) > 0 else 1)
    colors_hs = {"A": "#10b981", "B": "#f59e0b", "C": "#ef4444"}
    
    for i, (sh, df) in enumerate(dfs.items()):
        score, grade, crit = health_score(df, sh)
        color = colors_hs.get(grade, "#374151")
        with hcols[i]:
            crit_html = "".join(f'<div style="display:flex;justify-content:space-between;font-size:0.75rem;margin:3px 0;"><span style="color:#6b7280">{k}</span><span style="color:{"#10b981" if v>0.7 else "#f59e0b" if v>0.4 else "#ef4444"};font-weight:600;">{v*100:.0f}%</span></div>' for k, v in crit.items())
            st.markdown(f"""
<div style="border:2px solid {color};border-radius:14px;padding:1.2rem;text-align:center;">
  <div style="font-size:0.72rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;">
    {sh.replace("Deck ", "").replace(" - ", "·")}
  </div>
  <div style="font-size:3rem;font-weight:800;color:{color};line-height:1.1;">{score}</div>
  <div style="font-size:1rem;color:{color};font-weight:600;">Grade {grade}</div>
  <hr style="margin:0.8rem 0;border-color:#e5e7eb;">
  {crit_html}
</div>""", unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Status por Deck")
        rows = []
        for sh, df in dfs.items():
            if "Active_norm" in df.columns:
                vc = df["Active_norm"].value_counts()
                rows.append({
                    "Deck": sh.replace("Deck ", "").replace(" - ", "·"),
                    "Ativas": vc.get("Active", 0),
                    "Inativas": vc.get("Inactive/Empty", 0),
                    "Desconhecidas": vc.get("Unknown", 0),
                    "Não Doc.": vc.get("Not Documented", 0)
                })
        if rows:
            sdf = pd.DataFrame(rows)
            fig = px.bar(sdf.melt("Deck", var_name="Status", value_name="N"),
                         x="Deck", y="N", color="Status", barmode="stack", template=TEMPLATE,
                         color_discrete_map={"Ativas": "#10b981", "Inativas": "#6b7280", "Desconhecidas": "#f59e0b", "Não Doc.": "#ef4444"})
            fig.update_layout(height=320, margin=dict(t=10, b=0), legend=dict(font=dict(size=10)))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Radar de Saúde")
        cats = ["Documentação", "Utilização", "Mapeamento", "Sem Erros"]
        fig_r = go.Figure()
        cols_r = ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ec4899"]
        
        for i, (sh, df) in enumerate(dfs.items()):
            _, _, crit = health_score(df, sh)
            vals = [crit[c] * 100 for c in cats] + [crit[cats[0]] * 100]
            col_hex = cols_r[i % len(cols_r)]
            r, g, b = int(col_hex[1:3], 16), int(col_hex[3:5], 16), int(col_hex[5:7], 16)
            
            fig_r.add_trace(go.Scatterpolar(
                r=vals, theta=cats + [cats[0]],
                fill="toself", name=sh.replace("Deck ", "").replace(" - ", "·"),
                line=dict(color=col_hex, width=2),
                fillcolor=f"rgba({r},{g},{b},0.1)"
            ))
            
        fig_r.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            height=320, margin=dict(t=10, b=10), template=TEMPLATE,
            legend=dict(font=dict(size=10))
        )
        st.plotly_chart(fig_r, use_container_width=True)

    st.subheader("🏆 Top 20 Switches — Portas Ativas")
    sw_rows = []
    for sh, df in dfs.items():
        if "Active_norm" in df.columns:
            act = df[df["Active_norm"] == "Active"]
            if hascol(act, "Switch"):
                for sw, grp in act.groupby("Switch"):
                    sv = safe(sw)
                    if ign(sv): continue
                    sw_rows.append({"Switch": sv, "Deck": sh.replace("Deck ", "").replace(" - ", "·"), "N": len(grp)})
                    
    if sw_rows:
        sw_df = pd.DataFrame(sw_rows).groupby(["Switch", "Deck"])["N"].sum().reset_index()
        sw_df = sw_df.sort_values("N", ascending=False).head(20)
        fig_sw = px.bar(sw_df, x="N", y="Switch", color="Deck", orientation="h", text="N",
                      template=TEMPLATE, height=max(360, len(sw_df) * 26),
                      color_discrete_sequence=["#10b981", "#3b82f6", "#8b5cf6"])
        fig_sw.update_layout(margin=dict(t=10, b=0), yaxis={"categoryorder": "total ascending"},
                             legend=dict(font=dict(size=10)))
        st.plotly_chart(fig_sw, use_container_width=True)

    st.subheader("🌊 Fluxo Global — Rack → PP → Switch")
    if "Active_norm" in all_df.columns:
        all_act = all_df[all_df["Active_norm"] == "Active"].copy()
        if not all_act.empty and hascol(all_act, "Switch"):
            all_act["_r"] = all_act["Rack"].astype(str).str.strip()
            all_act["_p"] = all_act["Optic Patch Painel"].astype(str).str.strip() if hascol(all_act, "Optic Patch Painel") else "PP"
            all_act["_s"] = all_act["Switch"].astype(str).str.strip()
            all_act = all_act[~all_act["_s"].str.upper().isin(IGNORE)]
            
            # limit nodes to prevent massive browser freezing
            top_sw = all_act["_s"].value_counts().head(30).index
            sub_act = all_act[all_act["_s"].isin(top_sw)]
            nodes_set = list(dict.fromkeys(list(sub_act["_r"].unique()) + list(sub_act["_p"].unique()) + list(sub_act["_s"].unique())))
            idx = {n: i for i, n in enumerate(nodes_set)}
            
            s1 = sub_act.groupby(["_r", "_p"]).size().reset_index(name="v")
            s2 = sub_act.groupby(["_p", "_s"]).size().reset_index(name="v")
            
            src = [idx[r] for r in s1["_r"]] + [idx[p] for p in s2["_p"]]
            tgt = [idx[p] for p in s1["_p"]] + [idx[s] for s in s2["_s"]]
            val = list(s1["v"]) + list(s2["v"])
            
            nr = len(sub_act["_r"].unique())
            np2 = len(sub_act["_p"].unique())
            ns2 = len(sub_act["_s"].unique())
            
            node_colors = ["#8b5cf6"] * nr + ["#3b82f6"] * np2 + ["#10b981"] * ns2
            
            fig_s = go.Figure(go.Sankey(
                node=dict(label=nodes_set, color=node_colors, pad=12, thickness=16,
                          line=dict(color="#e5e7eb", width=0.5)),
                link=dict(source=src, target=tgt, value=val, color="rgba(59,130,246,0.15)")))
            fig_s.update_layout(height=520, template=TEMPLATE, margin=dict(t=10, b=0))
            st.plotly_chart(fig_s, use_container_width=True)
