"""Configuration loader and shared utilities."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Aleph
ALEPH_HOST = os.getenv("ALEPH_HOST", "https://aleph.occrp.org")
ALEPH_API_KEY = os.getenv("ALEPH_API_KEY", "")

# OpenSanctions
OPENSANCTIONS_API_KEY = os.getenv("OPENSANCTIONS_API_KEY", "")

# SEC EDGAR
SEC_EDGAR_USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "Investigator investigator@example.com")

# OpenFEC
OPENFEC_API_KEY = os.getenv("OPENFEC_API_KEY", "")

# CourtListener
COURTLISTENER_TOKEN = os.getenv("COURTLISTENER_TOKEN", "")

# Paths
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
INVESTIGATIONS_DIR = DATA_DIR / "investigations"
CACHE_DIR = DATA_DIR / "cache"
WATCHLIST_PATH = DATA_DIR / "watchlist.json"

# Ensure dirs exist
INVESTIGATIONS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def make_httpx_client(**kwargs):
    """Create a configured httpx.AsyncClient."""
    import httpx

    transport = httpx.AsyncHTTPTransport(retries=3)
    defaults = dict(
        timeout=httpx.Timeout(30.0, connect=10.0),
        transport=transport,
        follow_redirects=True,
    )
    defaults.update(kwargs)
    return httpx.AsyncClient(**defaults)
