"""Watchlist change detection across OSINT sources."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime

from models import SearchResult
from watchlist.store import list_entities, update_entity


async def scan_watchlist(search_fn) -> list[dict]:
    """Scan all watchlisted entities for changes.

    Args:
        search_fn: async function(query) -> SearchResult

    Returns:
        List of change reports for entities with new findings.
    """
    entries = list_entities()
    if not entries:
        return []

    changes = []

    for entry in entries:
        name = entry["name"]
        old_hash = entry.get("last_results_hash")

        # Run search
        result = await search_fn(name)

        # Compute hash of current results
        result_data = result.model_dump(mode="json", exclude={"metadata"})
        current_hash = hashlib.sha256(
            json.dumps(result_data, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        # Compare
        if old_hash and current_hash != old_hash:
            changes.append({
                "entity": name,
                "change_type": "updated",
                "new_entities": len(result.entities),
                "new_connections": len(result.connections),
                "high_score_entities": [
                    s.entity_name for s in result.scores if s.total_score >= 40
                ],
                "new_flags": list(set(
                    flag for e in result.entities for flag in e.flags
                )),
                "timestamp": datetime.now().isoformat(),
            })
        elif not old_hash:
            changes.append({
                "entity": name,
                "change_type": "initial_scan",
                "new_entities": len(result.entities),
                "new_connections": len(result.connections),
                "timestamp": datetime.now().isoformat(),
            })

        # Update the stored hash
        update_entity(
            name,
            last_checked=datetime.now().isoformat(),
            last_results_hash=current_hash,
        )

    return changes
