import math
from collections import defaultdict
import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import TEMPLATE, IGNORE
from app.data import safe, ign

def build_switch_graph(sw_name: str, rows_df: pd.DataFrame) -> nx.Graph:
    """Builds a NetworkX graph for a single switch's topology."""
    G = nx.Graph()
    sw_id = f"SW:{sw_name}"
    G.add_node(sw_id, type="switch", label=sw_name)
    
    for _, row in rows_df.iterrows():
        panel = safe(row.get("Optic Patch Painel", ""))
        wp = safe(row.get("Wall Port", ""))
        rack = safe(row.get("Rack", ""))
        port = str(int(row["Port"])) if pd.notna(row.get("Port")) else "?"
        sw_pt = safe(row.get("Switch Port", ""))
        obs = safe(row.get("Observation", ""))
        active = safe(row.get("Active_norm", ""))
        
        pp_id = f"PP:{panel}" if panel and not ign(panel) else f"RK:{rack}"
        pp_lbl = panel if panel and not ign(panel) else rack
        
        if pp_id not in G:
            G.add_node(pp_id, type="panel", label=pp_lbl)
            
        hover = f"<b>{pp_lbl} → {sw_name}</b><br>PP porta: {port} | SW porta: {sw_pt}<br>Status: {active}"
        if obs and not ign(obs): 
            hover += f"<br>Obs: {obs}"
            
        G.add_edge(sw_id, pp_id, hover=hover)
        
        if wp and not ign(wp):
            wp_id = f"WP:{wp}"
            if wp_id not in G:
                G.add_node(wp_id, type="wallport", label=wp)
            G.add_edge(pp_id, wp_id, hover=f"<b>Wall Port: {wp}</b><br>Via: {pp_lbl} porta {port}")
            
    return G


def radial_pos(G: nx.Graph, center: str) -> dict:
    """Calculates radial positions for switch topology graph."""
    pos = {center: (0.0, 0.0)}
    l1 = list(G.neighbors(center))
    for i, n in enumerate(l1):
        a = 2 * math.pi * i / max(len(l1), 1)
        pos[n] = (math.cos(a), math.sin(a))
        l2 = [nb for nb in G.neighbors(n) if nb != center and nb not in pos]
        sp = math.pi / max(len(l1), 1) * 0.85
        for j, nb in enumerate(l2):
            ba = a + sp * (j - (len(l2)-1)/2) / max(len(l2), 1) * len(l2)
            pos[nb] = (1.9 * math.cos(ba), 1.9 * math.sin(ba))
    return pos


def switch_radial_fig(G: nx.Graph, sw_id: str, sw_name: str) -> go.Figure:
    """Renders a 2D radial plot for a switch using Plotly."""
    NC = {"switch": "#10b981", "panel": "#3b82f6", "wallport": "#f59e0b", "rack": "#8b5cf6"}
    NS = {"switch": 30, "panel": 18, "wallport": 12, "rack": 10}
    pos = radial_pos(G, sw_id)
    
    traces = []
    # edges
    for u, v, data in G.edges(data=True):
        if u not in pos or v not in pos: 
            continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        col = "#10b981" if sw_id in (u, v) else "#f59e0b"
        lw = 2.2 if sw_id in (u, v) else 1.2
        traces.append(go.Scatter(x=[x0, x1, None], y=[y0, y1, None], mode="lines",
            line=dict(width=lw, color=col), hoverinfo="none", showlegend=False))
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        traces.append(go.Scatter(x=[mx], y=[my], mode="markers",
            marker=dict(size=7, color="rgba(0,0,0,0)"),
            hoverinfo="text", hovertext=data.get("hover", ""), showlegend=False))
            
    # nodes
    nx_l, ny_l, nc_l, ns_l, nt_l, nh_l = [], [], [], [], [], []
    for node in G.nodes():
        if node not in pos: 
            continue
        x, y = pos[node]
        ntype = G.nodes[node].get("type", "panel")
        lbl = G.nodes[node].get("label", node)
        deg = G.degree(node)
        nx_l.append(x)
        ny_l.append(y)
        nc_l.append(NC.get(ntype, "#94a3b8"))
        ns_l.append(NS.get(ntype, 14))
        nt_l.append(lbl)
        nh_l.append(f"<b>{lbl}</b><br>Tipo: {ntype}<br>Conexões: {deg}")
        
    traces.append(go.Scatter(
        x=nx_l, y=ny_l, mode="markers+text",
        hoverinfo="text", hovertext=nh_l,
        marker=dict(size=ns_l, color=nc_l, line=dict(width=2, color="white")),
        text=nt_l, textposition="top center",
        textfont=dict(size=9), showlegend=False
    ))
    
    np_ = sum(1 for n in G.nodes if G.nodes[n].get("type") == "panel")
    nw = sum(1 for n in G.nodes if G.nodes[n].get("type") == "wallport")
    nc2 = G.degree(sw_id)
    
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(text=f"<b>{sw_name}</b> · {nc2} conexões · {np_} panels · {nw} wall ports",
                   font=dict(size=13), x=0.5),
        showlegend=False, hovermode="closest", height=460,
        margin=dict(b=10, l=10, r=10, t=45),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.6, 2.6]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.6, 2.6]),
        template=TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


