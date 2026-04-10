# Investigator Toolkit — Instance Handoff Document

*April 10, 2026 — Comprehensive state transfer for new Claude Code instance*

---

## What This Is

An OSINT investigative journalism toolkit at `~/investigator/` built for Brian Nuckols (Hesitation Media / Memory Hole). It queries 7 public databases, scans 301K+ US nonprofits from IRS bulk data, runs 14 "smoking gun" composite pattern detectors, and auto-codes evidence using the MHEES notation system.

Brian is a licensed professional counselor AND investigative journalist. His methodology is documented in a master dossier (ask him for it or check memory). The toolkit is the OSINT Specialist persona from his Four-Persona Intelligence Framework.

**GitHub:** https://github.com/bnuckols13/investigator
**Git commit:** `d56b5ac` (8 commits total)

---

## What Works

### Sources (7 active, 1 pending)

| Source | Status | Auth | Notes |
|--------|--------|------|-------|
| OpenSanctions | LIVE | API key in `.env` | Trial key, 50 req/mo, expires 2026-05-10 |
| SEC EDGAR | LIVE | User-Agent header | No key needed |
| OpenFEC | LIVE | DEMO_KEY in `.env` | Real key got 403, using demo. Rate limited. |
| USASpending | LIVE | None needed | Connection mapping works (contracts return edges) |
| CourtListener | LIVE | No auth (anonymous tier) | 5K/hr unauthenticated. Brian has account but no token set. |
| ProPublica | LIVE | None needed | 990 data with officer comp extraction. Auto-pulls detail for top 5 results. |
| Aleph/OCCRP | NOT CONFIGURED | Needs API key | Brian applied, 72hr review. This unlocks 3B+ records. |

**`.env` location:** `~/investigator/.env` (gitignored)

### CLI Commands

```bash
cd ~/investigator
python3 investigate.py search "Entity Name" --output both    # Multi-source search
python3 investigate.py scan download --year 2024             # Download IRS bulk data
python3 investigate.py scan run --state PA --beat health     # Population scan
python3 investigate.py scan run --top 50                     # National scan
python3 investigate.py watchlist add "Entity"                # Monitor entity
python3 investigate.py watchlist scan                        # Check for changes
python3 investigate.py compare "Name A" "Name B"             # Fuzzy match test
python3 investigate.py graph "Entity" --html                 # Network graph only
```

### Slash Commands

- `/investigate [entity]` — Full investigation with case persistence
- `/investigate-setup` — Guided API key setup
- `/watchlist [add|remove|list|scan]` — Entity monitoring
- `/scan [beat] [state]` — Population scanner

### Scheduled Tasks

| Task | Schedule | What It Does |
|------|----------|-------------|
| `investigator-daily-scan` | 7:04am daily | Watchlist scan, email draft on changes |
| `investigator-weekly-filings` | 8:07am Monday | SEC/FEC filing monitor |
| `morning-intelligence-brief` | 6:50am daily | Current events + memory hole + watchlist |

### Data on Disk

| Path | Size | Contents |
|------|------|---------|
| `data/irs/soi/soi_2024_990.csv` | 247MB | IRS SOI Tax Stats 2024 (all 990 filers) |
| `data/irs/eo_bmf/eo_national.csv` | 309MB | IRS Business Master File (1.9M org names) |
| `data/irs/eo_bmf/eo_*.csv` | ~6MB each | Per-state BMF files (52 states) |
| `data/investigations/*.json` | 66 files | Per-entity investigation results |
| `research/scans/2026-04-10_national/` | — | First national scan (301K orgs, beat reports) |
| `research/scans/2026-04-10_PA/` | — | PA scan (14,888 orgs) |

---

## What Doesn't Work (Honest Assessment)

### Critical Gaps

1. **No interactive HTML report.** The `output/report.py` file from the plan was never built. All output is CLI tables and markdown files. There's no "wow factor" presentation layer. The plan calls for a self-contained HTML file with collapsible evidence chains, interactive Mermaid graphs, MHEES confidence badges, and a methodology footer. This is the highest priority unbuilt feature.

