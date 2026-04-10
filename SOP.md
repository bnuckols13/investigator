# Investigator Toolkit — Standard Operating Procedure

## 1. Starting an Investigation

### New Subject

```
/investigate [entity name]
```

This creates a new case file under `cases/`, searches all configured OSINT sources, and presents findings with suggested next steps. Each subsequent search adds to the same case.

### Continuing an Existing Investigation

Use `/investigate` with follow-up queries. The system checks for existing cases and adds new findings rather than starting from scratch. Ask things like:
- "dig deeper on [entity]"
- "who connects [entity A] to [entity B]"
- "what contracts did [company] receive"
- "check [entity] against sanctions"

### Checking Active Cases

```
/investigate cases
```

Lists all open investigations with entity counts, connection counts, and flags found.

## 2. Source Priority and Credibility

Not all sources carry equal weight. When evaluating findings:

| Tier | Source | Credibility Notes |
|------|--------|-------------------|
| 1 | **Aleph/OCCRP** | Primary documents, leaked records, corporate registries. High evidentiary value. |
| 1 | **OpenSanctions** | Official government sanctions lists and PEP databases. Authoritative. |
| 2 | **SEC EDGAR** | Mandatory regulatory filings. Legally binding disclosures. |
| 2 | **CourtListener** | Federal court records. Public legal proceedings. |
| 3 | **OpenFEC** | Self-reported campaign finance data. Check for amended filings. |
| 3 | **USASpending** | Federal award data. Amounts and recipients are reliable; descriptions vary. |

A finding corroborated across 2+ sources (especially Tier 1 + Tier 2) is significantly more reliable than a single-source hit.

## 3. Interpreting Lead Scores

The scoring algorithm assigns points based on:

| Component | Points | What It Means |
|-----------|--------|---------------|
| Sanctions/PEP hit | +40 each (max 80) | Entity appears on an official watchlist |
| Government contracts | +20 each (max 60) | Entity receives federal funding |
| Court cases | +25 each (max 75) | Entity is involved in federal litigation |
| Campaign finance | +15 each (max 45) | Significant political donations |
| Corporate complexity | +10 per directorship >2 (max 30) | Unusual number of corporate roles |
| Cross-jurisdiction | +15 per country >1 (max 45) | Multi-country presence |
| Network centrality | +20 | Entity is a bridge between otherwise disconnected groups |
| Recency | +10 | Activity in the last 90 days |

**Score > 80**: Drop everything and look at this.
**Score 40-80**: Significant investigative interest. Warrants deeper research.
**Score 10-40**: Background entity. Useful for context but may not be a lead on its own.
**Score 0**: No red flags detected in available data.

## 4. Verification Workflow

OSINT findings are leads, not conclusions. Before publishing:

1. **Cross-reference**: Does the finding appear in 2+ independent sources?
2. **Verify identity**: Is this the same "John Smith" or a false positive? Check dates, locations, middle names.
3. **Check dates**: Is the information current? Sanctions are added and removed. Directors change.
4. **Pull primary documents**: The toolkit surfaces leads. The documents themselves are the evidence. Pull the actual SEC filing, court docket, or contract.
5. **Seek comment**: Contact the subject for response before publication.

## 5. Watchlist Management

### Adding Entities to Monitor

```
/watchlist add "Entity Name"
```

The daily scan (7am) checks all watchlisted entities for new appearances across all sources. When changes are detected, an email alert is drafted.

### What Triggers an Alert

- New entity matches that weren't in the previous scan
- New sanctions or PEP list additions
- New court filings or SEC filings
- Changes in lead score
- New connections discovered

### Best Practices

- Watch both the person AND their known companies
- Watch alternate spellings and transliterations
- Review and prune the watchlist monthly
- Act on alerts within 24 hours, since competitors may be watching the same sources

## 6. Network Graph Analysis

The Mermaid network diagrams use visual conventions:

- **Rounded rectangles** = persons
- **Rectangles** = companies
- **Hexagons** = organizations
- **!! prefix** = sanctioned or OFAC-listed (yellow highlighting)
- **\* prefix** = politically exposed person (PEP)
- **Edge labels** = relationship type (ownership %, directorship, contribution amount)

When reading a graph, look for:
- **Hub nodes**: Entities with many connections may be controlling interests
- **Bridge nodes**: Entities connecting otherwise separate groups are investigatively significant
- **Cycles**: Circular ownership is a shell company red flag
- **Missing connections**: Two entities that should be connected but aren't may indicate deliberate concealment

## 7. OPSEC Considerations

- API queries are logged by the data providers. Assume your search patterns are visible.
- Case files contain sensitive investigative data. Do not commit `.env` or `cases/` to public repositories.
- The `.gitignore` excludes API keys and case data by default.
- For high-sensitivity investigations, consider using Tor or a VPN when querying OCCRP Aleph.
- Be aware that some OpenSanctions queries include the entity name in plaintext URLs.

## 8. Morning Intelligence Brief

A daily brief is delivered at ~6:47am covering:
- **Watchlist alerts**: Any changes to monitored entities
- **Current events**: Top investigative stories with angles
- **Memory hole**: Significant stories from 5, 10, and 25 years ago today, with questions about what happened next

The brief is drafted as a Gmail message. Review it with your morning coffee.
