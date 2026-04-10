"""Network graph analysis and Mermaid diagram generation."""

from __future__ import annotations

import networkx as nx

from models import Connection, Entity, EntityType


def build_graph(entities: list[Entity], connections: list[Connection]) -> nx.DiGraph:
    """Build a directed graph from entities and connections."""
    G = nx.DiGraph()

    # Add entity nodes
    for e in entities:
        G.add_node(e.id, name=e.name, entity_type=e.entity_type.value,
                   source=e.source.value, flags=e.flags)

    # Add connection edges
    for c in connections:
        # Create stub nodes for entities not in our list
        for node_id in [c.source_entity_id, c.target_entity_id]:
            if node_id not in G:
                G.add_node(node_id, name=node_id.split(":")[-1][:20],
                           entity_type="unknown", source="unknown", flags=[])

        G.add_edge(
            c.source_entity_id,
            c.target_entity_id,
            relation_type=c.relation_type,
            label=c.label or c.relation_type,
            weight=c.weight,
            source=c.source.value,
        )

    return G


def analyze_graph(G: nx.DiGraph) -> dict:
    """Compute network metrics for investigative analysis."""
    if len(G) == 0:
        return {"nodes": 0, "edges": 0, "components": 0, "metrics": {}}

    undirected = G.to_undirected()
    components = list(nx.connected_components(undirected))

    # Centrality (on undirected version for betweenness)
    degree_cent = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(undirected) if len(G) > 2 else {}

    # Most connected nodes
    top_by_degree = sorted(degree_cent.items(), key=lambda x: x[1], reverse=True)[:10]
    top_by_betweenness = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]

    # Bridge nodes (whose removal disconnects the graph)
    bridges = []
    if len(components) == 1 and len(G) > 2:
        try:
            bridges = list(nx.bridges(undirected))
        except Exception:
            pass

    return {
        "nodes": len(G),
        "edges": len(G.edges),
        "components": len(components),
        "top_by_connections": [
            {"id": nid, "name": G.nodes[nid].get("name", ""), "centrality": round(score, 3)}
            for nid, score in top_by_degree
        ],
        "top_by_betweenness": [
            {"id": nid, "name": G.nodes[nid].get("name", ""), "betweenness": round(score, 3)}
            for nid, score in top_by_betweenness
        ],
        "bridges": [
            {"from": G.nodes[a].get("name", a), "to": G.nodes[b].get("name", b)}
            for a, b in bridges[:10]
        ],
    }


def find_paths(G: nx.DiGraph, source_id: str, target_id: str, cutoff: int = 5) -> list[list[dict]]:
    """Find all simple paths between two entities."""
    paths = []
    try:
        for path in nx.all_simple_paths(G, source_id, target_id, cutoff=cutoff):
            named_path = []
            for node_id in path:
                named_path.append({
                    "id": node_id,
                    "name": G.nodes[node_id].get("name", node_id),
                    "type": G.nodes[node_id].get("entity_type", "unknown"),
                })
            paths.append(named_path)
    except (nx.NodeNotFound, nx.NetworkXError):
        pass
    return paths


def subgraph_around(G: nx.DiGraph, entity_id: str, depth: int = 2) -> nx.DiGraph:
    """Extract the subgraph within `depth` hops of an entity."""
    try:
        return nx.ego_graph(G, entity_id, radius=depth)
    except nx.NodeNotFound:
        return nx.DiGraph()


def _sanitize_mermaid_id(node_id: str) -> str:
    """Make a node ID safe for Mermaid syntax."""
    return node_id.replace(":", "_").replace("-", "_").replace(" ", "_").replace(".", "_")[:40]


def _sanitize_label(text: str) -> str:
    """Escape special characters for Mermaid labels."""
    return text.replace('"', "'").replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")[:50]


def to_mermaid(G: nx.DiGraph, highlight_ids: set[str] | None = None, max_nodes: int = 50) -> str:
    """Render graph as a Mermaid flowchart diagram.

    Node shapes: person=rounded rect, company=rect, organization=hexagon.
    Flagged entities get a warning indicator in the label.
    """
    if len(G) == 0:
        return "```mermaid\nflowchart LR\n    empty[No connections found]\n```"

    # If graph is too large, prune to most central nodes
    if len(G) > max_nodes:
        centrality = nx.degree_centrality(G)
        top_nodes = sorted(centrality, key=centrality.get, reverse=True)[:max_nodes]
        G = G.subgraph(top_nodes).copy()

    lines = ["```mermaid", "flowchart LR"]

    # Define nodes
    for node_id in G.nodes:
        data = G.nodes[node_id]
        name = _sanitize_label(data.get("name", node_id))
        entity_type = data.get("entity_type", "unknown")
        flags = data.get("flags", [])
        safe_id = _sanitize_mermaid_id(node_id)

        # Add flag indicators
        prefix = ""
        if "sanctioned" in flags or "ofac" in flags:
            prefix = "!! "
        elif "pep" in flags:
            prefix = "* "
        elif "criminal" in flags:
            prefix = "x "

        label = f"{prefix}{name}"

        # Shape by type
        if entity_type == "person":
            lines.append(f'    {safe_id}(["{label}"])')
        elif entity_type in ("company", "unknown"):
            lines.append(f'    {safe_id}["{label}"]')
        elif entity_type == "organization":
            lines.append(f'    {safe_id}{{{{"{label}"}}}}')
        else:
            lines.append(f'    {safe_id}["{label}"]')

    # Define edges
    for src, tgt, data in G.edges(data=True):
        safe_src = _sanitize_mermaid_id(src)
        safe_tgt = _sanitize_mermaid_id(tgt)
        label = _sanitize_label(data.get("label", data.get("relation_type", "")))
        weight = data.get("weight")
        if weight:
            label += f" ({weight}%)"
        if label:
            lines.append(f"    {safe_src} -->|{label}| {safe_tgt}")
        else:
            lines.append(f"    {safe_src} --> {safe_tgt}")

    # Style highlighted nodes
    if highlight_ids:
        styled = [_sanitize_mermaid_id(nid) for nid in highlight_ids if nid in G]
        if styled:
            lines.append(f"    style {','.join(styled)} fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px")

    # Style sanctioned/flagged nodes
    flagged = [
        _sanitize_mermaid_id(nid) for nid in G.nodes
        if any(f in G.nodes[nid].get("flags", []) for f in ["sanctioned", "ofac", "criminal"])
    ]
    if flagged:
        lines.append(f"    style {','.join(flagged)} fill:#ffe066,stroke:#e67700,stroke-width:2px")

    lines.append("```")
    return "\n".join(lines)
