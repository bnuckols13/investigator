"""Persistent investigation case management.

Each investigation is a "case" — a directory under ~/investigator/cases/ that
accumulates findings over time. The case holds a growing knowledge graph,
entity roster, timeline, and narrative log. Every search adds to the case
rather than producing a throwaway report.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from config import PROJECT_DIR
from models import Connection, Entity, LeadScore, SearchResult, TimelineEvent

CASES_DIR = PROJECT_DIR / "cases"
CASES_DIR.mkdir(exist_ok=True)


def _slug(name: str) -> str:
    """Convert a case name to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def list_cases() -> list[dict]:
    """List all investigation cases."""
    cases = []
    for d in sorted(CASES_DIR.iterdir()):
        if d.is_dir() and (d / "case.json").exists():
            meta = json.loads((d / "case.json").read_text())
            cases.append(meta)
    return cases


def get_case(case_name: str) -> "Case":
    """Load or create a case by name."""
    slug = _slug(case_name)
    case_dir = CASES_DIR / slug
    return Case(case_dir, case_name)


class Case:
    """A persistent investigation case that accumulates findings."""

    def __init__(self, path: Path, display_name: str):
        self.path = path
        self.path.mkdir(exist_ok=True)
        self.meta_path = path / "case.json"
        self.entities_path = path / "entities.json"
        self.connections_path = path / "connections.json"
        self.events_path = path / "events.json"
        self.scores_path = path / "scores.json"
        self.log_path = path / "investigation_log.md"
        self.graph_path = path / "network.html"

        if self.meta_path.exists():
            self.meta = json.loads(self.meta_path.read_text())
        else:
            self.meta = {
                "name": display_name,
                "slug": path.name,
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
                "searches": [],
                "entity_count": 0,
                "connection_count": 0,
                "flags_found": [],
                "status": "active",
            }
            self._save_meta()

    def _save_meta(self):
        self.meta["updated"] = datetime.now().isoformat()
        self.meta_path.write_text(json.dumps(self.meta, indent=2, default=str))

    def _load_json(self, path: Path) -> list[dict]:
        if path.exists():
            return json.loads(path.read_text())
        return []

    def _save_json(self, path: Path, data: list[dict]):
        path.write_text(json.dumps(data, indent=2, default=str))

    @property
    def entities(self) -> list[dict]:
        return self._load_json(self.entities_path)

    @property
    def connections(self) -> list[dict]:
        return self._load_json(self.connections_path)

    @property
    def events(self) -> list[dict]:
        return self._load_json(self.events_path)

    @property
    def scores(self) -> list[dict]:
        return self._load_json(self.scores_path)

    def ingest_results(self, result: SearchResult) -> dict:
        """Merge new search results into the case, deduplicating against existing data.

        Returns a diff summary: what was added, what was already known.
        """
        existing_entities = self._load_json(self.entities_path)
        existing_connections = self._load_json(self.connections_path)
        existing_events = self._load_json(self.events_path)

        existing_ids = {e["id"] for e in existing_entities}
        existing_conn_keys = {
            (c["source_entity_id"], c["target_entity_id"], c["relation_type"])
            for c in existing_connections
        }

        new_entities = []
        updated_entities = []
        new_connections = []
        new_events = []

        # Merge entities
        for entity in result.entities:
            ed = entity.model_dump(mode="json")
            if entity.id not in existing_ids:
                existing_entities.append(ed)
                new_entities.append(ed)
                existing_ids.add(entity.id)
            else:
                # Merge flags and aliases into existing
                for i, ex in enumerate(existing_entities):
                    if ex["id"] == entity.id:
                        merged_flags = list(set(ex.get("flags", []) + ed.get("flags", [])))
                        merged_aliases = list(set(ex.get("aliases", []) + ed.get("aliases", [])))
                        if merged_flags != ex.get("flags", []) or merged_aliases != ex.get("aliases", []):
                            existing_entities[i]["flags"] = merged_flags
                            existing_entities[i]["aliases"] = merged_aliases
                            updated_entities.append(existing_entities[i])
                        break

        # Merge connections
        for conn in result.connections:
            key = (conn.source_entity_id, conn.target_entity_id, conn.relation_type)
            if key not in existing_conn_keys:
                cd = conn.model_dump(mode="json")
                existing_connections.append(cd)
                new_connections.append(cd)
                existing_conn_keys.add(key)

        # Merge events (deduplicate by date + description similarity)
        existing_event_sigs = {
            (e["date"], e["description"][:50]) for e in existing_events
        }
        for event in result.events:
            sig = (str(event.date), event.description[:50])
            if sig not in existing_event_sigs:
                ed = event.model_dump(mode="json")
                existing_events.append(ed)
                new_events.append(ed)
                existing_event_sigs.add(sig)

        # Save merged data
        self._save_json(self.entities_path, existing_entities)
        self._save_json(self.connections_path, existing_connections)
        self._save_json(self.events_path, sorted(existing_events, key=lambda e: e.get("date", ""), reverse=True))

        # Update scores
        if result.scores:
            self._save_json(self.scores_path, [s.model_dump(mode="json") for s in result.scores])

        # Update metadata
        self.meta["entity_count"] = len(existing_entities)
        self.meta["connection_count"] = len(existing_connections)
        all_flags = set()
        for e in existing_entities:
            all_flags.update(e.get("flags", []))
        self.meta["flags_found"] = sorted(all_flags)
        self.meta["searches"].append({
            "query": result.query,
            "timestamp": datetime.now().isoformat(),
            "new_entities": len(new_entities),
            "new_connections": len(new_connections),
        })
        self._save_meta()

        # Update network graph HTML
        if existing_connections:
            self._update_graph(existing_entities, existing_connections)

        # Append to investigation log
        self._log_search(result, new_entities, new_connections, new_events)

        return {
            "new_entities": new_entities,
            "updated_entities": updated_entities,
            "new_connections": new_connections,
            "new_events": new_events,
            "total_entities": len(existing_entities),
            "total_connections": len(existing_connections),
            "total_events": len(existing_events),
        }

    def _update_graph(self, entities: list[dict], connections: list[dict]):
        """Regenerate the network graph HTML."""
        from analysis.network import build_graph, to_mermaid
        from output.mermaid import to_html

        ent_objects = [Entity(**e) for e in entities]
        conn_objects = [Connection(**c) for c in connections]
        G = build_graph(ent_objects, conn_objects)
        mermaid = to_mermaid(G)
        html = to_html(mermaid)
        self.graph_path.write_text(html)

    def _log_search(self, result: SearchResult, new_ents, new_conns, new_events):
        """Append a search entry to the investigation log."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n---\n### {ts} — Search: \"{result.query}\"\n\n"

        if new_ents:
            entry += f"**{len(new_ents)} new entities discovered:**\n"
            for e in new_ents[:10]:
                flags = f" [{', '.join(e.get('flags', []))}]" if e.get("flags") else ""
                entry += f"- {e['name']} ({e['entity_type']}){flags}\n"
            if len(new_ents) > 10:
                entry += f"- ...and {len(new_ents) - 10} more\n"
            entry += "\n"

        if new_conns:
            entry += f"**{len(new_conns)} new connections:**\n"
            for c in new_conns[:10]:
                entry += f"- {c['source_entity_id']} → {c['target_entity_id']} ({c['relation_type']})\n"
            entry += "\n"

        if new_events:
            entry += f"**{len(new_events)} new timeline events**\n\n"

        if not new_ents and not new_conns and not new_events:
            entry += "No new findings. All entities already known to this case.\n\n"

        # Top scores
        if result.scores:
            top = [s for s in result.scores if s.total_score > 0][:3]
            if top:
                entry += "**Top leads:**\n"
                for s in top:
                    entry += f"- {s.entity_name}: {s.total_score:.0f} ({', '.join(s.flags[:3])})\n"
                entry += "\n"

        with open(self.log_path, "a") as f:
            f.write(entry)

    def get_summary(self) -> str:
        """Generate a current case status summary."""
        entities = self.entities
        connections = self.connections
        events = self.events
        scores = self.scores

        lines = [
            f"# Case: {self.meta['name']}",
            f"*Opened {self.meta['created'][:10]} | Last updated {self.meta['updated'][:16]}*\n",
            f"**{len(entities)}** entities | **{len(connections)}** connections | **{len(events)}** events | **{len(self.meta.get('searches', []))}** searches\n",
        ]

        if self.meta.get("flags_found"):
            lines.append(f"**Flags:** {', '.join(self.meta['flags_found'])}\n")

        # Top scored entities
        if scores:
            scored = sorted(scores, key=lambda s: s.get("total_score", 0), reverse=True)
            top = [s for s in scored if s.get("total_score", 0) > 0][:5]
            if top:
                lines.append("**Priority leads:**")
                for s in top:
                    flags = ", ".join(s.get("flags", [])[:3])
                    lines.append(f"- {s['entity_name']}: score {s['total_score']:.0f} ({flags})")
                lines.append("")

        # Recent searches
        searches = self.meta.get("searches", [])[-5:]
        if searches:
            lines.append("**Recent searches:**")
            for s in reversed(searches):
                lines.append(f"- \"{s['query']}\" ({s['timestamp'][:16]}) — {s.get('new_entities', 0)} new entities")
            lines.append("")

        return "\n".join(lines)

    def get_entity_by_name(self, name: str) -> dict | None:
        """Find an entity in the case by name (fuzzy)."""
        from rapidfuzz import fuzz
        best = None
        best_score = 0
        for e in self.entities:
            score = fuzz.token_set_ratio(name.lower(), e["name"].lower())
            if score > best_score:
                best_score = score
                best = e
        return best if best_score > 70 else None
