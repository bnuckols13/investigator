"""USASpending source adapter — federal contracts, grants, and awards."""

from __future__ import annotations

from datetime import date

from models import Connection, Entity, EntityType, SourceEnum, TimelineEvent

from .base import BaseSource

BASE_URL = "https://api.usaspending.gov/api/v2"


class USASpendingSource(BaseSource):
    name = "usaspending"
    source_enum = SourceEnum.usaspending

    async def search_entity(
        self, query: str, entity_type: str | None = None, limit: int = 25
    ) -> list[Entity]:
        from config import make_httpx_client

        entities = []

        async with make_httpx_client() as client:
            # First try recipient autocomplete for name matching
            try:
                resp = await client.post(
                    f"{BASE_URL}/autocomplete/recipient/",
                    json={"search_text": query, "limit": min(limit, 10)},
                )
                if resp.status_code == 200:
                    for item in resp.json().get("results", []):
                        name = item.get("recipient_name", "") if isinstance(item, dict) else str(item)
                        if name:
                            entities.append(Entity(
                                id=f"usaspending:recipient:{name}",
                                source=SourceEnum.usaspending,
                                name=name,
                                entity_type=EntityType.company,
                                countries=["us"],
                                source_url=f"https://www.usaspending.gov/search",
                                flags=["govt_contractor"],
                            ))
            except Exception:
                pass

            # Then search awards for more detail
            try:
                resp = await client.post(
                    f"{BASE_URL}/search/spending_by_award/",
                    json={
                        "filters": {
                            "recipient_search_text": [query],
                            "award_type_codes": ["A", "B", "C", "D"],
                        },
                        "fields": [
                            "Award ID", "Recipient Name", "Award Amount",
                            "Awarding Agency", "Start Date", "End Date",
                            "Award Type", "Description",
                            "recipient_id", "generated_internal_id",
                        ],
                        "limit": min(limit, 25),
                        "page": 1,
                        "sort": "Award Amount",
                        "order": "desc",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                # Track unique recipients
                seen_recipients = set()
                for result in data.get("results", []):
                    recip_name = result.get("Recipient Name", "")
                    if not recip_name or recip_name in seen_recipients:
                        continue
                    seen_recipients.add(recip_name)

                    award_amount = result.get("Award Amount", 0)
                    entities.append(Entity(
                        id=f"usaspending:{result.get('recipient_id', result.get('generated_internal_id', recip_name))}",
                        source=SourceEnum.usaspending,
                        name=recip_name,
                        entity_type=EntityType.company,
                        countries=["us"],
                        properties={
                            "award_amount": [str(award_amount)],
                            "awarding_agency": [result.get("Awarding Agency", "")],
                            "award_type": [result.get("Award Type", "")],
                            "description": [result.get("Description", "")],
                        },
                        source_url="https://www.usaspending.gov/search",
                        flags=["govt_contractor"] if award_amount and award_amount > 0 else [],
                    ))
            except Exception:
                pass

        return entities[:limit]

    async def get_entity(self, entity_id: str) -> Entity | None:
        raw_id = entity_id.replace("usaspending:", "")
        from config import make_httpx_client

        async with make_httpx_client() as client:
            try:
                resp = await client.get(f"{BASE_URL}/recipient/{raw_id}/")
                if resp.status_code == 200:
                    data = resp.json()
                    return Entity(
                        id=entity_id,
                        source=SourceEnum.usaspending,
                        name=data.get("name", "Unknown"),
                        entity_type=EntityType.company,
                        countries=["us"],
                        properties={
                            "total_transaction_amount": [str(data.get("total_transaction_amount", 0))],
                            "total_face_value_loan_amount": [str(data.get("total_face_value_loan_amount", 0))],
                        },
                        source_url=f"https://www.usaspending.gov/recipient/{raw_id}/latest",
                        flags=["govt_contractor"],
                    )
            except Exception:
                pass
        return None

    async def get_connections(self, entity_id: str) -> list[Connection]:
        """Find contract/grant connections by searching entity name."""
        from config import make_httpx_client

        # Extract name from entity_id (format: usaspending:recipient:NAME)
        name = entity_id.replace("usaspending:", "").replace("recipient:", "")
        if not name:
            return []

        connections = []
        async with make_httpx_client() as client:
            try:
                resp = await client.post(
                    f"{BASE_URL}/search/spending_by_award/",
                    json={
                        "filters": {
                            "recipient_search_text": [name],
                            "award_type_codes": ["A", "B", "C", "D"],
                        },
                        "fields": ["Award ID", "Awarding Agency", "Award Amount", "Award Type", "Description"],
                        "limit": 20,
                        "page": 1,
                        "sort": "Award Amount",
                        "order": "desc",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for result in data.get("results", []):
                    agency = result.get("Awarding Agency", "")
                    amount = result.get("Award Amount", 0)
                    if agency and amount:
                        connections.append(Connection(
                            source_entity_id=f"usaspending:agency:{agency}",
                            target_entity_id=entity_id,
                            relation_type="contract",
                            label=f"${amount:,.0f} ({result.get('Award Type', 'award')})",
                            weight=amount,
                            properties={
                                "award_id": result.get("Award ID", ""),
                                "description": result.get("Description", ""),
                            },
                            source=SourceEnum.usaspending,
                        ))
            except Exception:
                pass
        return connections

    async def get_events(self, entity_id: str) -> list[TimelineEvent]:
        name = entity_id.replace("usaspending:", "").replace("recipient:", "")
        if not name:
            return []

        from config import make_httpx_client
        events = []
        async with make_httpx_client() as client:
            try:
                resp = await client.post(
                    f"{BASE_URL}/search/spending_by_award/",
                    json={
                        "filters": {
                            "recipient_search_text": [name],
                            "award_type_codes": ["A", "B", "C", "D"],
                        },
                        "fields": ["Award ID", "Awarding Agency", "Award Amount", "Start Date", "Award Type"],
                        "limit": 20,
                        "page": 1,
                        "sort": "Start Date",
                        "order": "desc",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for result in data.get("results", []):
                    start_date = result.get("Start Date")
                    if start_date:
                        try:
                            dt = date.fromisoformat(start_date[:10])
                            events.append(TimelineEvent(
                                date=dt,
                                event_type="award",
                                description=f"{name}: {result.get('Award Type', 'award')} from {result.get('Awarding Agency', '')}",
                                entity_ids=[entity_id],
                                source=SourceEnum.usaspending,
                                amount=result.get("Award Amount"),
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
                resp = await client.get(f"{BASE_URL}/references/filter_tree/psc/")
                return resp.status_code == 200
            except Exception:
                return False
