"""Lead scoring algorithm for investigative prioritization."""

from __future__ import annotations

from datetime import date, timedelta

import networkx as nx

from models import Connection, Entity, LeadScore, TimelineEvent


def score_entity(
    entity: Entity,
    connections: list[Connection],
    events: list[TimelineEvent],
    graph: nx.DiGraph | None = None,
) -> LeadScore:
    """Compute an investigative priority score for an entity.

    Higher score = more investigative angles worth pursuing.
    """
    components: dict[str, float] = {}

    # 1. Sanctions/PEP hit (+40 per match, cap 80)
    sanctions_flags = [f for f in entity.flags if f in ("sanctioned", "ofac", "eu_sanctioned", "pep", "criminal", "debarred")]
    components["sanctions_pep"] = min(len(sanctions_flags) * 40, 80)

    # 2. Government contracts (+20 per contract connection, cap 60)
    contract_conns = [c for c in connections if c.relation_type == "contract"]
    components["govt_contracts"] = min(len(contract_conns) * 20, 60)

    # 3. Court cases (+25 per litigation connection, cap 75)
    litigation_conns = [c for c in connections if c.relation_type == "litigation"]
    components["court_cases"] = min(len(litigation_conns) * 25, 75)

    # 4. Campaign finance (+15 per significant contribution, cap 45)
    finance_conns = [c for c in connections if c.relation_type == "contribution"]
    components["campaign_finance"] = min(len(finance_conns) * 15, 45)

    # 5. Corporate complexity (+10 per directorship beyond 2, cap 30)
    directorships = [c for c in connections if c.relation_type in ("directorship", "ownership")]
    excess = max(0, len(directorships) - 2)
    components["corporate_complexity"] = min(excess * 10, 30)

    # 6. Cross-jurisdiction (+15 per country beyond 1, cap 45)
    n_countries = len(set(entity.countries))
    components["cross_jurisdiction"] = min(max(0, n_countries - 1) * 15, 45)

    # 7. Network centrality (+20 if betweenness > 0.3)
    components["network_centrality"] = 0
    if graph and entity.id in graph:
        try:
            betweenness = nx.betweenness_centrality(graph.to_undirected())
            if betweenness.get(entity.id, 0) > 0.3:
                components["network_centrality"] = 20
        except Exception:
            pass

    # 8. Recency (+10 if any event in last 90 days)
    cutoff = date.today() - timedelta(days=90)
    recent = [e for e in events if e.date >= cutoff]
    components["recency"] = 10 if recent else 0

    total = sum(components.values())

    # Build flags summary
    flags = list(set(entity.flags))
    if contract_conns:
        flags.append("govt_contractor")
    if litigation_conns:
        flags.append("litigated")
    if finance_conns:
        flags.append("political_donor")

    return LeadScore(
        entity_id=entity.id,
        entity_name=entity.name,
        total_score=total,
        components=components,
        flags=flags,
        explanation=explain_score(components, entity.name),
    )


def explain_score(components: dict[str, float], name: str) -> str:
    """Generate a human-readable explanation of what drives the score."""
    parts = []
    labels = {
        "sanctions_pep": "sanctions/PEP list hits",
        "govt_contracts": "government contract connections",
        "court_cases": "court case involvement",
        "campaign_finance": "campaign finance activity",
        "corporate_complexity": "complex corporate structure",
        "cross_jurisdiction": "multi-jurisdiction presence",
        "network_centrality": "high network centrality (bridge entity)",
        "recency": "recent activity detected",
    }
    for key, val in sorted(components.items(), key=lambda x: x[1], reverse=True):
        if val > 0:
            parts.append(f"- **{labels.get(key, key)}**: +{val:.0f}")

    if not parts:
        return f"{name}: No significant investigative indicators detected."

    return f"**{name}** score breakdown:\n" + "\n".join(parts)


def score_all(
    entities: list[Entity],
    connections: list[Connection],
    events: list[TimelineEvent],
    graph: nx.DiGraph | None = None,
) -> list[LeadScore]:
    """Score all entities and return sorted by priority (highest first)."""
    scores = []
    for entity in entities:
        # Filter connections and events for this entity
        ent_conns = [
            c for c in connections
            if c.source_entity_id == entity.id or c.target_entity_id == entity.id
        ]
        ent_events = [e for e in events if entity.id in e.entity_ids]
        scores.append(score_entity(entity, ent_conns, ent_events, graph))

    scores.sort(key=lambda s: s.total_score, reverse=True)
    return scores
