# Investigator Toolkit

This is an OSINT investigative journalism toolkit. When working in this directory:

## Architecture

- `sources/` — API adapters for 6 OSINT databases. Each implements `BaseSource` with `search_entity()`, `get_connections()`, `get_events()`.
- `analysis/` — Entity resolution (RapidFuzz), network graphs (NetworkX), lead scoring, timeline analysis, ownership tracing, revolving door detection, procurement anomalies.
- `case_manager.py` — Persistent investigation cases under `cases/`. Each case accumulates findings across searches.
- `enrichment.py` — Auto-enrichment pipeline that deepens findings for high-priority leads.
- `investigate.py` — CLI entry point. Run `python3 investigate.py search "query"` to search all sources.

## Slash Commands

- `/investigate [entity]` — Full investigation with case persistence and narrative analysis
- `/investigate-setup` — Guided API key setup
- `/watchlist [add|remove|list|scan]` — Entity monitoring

## Key Patterns

When presenting investigation results, lead with the story, not the data. Identify the most interesting connection or anomaly and build the narrative around it. Always suggest specific next moves.

## API Keys

Stored in `.env`. Run `/investigate-setup` to configure. USASpending works without any key.
