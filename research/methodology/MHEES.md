# MHEES — Memory Hole Evidence Evaluation System v0.2

Every significant finding carries a six-axis MHEES notation code:

**`P[1-6] - R[A-F]† - C[1-5] - I[1-6]† - D[1-4] - F[1-4]`**

The dagger symbol (†) marks judgment axes requiring written justification.

## Axes

| Axis | Name | Scale |
|------|------|-------|
| **P** | Provenance | P1 = verified public record ... P6 = analytical product |
| **R†** | Source Reliability | A = completely reliable ... F = cannot judge |
| **C** | Corroboration | C1 = 3+ independent sources ... C5 = contested |
| **I†** | Credibility | I1 = confirmed by other means ... I6 = cannot judge |
| **D** | Inference Distance | D1 = direct statement ... D4 = interpretive |
| **F** | Defeasibility | F1 = falsification tested ... F4 = non-falsifiable |

## Reading an MHEES Code

Example: `P1-A†-C2-I2†-D1-F2`

This means: verified public record (P1), from a completely reliable source (A†, with justification), dual independent corroboration (C2), probably true (I2†, with justification), direct evidence (D1), falsification conditions specified (F2).

## Source Reliability Mapping

| Source | R† Rating | Rationale |
|--------|-----------|-----------|
| SEC EDGAR | A | Mandatory regulatory filings, legally binding |
| USASpending | A | Official federal award records |
| CourtListener | A | Federal court records, public proceedings |
| ProPublica/IRS 990 | A | Mandatory nonprofit tax filings |
| OpenSanctions | B | Compiled from authoritative government lists |
| OpenFEC | B | Self-reported campaign finance |
| Aleph/OCCRP | B | Curated corporate registries + leaked documents |

Full methodology: see the Trustless Journalism White Paper.
