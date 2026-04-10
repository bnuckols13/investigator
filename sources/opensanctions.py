"""OpenSanctions source adapter — sanctions, PEPs, and crime databases from 100+ sources."""

from __future__ import annotations

from datetime import date

import config
from models import Connection, Entity, EntityMatch, EntityType, SourceEnum, TimelineEvent

from .base import BaseSource

BASE_URL = "https://api.opensanctions.org"

_SCHEMA_MAP = {
    "Person": EntityType.person,
    "Company": EntityType.company,
    "Organization": EntityType.organization,
    "LegalEntity": EntityType.company,
    "Vessel": EntityType.vessel,
}

_TOPIC_FLAGS = {
    "sanction": "sanctioned",
    "role.pep": "pep",
    "crime": "criminal",
    "role.oligarch": "oligarch",
    "role.spy": "intelligence",
    "poi": "person_of_interest",
    "debarment": "debarred",
}


def _headers():
    return {"Authorization": f"ApiKey {config.OPENSANCTIONS_API_KEY}"}


def _result_to_entity(item: dict) -> Entity:
    """Convert an OpenSanctions search result to our Entity model."""
    props = item.get("properties", {})
    schema = item.get("schema", "Thing")
    entity_id = item.get("id", "")

    # Extract flags from topics and datasets
    flags = []
    for topic in item.get("topics", []):
        if topic in _TOPIC_FLAGS:
            flags.append(_TOPIC_FLAGS[topic])

    datasets = item.get("datasets", [])
    if any("ofac" in d for d in datasets):
        flags.append("ofac")
    if any("eu_fsf" in d or "eu_sanctions" in d for d in datasets):
        flags.append("eu_sanctioned")

    return Entity(
        id=f"opensanctions:{entity_id}",
        source=SourceEnum.opensanctions,
        name=item.get("caption", props.get("name", ["Unknown"])[0] if props.get("name") else "Unknown"),
        entity_type=_SCHEMA_MAP.get(schema, EntityType.unknown),
        aliases=props.get("alias", []),
        countries=props.get("country", []),
        properties=props,
        source_url=f"https://www.opensanctions.org/entities/{entity_id}/",
        flags=list(set(flags)),
        raw=item,
    )


class OpenSanctionsSource(BaseSource):
    name = "opensanctions"
    source_enum = SourceEnum.opensanctions

    async def search_entity(
        self, query: str, entity_type: str | None = None, limit: int = 25
    ) -> list[Entity]:
        from config import make_httpx_client

        params = {"q": query, "limit": min(limit, 50)}
        if entity_type:
            schema_map = {"person": "Person", "company": "Company", "organization": "Organization"}
            if entity_type in schema_map:
                params["schema"] = schema_map[entity_type]

        async with make_httpx_client() as client:
            resp = await client.get(
                f"{BASE_URL}/search/default",
                params=params,
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        return [_result_to_entity(r) for r in data.get("results", [])]

    async def match_entity(self, entity: Entity) -> list[EntityMatch]:
        """Precise entity matching using structured query."""
        from config import make_httpx_client

        # Build match query from entity properties
        query_props: dict = {"name": [entity.name]}
        if entity.aliases:
            query_props["name"].extend(entity.aliases[:3])
        if entity.countries:
            query_props["country"] = entity.countries[:3]

        # Add birth date if available
        birth_dates = entity.properties.get("birthDate", [])
        if birth_dates:
            query_props["birthDate"] = birth_dates[:1]

        schema_map = {
            EntityType.person: "Person",
            EntityType.company: "Company",
            EntityType.organization: "Organization",
        }

        body = {
            "schema": schema_map.get(entity.entity_type, "Thing"),
            "properties": query_props,
        }

        async with make_httpx_client() as client:
            resp = await client.post(
                f"{BASE_URL}/match/default",
                json=body,
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        matches = []
        for r in data.get("responses", {}).get("results", data.get("results", [])):
            matched_entity = _result_to_entity(r)
            score = r.get("score", 0)
            matches.append(EntityMatch(
                entity=matched_entity,
                score=min(score * 100, 100),
                match_method="structured_match",
            ))
        return matches

    async def get_entity(self, entity_id: str) -> Entity | None:
        raw_id = entity_id.replace("opensanctions:", "")
        from config import make_httpx_client

        async with make_httpx_client() as client:
            try:
                resp = await client.get(
                    f"{BASE_URL}/entities/{raw_id}",
                    headers=_headers(),
                )
                resp.raise_for_status()
                return _result_to_entity(resp.json())
            except Exception:
                return None

    async def get_connections(self, entity_id: str) -> list[Connection]:
        """OpenSanctions entities can reference related entities in properties."""
        entity = await self.get_entity(entity_id)
        if not entity:
            return []

        connections = []
        props = entity.properties

        # Check for relationship properties
        rel_fields = {
            "ownershipOwner": "ownership",
            "ownershipAsset": "ownership",
            "directorshipDirector": "directorship",
            "directorshipOrganization": "directorship",
            "associates": "association",
            "relatives": "association",
        }
        for field, rel_type in rel_fields.items():
            for target_id in props.get(field, []):
                connections.append(Connection(
                    source_entity_id=entity_id,
                    target_entity_id=f"opensanctions:{target_id}",
                    relation_type=rel_type,
                    label=field,
                    source=SourceEnum.opensanctions,
                ))
        return connections

    async def get_events(self, entity_id: str) -> list[TimelineEvent]:
        entity = await self.get_entity(entity_id)
        if not entity:
            return []

        events = []
        date_fields = {
            "createdAt": "listed",
            "modifiedAt": "updated",
            "startDate": "start",
            "endDate": "end",
        }
        for field, event_type in date_fields.items():
            for val in entity.properties.get(field, []):
                try:
                    dt = date.fromisoformat(val[:10])
                    events.append(TimelineEvent(
                        date=dt,
                        event_type=event_type,
                        description=f"{entity.name}: {event_type} on sanctions/PEP list",
                        entity_ids=[entity_id],
                        source=SourceEnum.opensanctions,
                        source_url=entity.source_url,
                    ))
                except (ValueError, TypeError):
                    pass
        return events

    async def health_check(self) -> bool:
        from config import make_httpx_client
        async with make_httpx_client() as client:
            try:
                resp = await client.get(f"{BASE_URL}/", headers=_headers())
                return resp.status_code == 200
            except Exception:
                return False
