"""Markdown investigation memo generator."""

from __future__ import annotations

from datetime import datetime

from models import SearchResult


def generate_memo(result: SearchResult) -> str:
    """Generate a structured Markdown investigation memo."""
    lines = []
    query = result.query
    ts = result.metadata.get("timestamp", datetime.now().isoformat())

    lines.append(f"# Investigation Memo: {query}")
    lines.append(f"*Generated {ts}*\n")

    # Sources summary
    sources_queried = result.metadata.get("sources_queried", [])
    sources_ok = result.metadata.get("sources_succeeded", [])
    sources_failed = result.metadata.get("sources_failed", [])
    if sources_queried:
        lines.append(f"**Sources queried:** {', '.join(sources_queried)}")
        if sources_failed:
            lines.append(f"**Sources failed:** {', '.join(sources_failed)}")
        lines.append("")

    # Executive summary
    lines.append("## Executive Summary\n")
    n_entities = len(result.entities)
    n_groups = len(result.resolved_groups)
    n_connections = len(result.connections)
    high_scores = [s for s in result.scores if s.total_score >= 40]

    lines.append(f"- **{n_entities}** entities found across {len(sources_ok)} sources, resolved to **{n_groups}** distinct entities")
    lines.append(f"- **{n_connections}** connections mapped")
    if high_scores:
        lines.append(f"- **{len(high_scores)}** high-priority leads identified")
        top = high_scores[0]
        lines.append(f"- Highest priority: **{top.entity_name}** (score: {top.total_score:.0f})")
    lines.append("")

    # High-priority entities table
    if result.scores:
        lines.append("## Priority Entities\n")
        lines.append("| Rank | Name | Type | Score | Flags |")
        lines.append("|------|------|------|-------|-------|")
        for i, score in enumerate(result.scores[:15], 1):
            # Find the entity
            entity = next((e for e in result.entities if e.id == score.entity_id), None)
            etype = entity.entity_type.value if entity else "?"
            flags_str = ", ".join(score.flags[:5]) if score.flags else "-"
            lines.append(f"| {i} | {score.entity_name} | {etype} | {score.total_score:.0f} | {flags_str} |")
        lines.append("")

    # Score explanations for top entities
    if high_scores:
        lines.append("## Lead Analysis\n")
        for score in high_scores[:5]:
            lines.append(score.explanation)
            lines.append("")

    # Network diagram
    if result.metadata.get("mermaid"):
        lines.append("## Network Map\n")
        lines.append(result.metadata["mermaid"])
        lines.append("")

    # Network metrics
    if result.metadata.get("network_analysis"):
        na = result.metadata["network_analysis"]
        lines.append("## Network Analysis\n")
        lines.append(f"- **{na.get('nodes', 0)}** nodes, **{na.get('edges', 0)}** edges, **{na.get('components', 0)}** components")

        top_conns = na.get("top_by_connections", [])
        if top_conns:
            lines.append("\n**Most connected entities:**")
            for item in top_conns[:5]:
                lines.append(f"- {item['name']} (centrality: {item['centrality']})")

        top_bridge = na.get("top_by_betweenness", [])
        if top_bridge:
            lines.append("\n**Bridge entities (removal would disconnect networks):**")
            for item in top_bridge[:5]:
                if item["betweenness"] > 0:
                    lines.append(f"- {item['name']} (betweenness: {item['betweenness']})")
        lines.append("")

    # Resolved entity groups (cross-source matches)
    cross_source = [g for g in result.resolved_groups if len(set(m.entity.source for m in g)) > 1]
    if cross_source:
        lines.append("## Cross-Source Matches\n")
        lines.append("Entities appearing in multiple databases:\n")
        for group in cross_source[:10]:
            primary = group[0].entity
            lines.append(f"**{primary.name}**")
            for match in group:
                e = match.entity
                flags = f" [{', '.join(e.flags)}]" if e.flags else ""
                lines.append(f"  - {e.source.value}: {e.name} (match: {match.score:.0f}%){flags}")
            lines.append("")

    # Timeline
    if result.events:
        lines.append("## Timeline\n")
        sorted_events = sorted(result.events, key=lambda e: e.date, reverse=True)
        for event in sorted_events[:20]:
            amount = f" (${event.amount:,.0f})" if event.amount else ""
            lines.append(f"- **{event.date}** [{event.source.value}] {event.description}{amount}")
        lines.append("")

    # Flags summary
    all_flags = set()
    for e in result.entities:
        all_flags.update(e.flags)
    if all_flags:
        lines.append("## Flags Detected\n")
        for flag in sorted(all_flags):
            count = sum(1 for e in result.entities if flag in e.flags)
            lines.append(f"- **{flag}**: {count} entities")
        lines.append("")

    return "\n".join(lines)