2. **No audit trail / chain of custody implemented.** `forensics.py` exists with SHA-256 hashing functions and `cache_response()` / `build_provenance()` / `build_chain_of_custody()`, but NONE of these are called anywhere in the actual pipeline. The archiving workflow (Wayback Machine, archive.ph, OpenTimestamps) is designed but not built. Evidence files don't include provenance metadata. This is the second highest priority.

3. **No multi-layer archive contingency.** The plan specifies: local + GitHub + GitLab mirror + cloud backup (rclone) + Wayback + archive.ph + Perma.cc + OpenTimestamps blockchain. Only local + GitHub exist. No GitLab mirror, no cloud sync, no web archiving, no blockchain timestamps.

4. **Connection mapping is thin.** USASpending returns contract edges (fixed). But OpenSanctions, SEC EDGAR, OpenFEC, CourtListener, and ProPublica `get_connections()` methods mostly return empty because they need entity-specific IDs that aren't available from name-based searches. The smoking gun detectors need edges to fire, and most searches still produce 0 edges except from USASpending. Aleph (when configured) would be the richest connection source.

5. **Auto-enrichment doesn't work in practice.** `enrichment.py` is wired into `investigate.py` but gated by `limit > 10` to prevent recursion. In practice, the preliminary scoring before enrichment often doesn't find entities above the threshold because there are no connections yet (circular dependency: need connections to score high, need high scores to trigger enrichment that finds connections).

6. **FEC data is unreliable.** The DEMO_KEY works but is rate-limited. FEC searches by entity name often return 0 because political spending is under PAC/committee names. The PAC-variant search helps but doesn't solve the fundamental issue: need to search by committee ID for disbursements (Schedule B).

7. **ProPublica search doesn't always match.** "Trump Foundation" doesn't match "Donald J Trump Foundation Inc" in the API. The EIN fallback works if you know the EIN, and the variant search tries "The X" prefix, but many organizations still require knowing the exact legal name or EIN.

### Bugs Still Open

| Bug | Impact | Where |
|-----|--------|-------|
| ProPublica revenue typed as "funding" but Ghost Contractor may still fire on it | False positives in scan | `sources/propublica.py` line ~223, `analysis/smoking_gun.py` Ghost Contractor |
| Pandas FutureWarnings on dtype in analyzer | Cosmetic but noisy | `scanner/analyzer.py` lines 130, 148, 154 — need `.astype(float)` on score columns |
| Some beat reports in PA scan directory have national data | Confusing — PA scan generates `top_100_national.md` alongside `top_25_pennsylvania.md` | `scanner/rankings.py` `create_scan_snapshot()` always writes national |
| Case files in `cases/` directory not gitignored properly | A Steve Bannon case leaked into git history from a run Brian did | `.gitignore` now excludes `cases/` but the old commit has it |
| `enrichment.py` import of `SearchResult` at top of `investigate.py` could cause circular issues | Hasn't crashed but fragile | `investigate.py` enrichment section |

---

## What Was Tested (53 Agents, 4 Rounds)

### Round 1: 20 Agents (National Entities)
Erik Prince, Deutsche Bank, Palantir, Wagner Group, Halliburton, Rosneft, NSO Group, Raytheon, Glencore, Boeing, Kushner Companies, Blackstone Group, Purdue Pharma, Sam Bankman-Fried, ExxonMobil, Monsanto, Meta Platforms, PWSA, National Ground Game, Prigozhin

### Round 2: 8 Agents (Re-tests + Pittsburgh)
ExxonMobil (re-test), Glencore (re-test), UPMC, PNC Financial, Port Authority, Allegheny County, Soul Strategies, New Sun Rising

### Round 3: 5 Agents (Deep-Dives)
UPMC (with ProPublica), Z Cohen Sanchez, Michael Dawida, Pittsburgh Foundation, ExxonMobil OFAC

