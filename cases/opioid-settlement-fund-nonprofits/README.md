# Investigation: Opioid Settlement Fund Nonprofits

**Case opened:** 2026-04-10
**Status:** Active
**Investigator:** Brian Nuckols / Hesitation Media (Memory Hole)
**Methodology:** Trustless Journalism Protocol — full transparency, reproducible OSINT

## Trustless Protocol Declaration

This investigation follows the Hesitation Media Trustless Journalism Protocol. Every search query, data source, entity resolution, and analytical conclusion is documented in the case files. Anyone with access to the same OSINT databases can reproduce these findings.

**Sources queried:**
- OpenSanctions (sanctions lists, PEP databases)
- SEC EDGAR (regulatory filings)
- OpenFEC (campaign finance)
- USASpending (federal contracts and grants)
- CourtListener (federal court records)
- ProPublica Nonprofit Explorer (990 filings)

**Verification standard:** Findings corroborated across 2+ independent sources carry higher evidentiary weight. Single-source findings are flagged as leads requiring verification.

## Summary of Findings

The $56 billion opioid settlement, the largest civil settlement in American history, is being distributed through a patchwork of state-created entities with minimal standardized oversight. Our OSINT sweep identified structural conditions for waste, fraud, and corruption:

### Key Findings

1. **Purdue Pharma held active DoD and VA contracts** ($265K+) for medical supplies while the opioid litigation was building. USASpending records show 20 contracts with the Department of Defense and Department of Veterans Affairs.

2. **McKinsey & Company** appears across multiple lawsuits from health and welfare funds. McKinsey paid $650M (Dec 2024) to resolve DOJ criminal investigation for advising Purdue Pharma's OxyContin sales strategy. Senior partner Martin Elling pleaded guilty to obstruction. 37 McKinsey consultants simultaneously staffed FDA contracts and advised Purdue.

3. **OneOhio Recovery Foundation** was sued at the Ohio Supreme Court (172 Ohio St. 3d 523, May 2023) by Harm Reduction Ohio for operating in secrecy despite controlling $440M in public settlement funds. The Ohio Senate attempted to exempt OneOhio from bribery and ethics laws.

4. **Documented fund diversion** (corroborated via web sources):
   - West Virginia: $3.5M+ in settlement funds spent on regional jail bills
   - New Jersey: $45M diverted to hospitals, bypassing advisory board
   - New Jersey (Irvington): $632K on "Opioid Awareness" concerts with zero treatment content
   - Nationwide: $61M on law enforcement equipment (Tasers, drones, gun silencers)
   - 20% of all settlement spending untrackable through public records (KFF Health News)

5. **Structural opacity**: States created "private nonprofits" to distribute public settlement money, then claimed those entities are exempt from public records laws. Only 3 states have specific processes for reporting misuse. Only New York and South Carolina have robust conflict-of-interest protocols.

### Opioid Master Disbursement Trust II

The actual money pipeline. Filed suit against Covidien Unlimited Company (Medtronic subsidiary) in US Bankruptcy Court, D. Delaware (22-50433, filed 2022-10-11).

## Case Files

| File | Contents |
|------|----------|
| `case.json` | Case metadata, search history, entity/connection counts |
| `entities.json` | All 60 resolved entities with source, type, properties, and flags |
| `connections.json` | Entity-to-entity relationships (contracts, directorships, etc.) |
| `events.json` | Timeline events extracted from connections |
| `scores.json` | Investigative priority scores with component breakdown |
| `smoking_guns.json` | Automated pattern detection results |
| `chain_of_custody.md` | Complete provenance chain for all data |
| `investigation_log.md` | Timestamped log of all searches and discoveries |
| `network.html` | Interactive network visualization |
| `report.html` | Generated investigation report |

## Searches Executed

| # | Query | Timestamp | New Entities | New Connections |
|---|-------|-----------|--------------|-----------------|
| 1 | `opioid settlement fund nonprofits` | 2026-04-10 19:51 | 20 | 0 |
| 2 | `OneOhio Recovery Foundation opioid` | 2026-04-10 19:51 | 1 | 0 |
| 3 | `opioid abatement treatment nonprofit SAMHSA grant` | 2026-04-10 19:52 | 10 | 2 |
| 4 | `opioid settlement fund fraud misuse` | 2026-04-10 19:52 | 17 | 0 |
| 5 | `McKinsey Company opioid consulting` | 2026-04-10 19:52 | 9 | 0 |
| 6 | `opioid recovery foundation abatement council nonprofit 501c3` | 2026-04-10 19:52 | 3 | 0 |

## Reproducibility

To reproduce these findings:

1. Clone the investigator toolkit
2. Configure API keys for the sources listed above (see `/investigate-setup`)
3. Run each query in the table above against the same sources
4. Compare entity resolution results

Note: OpenSanctions was rate-limited (429) during this session. Results from that source are incomplete and should be re-run.

## Next Investigative Steps

1. FOIA OneOhio board minutes and financial disbursements post-Supreme Court ruling
2. Pull McKinsey's current federal contracts via USASpending post-criminal plea
3. Search ProPublica 990 database for opioid-related nonprofit executive compensation
4. Cross-reference board members of state opioid settlement entities against OpenFEC and lobbying disclosures
5. Target West Virginia and New Jersey for deeper investigation
6. File FOIA with HHS/SAMHSA for full list of opioid abatement grants since 2022

## MHEES Evidence Rating

Per the Modified Hesitation Evidence Evaluation System:

- **Provenance**: Mixed. Court records and USASpending data are primary sources (P+). Web-sourced reporting is secondary (P-).
- **Reliability**: Court filings and federal spending data are high reliability (R†+). Settlement diversion examples rely on journalism (R†-).
- **Corroboration**: McKinsey findings corroborated across court records, DOJ, and multiple journalistic sources (C+). OneOhio findings corroborated across court records and journalism (C+).
- **Independence**: Sources are independent from each other (I†+).
- **Directness**: Most findings are direct evidence from court records and government databases (D+).
- **Freshness**: Data current as of April 2026 (F+).

## License

This investigation is published under the Hesitation Media Trustless Journalism Protocol. All data is derived from public sources. Reproduce, verify, challenge.
