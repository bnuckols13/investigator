"""Beneficial ownership chain tracing."""

from __future__ import annotations

import asyncio
from typing import Any

import networkx as nx

from models import Connection, Entity, EntityType, SourceEnum


async def trace_ownership(
    entity_id: str,
    sources: list[Any],
    max_depth: int = 5,
    visited: set[str] | None = None,
) -> tuple[nx.DiGraph, list[Entity]]:
    """Recursively trace beneficial ownership chains.

    Starts from a company and follows ownership/directorship links
    up to max_depth levels. Returns a directed graph and discovered entities.
    """
    G = nx.DiGraph()
    all_entities = []
    visited = visited or set()

    if entity_id in visited or len(visited) >= 100:
        return G, all_entities
    visited.add(entity_id)

    # Fetch connections from all sources
    conn_tasks = [s.get_connections(entity_id) for s in sources]
    results = await asyncio.gather(*conn_tasks, return_exceptions=True)

    ownership_connections = []
    for result in results:
        if isinstance(result, Exception):
            continue
        for conn in result:
            if conn.relation_type in ("ownership", "directorship"):
                ownership_connections.append(conn)
                G.add_edge(
                    conn.source_entity_id,
                    conn.target_entity_id,
                    relation_type=conn.relation_type,
                    weight=conn.weight,
                    label=conn.label,
                )

    # Fetch entity details for new nodes
    new_ids = set()
    for conn in ownership_connections:
        for nid in [conn.source_entity_id, conn.target_entity_id]:
            if nid not in visited:
                new_ids.add(nid)

    # Recurse into owners (go up the chain)
    if max_depth > 1:
        for nid in new_ids:
            sub_graph, sub_entities = await trace_ownership(
                nid, sources, max_depth - 1, visited
            )
            G = nx.compose(G, sub_graph)
            all_entities.extend(sub_entities)

    return G, all_entities


def find_ultimate_beneficial_owners(G: nx.DiGraph) -> list[str]:
    """Find natural persons at the top of ownership chains (leaf nodes with no outgoing ownership edges)."""
    ubos = []
    for node in G.nodes:
        # UBOs are nodes with no outgoing edges (no one owns them)
        # or nodes typed as persons
        if G.out_degree(node) == 0:
            ubos.append(node)
    return ubos


def detect_circular_ownership(G: nx.DiGraph) -> list[list[str]]:
    """Detect circular ownership structures (shell company red flag).

    Returns list of cycles found in the ownership graph.
    """
    cycles = []
    try:
        for cycle in nx.simple_cycles(G):
            if len(cycle) >= 2:
                cycles.append(cycle)
    except nx.NetworkXError:
        pass
    return cycles


def ownership_summary(G: nx.DiGraph) -> dict:
    """Generate a summary of the ownership structure."""
    ubos = find_ultimate_beneficial_owners(G)
    cycles = detect_circular_ownership(G)

    # Count layers
    layers = 0
    if G.nodes:
        try:
            layers = nx.dag_longest_path_length(G) if nx.is_directed_acyclic_graph(G) else 0
        except Exception:
            layers = 0

    return {
        "total_entities": len(G.nodes),
        "ownership_links": len(G.edges),
        "ultimate_beneficial_owners": ubos,
        "circular_structures": cycles,
        "max_ownership_layers": layers,
        "red_flags": {
            "circular_ownership": len(cycles) > 0,
            "deep_structure": layers > 3,
            "many_layers": layers > 5,
        },
    }
