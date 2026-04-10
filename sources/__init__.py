"""OSINT data source adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from .base import BaseSource


def get_enabled_sources() -> list[BaseSource]:
    """Return source adapters that have valid credentials configured."""
    sources: list[BaseSource] = []

    if config.ALEPH_API_KEY:
        from .aleph import AlephSource
        sources.append(AlephSource())

    if config.OPENSANCTIONS_API_KEY:
        from .opensanctions import OpenSanctionsSource
        sources.append(OpenSanctionsSource())

    if config.SEC_EDGAR_USER_AGENT and config.SEC_EDGAR_USER_AGENT != "Investigator investigator@example.com":
        from .sec_edgar import SECEdgarSource
        sources.append(SECEdgarSource())

    if config.OPENFEC_API_KEY:
        from .openfec import OpenFECSource
        sources.append(OpenFECSource())

    # USASpending needs no auth
    from .usaspending import USASpendingSource
    sources.append(USASpendingSource())

    # CourtListener works without auth (rate-limited), better with token
    from .courtlistener import CourtListenerSource
    sources.append(CourtListenerSource())

    return sources


SOURCE_REGISTRY: dict[str, type] = {}
