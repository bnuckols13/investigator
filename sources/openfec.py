"""OpenFEC source adapter — campaign finance data."""

from __future__ import annotations

from datetime import date

import config
from models import Connection, Entity, EntityType, SourceEnum, TimelineEvent

from .base import BaseSource

BASE_URL = "https://api.open.fec.gov/v1"


class OpenFECSource(BaseSource):
    name = "openfec"
    source_enum = SourceEnum.openfec

    async def search_entity(
        self, query: str, entity_type: str | None = None, limit: int = 25
    ) -> list[Entity]:
        from config import make_httpx_client

        entities = []
        params = {"api_key": config.OPENFEC_API_KEY, "q": query, "per_page": min(limit, 20)}

        async with make_httpx_client() as client:
            # Search candidates
            try:
                resp = await client.get(f"{BASE_URL}/candidates/search/", params=params)
                resp.raise_for_status()
                data = resp.json()
                for cand in data.get("results", []):
                    entities.append(Entity(
                        id=f"fec:{cand.get('candidate_id', '')}",
                        source=SourceEnum.openfec,
                        name=cand.get("name", "Unknown"),
                        entity_type=EntityType.person,
                        countries=["us"],
                        properties={
                            "candidate_id": [cand.get("candidate_id", "")],
                            "party": [cand.get("party", "")],
                            "office": [cand.get("office_full", "")],
                            "state": [cand.get("state", "")],
                            "district": [cand.get("district", "")] if cand.get("district") else [],
                            "cycles": [str(c) for c in cand.get("cycles", [])],
                            "incumbent_challenge": [cand.get("incumbent_challenge_full", "")],
                        },
                        source_url=f"https://www.fec.gov/data/candidate/{cand.get('candidate_id', '')}/",
                        flags=["political_candidate"],
                    ))
            except Exception:
                pass

            # Search committees
            try:
                resp = await client.get(f"{BASE_URL}/committees/", params=params)
                resp.raise_for_status()
                data = resp.json()
                for comm in data.get("results", []):
                    entities.append(Entity(
                        id=f"fec:{comm.get('committee_id', '')}",
                        source=SourceEnum.openfec,
                        name=comm.get("name", "Unknown"),
                        entity_type=EntityType.organization,
                        countries=["us"],
                        properties={
                            "committee_id": [comm.get("committee_id", "")],
                            "committee_type": [comm.get("committee_type_full", "")],
                            "designation": [comm.get("designation_full", "")],
                            "party": [comm.get("party_full", "")],
                            "treasurer_name": [comm.get("treasurer_name", "")] if comm.get("treasurer_name") else [],
                        },
                        source_url=f"https://www.fec.gov/data/committee/{comm.get('committee_id', '')}/",
                        flags=["political_committee"],
                    ))
            except Exception:
                pass

        return entities[:limit]

    async def get_entity(self, entity_id: str) -> Entity | None:
        raw_id = entity_id.replace("fec:", "")
        from config import make_httpx_client

        async with make_httpx_client() as client:
            params = {"api_key": config.OPENFEC_API_KEY}
            try:
                # Try candidate endpoint
                resp = await client.get(f"{BASE_URL}/candidate/{raw_id}/", params=params)
                if resp.status_code == 200:
                    data = resp.json().get("results", [{}])[0]
                    return Entity(
                        id=entity_id,
                        source=SourceEnum.openfec,
                        name=data.get("name", "Unknown"),
                        entity_type=EntityType.person,
                        countries=["us"],
                        properties={"candidate_id": [raw_id]},
                        source_url=f"https://www.fec.gov/data/candidate/{raw_id}/",
                    )
            except Exception:
                pass
            try:
                # Try committee endpoint
                resp = await client.get(f"{BASE_URL}/committee/{raw_id}/", params=params)
                if resp.status_code == 200:
                    data = resp.json().get("results", [{}])[0]
                    return Entity(
                        id=entity_id,
                        source=SourceEnum.openfec,
                        name=data.get("name", "Unknown"),
                        entity_type=EntityType.organization,
                        countries=["us"],
                        source_url=f"https://www.fec.gov/data/committee/{raw_id}/",
                    )
            except Exception:
                pass
        return None

    async def get_connections(self, entity_id: str) -> list[Connection]:
        """Get contribution connections for a candidate/committee."""
        raw_id = entity_id.replace("fec:", "")
        from config import make_httpx_client

        connections = []
        async with make_httpx_client() as client:
            params = {
                "api_key": config.OPENFEC_API_KEY,
                "per_page": 20,
                "sort": "-contribution_receipt_amount",
            }

            try:
                # Get top contributors
                resp = await client.get(
                    f"{BASE_URL}/schedules/schedule_a/",
                    params={**params, "committee_id": raw_id},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for contrib in data.get("results", []):
                        contributor_name = contrib.get("contributor_name", "")
                        amount = contrib.get("contribution_receipt_amount", 0)
                        if contributor_name and amount:
                            connections.append(Connection(
                                source_entity_id=f"fec:contributor:{contributor_name}",
                                target_entity_id=entity_id,
                                relation_type="contribution",
                                label=f"${amount:,.0f}",
                                weight=amount,
                                properties={
                                    "contributor_employer": contrib.get("contributor_employer", ""),
                                    "contributor_occupation": contrib.get("contributor_occupation", ""),
                                    "receipt_date": contrib.get("contribution_receipt_date", ""),
                                },
                                source=SourceEnum.openfec,
                            ))
            except Exception:
                pass

        return connections

    async def get_events(self, entity_id: str) -> list[TimelineEvent]:
        raw_id = entity_id.replace("fec:", "")
        from config import make_httpx_client

        events = []
        async with make_httpx_client() as client:
            params = {"api_key": config.OPENFEC_API_KEY, "per_page": 20, "committee_id": raw_id}
            try:
                resp = await client.get(f"{BASE_URL}/filings/", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    for filing in data.get("results", []):
                        receipt_date = filing.get("receipt_date")
                        if receipt_date:
                            try:
                                dt = date.fromisoformat(receipt_date[:10])
                                events.append(TimelineEvent(
                                    date=dt,
                                    event_type="filing",
                                    description=f"FEC {filing.get('form_type', 'filing')}: {filing.get('document_description', '')}",
                                    entity_ids=[entity_id],
                                    source=SourceEnum.openfec,
                                    amount=filing.get("total_receipts"),
                                ))
                            except (ValueError, TypeError):
                                pass
            except Exception:
                pass
        return events

    async def health_check(self) -> bool:
        from config import make_httpx_client
        async with make_httpx_client() as client:
            try:
                resp = await client.get(f"{BASE_URL}/", params={"api_key": config.OPENFEC_API_KEY})
                return resp.status_code == 200
            except Exception:
                return False
