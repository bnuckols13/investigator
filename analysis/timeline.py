"""Cross-source timeline assembly and suspicious sequence detection."""

from __future__ import annotations

from datetime import timedelta

from rapidfuzz import fuzz

from models import TimelineEvent


def merge_events(events: list[TimelineEvent], dedup_threshold: float = 80.0) -> list[TimelineEvent]:
    """Merge and deduplicate timeline events from multiple sources.

    Events on the same date for the same entity with similar descriptions
    are considered duplicates.
    """
    if not events:
        return []

    sorted_events = sorted(events, key=lambda e: e.date)
    merged = [sorted_events[0]]

    for event in sorted_events[1:]:
        is_dup = False
        for existing in merged:
            if (
                event.date == existing.date
                and set(event.entity_ids) & set(existing.entity_ids)
                and fuzz.token_set_ratio(event.description, existing.description) > dedup_threshold
            ):
                is_dup = True
                break
        if not is_dup:
            merged.append(event)

    return merged


def detect_suspicious_sequences(events: list[TimelineEvent]) -> list[dict]:
    """Detect temporal patterns that warrant investigation.

    Patterns detected:
    - Insider trade (SEC Form 4) within 14 days of material event (8-K)
    - Government appointment followed by contract award within 180 days
    - Sanctions listing near corporate filing dates
    - Rapid succession of similar events (potential bid-rigging)
    """
    if len(events) < 2:
        return []

    sorted_events = sorted(events, key=lambda e: e.date)
    alerts = []

    for i, event_a in enumerate(sorted_events):
        for event_b in sorted_events[i + 1:]:
            gap = (event_b.date - event_a.date).days

            if gap > 365:
                break  # Don't look more than a year ahead

            # Pattern 1: Insider trade near material event
            if (
                gap <= 14
                and _is_insider_trade(event_a, event_b)
            ):
                alerts.append({
                    "pattern": "insider_trade_near_material_event",
                    "severity": "high",
                    "description": f"Insider trade within {gap} days of material event",
                    "event_a": event_a.model_dump(mode="json"),
                    "event_b": event_b.model_dump(mode="json"),
                    "gap_days": gap,
                })

            # Pattern 2: Appointment followed by contract
            if (
                gap <= 180
                and _is_appointment_then_contract(event_a, event_b)
            ):
                alerts.append({
                    "pattern": "revolving_door_contract",
                    "severity": "medium",
                    "description": f"Contract awarded {gap} days after government appointment",
                    "event_a": event_a.model_dump(mode="json"),
                    "event_b": event_b.model_dump(mode="json"),
                    "gap_days": gap,
                })

            # Pattern 3: Sanctions near filing
            if (
                gap <= 30
                and _is_sanctions_near_filing(event_a, event_b)
            ):
                alerts.append({
                    "pattern": "sanctions_filing_proximity",
                    "severity": "medium",
                    "description": f"Filing within {gap} days of sanctions event",
                    "event_a": event_a.model_dump(mode="json"),
                    "event_b": event_b.model_dump(mode="json"),
                    "gap_days": gap,
                })

    # Pattern 4: Rapid succession (potential bid rigging)
    _check_rapid_succession(sorted_events, alerts)

    return alerts


def _is_insider_trade(a: TimelineEvent, b: TimelineEvent) -> bool:
    """Check if one event is an insider trade and the other is material."""
    trade_keywords = ["form 4", "insider", "trade"]
    material_keywords = ["8-k", "material", "acquisition", "merger"]

    a_desc = a.description.lower()
    b_desc = b.description.lower()

    a_is_trade = any(k in a_desc for k in trade_keywords) or a.event_type == "filing"
    b_is_trade = any(k in b_desc for k in trade_keywords) or b.event_type == "filing"
    a_is_material = any(k in a_desc for k in material_keywords)
    b_is_material = any(k in b_desc for k in material_keywords)

    return (a_is_trade and b_is_material) or (a_is_material and b_is_trade)


def _is_appointment_then_contract(a: TimelineEvent, b: TimelineEvent) -> bool:
    """Check if an appointment is followed by a contract."""
    appt_keywords = ["appointed", "hired", "joined", "employment", "start"]
    contract_keywords = ["contract", "award", "grant"]

    a_desc = a.description.lower()
    b_desc = b.description.lower()

    return (
        (any(k in a_desc for k in appt_keywords) and any(k in b_desc for k in contract_keywords))
        or (a.event_type in ("start", "employment") and b.event_type in ("award", "contract"))
    )


def _is_sanctions_near_filing(a: TimelineEvent, b: TimelineEvent) -> bool:
    """Check if sanctions event is near a corporate filing."""
    a_desc = a.description.lower()
    b_desc = b.description.lower()

    sanctions_check = "sanction" in a_desc or a.event_type == "listed"
    filing_check = "filing" in b_desc or "sec" in b_desc or b.event_type == "filing"

    return (sanctions_check and filing_check) or (filing_check and sanctions_check)


def _check_rapid_succession(events: list[TimelineEvent], alerts: list[dict]):
    """Detect rapid succession of same-type events (potential bid rigging)."""
    type_groups: dict[str, list[TimelineEvent]] = {}
    for e in events:
        key = e.event_type
        type_groups.setdefault(key, []).append(e)

    for event_type, group in type_groups.items():
        if len(group) < 3:
            continue
        for i in range(len(group) - 2):
            gaps = [
                (group[i + 1].date - group[i].date).days,
                (group[i + 2].date - group[i + 1].date).days,
            ]
            if all(0 < g <= 7 for g in gaps):
                alerts.append({
                    "pattern": "rapid_succession",
                    "severity": "low",
                    "description": f"3+ {event_type} events within 7 days each",
                    "events": [e.model_dump(mode="json") for e in group[i:i + 3]],
                })