@st.cache_data(show_spinner=False)
def get_global_3d_layout(df_json: str):
    """
    Computes and caches the 3D spring layout for the global graph.
    We pass JSON to safely hash for streamlit caching.
    """
    df = pd.read_json(df_json, orient="records")
    G = nx.Graph()
    for _, row in df.iterrows():
        sw = safe(row.get("Switch", ""))
        pp = safe(row.get("Optic Patch Painel", ""))
        rk = safe(row.get("Rack", ""))
        
        if ign(sw) or not sw: 
            continue
            
        sw_id = f"SW:{sw}"
        rk_id = f"RK:{rk}"
        pp_id = f"PP:{pp}" if pp and not ign(pp) else None
        
        G.add_node(sw_id, type="switch", label=sw)
        G.add_node(rk_id, type="rack", label=rk)
        
        if pp_id:
            G.add_node(pp_id, type="panel", label=pp)
            G.add_edge(rk_id, pp_id)
            G.add_edge(pp_id, sw_id)
        else:
            G.add_edge(rk_id, sw_id)
            
    if len(G.nodes) > 160:
        top = sorted(G.degree, key=lambda x: x[1], reverse=True)[:160]
        G = G.subgraph([n for n, _ in top]).copy()
        
    pos = nx.spring_layout(G, dim=3, seed=42, k=1.0)
    
    # We must return serialized/primitive friendly structures from cache
    nodes_data = {
        node: {"pos": pos[node], "type": G.nodes[node].get("type", "panel"), 
               "label": G.nodes[node].get("label", node), "degree": G.degree(node)}
        for node in G.nodes()
    }
    edges = list(G.edges())
    return nodes_data, edges


def global_3d_fig(all_active: pd.DataFrame) -> go.Figure:
    """Renders a 3D Plotly graph representing the global network topology."""
    # Convert DF to JSON string for the @st.cache_data hash to work easily
    df_json = all_active[["Switch", "Optic Patch Painel", "Rack"]].to_json(orient="records")
    
    # Leverage cached layout processing
    nodes_data, edges = get_global_3d_layout(df_json)
    
    NC3 = {"switch": "#10b981", "panel": "#3b82f6", "rack": "#8b5cf6", "wallport": "#f59e0b"}
    NS3 = {"switch": 9, "panel": 5, "rack": 4}
    
    ex, ey, ez = [], [], []
    for u, v in edges:
        x0, y0, z0 = nodes_data[u]["pos"]
        x1, y1, z1 = nodes_data[v]["pos"]
        ex += [x0, x1, None]
        ey += [y0, y1, None]
        ez += [z0, z1, None]
        
    traces = [go.Scatter3d(x=ex, y=ey, z=ez, mode="lines",
        line=dict(width=1, color="rgba(100,130,200,0.25)"), hoverinfo="none", showlegend=False)]
        
    groups = defaultdict(lambda: {"x": [], "y": [], "z": [], "txt": [], "sz": []})
    for node, data in nodes_data.items():
        x, y, z = data["pos"]
        ntype = data["type"]
        lbl = data["label"]
        deg = data["degree"]
        
        groups[ntype]["x"].append(x)
        groups[ntype]["y"].append(y)
        groups[ntype]["z"].append(z)
        groups[ntype]["txt"].append(f"<b>{lbl}</b><br>{ntype} · {deg} conexões")
        groups[ntype]["sz"].append(min(NS3.get(ntype, 4) + deg * 0.7, 20))
        
    lmap = {"switch": "Switches", "panel": "Patch Panels", "rack": "Racks"}
    for ntype, d in groups.items():
        traces.append(go.Scatter3d(
            x=d["x"], y=d["y"], z=d["z"], mode="markers", name=lmap.get(ntype, ntype),
            marker=dict(size=d["sz"], color=NC3.get(ntype, "#94a3b8"),
                        line=dict(width=0.5, color="white"), opacity=0.92),
            hoverinfo="text", hovertext=d["txt"]
        ))
        
    fig = go.Figure(data=traces)
    fig.update_layout(
        height=640, margin=dict(t=10, b=0, l=0, r=0),
        legend=dict(font=dict(size=11), bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="#e5e7eb", borderwidth=1),
        scene=dict(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
            zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
        ),
        template=TEMPLATE,
    )
    return fig
