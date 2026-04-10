"""Ranking output generator for nonprofit population scans.

Produces tiered output: Markdown reports, CSV exports, JSON data.
Each scan gets a dated snapshot directory with full methodology docs.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import PROJECT_DIR
from forensics import generate_methodology, get_tool_version, sha256_file

RESEARCH_DIR = PROJECT_DIR / "research"
SCANS_DIR = RESEARCH_DIR / "scans"
SCANS_DIR.mkdir(parents=True, exist_ok=True)


def create_scan_snapshot(
    scored_df: pd.DataFrame,
    scan_name: str = "national",
    parameters: dict = None,
    source_files: list[dict] = None,
) -> Path:
    """Create a dated snapshot directory with all scan outputs.

    Returns the path to the snapshot directory.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    snapshot_dir = SCANS_DIR / f"{date_str}_{scan_name}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    parameters = parameters or {}
    source_files = source_files or []

    # Generate all outputs
    _write_top_n(scored_df, snapshot_dir, "top_100_national", 100)
    _write_top_n(scored_df, snapshot_dir, "top_25_pennsylvania", 25, state="PA")

    # Beat-specific reports
    from scanner.analyzer import BEAT_FILTERS
    for beat_name, prefixes in BEAT_FILTERS.items():
        beat_df = scored_df[scored_df["ntee"].fillna("").str[0].isin(prefixes)]
        if len(beat_df) > 0:
            _write_top_n(beat_df, snapshot_dir, f"top_25_{beat_name}", 25)

    # Raw scores CSV
    csv_path = snapshot_dir / "raw_scores.csv"
    scored_df.to_csv(csv_path, index=False)

    # Parameters JSON
    (snapshot_dir / "parameters.json").write_text(
        json.dumps({
            **parameters,
            "scan_date": date_str,
            "total_orgs_scanned": len(scored_df),
            "orgs_with_flags": len(scored_df[scored_df["flags"] != ""]),
            "tool_version": get_tool_version(),
        }, indent=2, default=str)
    )

    # Methodology
    (snapshot_dir / "METHODOLOGY.md").write_text(
        generate_methodology(
            scan_name=f"Nonprofit Population Scan — {scan_name}",
            parameters=parameters,
            data_sources=source_files,
            anomaly_metrics=[
                {"name": "exec_comp_ratio", "formula": "officer_comp / total_expenses", "weight": "15", "threshold": "> 10% = flagged"},
                {"name": "exec_comp_absolute", "formula": "officer_comp > threshold", "weight": "10", "threshold": "> $500K"},
                {"name": "program_ratio", "formula": "program_revenue / total_revenue", "weight": "15", "threshold": "< 65% = flagged"},
                {"name": "overhead_ratio", "formula": "1 - (program / expenses)", "weight": "10", "threshold": "> 50% = flagged"},
                {"name": "fundraising_efficiency", "formula": "fundraising_exp / contributions", "weight": "10", "threshold": "> 50% = flagged"},
                {"name": "deficit_spending", "formula": "(expenses - revenue) / revenue", "weight": "5", "threshold": "> 20% = flagged"},
                {"name": "asset_hoarding", "formula": "assets / revenue", "weight": "5", "threshold": "> 5x = flagged"},
                {"name": "comp_vs_revenue", "formula": "officer_comp / expenses", "weight": "10", "threshold": "> 10% = flagged"},
            ],
            limitations=[
                "IRS 990 data is self-reported by the organizations.",
                "Filing year may lag actual fiscal year by 1-2 years.",
                "Church/religious organizations exempt from 990 filing are invisible to this scan.",
                "Anomaly scores identify statistical outliers, not proven fraud.",
                "Multi-year trend analysis requires comparing across SOI extract years.",
                "Officer compensation may be split across affiliated entities.",
            ],
        )
    )

    # README with links
    _write_scan_readme(snapshot_dir, scored_df, scan_name, date_str)

    return snapshot_dir


def _write_top_n(df: pd.DataFrame, out_dir: Path, name: str, n: int, state: str = None):
    """Write a top-N Markdown report."""
    if state:
        df = df[df["state"].str.upper() == state.upper()]

    top = df.head(n)
    if len(top) == 0:
        return

    lines = [
        f"# {name.replace('_', ' ').title()}",
        f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | {len(df):,} organizations scanned*\n",
        "| Rank | Name | State | Revenue | Officer Comp | Score | Flags |",
        "|------|------|-------|---------|-------------|-------|-------|",
    ]

    for i, (_, row) in enumerate(top.iterrows(), 1):
        name_str = str(row.get("name", ""))[:40]
        state_str = str(row.get("state", ""))
        rev = f"${row.get('revenue', 0):,.0f}"
        comp = f"${row.get('officer_comp', 0):,.0f}"
        score = f"{row.get('anomaly_score', 0):.1f}"
        flags = str(row.get("flags", ""))[:50]
        ein = str(row.get("ein", ""))
        propublica = f"[990](https://projects.propublica.org/nonprofits/organizations/{ein})"

        lines.append(f"| {i} | {name_str} {propublica} | {state_str} | {rev} | {comp} | {score} | {flags} |")

    lines.append(f"\n*[Full dataset](./raw_scores.csv) | [Methodology](./METHODOLOGY.md)*")

    (out_dir / f"{name}.md").write_text("\n".join(lines))


def _write_scan_readme(out_dir: Path, df: pd.DataFrame, scan_name: str, date_str: str):
    """Write the scan README linking all outputs."""
    flagged = len(df[df["flags"] != ""])
    high_score = len(df[df["anomaly_score"] >= 50])
    avg_score = df["anomaly_score"].mean() if len(df) > 0 else 0

    files = sorted(out_dir.iterdir())
    file_links = "\n".join(f"- [{f.name}](./{f.name})" for f in files if f.name != "README.md")

    readme = f"""# Scan: {scan_name} — {date_str}

## Summary

- **{len(df):,}** organizations scanned
- **{flagged:,}** organizations with anomaly flags
- **{high_score}** organizations scoring above 50
- **Average anomaly score:** {avg_score:.1f}

## Reports

{file_links}

## Methodology

See [METHODOLOGY.md](./METHODOLOGY.md) for complete documentation of data sources,
scoring formula, and known limitations.

## Reproducibility

```bash
cd ~/investigator
git checkout {get_tool_version()}
python investigate.py scan run --scope {scan_name}
```

Compare SHA-256 hashes in [parameters.json](./parameters.json) to verify data integrity.
"""
    (out_dir / "README.md").write_text(readme)
