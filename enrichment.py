"""Auto-enrichment pipeline — automatically deepen findings without being asked.

When a search surfaces high-priority entities, this module triggers
follow-up searches to map their full network, check for government
contracts, cross-reference sanctions, and find connected entities
that haven't been investigated yet.
"""

from __future__ import annotations

import asyncio
from typing import Any

from models import Entity, SearchResult


async def auto_enrich(
    result: SearchResult,
    search_fn,
    threshold: float = 30.0,
    max_followups: int = 5,
) -> list[SearchResult]:
    """Automatically deepen findings for high-priority entities.

    Args:
        result: Initial search results
        search_fn: async function(query, entity_type, source_filter, limit) -> SearchResult
        threshold: Minimum lead score to trigger enrichment
        max_followups: Maximum number of follow-up searches

    Returns:
        List of additional SearchResults from follow-up queries
    """
    followup_results = []
    followup_queries = set()

    # Identify high-priority entities
    high_priority = [s for s in result.scores if s.total_score >= threshold]

    if not high_priority:
        return followup_results

    for score in high_priority[:max_followups]:
        entity = next((e for e in result.entities if e.id == score.entity_id), None)
        if not entity:
            continue

        # Strategy 1: Search connected entity names we haven't investigated
        for conn in result.connections:
            connected_id = None
            if conn.source_entity_id == entity.id:
                connected_id = conn.target_entity_id
            elif conn.target_entity_id == entity.id:
                connected_id = conn.source_entity_id

            if connected_id:
                # Extract name from the connected entity
                connected_entity = next(
                    (e for e in result.entities if e.id == connected_id), None
                )
                if connected_entity and connected_entity.name not in followup_queries:
                    followup_queries.add(connected_entity.name)

        # Strategy 2: If entity is sanctioned, check for US contracts
        if any(f in entity.flags for f in ("sanctioned", "ofac", "pep")):
            if entity.name not in followup_queries:
                followup_queries.add(entity.name)

        # Strategy 3: Search aliases we haven't tried
        for alias in entity.aliases[:2]:
            if alias not in followup_queries and alias != entity.name:
                followup_queries.add(alias)

    # Execute follow-up searches (limit to max_followups)
    queries = list(followup_queries)[:max_followups]
    if queries:
        tasks = [search_fn(q, limit=10) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for query, res in zip(queries, results):
            if isinstance(res, Exception):
                continue
            if res.entities:
                followup_results.append(res)

    return followup_results


def suggest_next_moves(result: SearchResult) -> list[dict]:
    """Generate specific investigative next-move suggestions based on findings.

    Returns actionable suggestions with rationale.
    """
    suggestions = []

    # Analyze what we found
    sanctioned = [e for e in result.entities if any(f in e.flags for f in ("sanctioned", "ofac", "pep"))]
    contractors = [e for e in result.entities if "govt_contractor" in e.flags]
    litigated = [e for e in result.entities if "litigated" in e.flags]
    multi_jurisdiction = [e for e in result.entities if len(e.countries) > 2]

    # Pattern: Sanctioned entity with corporate connections
    if sanctioned:
        for entity in sanctioned[:3]:
            connected_companies = [
                c for c in result.connections
                if (c.source_entity_id == entity.id or c.target_entity_id == entity.id)
                and c.relation_type in ("ownership", "directorship")
            ]
            if connected_companies:
                suggestions.append({
                    "type": "sanctions_corporate_nexus",
                    "priority": "high",
                    "action": f"Trace the full ownership chain of companies connected to {entity.name}",
                    "rationale": f"{entity.name} appears on sanctions/PEP lists but has {len(connected_companies)} corporate connections worth mapping",
                    "search": [c.target_entity_id.split(":")[-1] for c in connected_companies[:3]],
                })

    # Pattern: Government contractor with court cases
    contractor_litigants = set(e.name for e in contractors) & set(e.name for e in litigated)
    if contractor_litigants:
        for name in list(contractor_litigants)[:2]:
            suggestions.append({
                "type": "contractor_litigation",
                "priority": "high",
                "action": f"Pull court filings for {name} and cross-reference with contract award dates",
                "rationale": f"{name} holds government contracts AND has federal court cases, a pattern worth investigating for fraud or compliance violations",
                "foia": f"FOIA the contracting officer's conflict-of-interest disclosures at the awarding agency",
            })

    # Pattern: Multi-jurisdiction entities
    if multi_jurisdiction:
        for entity in multi_jurisdiction[:2]:
            suggestions.append({
                "type": "jurisdiction_complexity",
                "priority": "medium",
                "action": f"Search corporate registries in {', '.join(entity.countries)} for {entity.name}",
                "rationale": f"{entity.name} operates across {len(entity.countries)} jurisdictions, raising beneficial ownership questions",
            })

    # Pattern: Campaign finance connections
    donors = [e for e in result.entities if "political_donor" in e.flags or "political_candidate" in e.flags]
    if donors and contractors:
        suggestions.append({
            "type": "pay_to_play",
            "priority": "high",
            "action": "Cross-reference campaign donors against government contract recipients",
            "rationale": f"Found {len(donors)} political entities and {len(contractors)} contractors in the same network. Check for pay-to-play patterns.",
        })

    # Pattern: Entity appears in Aleph leaks
    aleph_entities = [e for e in result.entities if e.source.value == "aleph"]
    if aleph_entities:
        for entity in aleph_entities[:2]:
            suggestions.append({
                "type": "leaked_documents",
                "priority": "medium",
                "action": f"Search Aleph for documents mentioning {entity.name} — look for emails, contracts, and financial records",
                "rationale": f"{entity.name} appears in OCCRP's database, which includes leaked documents and corporate registries",
            })

    # Always suggest: Look for what's missing
    all_sources = {e.source.value for e in result.entities}
    missing_sources = {"aleph", "opensanctions", "sec_edgar", "openfec", "usaspending", "courtlistener"} - all_sources
    if missing_sources:
        suggestions.append({
            "type": "coverage_gap",
            "priority": "low",
            "action": f"Enable additional sources: {', '.join(missing_sources)}",
            "rationale": "More sources mean more cross-referencing power. Each new source can reveal connections invisible to the others.",
        })

    return suggestions
