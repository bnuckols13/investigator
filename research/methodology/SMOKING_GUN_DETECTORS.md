# Smoking Gun Composite Detectors

14 pattern detectors that look for multi-source intersections making innocent explanations implausible.

## Scoring

`final_score = min(raw_score * temporal * sources * concealment * recency, 100)`

| Multiplier | Logic |
|---|---|
| Temporal proximity | 0-2 days: x1.8, 3-7: x1.5, 8-30: x1.2, 31-90: x1.0, 91-365: x0.8 |
| Source independence | 2 sources: x1.3, 3: x1.5, 4+: x1.7 |
| Concealment layers | 1 intermediary: x1.15, 2: x1.3, 3+: x1.5 |
| Recency | Last 30 days: x1.3, 90: x1.2, 1 year: x1.0, older: x0.8 |

## Tier 1: Direct Smoking Guns (base 80-100)

| Detector | Pattern | Base |
|---|---|---|
| Sanctions Evasion Chain | Sanctioned person -> ownership chain -> US govt contracts | 85 |
| Quid Pro Quo | Campaign donation -> contract award within 365 days | 80 |
| Insider Trading Signal | Stock trade within 14 days of material corporate event | 85 |
| Revolving Door Contract | PEP connected to company holding govt contracts | 85 |
| Self-Dealing | Nonprofit officer also connected to entity receiving payments from nonprofit | 85 |

## Tier 2: Strong Circumstantial (base 50-79)

| Detector | Pattern | Base |
|---|---|---|
| Concurrent Contradiction | Entity on sanctions list AND holding active contracts | 75 |
| Shell Company Obfuscation | Circular ownership + secrecy jurisdictions + contracts | 60 |
| Threshold Gaming | Contracts clustering below reporting thresholds | 60 |
| Ghost Contractor | First-time vendor, large contract, connected to flagged entity | 55 |

## Tier 3: Indicators (base 20-49)

| Detector | Pattern | Base |
|---|---|---|
| Jurisdiction Anomaly | 3+ countries including secrecy jurisdictions | 35 |
| Network Bridge | High betweenness connecting flagged clusters | 35 |
| Temporal Clustering | 3+ events from 2+ sources in 7-day window | 30 |
| Financial Outlier | Contract > 3x entity's median | 30 |