### Round 4: 20 Agents (Nonprofit Series)
**Pittsburgh:** UPMC Health, Highmark Health, Pittsburgh Cultural Trust, Pittsburgh Promise, AHN, Housing Authority, URA
**National:** Wounded Warrior, NRA, Goodwill, Salvation Army, Red Cross, Federalist Society, Heritage Foundation, Turning Point USA, Planned Parenthood, Susan G. Komen, Kenneth Copeland, Clinton Foundation, Trump Foundation

### Smoking Gun Detectors That Fired

| Target | Detector | Score | Heat |
|--------|----------|-------|------|
| ExxonMobil | Concurrent Contradiction | 75 | 45 |
| UPMC Health | 2x Ghost Contractor | 50 each | 42 |
| UPMC (main) | 2x Financial Outlier | 49, 34 | 38 |
| NRA | Financial Outlier | — | 38 |
| Red Cross | Ghost Contractor (FALSE POSITIVE) | 50 | 37 |
| Highmark | Ghost Contractor (FALSE POSITIVE) | 50 | 30 |
| AHN | Ghost Contractor | 50 | 30 |
| Port Authority | Financial Outlier | 49 | 29 |
| Glencore | Jurisdiction Anomaly | 40 | 24 |

### Validation Results

| Known Case | Expected | Got | Status |
|------------|----------|-----|--------|
| ExxonMobil OFAC penalty | Should fire Concurrent Contradiction | Fired (75) | PASS |
| UPMC exec comp | Should flag high_exec_comp | Flagged ($1.5-2.4M) | PASS |
| Wounded Warrior (reformed) | Clean ratios | Confirmed clean | PASS |
| Trump Foundation (fraud) | Should flag | Flagged high_overhead (after bug fix) | PASS (with fix) |
| Kenneth Copeland (church) | No 990 data | Correctly identified opacity | PASS |
| Wagner Group | OFAC/EU flags | 16 OFAC, 17 EU sanctioned | PASS |

---

## File Map (Critical Files)

### Core Pipeline
- `investigate.py` — CLI entry point. `run_search()` is the main orchestration function (~line 25). Calls sources, resolves entities, fetches connections, runs enrichment, builds graph, scores, runs smoking gun detectors, generates memo.
- `models.py` — Pydantic v2 models: `Entity`, `Connection`, `TimelineEvent`, `LeadScore`, `SearchResult`. The `SourceEnum` includes all 7 sources + `propublica`.
- `config.py` — Loads `.env`, exports API keys, `make_httpx_client()` factory.

### Sources (`sources/`)
- `base.py` — Abstract `BaseSource` interface: `search_entity()`, `get_entity()`, `get_connections()`, `get_events()`
- `opensanctions.py` — REST API with `ApiKey` auth. `match_entity()` for structured matching.
- `sec_edgar.py` — Full-text search. Needs `User-Agent`. 10 req/sec.
- `openfec.py` — Candidate + committee search. PAC-variant search added. `get_connections()` returns Schedule A contributions.
- `usaspending.py` — The best connection source. `get_connections()` searches by entity name, returns contract edges with dollar amounts. Requires `award_type_codes: ["A","B","C","D"]` filter.
- `courtlistener.py` — RECAP docket search + opinion search. Works without auth.
- `propublica.py` — Search + EIN fallback + auto-detail pull for top 5 results. `get_entity()` extracts: revenue, expenses, officer comp, program ratio, fundraising expense. Flags: `high_exec_comp`, `high_overhead`, `revenue_decline`, `high_fundraising_cost`. Known bug: `ntee_code` can be None, fixed with `str(x or "")`.

