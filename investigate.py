#!/usr/bin/env python3
"""Multi-source OSINT investigation CLI."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from models import SearchResult

console = Console()


async def run_search(
    query: str,
    entity_type: str | None = None,
    source_filter: list[str] | None = None,
    limit: int = 25,
) -> SearchResult:
    """Execute a multi-source investigation search."""
    from sources import get_enabled_sources
    from analysis.entity_resolver import resolve_entities, deduplicate
    from analysis.network import build_graph, analyze_graph, to_mermaid
    from analysis.scoring import score_all

    start_time = datetime.now()

    # Get enabled sources
    all_sources = get_enabled_sources()
    if source_filter:
        all_sources = [s for s in all_sources if s.name in source_filter]

    if not all_sources:
        console.print("[red]No sources available. Check your .env configuration.[/red]")
        return SearchResult(query=query, metadata={"error": "No sources configured"})

    source_names = [s.name for s in all_sources]
    console.print(f"[blue]Searching {len(all_sources)} sources:[/blue] {', '.join(source_names)}")

    # Fan out searches concurrently
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Searching all sources...", total=None)

        search_tasks = [s.search_entity(query, entity_type, limit) for s in all_sources]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Process results
    all_entities = []
    sources_succeeded = []
    sources_failed = []

    for source, result in zip(all_sources, search_results):
        if isinstance(result, Exception):
            sources_failed.append(source.name)
            console.print(f"  [yellow]Warning: {source.name} failed: {result}[/yellow]")
        else:
            sources_succeeded.append(source.name)
            all_entities.extend(result)
            console.print(f"  [green]{source.name}:[/green] {len(result)} entities")

    if not all_entities:
        console.print("[yellow]No entities found across any source.[/yellow]")
        return SearchResult(
            query=query,
            metadata={
                "sources_queried": source_names,
                "sources_succeeded": sources_succeeded,
                "sources_failed": sources_failed,
            },
        )

    console.print(f"\n[blue]Total: {len(all_entities)} raw entities. Resolving duplicates...[/blue]")

    # Resolve entities across sources
    resolved_groups = resolve_entities(all_entities)
    canonical = deduplicate(all_entities)
    console.print(f"[green]Resolved to {len(resolved_groups)} distinct entities[/green]")

    # Fetch connections for top entities (by group size or cross-source matches)
    top_entities = canonical[:10]
    all_connections = []
    all_events = []

    if top_entities:
        console.print(f"\n[blue]Fetching connections for top {len(top_entities)} entities...[/blue]")

        conn_tasks = []
        event_tasks = []
        for ent in top_entities:
            # Query the entity's own source (always works)
            own_source = next((s for s in all_sources if s.name == ent.source.value), None)
            if own_source:
                conn_tasks.append(own_source.get_connections(ent.id))
                event_tasks.append(own_source.get_events(ent.id))

            # Also query USASpending for any entity (name-based search works cross-source)
            usa_source = next((s for s in all_sources if s.name == "usaspending"), None)
            if usa_source and ent.source.value != "usaspending":
                # Create a usaspending-compatible ID from the entity name
                usa_id = f"usaspending:recipient:{ent.name}"
                conn_tasks.append(usa_source.get_connections(usa_id))
                event_tasks.append(usa_source.get_events(usa_id))

            # Also query OpenFEC for person entities (campaign finance cross-reference)
            fec_source = next((s for s in all_sources if s.name == "openfec"), None)
            if fec_source and ent.entity_type.value == "person" and ent.source.value != "openfec":
                conn_tasks.append(fec_source.get_connections(f"fec:{ent.name}"))

        conn_results = await asyncio.gather(*conn_tasks, return_exceptions=True)
        event_results = await asyncio.gather(*event_tasks, return_exceptions=True)

        for r in conn_results:
            if not isinstance(r, Exception) and r:
                all_connections.extend(r)
        for r in event_results:
            if not isinstance(r, Exception) and r:
                all_events.extend(r)

        console.print(f"  [green]{len(all_connections)} connections, {len(all_events)} timeline events[/green]")

    # Auto-enrich high-priority entities (skip if this is already an enrichment sub-search)
    if limit > 10:  # Only enrich on primary searches, not sub-searches
        from enrichment import auto_enrich

        async def _enrichment_search(q, **kwargs):
            return await run_search(q, limit=10)  # limit=10 prevents recursive enrichment

        # Build a preliminary score to identify high-priority entities
        prelim_scores = score_all(canonical, all_connections, all_events, None)

        try:
            enrichment_results = await auto_enrich(
                SearchResult(query=query, entities=canonical, connections=all_connections,
                             events=all_events, scores=prelim_scores, metadata={}),
                _enrichment_search, threshold=30, max_followups=3,
            )
            for er in enrichment_results:
                for ent in er.entities:
                    if ent.id not in {e.id for e in canonical}:
                        canonical.append(ent)
                all_connections.extend(er.connections)
                all_events.extend(er.events)
            if enrichment_results:
                console.print(f"  [cyan]Auto-enrichment added {sum(len(r.entities) for r in enrichment_results)} entities from {len(enrichment_results)} follow-up searches[/cyan]")
        except Exception:
            pass  # Enrichment is non-critical

    # Build network graph
    graph = build_graph(canonical, all_connections)
    network_analysis = analyze_graph(graph)
    mermaid_diagram = to_mermaid(graph)

    # Score all entities
    scores = score_all(canonical, all_connections, all_events, graph)

    # Run smoking gun composite detectors
    console.print("\n[blue]Running smoking gun analysis...[/blue]")
    from analysis.smoking_gun import detect_all as detect_smoking_guns
    from analysis.mhees import auto_code
    sg_report = detect_smoking_guns(canonical, all_connections, all_events, graph)

    # Auto-code MHEES for each detected pattern
    for pattern in sg_report.patterns:
        if not pattern.mhees_code:
            pattern.mhees_code = auto_code(pattern)

    if sg_report.patterns:
        console.print(f"  [bold red]HEAT SCORE: {sg_report.heat_score:.0f}/100 — {len(sg_report.patterns)} patterns detected[/bold red]")
        for p in sg_report.patterns[:3]:
            console.print(f"    [{p.tier.upper()}] {p.display_name}: {p.final_score:.0f} ({p.mhees_code})")
    else:
        console.print("  [green]No smoking gun patterns detected[/green]")

    sg_data = sg_report.model_dump(mode="json")

    elapsed = (datetime.now() - start_time).total_seconds()

    return SearchResult(
        query=query,
        entities=canonical,
        resolved_groups=resolved_groups,
        connections=all_connections,
        events=all_events,
        scores=scores,
        metadata={
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "sources_queried": source_names,
            "sources_succeeded": sources_succeeded,
            "sources_failed": sources_failed,
            "smoking_gun_report": sg_data,
            "mermaid": mermaid_diagram,
            "network_analysis": network_analysis,
        },
    )


@click.group()
def cli():
    """Multi-source OSINT investigation toolkit."""
    pass


@cli.command()
@click.argument("query")
@click.option("--type", "entity_type", type=click.Choice(["person", "company", "organization"]), default=None)
@click.option("--sources", default=None, help="Comma-separated source names to query")
@click.option("--output", "output_format", type=click.Choice(["memo", "json", "both"]), default="memo")
@click.option("--limit", default=25, help="Max results per source")
def search(query: str, entity_type: str | None, sources: str | None, output_format: str, limit: int):
    """Search for an entity across all OSINT sources."""
    source_filter = sources.split(",") if sources else None
    result = asyncio.run(run_search(query, entity_type, source_filter, limit))

    # Generate outputs
    from output.memo import generate_memo

    if output_format in ("memo", "both"):
        memo = generate_memo(result)
        console.print("\n")
        console.print(memo)

    if output_format in ("json", "both"):
        # Save JSON report
        from config import INVESTIGATIONS_DIR
        safe_query = "".join(c if c.isalnum() or c in " _-" else "_" for c in query)[:50]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = INVESTIGATIONS_DIR / f"{safe_query}_{ts}.json"
        json_data = result.model_dump(mode="json")
        json_path.write_text(json.dumps(json_data, indent=2, default=str))
        console.print(f"\n[green]JSON saved to:[/green] {json_path}")


@cli.command()
@click.argument("entity_id")
@click.option("--source", required=True, help="Source name (aleph, opensanctions, etc.)")
def entity(entity_id: str, source: str):
    """Deep-dive into a single entity by ID."""
    from sources import get_enabled_sources

    async def _fetch():
        sources_list = get_enabled_sources()
        src = next((s for s in sources_list if s.name == source), None)
        if not src:
            console.print(f"[red]Source '{source}' not available[/red]")
            return
        ent = await src.get_entity(entity_id)
        if ent:
            console.print(f"\n[bold]{ent.name}[/bold] ({ent.entity_type.value})")
            console.print(f"Source: {ent.source.value}")
            if ent.flags:
                console.print(f"[red]Flags: {', '.join(ent.flags)}[/red]")
            if ent.countries:
                console.print(f"Countries: {', '.join(ent.countries)}")
            if ent.aliases:
                console.print(f"Aliases: {', '.join(ent.aliases[:10])}")
            console.print(f"URL: {ent.source_url}")
            console.print("\n[bold]Properties:[/bold]")
            for k, v in ent.properties.items():
                if v:
                    console.print(f"  {k}: {', '.join(str(x) for x in v[:5])}")
        else:
            console.print(f"[yellow]Entity not found: {entity_id}[/yellow]")

    asyncio.run(_fetch())


@cli.command()
@click.argument("query")
@click.option("--depth", default=2, help="Graph depth around central entities")
@click.option("--html", is_flag=True, help="Also save as standalone HTML file")
def graph(query: str, depth: int, html: bool):
    """Search and output only the network graph."""
    result = asyncio.run(run_search(query, limit=15))

    mermaid_str = result.metadata.get("mermaid", "")
    if mermaid_str:
        console.print("\n")
        console.print(mermaid_str)

        if html:
            from output.mermaid import to_html
            from config import INVESTIGATIONS_DIR
            safe_query = "".join(c if c.isalnum() or c in " _-" else "_" for c in query)[:50]
            html_path = INVESTIGATIONS_DIR / f"{safe_query}_graph.html"
            html_path.write_text(to_html(mermaid_str))
            console.print(f"\n[green]HTML graph saved to:[/green] {html_path}")
    else:
        console.print("[yellow]No network connections found.[/yellow]")


@cli.command()
@click.argument("name1")
@click.argument("name2")
def compare(name1: str, name2: str):
    """Check fuzzy similarity between two entity names."""
    from rapidfuzz import fuzz

    scores = {
        "token_sort_ratio": fuzz.token_sort_ratio(name1, name2),
        "token_set_ratio": fuzz.token_set_ratio(name1, name2),
        "partial_ratio": fuzz.partial_ratio(name1, name2),
        "ratio": fuzz.ratio(name1, name2),
    }

    table = Table(title=f"Similarity: '{name1}' vs '{name2}'")
    table.add_column("Method", style="cyan")
    table.add_column("Score", style="green")
    for method, score in scores.items():
        table.add_row(method, f"{score:.1f}")
    console.print(table)

    avg = sum(scores.values()) / len(scores)
    if avg >= 80:
        console.print("[green]HIGH match - likely the same entity[/green]")
    elif avg >= 60:
        console.print("[yellow]MODERATE match - possibly the same entity[/yellow]")
    else:
        console.print("[red]LOW match - likely different entities[/red]")


@cli.group()
def watchlist():
    """Manage the investigative watchlist."""
    pass


@watchlist.command("add")
@click.argument("name")
@click.option("--type", "entity_type", default="unknown", help="Entity type: person, company, organization")
def watchlist_add(name: str, entity_type: str):
    """Add an entity to the watchlist."""
    from watchlist.store import add_entity
    entry = add_entity(name, entity_type)
    console.print(f"[green]Added to watchlist:[/green] {entry['name']} (type: {entry['entity_type']})")


@watchlist.command("remove")
@click.argument("name")
def watchlist_remove(name: str):
    """Remove an entity from the watchlist."""
    from watchlist.store import remove_entity
    if remove_entity(name):
        console.print(f"[green]Removed from watchlist:[/green] {name}")
    else:
        console.print(f"[yellow]Not found in watchlist:[/yellow] {name}")


@watchlist.command("list")
def watchlist_list():
    """Show all monitored entities."""
    from watchlist.store import list_entities

    entries = list_entities()
    if not entries:
        console.print("[yellow]Watchlist is empty.[/yellow]")
        return

    table = Table(title="Investigative Watchlist")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Added")
    table.add_column("Last Checked")
    for entry in entries:
        table.add_row(
            entry["name"],
            entry.get("entity_type", "unknown"),
            entry.get("added", "?")[:10],
            entry.get("last_checked", "never")[:10] if entry.get("last_checked") else "never",
        )
    console.print(table)


@watchlist.command("scan")
@click.option("--sources", default=None, help="Comma-separated source filter")
def watchlist_scan(sources: str | None):
    """Scan all watchlisted entities for changes."""
    from watchlist.scanner import scan_watchlist

    source_filter = sources.split(",") if sources else None

    async def _search(query):
        return await run_search(query, source_filter=source_filter, limit=15)

    changes = asyncio.run(scan_watchlist(_search))

    if not changes:
        console.print("[green]No changes detected across watchlisted entities.[/green]")
    else:
        console.print(f"\n[bold red]Changes detected for {len(changes)} entities:[/bold red]\n")
        for change in changes:
            console.print(f"[bold]{change['entity']}[/bold] ({change['change_type']})")
            console.print(f"  Entities: {change.get('new_entities', 0)}, Connections: {change.get('new_connections', 0)}")
            if change.get("new_flags"):
                console.print(f"  [red]Flags: {', '.join(change['new_flags'])}[/red]")
            if change.get("high_score_entities"):
                console.print(f"  High priority: {', '.join(change['high_score_entities'])}")
            console.print()


if __name__ == "__main__":
    cli()
