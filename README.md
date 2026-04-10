# Investigator — OSINT Journalism Toolkit

A multi-source open-source intelligence toolkit for investigative journalists, built to run from [Claude Code](https://claude.ai/code). Queries 7 public databases simultaneously, scans 301,484 US nonprofits from IRS bulk data, detects 14 composite "smoking gun" patterns, and produces MHEES-coded evidence with forensic chain of custody.

**Hesitation Media / Memory Hole** — Slow journalism. Being right over being first.

---

## Current Research

**[View the full synthesis report](research/SYNTHESIS.md)** — all findings, beat reports, and next actions.

### Active Investigations

| Investigation | Status | Heat | Key Finding | Files |
|--------------|--------|------|-------------|-------|
| ExxonMobil OFAC | Publishable lead | 45 | OFAC penalty + $33.6M DoD contracts | [data](data/investigations/) |
| UPMC System | Deepening | 42 | $2.4M exec comp, pass-through entities, ghost contractors | [data](data/investigations/) |
| Glencore | Needs verification | 24 | DOJ bribery + secrecy jurisdictions + active contracts | [data](data/investigations/) |
| Port Authority Allegheny Co | FOIA needed | 29 | $164K VA contract (47x median) | [data](data/investigations/) |
| PWSA Board Governance | Near-complete (PublicSource) | — | 98.6% unanimity, $1.15B no questions | [data](data/investigations/) |
| Natl Ground Game / Soul Strategies | Needs FEC Schedule B | — | Zero hits under entity names | [data](data/investigations/) |

### Population Scans

| Scan | Date | Orgs Scored | Above 50 | Top Finding |
|------|------|------------|----------|-------------|
| [National](research/scans/2026-04-10_national/) | 2026-04-10 | 301,484 | 3,003 | Pediatric Health Mgmt (TX): officers paid 4x revenue |
| [Pennsylvania](research/scans/2026-04-10_PA/) | 2026-04-10 | 14,888 | 100 | Swedenborg Foundation: 69% to officers |

### Beat Reports

| Beat | Link | Top Anomaly |
|------|------|-------------|
| Health | [top_25_health.md](research/scans/2026-04-10_national/top_25_health.md) | Health systems with outsized exec comp |
| Political | [top_25_political.md](research/scans/2026-04-10_national/top_25_political.md) | Advocacy orgs with low program ratios |
| Religious | [top_25_religious.md](research/scans/2026-04-10_national/top_25_religious.md) | Church-adjacent orgs |
| Education | [top_25_education.md](research/scans/2026-04-10_national/top_25_education.md) | University foundations |
| Veterans | [top_25_veterans.md](research/scans/2026-04-10_national/top_25_veterans.md) | Veteran service orgs |
| PA Local | [top_25_pennsylvania.md](research/scans/2026-04-10_PA/top_25_pennsylvania.md) | PA nonprofits |

---

## What It Does

### Entity Investigation (`/investigate`)

Search 7 OSINT databases simultaneously, resolve entities across sources, build network graphs, detect smoking gun patterns, and maintain persistent case files:

1. **OpenSanctions** — sanctions lists, PEPs, crime databases from 100+ government sources
2. **SEC EDGAR** — corporate filings, insider trading, beneficial ownership
3. **OpenFEC** — campaign contributions, PAC data, committee filings
4. **USASpending** — federal contracts, grants, awards
5. **CourtListener** — federal court dockets, opinions, PACER data
6. **ProPublica Nonprofit Explorer** — IRS 990 filings, officer compensation, financial data
7. **Aleph/OCCRP** — 3B+ records: corporate registries, leaked documents *(pending API key)*

### Population Scanner (`/scan`)

Scan IRS 990 bulk data (247MB, 345K+ filers) for financial anomalies:
- 11 anomaly metrics (exec comp ratio, program ratio, overhead, fundraising efficiency, deficit spending, asset hoarding, etc.)
- Beat-specific filters (health, political, religious, education, veterans, arts)
- State-level filtering
- Dated research snapshots with full methodology documentation

### Smoking Gun Detection

14 composite pattern detectors with multiplicative scoring:

| Tier | Detectors |
|------|-----------|
| **Smoking Gun** | Sanctions Evasion Chain, Quid Pro Quo, Insider Trading Signal, Revolving Door Contract, Self-Dealing |
| **Strong** | Concurrent Contradiction, Shell Company Obfuscation, Threshold Gaming, Ghost Contractor |
| **Indicator** | Jurisdiction Anomaly, Network Bridge, Temporal Clustering, Financial Outlier |

### Evidence Evaluation (MHEES)

Every finding carries a six-axis MHEES code: `P[1-6]-R[A-F]†-C[1-5]-I[1-6]†-D[1-4]-F[1-4]`

See [methodology/MHEES.md](research/methodology/MHEES.md) for the full system.

---

## Quick Start

```bash
cd ~/investigator

# Install dependencies
pip install httpx[http2] alephclient rapidfuzz networkx pydantic python-dotenv click rich eval_type_backport pandas

# Copy env and add API keys
cp .env.example .env

# Investigate an entity
/investigate "Entity Name"

# Scan nonprofits
/scan download           # Download IRS bulk data (first time)
/scan health PA          # Scan PA health nonprofits
/scan political          # National political nonprofit scan
/scan top 25             # Show top anomalies

# Manage watchlist
/watchlist add "Entity"
/watchlist scan

# Setup wizard
/investigate-setup
```

---

## Version History

| Version | Date | Commit | Changes |
|---------|------|--------|---------|
| v0.7 | 2026-04-10 | `5966e71` | Nonprofit population scanner (301K orgs), research repository, IRS bulk data, forensics chain of custody |
| v0.6 | 2026-04-10 | `b1b4ead` | Self-Dealing Detector, ProPublica EIN fallback, Trump Foundation validation, 990 None-field fix |
| v0.5 | 2026-04-10 | `66afa6a` | 990 officer comp extraction ($-amounts), 4 nonprofit fraud flags (high_exec_comp, high_overhead, revenue_decline, high_fundraising_cost) |
| v0.4 | 2026-04-10 | `5bab078` | ProPublica Nonprofit Explorer (7th source), FEC PAC name search, entity resolver company bias, enrichment pipeline, score cap |
| v0.3 | 2026-04-10 | `673008b` | Connection mapping fix (USASpending returns edges), additive score capped at 100 |
| v0.2 | 2026-04-09 | `c892166` | 12 smoking gun detectors, MHEES auto-coding, evidence file generation, CourtListener no-auth |
| v0.1 | 2026-04-09 | `08036ba` | Initial release: 6 sources, entity resolution, network graphs, lead scoring, CLI, slash commands, scheduled tasks |

---

## Architecture

```
investigator/
├── investigate.py          # CLI entry point
├── case_manager.py         # Persistent investigation cases
├── enrichment.py           # Auto-enrichment pipeline
├── forensics.py            # SHA-256 hashing, chain of custody, archiving
├── config.py               # Configuration and API client factory
├── models.py               # Pydantic v2 data models
├── sources/                # 7 OSINT data source adapters
│   ├── aleph.py            # OCCRP Aleph (3B+ records)
│   ├── opensanctions.py    # Sanctions/PEP/crime databases
│   ├── sec_edgar.py        # SEC corporate filings
│   ├── openfec.py          # FEC campaign finance
│   ├── usaspending.py      # Federal contracts/grants
│   ├── courtlistener.py    # Federal court records
│   └── propublica.py       # IRS 990 nonprofit data
├── analysis/               # Analytical engines
│   ├── smoking_gun.py      # 14 composite pattern detectors
│   ├── mhees.py            # Evidence evaluation auto-coding
│   ├── entity_resolver.py  # Cross-source entity deduplication
│   ├── network.py          # NetworkX graph + Mermaid diagrams
│   ├── scoring.py          # Lead prioritization algorithm
│   ├── timeline.py         # Temporal pattern detection
│   ├── ownership.py        # Beneficial ownership chain tracing
│   ├── revolving_door.py   # Government-corporate transition detection
│   └── procurement.py      # Contract anomaly detection
├── scanner/                # Population-level nonprofit scanning
│   ├── downloader.py       # IRS bulk data download
│   ├── analyzer.py         # Anomaly scoring (11 metrics)
│   └── rankings.py         # Beat reports + research snapshots
├── output/                 # Output formatters
│   ├── memo.py             # Markdown investigation memos
│   └── mermaid.py          # Network diagrams + HTML export
├── watchlist/              # Entity monitoring
│   ├── store.py            # Watchlist persistence
│   └── scanner.py          # Change detection
├── research/               # Shareable research repository
│   ├── SYNTHESIS.md        # Master synthesis of all findings
│   ├── scans/              # Dated population scan snapshots
│   └── methodology/        # MHEES, data sources, detector docs
└── data/                   # Local data (gitignored)
    ├── irs/                # IRS bulk CSVs (247MB SOI + 309MB BMF)
    ├── investigations/     # Per-entity investigation JSONs
    └── cache/              # API response cache with provenance
```

## Methodology

- [MHEES Evidence Evaluation](research/methodology/MHEES.md)
- [Data Sources](research/methodology/DATA_SOURCES.md)
- [Smoking Gun Detectors](research/methodology/SMOKING_GUN_DETECTORS.md)
- [Trustless Journalism Protocol](SOP.md)

## License

Code: MIT. Research outputs: CC BY-SA 4.0.