### Analysis (`analysis/`)
- `smoking_gun.py` — THE CORE. 14 detectors in `ALL_DETECTORS` list. `detect_all()` builds `DetectionContext` (pre-computed indexes), runs all detectors, deduplicates, computes heat score. Each detector is a class inheriting `BaseDetector`. Multiplier functions: `temporal_multiplier()`, `source_independence_multiplier()`, `concealment_multiplier()`, `recency_multiplier()`. Returns `SmokingGunReport`.
- `mhees.py` — Auto-codes MHEES notation from `DetectedPattern`. `auto_code()`, `generate_justification()`, `mhees_to_confidence_badge()`, `generate_evidence_file()`.
- `entity_resolver.py` — RapidFuzz dedup. `compute_similarity()` (weighted: name 50%, country 20%, type 20%, alias 10%). `resolve_entities()` uses union-find clustering with window=50. `deduplicate()` picks canonical entity by type priority (company > person) then source priority.
- `network.py` — NetworkX DiGraph. `build_graph()`, `analyze_graph()` (centrality, bridges), `to_mermaid()` (node shapes by type, flag highlighting), `find_paths()`, `subgraph_around()`.
- `scoring.py` — Additive lead scoring (capped at 100). Components: sanctions_pep, govt_contracts, court_cases, campaign_finance, corporate_complexity, cross_jurisdiction, network_centrality, recency.
- `timeline.py` — `merge_events()` (dedup), `detect_suspicious_sequences()` (insider trade near material event, revolving door timing, sanctions near filing, rapid succession).
- `ownership.py` — `trace_ownership()` (recursive), `find_ultimate_beneficial_owners()`, `detect_circular_ownership()`.
- `revolving_door.py` — `detect_revolving_door()` — PEP + corporate transitions + campaign-contract links.
- `procurement.py` — `detect_procurement_anomalies()` — sole-source concentration, threshold gaming, award velocity, new-vendor-large-award.

### Scanner (`scanner/`)
- `downloader.py` — `download_soi(year)` downloads ZIP, extracts CSV. `download_bmf_national()` downloads all 52 state files. `load_soi(year)` joins SOI with BMF for names.
- `analyzer.py` — `scan_population()` computes 11 anomaly metrics, returns scored DataFrame. `BEAT_FILTERS` maps beat names to NTEE prefixes.
- `rankings.py` — `create_scan_snapshot()` generates dated directory with methodology, beat reports, parameters, README.

### Output (`output/`)
- `memo.py` — `generate_memo()` produces markdown investigation memos with smoking gun section, entity tables, network diagram, timeline, flags.
- `mermaid.py` — `to_html()` wraps Mermaid in standalone HTML with dark theme.
- `report.py` — **DOES NOT EXIST.** This is the interactive HTML report generator from the plan. Highest priority unbuilt feature.

### Other
- `case_manager.py` — `Case` class with `ingest_results()`, `create_pre_registration()`, `get_summary()`, `_generate_evidence_files()`. Cases live in `cases/{slug}/`.
- `enrichment.py` — `auto_enrich()` follows up on high-priority entities. `suggest_next_moves()` generates investigative suggestions.
- `forensics.py` — `sha256_file()`, `sha256_bytes()`, `cache_response()`, `build_provenance()`, `build_chain_of_custody()`, `submit_to_wayback()`, `generate_methodology()`. **Functions exist but are NOT called in the main pipeline.**

### Slash Commands (`~/.claude/commands/`)
- `investigate.md` — Main investigation skill
- `investigate-setup.md` — API key setup wizard
- `watchlist.md` — Watchlist management
- `scan.md` — Population scanner

### Research (`research/`)
- `SYNTHESIS.md` — Master synthesis connecting all findings
- `methodology/MHEES.md` — Evidence evaluation system
- `methodology/DATA_SOURCES.md` — All 7 sources documented
- `methodology/SMOKING_GUN_DETECTORS.md` — All 14 detectors
- `scans/2026-04-10_national/` — First national scan snapshot
- `scans/2026-04-10_PA/` — First PA scan snapshot

---

## Brian's Active Investigations

1. **PWSA Board Governance** — Near-complete with PublicSource. 98.6% unanimity rate, $1.15B authorized with no questions. The toolkit supplements with federal contract/litigation data.
2. **National Ground Game / Soul Strategies** — PAC fraud allegations. $344,600 in payments to chair's own company. Needs FEC Schedule B direct query by committee ID.
3. **Ohio River Corridor / Project CURRENT** — Dakota James case. Pre-registration phase. Not yet in the toolkit.
4. **Unfuck America Tour** — Framework complete, needs active reporting.

