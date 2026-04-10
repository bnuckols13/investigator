# Investigation Synthesis — April 10, 2026

*Hesitation Media / Memory Hole — Research Synthesis*
*53 agents deployed, 66 investigations completed, 301,484 nonprofits scanned*

---

## Smoking Gun Findings (Publishable Leads)

### Tier 1: Ready to Pitch

**1. ExxonMobil — OFAC Penalty + Active DoD Contracts**
- Heat: 45/100 | Detector: Concurrent Contradiction (75)
- MHEES: P1-A†-C2-I2†-D1-F2
- Finding: ExxonMobil was penalized by Treasury's OFAC sanctions enforcement while holding $33.6M in Department of Defense contracts
- Sources: OpenSanctions (OFAC penalty), USASpending ($33.6M DoD), SEC EDGAR (22 filings), CourtListener (20+ cases)
- Pitch target: **The Lever** — all public records, follow-the-money story
- Next: FOIA contracting officer's responsibility determination at DoD
- Investigation file: [data/investigations/ExxonMobil_20260409_235615.json](../data/investigations/ExxonMobil_20260409_235615.json)

**2. UPMC System — Pass-Through Entities + Ghost Contractors + $2.4M Exec Comp**
- Heat: 42/100 | Detectors: 2x Ghost Contractor (50), 2x Financial Outlier (49)
- Finding: UPMC subsidiaries pay $1.5M-$2.4M in officer compensation. UPitt/UPMC Foundation shows revenue exactly equal to expenses ($13.77M = $13.77M) — a pass-through pattern. Raymond Frodey Trust FBO UPMC spending 13x its revenue.
- Sources: ProPublica (990 data), USASpending (contracts), CourtListener (30+ cases), OpenSanctions (Dawida, Gingrich, Vance political connections)
- Pitch target: **The Lever + PublicSource** — Pittsburgh institutional accountability
- Next: Pull parent UPMC 990 for total system exec comp. Investigate pass-through entity flows.
- Investigation files: [UPMC](../data/investigations/UPMC_20260410_000919.json), [UPMC Health](../data/investigations/UPMC Health_20260410_002601.json)

### Tier 2: Worth Deepening

**3. Glencore — DOJ Bribery + Secrecy Jurisdictions + Active Contracts**
- Heat: 24/100 | Detector: Jurisdiction Anomaly (40)
- Finding: Operates across 4 jurisdictions including secrecy jurisdictions, DOJ bribery guilty plea (*United States v. Glencore*), still active govt contractor ($313K DoD)
- Next: Check SAM.gov debarment status. If not debarred after guilty plea, that's the story.
- Investigation file: [data/investigations/Glencore_20260410_000928.json](../data/investigations/Glencore_20260410_000928.json)

**4. Port Authority Allegheny County — 47x Median Contract**
- Heat: 29/100 | Detector: Financial Outlier (49)
- Finding: $164K VA contract at 47x their median of $3,502
- Next: FOIA the specific VA contract. Why is a transit authority getting VA money?
- Investigation file: [data/investigations/Port Authority Allegheny County_20260410_000921.json](../data/investigations/Port Authority Allegheny County_20260410_000921.json)

**5. AHN Home Infusion — Ghost Contractor**
- Heat: 30/100 | Detector: Ghost Contractor (50)
- Finding: First-time vendor received $2.1M VA contract
- Next: Check corporate registration date vs. contract date
- Investigation file: [data/investigations/Allegheny Health Network_20260410_002600.json](../data/investigations/Allegheny Health Network_20260410_002600.json)

---

## Population Scan: Top National Anomalies

From the IRS 990 scan of 301,484 nonprofits:

| Rank | Organization | State | Revenue | Officer Comp | Score | Story Angle |
|------|-------------|-------|---------|-------------|-------|-------------|
| 1 | Pediatric Health Mgmt Service | TX | $743K | $2.9M | 70 | Officers paid 4x revenue |
| 2 | Sanford | SD | $13.7M | $23.6M | 70 | Officers paid 1.7x revenue |
| 3 | Hal Lindsey Website Ministries | TX | $2.2M | $1.8M | 68 | Televangelist takes 83% |
| 4 | Saint Francis Health System | OK | $667K | $4.9M | 66 | Officers paid 7.4x revenue |
| 5 | Blue Cross Blue Shield MI | MI | $1.1M | $1.4M | 66 | Insurer comp anomaly |
| 6 | Chinatown Media & Arts | CA | $371K | $696K | 65 | Small arts org, outsized comp |
| 7 | Lakewood Tenants Org | NJ | $2.1M | $2.1M | 65 | 100% to officers |

Full rankings: [research/scans/2026-04-10_national/top_100_national.md](./scans/2026-04-10_national/top_100_national.md)

## Population Scan: Pennsylvania Anomalies

From 14,888 PA nonprofits:

