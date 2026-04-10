"""CourtListener source adapter — federal court records and dockets."""

from __future__ import annotations

from datetime import date

import config
from models import Connection, Entity, EntityType, SourceEnum, TimelineEvent

from .base import BaseSource

BASE_URL = "https://www.courtlistener.com/api/rest/v4"


def _headers():
    return {
        "Authorization": f"Token {config.COURTLISTENER_TOKEN}",
        "Content-Type": "application/json",
    }


class CourtListenerSource(BaseSource):
    name = "courtlistener"
    source_enum = SourceEnum.courtlistener

    async def search_entity(
        self, query: str, entity_type: str | None = None, limit: int = 25
    ) -> list[Entity]:
        from config import make_httpx_client

        entities = []

        async with make_httpx_client() as client:
            # Search RECAP dockets
            try:
                resp = await client.get(
                    f"{BASE_URL}/search/",
                    params={"q": query, "type": "r", "page_size": min(limit, 20)},
                    headers=_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                for result in data.get("results", []):
                    case_name = result.get("caseName", result.get("case_name", ""))
                    docket_id = result.get("docket_id", "")
                    court = result.get("court", "")
                    date_filed = result.get("dateFiled", result.get("date_filed", ""))

                    if case_name:
                        # Extract party names from case name
                        parties = case_name.split(" v. ") if " v. " in case_name else [case_name]

                        entities.append(Entity(
                            id=f"court:{docket_id}",
                            source=SourceEnum.courtlistener,
                            name=case_name,
                            entity_type=EntityType.unknown,
                            countries=["us"],
                            properties={
                                "docket_id": [str(docket_id)],
                                "court": [court],
                                "date_filed": [date_filed],
                                "parties": parties,
                                "docket_number": [result.get("docketNumber", result.get("docket_number", ""))],
                            },
                            source_url=f"https://www.courtlistener.com/docket/{docket_id}/",
                            flags=["litigated"],
                        ))
            except Exception:
                pass

            # Search opinions
            try:
                resp = await client.get(
                    f"{BASE_URL}/search/",
                    params={"q": query, "type": "o", "page_size": min(limit, 10)},
                    headers=_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                for result in data.get("results", []):
                    case_name = result.get("caseName", result.get("case_name", ""))
                    cluster_id = result.get("cluster_id", "")

                    if case_name and f"court:{cluster_id}" not in [e.id for e in entities]:
                        entities.append(Entity(
                            id=f"court:opinion:{cluster_id}",
                            source=SourceEnum.courtlistener,
                            name=case_name,
                            entity_type=EntityType.unknown,
                            countries=["us"],
                            properties={
                                "court": [result.get("court", "")],
                                "date_filed": [result.get("dateFiled", "")],
                                "citation": [result.get("citation", [""])[0]] if result.get("citation") else [],
                            },
                            source_url=f"https://www.courtlistener.com/opinion/{cluster_id}/",
                            flags=["litigated"],
                        ))
            except Exception:
                pass

        return entities[:limit]

    async def get_entity(self, entity_id: str) -> Entity | None:
        raw_id = entity_id.replace("court:opinion:", "").replace("court:", "")
        from config import make_httpx_client

        async with make_httpx_client() as client:
            try:
                resp = await client.get(
                    f"{BASE_URL}/dockets/{raw_id}/",
                    headers=_headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return Entity(
                        id=entity_id,
                        source=SourceEnum.courtlistener,
                        name=data.get("case_name", "Unknown"),
                        entity_type=EntityType.unknown,
                        countries=["us"],
                        properties={
                            "court": [data.get("court", "")],
                            "docket_number": [data.get("docket_number", "")],
                            "date_filed": [data.get("date_filed", "")],
                            "date_terminated": [data.get("date_terminated", "")] if data.get("date_terminated") else [],
                            "cause": [data.get("cause", "")] if data.get("cause") else [],
                            "nature_of_suit": [data.get("nature_of_suit", "")] if data.get("nature_of_suit") else [],
                        },
                        source_url=f"https://www.courtlistener.com/docket/{raw_id}/",
                        flags=["litigated"],
                    )
            except Exception:
                pass
        return None

    async def get_connections(self, entity_id: str) -> list[Connection]:
        """Extract party relationships from case names."""
        entity = await self.get_entity(entity_id)
        if not entity:
            return []

        connections = []
        parties = entity.properties.get("parties", [])
        if len(parties) >= 2:
            connections.append(Connection(
                source_entity_id=f"court:party:{parties[0].strip()}",
                target_entity_id=f"court:party:{parties[1].strip()}",
                relation_type="litigation",
                label=entity.name,
                source=SourceEnum.courtlistener,
            ))
        return connections

    async def get_events(self, entity_id: str) -> list[TimelineEvent]:
        entity = await self.get_entity(entity_id)
        if not entity:
            return []

        events = []
        date_filed = entity.properties.get("date_filed", [""])[0]
        if date_filed:
            try:
                dt = date.fromisoformat(date_filed[:10])
                events.append(TimelineEvent(
                    date=dt,
                    event_type="case",
                    description=f"Case filed: {entity.name}",
                    entity_ids=[entity_id],
                    source=SourceEnum.courtlistener,
                    source_url=entity.source_url,
                ))
            except (ValueError, TypeError):
                pass

        date_terminated = entity.properties.get("date_terminated", [""])[0]
        if date_terminated:
            try:
                dt = date.fromisoformat(date_terminated[:10])
                events.append(TimelineEvent(
                    date=dt,
                    event_type="case",
                    description=f"Case terminated: {entity.name}",
                    entity_ids=[entity_id],
                    source=SourceEnum.courtlistener,
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
