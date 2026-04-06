import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..data import health_score, hascol, ign, safe, detect_errors
from ..graphs import build_switch_graph, switch_radial_fig
from ..ui import go_wiki, style_status, patch_panel_html
from ..config import TEMPLATE, CMAP, IGNORE

def render_deck_view(sheet_name: str, full_df: pd.DataFrame):
    """Renders the detailed view for a specific deck/sheet."""
    df = full_df.copy()
    st.title(f"📋 {sheet_name}")

    if "Active_norm" not in df.columns:
        st.warning("Dados não normalizados corretamente para esta aba.")
        return

    with st.sidebar:
        st.divider()
        active_opts = df["Active_norm"].unique().tolist()
        active_f = st.multiselect("Status", active_opts, default=active_opts)
        
        rack_opts = sorted(df["Rack"].dropna().astype(str).unique()) if "Rack" in df.columns else []
        rack_f = st.multiselect("Rack", rack_opts, default=rack_opts)

    mask = df["Active_norm"].isin(active_f)
    if rack_f and "Rack" in df.columns:
        mask &= df["Rack"].astype(str).isin(rack_f)
        
    df_f = df[mask]

    score, grade, crit = health_score(df_f, sheet_name)
    gc = {"A": "#10b981", "B": "#f59e0b", "C": "#ef4444"}.get(grade, "#374151")

    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])
    c1.metric("Filtradas", len(df_f))
    c2.metric("✅ Ativas", (df_f["Active_norm"] == "Active").sum())
    c3.metric("❓ Desconh.", (df_f["Active_norm"] == "Unknown").sum())
    c4.metric("⬜ Inativas", (df_f["Active_norm"] == "Inactive/Empty").sum())
    
    with c5:
        crit_html = " · ".join(f"{k}: {v*100:.0f}%" for k, v in crit.items())
        st.markdown(f"""
<div style="border:2px solid {gc};border-radius:10px;padding:0.6rem 1rem;display:flex;align-items:center;gap:12px;">
  <div style="font-size:2rem;font-weight:800;color:{gc};">{score}</div>
  <div>
    <div style="font-size:0.65rem;color:#6b7280;text-transform:uppercase;">Health Score · Grade {grade}</div>
    <div style="font-size:0.7rem;color:#374151;">{crit_html}</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.divider()
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Análise", "🔗 Grafos por Switch", "🌊 Fluxo", "🚨 Erros", "📋 Dados"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            vc = df_f["Active_norm"].value_counts().reset_index()
            vc.columns = ["Status", "N"]
            fig = px.bar(vc, x="Status", y="N", color="Status", text="N",
                         color_discrete_map=CMAP, template=TEMPLATE)
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, height=280, margin=dict(t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            if hascol(df_f, "Observation"):
                obs = df_f["Observation"].dropna().astype(str)
                obs = obs[~obs.isin(["Observation"])].value_counts().head(10).reset_index()
                obs.columns = ["Obs", "N"]
                if not obs.empty:
                    fig2 = px.bar(obs, x="N", y="Obs", orientation="h", text="N", template=TEMPLATE, color="N", color_continuous_scale="Blues")
                    fig2.update_layout(height=280, margin=dict(t=10, b=0), coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig2, use_container_width=True)

        if hascol(df_f, "Optic Patch Painel") and hascol(df_f, "Port"):
            try:
                pp_df2 = df_f[df_f["Optic Patch Painel"].notna()].copy()
                pp_df2["Port_int"] = pd.to_numeric(pp_df2["Port"], errors="coerce")
                pp_df2 = pp_df2[pp_df2["Port_int"].notna()]
                heat = pp_df2[pp_df2["Active_norm"] == "Active"].groupby(["Optic Patch Painel", "Port_int"]).size().reset_index(name="N")
                if not heat.empty:
                    piv = heat.pivot(index="Optic Patch Painel", columns="Port_int", values="N").fillna(0)
                    fig_h = px.imshow(piv, color_continuous_scale="Greens",
                                      labels=dict(x="Porta", y="Patch Panel", color="Ativas"),
                                      aspect="auto", template=TEMPLATE, height=max(340, len(piv) * 16))
                    fig_h.update_layout(margin=dict(t=10, b=0))
                    st.plotly_chart(fig_h, use_container_width=True)
            except Exception as e:
                pass # fail silently on heat map generation
                
        act_df2 = df_f[df_f["Active_norm"] == "Active"].copy()
        if not act_df2.empty and hascol(act_df2, "Switch") and hascol(act_df2, "Optic Patch Painel") and hascol(act_df2, "Rack"):
            act_df2["_r"] = act_df2["Rack"].astype(str).str.strip()
            act_df2["_p"] = act_df2["Optic Patch Painel"].astype(str).str.strip()
            act_df2["_s"] = act_df2["Switch"].astype(str).str.strip()
            sun = act_df2[~act_df2["_s"].str.upper().isin(IGNORE)].groupby(["_r", "_p", "_s"]).size().reset_index(name="v")
            if not sun.empty:
                fig_sun = px.sunburst(sun, path=["_r", "_p", "_s"], values="v",
                                      color="v", color_continuous_scale="Teal", template=TEMPLATE, height=500)
                fig_sun.update_layout(margin=dict(t=10, b=0))
                st.plotly_chart(fig_sun, use_container_width=True)

    with tab2:
        st.caption("🟢 Switch (centro) · 🔵 Patch Panel · 🟡 Wall Port · Hover nas arestas para detalhes")
        if not hascol(df_f, "Switch"):
            st.warning("Coluna Switch não disponível.")
        else:
            act = df_f[df_f["Active_norm"] == "Active"].copy()
            sw_grp = {}
            for _, row in act.iterrows():
                sw = safe(row.get("Switch", ""))
                if not sw or ign(sw): continue
                sw_grp.setdefault(sw, []).append(row)
                
            sw_list = sorted(sw_grp.keys(), key=lambda s: len(sw_grp[s]), reverse=True)
            ca2, cb2, cc2 = st.columns([3, 1, 1])
            with ca2: srch = st.text_input("Filtrar switch", "", key=f"sw_{sheet_name}")
            with cb2: cpr = st.selectbox("Por linha", [1, 2, 3], index=1, key=f"cpr_{sheet_name}")
            with cc2: tall = st.checkbox("Todos", False, key=f"tall_{sheet_name}")
            
            if srch: sw_list = [s for s in sw_list if srch.lower() in s.lower()]
            if not tall: sw_list = sw_list[:16]
            
            st.caption(f"{len(sw_list)} switches · {sum(len(sw_grp[s]) for s in sw_list)} conexões")
            
            badges_html = "".join(f'<span class="badge {"b-green" if len(sw_grp[s])>5 else "b-blue" if len(sw_grp[s])>2 else "b-gray"}">{s} ({len(sw_grp[s])})</span>' for s in sw_list[:40])
            st.markdown(badges_html, unsafe_allow_html=True)
            st.divider()
            
            for i in range(0, len(sw_list), cpr):
                cols = st.columns(cpr)
                for j, col in enumerate(cols):
                    if i + j >= len(sw_list): break
                    sw_name = sw_list[i + j]
                    rdf = pd.DataFrame(sw_grp[sw_name])
                    G = build_switch_graph(sw_name, rdf)
                    sw_id = f"SW:{sw_name}"
                    if len(G.nodes) > 1:
                        col.plotly_chart(switch_radial_fig(G, sw_id, sw_name), use_container_width=True)
                        if col.button(f"📖 Wiki: {sw_name}", key=f"wiki_btn_{sw_name}_{sheet_name}"):
                            go_wiki("switch", sw_name)

    with tab3:
        act_s = df_f[df_f["Active_norm"] == "Active"].copy()
        if not act_s.empty and hascol(act_s, "Switch"):
            act_s["_r"] = act_s["Rack"].astype(str).str.strip()
            act_s["_p"] = act_s["Optic Patch Painel"].astype(str).str.strip() if hascol(act_s, "Optic Patch Painel") else "PP"
            act_s["_s"] = act_s["Switch"].astype(str).str.strip()
            act_s = act_s[~act_s["_s"].str.upper().isin(IGNORE)]
            
            nodes_set = list(dict.fromkeys(list(act_s["_r"].unique()) + list(act_s["_p"].unique()) + list(act_s["_s"].unique())))
            idx = {n: i for i, n in enumerate(nodes_set)}
            
            s1 = act_s.groupby(["_r", "_p"]).size().reset_index(name="v")
            s2 = act_s.groupby(["_p", "_s"]).size().reset_index(name="v")
            
            src = [idx[r] for r in s1["_r"]] + [idx[p] for p in s2["_p"]]
            tgt = [idx[p] for p in s1["_p"]] + [idx[s] for s in s2["_s"]]
            val = list(s1["v"]) + list(s2["v"])
            
            nr = len(act_s["_r"].unique())
            np3 = len(act_s["_p"].unique())
            nc3 = len(act_s["_s"].unique())
            
            node_colors = ["#8b5cf6"] * nr + ["#3b82f6"] * np3 + ["#10b981"] * nc3
            
            fig_s = go.Figure(go.Sankey(
                node=dict(label=nodes_set, color=node_colors, pad=14, thickness=16,
                          line=dict(color="#e5e7eb", width=0.5)),
                link=dict(source=src, target=tgt, value=val, color="rgba(59,130,246,0.18)")))
            fig_s.update_layout(height=480, template=TEMPLATE, margin=dict(t=10, b=0))
            st.plotly_chart(fig_s, use_container_width=True)

    with tab4:
        # Re-using the full unfiltered df for errors
        issues = detect_errors(full_df, sheet_name)
        if issues:
            idf2 = pd.concat(issues, ignore_index=True)
            by_iss = idf2.groupby("Issue").size().reset_index(name="N").sort_values("N", ascending=False)
            fig_e = px.bar(by_iss, x="N", y="Issue", orientation="h", color="N", color_continuous_scale="Reds",
                         text="N", template=TEMPLATE, height=max(220, len(by_iss) * 40))
            fig_e.update_layout(margin=dict(t=10, b=0), yaxis_title="", coloraxis_showscale=False)
            st.plotly_chart(fig_e, use_container_width=True)
            
            for _, ri in by_iss.iterrows():
                icon = '🔴' if 'duplicad' in ri['Issue'] or 'Ativo' in ri['Issue'] else '🟡'
                with st.expander(f"{icon} {ri['Issue']} — {ri['N']} ocorrências"):
                    sub = idf2[idf2["Issue"] == ri["Issue"]]
                    dcols = [c for c in ["Rack", "Optic Patch Painel", "Port", "Wall Port", "Switch", "Switch Port", "Active", "Observation"] if c in sub.columns]
                    st.dataframe(sub[dcols], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Nenhum erro detectado!")

        _, _, crit = health_score(df_f, sheet_name)
        fig_g = go.Figure()
        glab = ["Documentação", "Utilização", "Mapeamento", "Sem Erros"]
        gcols = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6"]
        
        for i, (lab, col) in enumerate(zip(glab, gcols)):
            fig_g.add_trace(go.Indicator(mode="gauge+number", value=crit[lab] * 100,
                title={"text": lab, "font": {"size": 10}},
                number={"suffix": "%", "font": {"size": 18}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": col},
                       "steps": [{"range": [0, 50], "color": "#fee2e2"}, {"range": [50, 80], "color": "#fef3c7"}, {"range": [80, 100], "color": "#d1fae5"}]},
                domain={"row": 0, "column": i}))
                
        fig_g.update_layout(grid={"rows": 1, "columns": 4}, height=220, margin=dict(t=40, b=0), template=TEMPLATE)
        st.plotly_chart(fig_g, use_container_width=True)

    with tab5:
        srch2 = st.text_input("Busca livre", "", key=f"srch_{sheet_name}")
        disp = df_f.copy()
        if srch2:
            m2 = disp.astype(str).apply(lambda c: c.str.contains(srch2, case=False, na=False)).any(axis=1)
            disp = disp[m2]
            
        st.caption(f"{len(disp)} de {len(full_df)} linhas")
        show_cols = [c for c in disp.columns if not c.startswith("Unnamed") and c != "Active_norm"]
        ren = disp[show_cols + ["Active_norm"]].rename(columns={"Active_norm": "Status"})
        
        st.dataframe(style_status(ren), use_container_width=True, hide_index=True, height=500)
        st.download_button("⬇️ Exportar CSV", disp[show_cols].to_csv(index=False).encode(), f"{sheet_name}_data.csv", "text/csv")
