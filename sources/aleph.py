"""OCCRP Aleph source adapter — 3B+ records of corporate, leak, and public data."""

from __future__ import annotations

import asyncio
from datetime import datetime

import config
from models import Connection, Entity, EntityType, SourceEnum, TimelineEvent

from .base import BaseSource

# Map our entity types to FollowTheMoney schema names
_FTM_SCHEMA_MAP = {
    "person": "Person",
    "company": "Company",
    "organization": "Organization",
    None: "Thing",
}

# Map FtM schemas back to our types
_REVERSE_SCHEMA = {
    "Person": EntityType.person,
    "Company": EntityType.company,
    "Organization": EntityType.organization,
    "LegalEntity": EntityType.company,
    "PublicBody": EntityType.organization,
    "Vessel": EntityType.vessel,
}

# FtM relationship schemas and their mapping
_RELATION_SCHEMAS = {
    "Ownership": "ownership",
    "Directorship": "directorship",
    "Membership": "employment",
    "Employment": "employment",
    "Representation": "employment",
    "UnknownLink": "association",
}


def _get_api():
    """Lazy-load AlephAPI to avoid import cost when source is disabled."""
    from alephclient.api import AlephAPI
    return AlephAPI(host=config.ALEPH_HOST, api_key=config.ALEPH_API_KEY)


def _ftm_to_entity(raw: dict) -> Entity:
    """Convert a FollowTheMoney entity dict to our Entity model."""
    props = raw.get("properties", {})
    schema = raw.get("schema", "Thing")

    # Extract name — FtM stores names as arrays
    names = props.get("name", [])
    name = names[0] if names else raw.get("caption", "Unknown")

    # Build source URL
    entity_id = raw.get("id", "")
    source_url = f"{config.ALEPH_HOST}/entities/{entity_id}" if entity_id else None

    # Parse last_seen
    last_seen = None
    updated = raw.get("updated_at") or raw.get("created_at")
    if updated:
        try:
            last_seen = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    return Entity(
        id=f"aleph:{entity_id}",
        source=SourceEnum.aleph,
        name=name,
        entity_type=_REVERSE_SCHEMA.get(schema, EntityType.unknown),
        aliases=props.get("alias", []),
        countries=props.get("country", []),
        properties=props,
        source_url=source_url,
        last_seen=last_seen,
        flags=_extract_flags(props, schema),
        raw=raw,
    )


def _extract_flags(props: dict, schema: str) -> list[str]:
    """Extract investigative flags from entity properties."""
    flags = []
    if schema == "Sanction":
        flags.append("sanctioned")
    topics = props.get("topics", [])
    if "role.pep" in topics:
        flags.append("pep")
    if "sanction" in topics:
        flags.append("sanctioned")
    if "crime" in topics:
        flags.append("criminal")
    return flags


class AlephSource(BaseSource):
    name = "aleph"
    source_enum = SourceEnum.aleph

    async def search_entity(
        self, query: str, entity_type: str | None = None, limit: int = 25
    ) -> list[Entity]:
        schema = _FTM_SCHEMA_MAP.get(entity_type, _FTM_SCHEMA_MAP[None])

        def _search():
            api = _get_api()
            results = []
            params = {"q": query}
            if schema != "Thing":
                params["filter:schemata"] = schema
            try:
                for item in api.search_entities(query, schema=schema if schema != "Thing" else None):
                    results.append(_ftm_to_entity(item))
                    if len(results) >= limit:
                        break
            except Exception:
                # Fall back to basic search if schema filtering fails
                for item in api.search_entities(query):
                    results.append(_ftm_to_entity(item))
                    if len(results) >= limit:
                        break
            return results

        return await asyncio.to_thread(_search)

    async def get_entity(self, entity_id: str) -> Entity | None:
        # Strip our prefix
        raw_id = entity_id.replace("aleph:", "")

        def _get():
            api = _get_api()
            try:
                raw = api.get_entity(raw_id)
                return _ftm_to_entity(raw) if raw else None
            except Exception:
                return None

        return await asyncio.to_thread(_get)

    async def get_connections(self, entity_id: str) -> list[Connection]:
        raw_id = entity_id.replace("aleph:", "")

        def _get_connections():
            api = _get_api()
            connections = []
            try:
                # Get entity and inspect its properties for relationships
                entity = api.get_entity(raw_id)
                if not entity:
                    return connections

                schema = entity.get("schema", "")
                props = entity.get("properties", {})

                # For relationship schemas (Ownership, Directorship, etc.)
                if schema in _RELATION_SCHEMAS:
                    rel_type = _RELATION_SCHEMAS[schema]
                    # These entities link two other entities
                    owners = props.get("owner", [])
                    assets = props.get("asset", [])
                    directors = props.get("director", [])
                    organizations = props.get("organization", [])
                    members = props.get("member", [])

                    for src_list, tgt_list in [
                        (owners, assets),
                        (directors, organizations),
                        (members, organizations),
                    ]:
                        for s in src_list:
                            for t in tgt_list:
                                share = props.get("percentage", [None])[0] if props.get("percentage") else None
                                connections.append(Connection(
                                    source_entity_id=f"aleph:{s}",
                                    target_entity_id=f"aleph:{t}",
                                    relation_type=rel_type,
                                    label=schema,
                                    weight=float(share) if share else None,
                                    source=SourceEnum.aleph,
                                ))
            except Exception:
                pass
            return connections

        return await asyncio.to_thread(_get_connections)

    async def get_events(self, entity_id: str) -> list[TimelineEvent]:
        raw_id = entity_id.replace("aleph:", "")

        def _get_events():
            api = _get_api()
            events = []
            try:
                entity = api.get_entity(raw_id)
                if not entity:
                    return events

                props = entity.get("properties", {})
                name = (props.get("name", ["Unknown"]) or ["Unknown"])[0]

                date_fields = {
                    "incorporationDate": "incorporation",
                    "dissolutionDate": "dissolution",
                    "startDate": "start",
                    "endDate": "end",
                    "date": "event",
                    "modifiedAt": "modified",
                    "createdAt": "created",
                }
                for field, event_type in date_fields.items():
                    for val in props.get(field, []):
                        try:
                            from datetime import date as d
                            dt = d.fromisoformat(val[:10])
                            events.append(TimelineEvent(
                                date=dt,
                                event_type=event_type,
                                description=f"{name}: {event_type} ({field})",
                                entity_ids=[entity_id],
                                source=SourceEnum.aleph,
                            ))
                        except (ValueError, TypeError):
                            pass
            except Exception:
                pass
            return events

        return await asyncio.to_thread(_get_events)

    async def health_check(self) -> bool:
        def _check():
            try:
                api = _get_api()
                # Simple search to verify connectivity
                for _ in api.search_entities("test"):
                    return True
                return True
            except Exception:
                return False
        return await asyncio.to_thread(_check)
