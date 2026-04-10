# Data Sources

The investigator toolkit queries 7 independent public databases plus IRS bulk data.

## Live API Sources

| # | Source | What It Contains | Auth | Rate Limit |
|---|--------|-----------------|------|-----------|
| 1 | **OpenSanctions** | Sanctions lists, PEPs, crime databases from 100+ government sources | API key | 50 req/mo (trial) |
| 2 | **SEC EDGAR** | Mandatory corporate filings: 10-K, 8-K, Form 4, SC 13D | User-Agent | 10 req/sec |
| 3 | **OpenFEC** | Campaign contributions, PAC data, committee filings | API key | 1000/hr |
| 4 | **USASpending** | Federal contracts, grants, awards | None | Unlimited |
| 5 | **CourtListener** | Federal court dockets, opinions, PACER data | Token (optional) | 5000/hr |
| 6 | **ProPublica Nonprofit Explorer** | IRS 990 filings: revenue, expenses, officer compensation | None | Unlimited |
| 7 | **Aleph/OCCRP** | 3B+ records: corporate registries, leaked documents, sanctions | API key | N/A |

## IRS Bulk Data (Scanner)

| Source | What It Contains | Format | Size |
|--------|-----------------|--------|------|
| **SOI Tax Stats** | All Form 990 financial data for every US nonprofit | CSV (from ZIP) | ~250MB/year |
| **EO BMF** | Organization names, addresses, NTEE codes, EINs | CSV (by state) | ~300MB total |

## Source Independence

Findings corroborated across 2+ independent databases are significantly more credible than single-source findings. The MHEES C axis (Corroboration) reflects this:
- C1: 3+ independent sources
- C2: 2 independent sources
- C3: Single source + supporting data
- C4: Single source only
