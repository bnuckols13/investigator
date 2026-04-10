# Methodology: Nonprofit Population Scan — PA

*Generated: 2026-04-10T08:35:06.078930*
*Tool version: 52c6fb3acc2f*

## Parameters

```json
{
  "state": "PA",
  "beat": null,
  "min_revenue": 100000,
  "year": 2024
}
```

## Data Sources

| Source | Version | URL | Retrieved |
|--------|---------|-----|----------|
| IRS SOI Tax Stats 2024 | 2024 | https://www.irs.gov/pub/irs-soi/2024eofinextract990.csv | 2026-04-10T08:35:05.944152 |


## Anomaly Scoring

| Metric | Formula | Weight | Threshold |
|--------|---------|--------|----------|
| exec_comp_ratio | officer_comp / total_expenses | 15 | > 10% = flagged |
| exec_comp_absolute | officer_comp > threshold | 10 | > $500K |
| program_ratio | program_revenue / total_revenue | 15 | < 65% = flagged |
| overhead_ratio | 1 - (program / expenses) | 10 | > 50% = flagged |
| fundraising_efficiency | fundraising_exp / contributions | 10 | > 50% = flagged |
| deficit_spending | (expenses - revenue) / revenue | 5 | > 20% = flagged |
| asset_hoarding | assets / revenue | 5 | > 5x = flagged |
| comp_vs_revenue | officer_comp / expenses | 10 | > 10% = flagged |


**Composite score:** Weighted sum of all metrics, 0-100. Higher = more anomalous.

## Known Limitations

- IRS 990 data is self-reported by the organizations.
- Filing year may lag actual fiscal year by 1-2 years.
- Church/religious organizations exempt from 990 filing are invisible to this scan.
- Anomaly scores identify statistical outliers, not proven fraud.
- Multi-year trend analysis requires comparing across SOI extract years.
- Officer compensation may be split across affiliated entities.

## Reproducibility

To reproduce this analysis:
1. Clone the repository: `git clone https://github.com/bnuckols13/investigator.git`
2. Checkout the commit: `git checkout 52c6fb3acc2f`
3. Install dependencies: `pip install -e .`
4. Run: `python investigate.py scan run` with the parameters above
5. Compare SHA-256 hashes of source data files to verify you have the same inputs

## Chain of Custody

All source data files are archived in `data/irs/` with SHA-256 hashes recorded.
Raw API responses are cached in `data/cache/` with provenance metadata.
The git commit hash of this analysis serves as a forensic seal.
