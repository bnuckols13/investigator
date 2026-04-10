# Investigator — OSINT Journalism Toolkit

A multi-source open-source intelligence toolkit for investigative journalists, built to run from [Claude Code](https://claude.ai/code). Queries 6 public databases simultaneously, resolves entities across sources, builds network graphs, scores leads by investigative priority, and maintains persistent case files that grow with each search.

## What It Does

Type `/investigate Gazprom` in Claude Code and the system:

1. Searches **Aleph/OCCRP** (3B+ records: corporate registries, leaked documents, sanctions), **OpenSanctions** (100+ sanctions/PEP/crime lists), **SEC EDGAR** (corporate filings, insider trading), **OpenFEC** (campaign finance), **USASpending** (federal contracts), and **CourtListener** (federal court records)
2. Resolves entities across sources using fuzzy matching (RapidFuzz)
3. Builds a network graph of connections (NetworkX)
4. Scores each entity for investigative priority (sanctions hits, government contracts, court cases, corporate complexity, cross-jurisdiction presence)
5. Saves everything to a persistent case file that accumulates findings over time
6. Presents the findings as a narrative with a network diagram and specific next investigative steps

## Quick Start

```bash
# 1. Clone and enter the directory
cd ~/investigator

# 2. Install dependencies
pip install httpx[http2] alephclient rapidfuzz networkx pydantic python-dotenv click rich eval_type_backport

# 3. Copy the env template and add your API keys
cp .env.example .env
# Edit .env with your keys (see Setup below)

# 4. Use from Claude Code
/investigate "Entity Name"
/investigate-setup           # Guided API key setup
/watchlist add "Entity"      # Monitor an entity
```

## Setup — API Keys

| Source | How to Get Key | Required? |
|--------|---------------|-----------|
| **Aleph/OCCRP** | Apply at [aleph.occrp.org](https://aleph.occrp.org) (72hr review) | Recommended |
| **OpenSanctions** | Sign up at [opensanctions.org](https://www.opensanctions.org) | Recommended |
| **SEC EDGAR** | No key needed — just your name/email in `.env` | Free |
| **OpenFEC** | Instant key at [api.data.gov/signup](https://api.data.gov/signup/) | Free |
| **USASpending** | No key needed | Free |
| **CourtListener** | Sign up at [courtlistener.com](https://www.courtlistener.com) | Free |

Run `/investigate-setup` in Claude Code for a guided walkthrough.

## CLI Usage

```bash
# Search all sources for an entity
python3 investigate.py search "Gazprom" --output both

# Search specific sources only
python3 investigate.py search "Lockheed Martin" --sources usaspending,sec_edgar

# Deep-dive a single entity by ID
python3 investigate.py entity "aleph:abc123" --source aleph

# Network graph only
python3 investigate.py graph "Erik Prince" --html

# Compare two entity names (fuzzy matching)
python3 investigate.py compare "Viktor Orban" "Orbán Viktor"

# Watchlist management
python3 investigate.py watchlist add "Entity Name" --type company
python3 investigate.py watchlist list
python3 investigate.py watchlist scan
python3 investigate.py watchlist remove "Entity Name"
```

## Architecture

```
investigator/
├── investigate.py          # CLI entry point
├── case_manager.py         # Persistent investigation cases
├── enrichment.py           # Auto-enrichment pipeline
├── config.py               # Configuration and API client factory
├── models.py               # Pydantic v2 data models
├── sources/                # OSINT data source adapters
│   ├── aleph.py            # OCCRP Aleph (3B+ records)
│   ├── opensanctions.py    # Sanctions/PEP/crime databases
│   ├── sec_edgar.py        # SEC corporate filings
│   ├── openfec.py          # FEC campaign finance
│   ├── usaspending.py      # Federal contracts/grants
│   └── courtlistener.py    # Federal court records
├── analysis/               # Analytical engines
│   ├── entity_resolver.py  # Cross-source entity deduplication
│   ├── network.py          # NetworkX graph + Mermaid diagrams
│   ├── scoring.py          # Lead prioritization algorithm
│   ├── timeline.py         # Temporal pattern detection
│   ├── ownership.py        # Beneficial ownership chain tracing
│   ├── revolving_door.py   # Government-corporate transition detection
│   └── procurement.py      # Contract anomaly detection
├── output/                 # Output formatters
│   ├── memo.py             # Markdown investigation memos
│   └── mermaid.py          # Network diagrams + HTML export
├── watchlist/              # Entity monitoring
│   ├── store.py            # Watchlist persistence
│   └── scanner.py          # Change detection
└── cases/                  # Persistent investigation case files
```

## Investigative Patterns Detected

| Pattern | What It Finds |
|---------|---------------|
| **Sanctions evasion** | Sanctioned persons linked to US-registered companies |
| **Shell company networks** | Circular ownership, shared directors, offshore jurisdictions |
| **Revolving door** | Officials who move to industries they regulated |
| **Pay-to-play** | Campaign donors who receive government contracts |
| **Insider trading signals** | Stock trades near material corporate events |
| **Procurement fraud** | Sole-source concentration, threshold-splitting, rapid award velocity |

## Scheduled Automation

Three scheduled tasks run automatically:
- **Daily watchlist scan** (7am) — checks monitored entities for new appearances
- **Weekly filing monitor** (Monday 8am) — new SEC/FEC filings for watched entities
- **Morning intelligence brief** (6:47am) — current events, watchlist alerts, and "memory hole" stories from 5/10/25 years ago

## How Case Files Work

Every `/investigate` search adds findings to a persistent case file under `cases/`. The case accumulates:
- All discovered entities (deduplicated across searches)
- All connections between entities
- Timeline events
- Lead scores
- A growing network graph (auto-updated HTML file)
- An investigation log with timestamped entries

This means your second search for a related entity builds on your first, growing the network map and revealing connections that only become visible when you combine multiple queries.

## License

MIT
