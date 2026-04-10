"""SEC EDGAR source adapter — corporate filings, insider trading, beneficial ownership."""

from __future__ import annotations

import asyncio
from datetime import date

import config
from models import Connection, Entity, EntityType, SourceEnum, TimelineEvent

from .base import BaseSource

EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
SUBMISSIONS_URL = "https://data.sec.gov/submissions"
SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
FULL_TEXT_URL = "https://efts.sec.gov/LATEST/search-index"


def _headers():
    return {"User-Agent": config.SEC_EDGAR_USER_AGENT, "Accept": "application/json"}


class SECEdgarSource(BaseSource):
    name = "sec_edgar"
    source_enum = SourceEnum.sec_edgar

    async def search_entity(
        self, query: str, entity_type: str | None = None, limit: int = 25
    ) -> list[Entity]:
        from config import make_httpx_client

        entities = []

        # Full-text search across filings
        async with make_httpx_client() as client:
            try:
                resp = await client.get(
                    "https://efts.sec.gov/LATEST/search-index",
                    params={
                        "q": f'"{query}"',
                        "dateRange": "custom",
                        "forms": "10-K,10-Q,8-K,DEF 14A,SC 13D,SC 13G,4",
                    },
                    headers=_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                # Fall back to EDGAR full-text search
                try:
                    resp = await client.get(
                        "https://efts.sec.gov/LATEST/search-index",
                        params={"q": query, "forms": "10-K,8-K,SC 13D,4"},
                        headers=_headers(),
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception:
                    data = {}

        # Also try company search
        async with make_httpx_client() as client:
            try:
                resp = await client.get(
                    "https://efts.sec.gov/LATEST/search-index",
                    params={"q": query, "forms": "10-K"},
                    headers=_headers(),
                )
                if resp.status_code == 200:
                    company_data = resp.json()
                    hits = company_data.get("hits", {}).get("hits", [])
                    for hit in hits[:limit]:
                        src = hit.get("_source", {})
                        entity_name = src.get("display_names", [query])[0] if src.get("display_names") else src.get("entity_name", query)
                        file_date = src.get("file_date", "")
                        form_type = src.get("form_type", "")

                        entities.append(Entity(
                            id=f"sec:{src.get('file_num', hit.get('_id', ''))}",
                            source=SourceEnum.sec_edgar,
                            name=entity_name,
                            entity_type=EntityType.company,
                            countries=["us"],
                            properties={
                                "form_type": [form_type],
                                "file_date": [file_date],
                                "cik": [str(src.get("ciks", [""])[0])] if src.get("ciks") else [],
                            },
                            source_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={query}&type=&dateb=&owner=include&count=40",
                        ))
            except Exception:
                pass

        return entities[:limit]

    async def get_entity(self, entity_id: str) -> Entity | None:
        raw_id = entity_id.replace("sec:", "")
        # Try to fetch CIK-based submission
        from config import make_httpx_client
        async with make_httpx_client() as client:
            try:
                cik = raw_id.zfill(10)
                resp = await client.get(
                    f"{SUBMISSIONS_URL}/CIK{cik}.json",
                    headers=_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return Entity(
                    id=entity_id,
                    source=SourceEnum.sec_edgar,
                    name=data.get("name", "Unknown"),
                    entity_type=EntityType.company,
                    countries=["us"],
                    properties={
                        "cik": [str(data.get("cik", ""))],
                        "sic": [data.get("sic", "")],
                        "sicDescription": [data.get("sicDescription", "")],
                        "stateOfIncorporation": [data.get("stateOfIncorporation", "")],
                    },
                    source_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
                )
            except Exception:
                return None

    async def get_events(self, entity_id: str) -> list[TimelineEvent]:
        """Extract filing dates as timeline events."""
        entity = await self.get_entity(entity_id)
        if not entity:
            return []

        events = []
        file_dates = entity.properties.get("file_date", [])
        form_types = entity.properties.get("form_type", [])

        for i, fd in enumerate(file_dates[:20]):
            try:
                dt = date.fromisoformat(fd[:10])
                form = form_types[i] if i < len(form_types) else "filing"
                events.append(TimelineEvent(
                    date=dt,
                    event_type="filing",
                    description=f"{entity.name}: SEC {form} filed",
                    entity_ids=[entity_id],
                    source=SourceEnum.sec_edgar,
                    source_url=entity.source_url,
                ))
            except (ValueError, TypeError):
                pass
        return events

    async def health_check(self) -> bool:
        from config import make_httpx_client
        async with make_httpx_client() as client:
            try:
                resp = await client.get("https://data.sec.gov/", headers=_headers())
                return resp.status_code == 200
            except Exception:
                return False
