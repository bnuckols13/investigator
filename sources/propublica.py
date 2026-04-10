"""ProPublica Nonprofit Explorer source adapter — IRS 990 data for nonprofits.

Free API, no auth required. Provides:
- Organization search by name
- 990 filing data (revenue, expenses, assets, officer compensation)
- EIN-based lookup
- Tax-exempt status and NTEE classification
"""

from __future__ import annotations

from datetime import date

from models import Connection, Entity, EntityType, SourceEnum, TimelineEvent

from .base import BaseSource

BASE_URL = "https://projects.propublica.org/nonprofits/api/v2"

# Register as a source
PROPUBLICA_SOURCE = "propublica"


class ProPublicaSource(BaseSource):
    name = "propublica"
    source_enum = SourceEnum.propublica

    async def search_entity(
        self, query: str, entity_type: str | None = None, limit: int = 25
    ) -> list[Entity]:
        from config import make_httpx_client

        entities = []
        async with make_httpx_client() as client:
            try:
                resp = await client.get(
                    f"{BASE_URL}/search.json",
                    params={"q": query, "page": 0},
                )
                resp.raise_for_status()
                data = resp.json()

                for org in data.get("organizations", [])[:limit]:
                    ein = org.get("ein", "")
                    name = org.get("name", "Unknown")
                    sub_name = org.get("sub_name", "")
                    display_name = sub_name if sub_name else name
                    city = org.get("city", "")
                    state = org.get("state", "")

                    entities.append(Entity(
                        id=f"propublica:{ein}",
                        source=SourceEnum.propublica,
                        name=display_name,
                        entity_type=EntityType.organization,
                        countries=["us"],
                        properties={
                            "ein": [str(ein)],
                            "strein": [org.get("strein", "")],
                            "city": [city],
                            "state": [state],
                            "ntee_code": [org.get("ntee_code", "")],
                            "subsection_code": [str(org.get("subseccd", ""))],
                        },
                        source_url=f"https://projects.propublica.org/nonprofits/organizations/{ein}",
                        flags=["nonprofit"],
                    ))
            except Exception:
                pass

        return entities[:limit]

    async def get_entity(self, entity_id: str) -> Entity | None:
        ein = entity_id.replace("propublica:", "")
        from config import make_httpx_client

        async with make_httpx_client() as client:
            try:
                resp = await client.get(f"{BASE_URL}/organizations/{ein}.json")
                resp.raise_for_status()
                data = resp.json()
                org = data.get("organization", {})
                filings = data.get("filings_with_data", [])

                # Get latest filing data
                latest = filings[0] if filings else {}
                revenue = latest.get("totrevenue", 0)
                expenses = latest.get("totfuncexpns", 0)
                assets = latest.get("totassetsend", 0)
                liabilities = latest.get("totliabend", 0)
                officer_comp = latest.get("pct_compnsatncurrofcr", 0)
                contributions = latest.get("totcntrbgfts", 0)
                program_revenue = latest.get("totprgmrevnue", 0)

                # Flag suspicious patterns
                flags = ["nonprofit"]
                if revenue > 0 and expenses > 0:
                    overhead_ratio = 1 - (latest.get("totprgmrevnue", 0) / revenue) if revenue else 0
                    if overhead_ratio > 0.5:
                        flags.append("high_overhead")
                if officer_comp and revenue and officer_comp > 0.15:
                    flags.append("high_exec_comp")

                return Entity(
                    id=entity_id,
                    source=SourceEnum.propublica,
                    name=org.get("name", "Unknown"),
                    entity_type=EntityType.organization,
                    countries=["us"],
                    properties={
                        "ein": [str(org.get("ein", ""))],
                        "address": [org.get("address", "")],
                        "city": [org.get("city", "")],
                        "state": [org.get("state", "")],
                        "ruling_date": [str(org.get("ruling_date", ""))],
                        "subsection_code": [str(org.get("subsection_code", ""))],
                        "ntee_code": [org.get("ntee_code", "")],
                        "total_revenue": [str(revenue)],
                        "total_expenses": [str(expenses)],
                        "total_assets": [str(assets)],
                        "total_liabilities": [str(liabilities)],
                        "contributions": [str(contributions)],
                        "program_revenue": [str(program_revenue)],
                        "officer_compensation_pct": [str(officer_comp)],
                        "tax_period": [str(latest.get("tax_prd_yr", ""))],
                        "filing_count": [str(len(filings))],
                    },
                    source_url=f"https://projects.propublica.org/nonprofits/organizations/{ein}",
                    flags=flags,
                )
            except Exception:
                return None

    async def get_connections(self, entity_id: str) -> list[Connection]:
        """Get officer/director connections from 990 filings."""
        ein = entity_id.replace("propublica:", "")
        from config import make_httpx_client

        connections = []
        async with make_httpx_client() as client:
            try:
                resp = await client.get(f"{BASE_URL}/organizations/{ein}.json")
                resp.raise_for_status()
                data = resp.json()

                filings = data.get("filings_with_data", [])
                if not filings:
                    return connections

                # Get the latest filing's object_id for detailed data
                latest = filings[0]
                obj_id = latest.get("object_id") or data.get("organization", {}).get("latest_object_id")

                if obj_id:
                    # Fetch the full filing
                    filing_resp = await client.get(
                        f"https://projects.propublica.org/nonprofits/api/v2/filings/{obj_id}.json"
                    )
                    if filing_resp.status_code == 200:
                        filing_data = filing_resp.json()

                        # Extract officers/directors from Part VII
                        officers = filing_data.get("officers", []) or []
                        for officer in officers[:20]:
                            officer_name = officer.get("name", "")
                            title = officer.get("title", "")
                            comp = officer.get("compensation", 0) or 0

                            if officer_name:
                                connections.append(Connection(
                                    source_entity_id=f"propublica:officer:{officer_name}",
                                    target_entity_id=entity_id,
                                    relation_type="directorship",
                                    label=f"{title} (${comp:,.0f})" if comp else title,
                                    weight=comp if comp else None,
                                    properties={
                                        "title": title,
                                        "compensation": str(comp),
                                        "hours": str(officer.get("hours", "")),
                                    },
                                    source=SourceEnum.propublica,
                                ))

                # Also create financial flow connections
                org = data.get("organization", {})
                revenue = latest.get("totrevenue", 0)
                if revenue and revenue > 0:
                    connections.append(Connection(
                        source_entity_id="propublica:revenue",
                        target_entity_id=entity_id,
                        relation_type="contract",
                        label=f"Total revenue: ${revenue:,.0f}",
                        weight=revenue,
                        source=SourceEnum.propublica,
                    ))

            except Exception:
                pass
        return connections

    async def get_events(self, entity_id: str) -> list[TimelineEvent]:
        """Get filing dates and financial milestones from 990 data."""
        ein = entity_id.replace("propublica:", "")
        from config import make_httpx_client

        events = []
        async with make_httpx_client() as client:
            try:
                resp = await client.get(f"{BASE_URL}/organizations/{ein}.json")
                resp.raise_for_status()
                data = resp.json()
                org = data.get("organization", {})
                org_name = org.get("name", "Unknown")

                for filing in data.get("filings_with_data", [])[:10]:
                    tax_year = filing.get("tax_prd_yr")
                    revenue = filing.get("totrevenue", 0)
                    expenses = filing.get("totfuncexpns", 0)

                    if tax_year:
                        try:
                            dt = date(int(tax_year), 12, 31)
                            events.append(TimelineEvent(
                                date=dt,
                                event_type="filing",
                                description=f"{org_name}: 990 filed (FY{tax_year}, revenue ${revenue:,.0f}, expenses ${expenses:,.0f})",
                                entity_ids=[entity_id],
                                source=SourceEnum.propublica,
                                source_url=filing.get("pdf_url"),
                                amount=revenue,
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
                resp = await client.get(f"{BASE_URL}/search.json", params={"q": "test"})
                return resp.status_code == 200
            except Exception:
                return False
