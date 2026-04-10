"""JSON-file watchlist persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config import WATCHLIST_PATH


def _load() -> list[dict]:
    if WATCHLIST_PATH.exists():
        return json.loads(WATCHLIST_PATH.read_text())
    return []


def _save(entries: list[dict]):
    WATCHLIST_PATH.write_text(json.dumps(entries, indent=2, default=str))


def add_entity(name: str, entity_type: str = "unknown") -> dict:
    """Add an entity to the watchlist."""
    entries = _load()

    # Check for duplicates
    for entry in entries:
        if entry["name"].lower() == name.lower():
            return entry  # Already exists

    entry = {
        "name": name,
        "entity_type": entity_type,
        "added": datetime.now().isoformat(),
        "last_checked": None,
        "last_results_hash": None,
    }
    entries.append(entry)
    _save(entries)
    return entry


def remove_entity(name: str) -> bool:
    """Remove an entity from the watchlist. Returns True if found and removed."""
    entries = _load()
    original_count = len(entries)
    entries = [e for e in entries if e["name"].lower() != name.lower()]
    if len(entries) < original_count:
        _save(entries)
        return True
    return False


def list_entities() -> list[dict]:
    """List all watchlisted entities."""
    return _load()


def update_entity(name: str, **kwargs):
    """Update fields on a watchlist entry."""
    entries = _load()
    for entry in entries:
        if entry["name"].lower() == name.lower():
            entry.update(kwargs)
            break
    _save(entries)
