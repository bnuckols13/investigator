"""Cross-source entity resolution using fuzzy matching."""

from __future__ import annotations

from rapidfuzz import fuzz

from models import Entity, EntityMatch


def compute_similarity(a: Entity, b: Entity) -> float:
    """Compute weighted similarity between two entities (0-100)."""
    # Name similarity (50% weight) — use token_sort_ratio to handle name reordering
    name_score = fuzz.token_sort_ratio(a.name.lower(), b.name.lower())
    # Also check token_set_ratio for partial name matches
    name_set_score = fuzz.token_set_ratio(a.name.lower(), b.name.lower())
    name_sim = max(name_score, name_set_score)

    # Country overlap (20% weight)
    country_sim = 0.0
    if a.countries and b.countries:
        overlap = len(set(a.countries) & set(b.countries))
        total = max(len(set(a.countries) | set(b.countries)), 1)
        country_sim = (overlap / total) * 100
    elif not a.countries and not b.countries:
        country_sim = 50  # Neutral when both unknown

    # Entity type match (20% weight)
    if a.entity_type == b.entity_type:
        type_sim = 100.0
    elif a.entity_type.value == "unknown" or b.entity_type.value == "unknown":
        type_sim = 50.0
    else:
        type_sim = 0.0

    # Alias cross-match (10% weight)
    alias_sim = 0.0
    a_all_names = {a.name.lower()} | {al.lower() for al in a.aliases}
    b_all_names = {b.name.lower()} | {al.lower() for al in b.aliases}
    # Check if any name from A matches any name from B
    for a_name in a_all_names:
        for b_name in b_all_names:
            if fuzz.token_sort_ratio(a_name, b_name) > 85:
                alias_sim = 100.0
                break
        if alias_sim > 0:
            break

    return (name_sim * 0.5) + (country_sim * 0.2) + (type_sim * 0.2) + (alias_sim * 0.1)


def resolve_entities(
    entities: list[Entity], threshold: float = 75.0
) -> list[list[EntityMatch]]:
    """Cluster entities that likely refer to the same real-world entity.

    Returns groups of EntityMatch objects, where each group represents
    one deduplicated entity with matches from different sources.
    """
    if not entities:
        return []

    # Sort by name for windowed comparison
    sorted_ents = sorted(entities, key=lambda e: e.name.lower())
    n = len(sorted_ents)

    # Union-Find for clustering
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Compare within a sliding window (O(n * window) instead of O(n^2))
    window = min(50, n)
    scores: dict[tuple[int, int], float] = {}

    for i in range(n):
        for j in range(i + 1, min(i + window, n)):
            # Skip if same source — we want cross-source matches
            if sorted_ents[i].source == sorted_ents[j].source:
                # Still compute for within-source dedup
                pass
            score = compute_similarity(sorted_ents[i], sorted_ents[j])
            if score >= threshold:
                union(i, j)
                scores[(i, j)] = score

    # Build clusters
    clusters: dict[int, list[tuple[int, float]]] = {}
    for i in range(n):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        # Find the best score this entity got matched with
        best_score = 100.0 if i == root else 0.0
        for (a, b), s in scores.items():
            if a == i or b == i:
                best_score = max(best_score, s)
        clusters[root].append((i, best_score))

    # Convert to EntityMatch groups
    result = []
    for members in clusters.values():
        group = []
        for idx, score in members:
            group.append(EntityMatch(
                entity=sorted_ents[idx],
                score=score,
                match_method="fuzzy" if score < 100 else "exact",
            ))
        # Sort by score descending within group
        group.sort(key=lambda m: m.score, reverse=True)
        result.append(group)

    # Sort groups by best score in group
    result.sort(key=lambda g: g[0].score, reverse=True)
    return result


def deduplicate(entities: list[Entity]) -> list[Entity]:
    """Return one canonical entity per cluster.

    Priority: aleph > opensanctions > sec_edgar > openfec > usaspending > courtlistener
    """
    source_priority = {
        "aleph": 0,
        "opensanctions": 1,
        "sec_edgar": 2,
        "openfec": 3,
        "usaspending": 4,
        "courtlistener": 5,
    }

    groups = resolve_entities(entities)
    canonical = []
    for group in groups:
        # Pick the entity from the highest-priority source
        best = min(group, key=lambda m: source_priority.get(m.entity.source.value, 99))
        # Merge flags from all matches
        all_flags = set()
        all_aliases = set()
        all_countries = set()
        for m in group:
            all_flags.update(m.entity.flags)
            all_aliases.update(m.entity.aliases)
            all_countries.update(m.entity.countries)

        merged = best.entity.model_copy()
        merged.flags = list(all_flags)
        merged.aliases = list(all_aliases - {merged.name})
        merged.countries = list(all_countries)
        canonical.append(merged)

    return canonical