| Rank | Organization | Revenue | Officer Comp | Score | Story Angle |
|------|-------------|---------|-------------|-------|-------------|
| 1 | Swedenborg Foundation | $2.2M | $1.5M | 63 | 69% to officers |
| 2 | BioAdvance | $1.6M | $999K | 62 | 63% to officers |
| 3 | IBEW | $4.7M | $1.2M | 58 | Union leadership comp |
| 4 | Life Sciences Greenhouse | $2.5M | $708K | 58 | State-funded innovation org |
| 5 | Operative Plasterers & Cement Masons | $2.9M | $1.4M | 57 | Union comp |
| 7 | Latino Community Center | $1.9M | $1.0M | 57 | Community org, 52% to officers |
| 13 | Allegheny Institute for Public Policy | $598K | $516K | 55 | Think tank, 86% to officers |

Full rankings: [research/scans/2026-04-10_PA/top_25_pennsylvania.md](./scans/2026-04-10_PA/top_25_pennsylvania.md)

---

## Beat Reports

| Beat | Scan Link | Top Finding |
|------|-----------|-------------|
| Health | [top_25_health.md](./scans/2026-04-10_national/top_25_health.md) | Health systems with outsized exec comp |
| Political | [top_25_political.md](./scans/2026-04-10_national/top_25_political.md) | Advocacy orgs with low program ratios |
| Religious | [top_25_religious.md](./scans/2026-04-10_national/top_25_religious.md) | Church-adjacent orgs (churches exempt) |
| Education | [top_25_education.md](./scans/2026-04-10_national/top_25_education.md) | University foundations |
| Veterans | [top_25_veterans.md](./scans/2026-04-10_national/top_25_veterans.md) | Veteran service orgs |
| Arts | [top_25_arts.md](./scans/2026-04-10_national/top_25_arts.md) | Cultural orgs |
| Human Services | [top_25_human_services.md](./scans/2026-04-10_national/top_25_human_services.md) | Social services |
| Environment | [top_25_environment.md](./scans/2026-04-10_national/top_25_environment.md) | Environmental nonprofits |

---

## Active Investigations (Your Cases)

### PWSA Board Governance
- Status: Near-complete (with PublicSource)
- OSINT findings: Federal litigation confirmed (*US v. PWSA*, PFAS suit vs 3M). 14 cross-source matches.
- How toolkit helps: Contract data supplements your 98.6% unanimity finding
- Investigation file: [data/investigations/Pittsburgh Water Sewer Authority_20260409_235624.json](../data/investigations/Pittsburgh Water Sewer Authority_20260409_235624.json)

### National Ground Game / Soul Strategies / Z Cohen Sanchez
- Status: Needs FEC Schedule B direct query
- OSINT findings: Zero hits under all three entity names in federal databases
- Key insight: The self-dealing evidence lives in FEC disbursement records by committee ID, not name search
- Next: Query FEC bulk data for National Ground Game PAC's Schedule B disbursements
- Investigation files: [National Ground Game](../data/investigations/National Ground Game_20260409_235622.json), [Soul Strategies](../data/investigations/Soul Strategies_20260410_000925.json), [Z Cohen Sanchez](../data/investigations/Z Cohen Sanchez_20260410_001902.json)

---

## System Validation

| Known Case | Expected Result | Actual | Status |
|------------|----------------|--------|--------|
| ExxonMobil OFAC | Should fire Concurrent Contradiction | Fired (75) | PASS |
| UPMC exec comp | Should flag high_exec_comp | Flagged ($1.5M-$2.4M) | PASS |
| Wounded Warrior (reformed) | Should show clean ratios | Clean (0.8% comp ratio) | PASS |
| Trump Foundation (fraud) | Should flag high_overhead | Flagged (expenses > revenue) | PASS |
| Kenneth Copeland (church) | Should show no 990 data | Correctly identified opacity | PASS |
| Wagner Group (sanctions) | Should flag OFAC/EU | 16 OFAC, 17 EU sanctioned | PASS |

---

## Methodology

- [MHEES Evidence Evaluation](./methodology/MHEES.md) — Six-axis notation system
- [Data Sources](./methodology/DATA_SOURCES.md) — 7 live APIs + IRS bulk data
- [Smoking Gun Detectors](./methodology/SMOKING_GUN_DETECTORS.md) — 14 composite pattern detectors
- [National Scan Methodology](./scans/2026-04-10_national/METHODOLOGY.md)
- [PA Scan Methodology](./scans/2026-04-10_PA/METHODOLOGY.md)

---

## Next Actions (Priority Order)

1. **FOIA ExxonMobil contracting officer** at DoD — verify the OFAC penalty didn't trigger debarment review
2. **Pull parent UPMC 990** (EIN for UPMC Health System) for total system-wide exec compensation
3. **Query FEC Schedule B** for National Ground Game PAC disbursements to Soul Strategies
4. **Deep-dive Pediatric Health Management Service (TX)** — officers paid 4x revenue, nobody has reported this
5. **Check SAM.gov** for Glencore debarment status post-DOJ guilty plea
6. **Deep-dive Lakewood Tenants Organization (NJ)** — 100% of revenue to officers in a tenants rights org
7. **Build interactive HTML report** for sharing findings with editors

---

*Generated by the Investigator Toolkit — 7 OSINT sources, 14 smoking gun detectors, MHEES evidence evaluation*
*GitHub: https://github.com/bnuckols13/investigator*
