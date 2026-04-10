import math
from collections import defaultdict

import networkx as nx
import pandas as pd

from app.services.mapping_service import ign, safe


def build_switch_graph(sw_name: str, rows_df: pd.DataFrame) -> nx.Graph:
    """Build a NetworkX graph for a single switch topology."""
    graph = nx.Graph()
    sw_id = f"SW:{sw_name}"
    graph.add_node(sw_id, type="switch", label=sw_name)

    for _, row in rows_df.iterrows():
        panel = safe(row.get("Optic Patch Painel", ""))
        wall_port = safe(row.get("Wall Port", ""))
        rack = safe(row.get("Rack", ""))
        port = str(int(row["Port"])) if pd.notna(row.get("Port")) else "?"
        switch_port = safe(row.get("Switch Port", ""))
        observation = safe(row.get("Observation", ""))
        active = safe(row.get("Active_norm", ""))

        panel_id = f"PP:{panel}" if panel and not ign(panel) else f"RK:{rack}"
        panel_label = panel if panel and not ign(panel) else rack

        if panel_id not in graph:
            graph.add_node(panel_id, type="panel", label=panel_label)

        hover = f"<b>{panel_label} -> {sw_name}</b><br>PP porta: {port} | SW porta: {switch_port}<br>Status: {active}"
        if observation and not ign(observation):
            hover += f"<br>Obs: {observation}"

        graph.add_edge(sw_id, panel_id, hover=hover)

        if wall_port and not ign(wall_port):
            wall_port_id = f"WP:{wall_port}"
            if wall_port_id not in graph:
                graph.add_node(wall_port_id, type="wallport", label=wall_port)
            graph.add_edge(panel_id, wall_port_id, hover=f"<b>Wall Port: {wall_port}</b><br>Via: {panel_label} porta {port}")

    return graph


def radial_pos(graph: nx.Graph, center: str) -> dict:
    """Calculate radial positions for a switch-centered topology graph."""
    positions = {center: (0.0, 0.0)}
    level_one = list(graph.neighbors(center))
    for i, node in enumerate(level_one):
        angle = 2 * math.pi * i / max(len(level_one), 1)
        positions[node] = (math.cos(angle), math.sin(angle))
        level_two = [neighbor for neighbor in graph.neighbors(node) if neighbor != center and neighbor not in positions]
        spread = math.pi / max(len(level_one), 1) * 0.85
        for j, neighbor in enumerate(level_two):
            branch_angle = angle + spread * (j - (len(level_two) - 1) / 2) / max(len(level_two), 1) * len(level_two)
            positions[neighbor] = (1.9 * math.cos(branch_angle), 1.9 * math.sin(branch_angle))
    return positions


def get_global_3d_layout(df_json: str):
    """
    Compute the 3D spring layout for the global graph from a serialized dataframe.
    """
    df = pd.read_json(df_json, orient="records")
    graph = nx.Graph()
    for _, row in df.iterrows():
        switch = safe(row.get("Switch", ""))
        panel = safe(row.get("Optic Patch Painel", ""))
        rack = safe(row.get("Rack", ""))

        if ign(switch) or not switch:
            continue

        switch_id = f"SW:{switch}"
        rack_id = f"RK:{rack}"
        panel_id = f"PP:{panel}" if panel and not ign(panel) else None

        graph.add_node(switch_id, type="switch", label=switch)
        graph.add_node(rack_id, type="rack", label=rack)

        if panel_id:
            graph.add_node(panel_id, type="panel", label=panel)
            graph.add_edge(rack_id, panel_id)
            graph.add_edge(panel_id, switch_id)
        else:
            graph.add_edge(rack_id, switch_id)

    if len(graph.nodes) > 160:
        top_nodes = sorted(graph.degree, key=lambda item: item[1], reverse=True)[:160]
        graph = graph.subgraph([node for node, _ in top_nodes]).copy()

    positions = nx.spring_layout(graph, dim=3, seed=42, k=1.0)
    nodes_data = {
        node: {
            "pos": positions[node],
            "type": graph.nodes[node].get("type", "panel"),
            "label": graph.nodes[node].get("label", node),
            "degree": graph.degree(node),
        }
        for node in graph.nodes()
    }
    edges = list(graph.edges())
    return nodes_data, edges
