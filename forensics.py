"""Digital forensics chain of custody for investigative evidence.

Every piece of evidence is hashed, timestamped, and archived.
The principle: save the receipt, not just the result.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import DATA_DIR, PROJECT_DIR

CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_string(text: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_tool_version() -> str:
    """Get the current git commit hash of the toolkit."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(PROJECT_DIR),
        )
        return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def cache_response(
    source_url: str,
    response_data: bytes | str,
    prefix: str = "api",
) -> dict:
    """Cache an API response with provenance metadata.

    Returns metadata dict with hash, cache path, and timestamp.
    """
    timestamp = datetime.now().isoformat()
    data_bytes = response_data.encode("utf-8") if isinstance(response_data, str) else response_data
    data_hash = sha256_bytes(data_bytes)

    # Create a filename from the URL and timestamp
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in source_url)[:80]
    ts_short = datetime.now().strftime("%Y%m%d_%H%M%S")
    cache_file = CACHE_DIR / f"{prefix}_{safe_name}_{ts_short}.json"

    # Save the raw response
    cache_file.write_bytes(data_bytes)

    return {
        "source_url": source_url,
        "retrieved_at": timestamp,
        "sha256": data_hash,
        "cached_at": str(cache_file.relative_to(PROJECT_DIR)),
        "tool_version": get_tool_version(),
        "size_bytes": len(data_bytes),
    }


def build_provenance(
    source_url: str,
    data_hash: str,
    cache_path: str = "",
    source_version: str = "",
) -> dict:
    """Build a provenance metadata record for an evidence file."""
    return {
        "source_url": source_url,
        "retrieved_at": datetime.now().isoformat(),
        "source_version": source_version,
        "sha256": data_hash,
        "cached_at": cache_path,
        "tool_version": get_tool_version(),
    }


def build_chain_of_custody(entries: list[dict]) -> str:
    """Format chain of custody entries for an evidence file.

    Each entry is a dict from build_provenance() or cache_response().
    """
    lines = ["## Chain of Custody\n"]
    for i, entry in enumerate(entries, 1):
        lines.append(f"**Source {i}:**")
        lines.append(f"- URL: `{entry.get('source_url', 'N/A')}`")
        lines.append(f"- Retrieved: {entry.get('retrieved_at', 'N/A')}")
        lines.append(f"- SHA-256: `{entry.get('sha256', 'N/A')}`")
        if entry.get("cached_at"):
            lines.append(f"- Local cache: `{entry['cached_at']}`")
        if entry.get("archive_url"):
            lines.append(f"- Archive: {entry['archive_url']}")
        if entry.get("archive_ph_url"):
            lines.append(f"- Archive.ph: {entry['archive_ph_url']}")
        lines.append(f"- Tool version: `{entry.get('tool_version', 'N/A')}`")
        lines.append("")
    return "\n".join(lines)


async def submit_to_wayback(url: str) -> Optional[str]:
    """Submit a URL to the Internet Archive Wayback Machine.

    Returns the archived URL if successful.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"https://web.archive.org/save/{url}",
                follow_redirects=True,
            )
            if resp.status_code in (200, 302):
                # The Wayback Machine returns the archived URL in headers
                archived = resp.headers.get("Content-Location") or resp.headers.get("Location")
                if archived:
                    return f"https://web.archive.org{archived}"
                return f"https://web.archive.org/web/{datetime.now().strftime('%Y%m%d%H%M%S')}/{url}"
    except Exception:
        pass
    return None


def generate_methodology(
    scan_name: str,
    parameters: dict,
    data_sources: list[dict],
    anomaly_metrics: list[dict],
    limitations: list[str],
) -> str:
    """Generate a METHODOLOGY.md file for a scan or investigation.

    This documents everything needed to reproduce the analysis.
    """
    ts = datetime.now().isoformat()

    source_table = "| Source | Version | URL | Retrieved |\n|--------|---------|-----|----------|\n"
    for src in data_sources:
        source_table += f"| {src.get('name', '')} | {src.get('version', '')} | {src.get('url', '')} | {src.get('retrieved', '')} |\n"

    metric_table = "| Metric | Formula | Weight | Threshold |\n|--------|---------|--------|----------|\n"
    for m in anomaly_metrics:
        metric_table += f"| {m.get('name', '')} | {m.get('formula', '')} | {m.get('weight', '')} | {m.get('threshold', '')} |\n"

    limits = "\n".join(f"- {l}" for l in limitations)

    return f"""# Methodology: {scan_name}

*Generated: {ts}*
*Tool version: {get_tool_version()}*

## Parameters

```json
{json.dumps(parameters, indent=2, default=str)}
```

## Data Sources

{source_table}

## Anomaly Scoring

{metric_table}

**Composite score:** Weighted sum of all metrics, 0-100. Higher = more anomalous.

## Known Limitations

{limits}

## Reproducibility

To reproduce this analysis:
1. Clone the repository: `git clone https://github.com/bnuckols13/investigator.git`
2. Checkout the commit: `git checkout {get_tool_version()}`
3. Install dependencies: `pip install -e .`
4. Run: `python investigate.py scan run` with the parameters above
5. Compare SHA-256 hashes of source data files to verify you have the same inputs

## Chain of Custody

All source data files are archived in `data/irs/` with SHA-256 hashes recorded.
Raw API responses are cached in `data/cache/` with provenance metadata.
The git commit hash of this analysis serves as a forensic seal.
"""
