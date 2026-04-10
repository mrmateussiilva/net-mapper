import math
from collections import defaultdict
import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import TEMPLATE, IGNORE
from app.data import safe, ign
from app.services.graph_service import build_switch_graph, get_global_3d_layout as get_global_3d_layout_service, radial_pos


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
    """Cached Streamlit wrapper around the pure graph service."""
    return get_global_3d_layout_service(df_json)


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
