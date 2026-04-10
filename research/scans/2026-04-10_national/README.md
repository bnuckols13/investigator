# Scan: national — 2026-04-10

## Summary

- **301,484** organizations scanned
- **248,236** organizations with anomaly flags
- **3003** organizations scoring above 50
- **Average anomaly score:** 20.6

## Reports

- [METHODOLOGY.md](./METHODOLOGY.md)
- [parameters.json](./parameters.json)
- [raw_scores.csv](./raw_scores.csv)
- [top_100_national.md](./top_100_national.md)
- [top_25_arts.md](./top_25_arts.md)
- [top_25_education.md](./top_25_education.md)
- [top_25_environment.md](./top_25_environment.md)
- [top_25_health.md](./top_25_health.md)
- [top_25_human_services.md](./top_25_human_services.md)
- [top_25_international.md](./top_25_international.md)
- [top_25_pennsylvania.md](./top_25_pennsylvania.md)
- [top_25_political.md](./top_25_political.md)
- [top_25_religious.md](./top_25_religious.md)
- [top_25_veterans.md](./top_25_veterans.md)

## Methodology

See [METHODOLOGY.md](./METHODOLOGY.md) for complete documentation of data sources,
scoring formula, and known limitations.

## Reproducibility

```bash
cd ~/investigator
git checkout 12c695d9693c
python investigate.py scan run --scope national
```

Compare SHA-256 hashes in [parameters.json](./parameters.json) to verify data integrity.