## Brian's Publication Targets

- **The Lever** (David Sirota) — Corporate corruption, revolving door, dark money. Needs: public records only, dollar amounts, named individuals, repeating patterns.
- **PublicSource** — Pittsburgh local accountability. PWSA story already in progress with Rich Lord and Tory Basile.
- **Memory Hole** (own imprint) — Cold cases, institutional corruption, forgotten stories.

---

## What the Next Instance Should Build (Priority Order)

### 1. Interactive HTML Report Generator (`output/report.py`)
Self-contained HTML file with: HEAT score badge, collapsible evidence chains with MHEES badges, interactive Mermaid network graph, timeline view, smoking gun cards with multiplier breakdowns, methodology footer with git hash. No external CDN dependencies. Must work offline from a USB drive in 2031. This is the "wow factor" that's missing.

### 2. Wire Forensics Into Pipeline
Call `forensics.cache_response()` on every API response. Call `forensics.build_provenance()` when saving evidence files. Call `forensics.submit_to_wayback()` for web sources. Add provenance metadata to every evidence file. Make the chain of custody real, not just functions sitting unused.

### 3. Fix the False Positive Issue
The Ghost Contractor detector fires on ProPublica revenue connections even after the `relation_type` fix to "funding". The detector should explicitly skip `relation_type == "funding"` connections. Also fix the PA scan generating `top_100_national.md` (should only generate PA-specific reports).

### 4. Build the Archive Contingency
- GitLab mirror: `git remote add gitlab [url]`
- Cloud sync: rclone to Backblaze B2 or similar
- Wayback + archive.ph auto-submission for web evidence
- OpenTimestamps for critical milestones

### 5. FEC Schedule B Direct Query
Add a method to `openfec.py` that queries disbursements by committee_id, not entity name. This unblocks the National Ground Game investigation.

### 6. Improve Connection Mapping
The biggest systemic issue. Most sources return 0 connections. Options:
- For OpenSanctions: use the `/match` endpoint to find related entities, then query their connections
- For SEC: parse SC 13D/G filings for beneficial ownership
- For CourtListener: extract party names from case names as connection edges
- For ProPublica: the officer/director connections from `get_connections()` need the filing detail endpoint to work (currently returns 404 for most object_ids)

### 7. Nonprofit Beat Deep Scanner
Add scheduled weekly scan that: downloads fresh IRS data, runs full population scan, diffs against previous scan, flags new high-anomaly orgs, drafts email alert. The infrastructure exists (`scanner/`) but the scheduled task doesn't.

---

## Key Design Decisions to Preserve

1. **Multiplicative scoring, not additive.** The smoking gun system scores intersections, not sums. Sanctions + contracts near each other is not +40+20. The multipliers (temporal, source independence, concealment, recency) are the intelligence.

2. **MHEES on everything.** Every finding gets a six-axis evidence code. Judgment axes (R†, I†) require justification. This is the Trustless Journalism Protocol.

3. **Being right over being first.** The system is designed to avoid false positives. It requires proven paths between entities, not just name matches. The Trump Foundation initially failed validation because the system correctly refused to make assumptions from partial data.

4. **The research repository is the product.** `research/` is the shareable, auditable output. It uses relative links, dated snapshots, METHODOLOGY.md in every scan directory, and git-tracked provenance. This is what gets sent to editors.

5. **Cases accumulate.** Each `/investigate` search adds to a persistent case file, not a throwaway report. The case grows a knowledge graph over time.

---

## Memory Files

Check `~/.claude/projects/-Users-briannuckols/memory/` for:
- `user_journalist_identity.md` — Brian's background and methodology
- `reference_mhees.md` — MHEES notation system
- `reference_hesitation_media_docs.md` — Google Drive IDs for methodology docs

Also check `~/.claude/CLAUDE.md` for writing style rules (no AI slop, no em-dashes, etc.).

---

*Handoff generated April 10, 2026. 8 commits, 153 files, 66 investigations, 301,484 nonprofits scored.*
