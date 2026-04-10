"""Procurement anomaly detection for government contracts."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta

from models import Connection, TimelineEvent


def detect_procurement_anomalies(
    connections: list[Connection],
    events: list[TimelineEvent],
) -> list[dict]:
    """Detect suspicious patterns in government procurement data.

    Patterns:
    - Sole-source concentration: one vendor getting disproportionate share
    - Just-under-threshold: amounts clustering below reporting limits
    - Award velocity: unusually rapid sequential awards
    - New-vendor-large-award: first-time vendor getting a big contract
    """
    alerts = []

    contract_conns = [c for c in connections if c.relation_type == "contract"]
    award_events = [e for e in events if e.event_type in ("award", "contract")]

    if not contract_conns:
        return alerts

    # 1. Sole-source concentration
    vendor_counts = Counter()
    vendor_totals: dict[str, float] = {}
    for conn in contract_conns:
        vendor = conn.target_entity_id
        vendor_counts[vendor] += 1
        vendor_totals[vendor] = vendor_totals.get(vendor, 0) + (conn.weight or 0)

    total_contracts = sum(vendor_counts.values())
    total_value = sum(vendor_totals.values())

    for vendor, count in vendor_counts.most_common(5):
        share = count / total_contracts if total_contracts > 0 else 0
        value_share = vendor_totals.get(vendor, 0) / total_value if total_value > 0 else 0

        if share > 0.4 and count >= 3:
            alerts.append({
                "pattern": "sole_source_concentration",
                "severity": "high" if share > 0.6 else "medium",
                "vendor": vendor,
                "contract_count": count,
                "contract_share": round(share, 2),
                "total_value": vendor_totals.get(vendor, 0),
                "value_share": round(value_share, 2),
                "description": f"Vendor receives {share:.0%} of contracts ({count}/{total_contracts})",
            })

    # 2. Just-under-threshold clustering
    # Common thresholds: $10K (micro-purchase), $250K (simplified acquisition), $750K
    thresholds = [10_000, 250_000, 750_000]
    for threshold in thresholds:
        near_threshold = [
            c for c in contract_conns
            if c.weight and (threshold * 0.85) <= c.weight < threshold
        ]
        if len(near_threshold) >= 3:
            alerts.append({
                "pattern": "just_under_threshold",
                "severity": "medium",
                "threshold": threshold,
                "count": len(near_threshold),
                "description": f"{len(near_threshold)} contracts just under ${threshold:,.0f} threshold (potential split to avoid oversight)",
            })

    # 3. Award velocity (rapid sequential awards to same vendor)
    if award_events:
        sorted_awards = sorted(award_events, key=lambda e: e.date)
        for i in range(len(sorted_awards) - 2):
            window = sorted_awards[i:i + 3]
            if len(window) == 3:
                gap1 = (window[1].date - window[0].date).days
                gap2 = (window[2].date - window[1].date).days
                if gap1 <= 7 and gap2 <= 7:
                    alerts.append({
                        "pattern": "rapid_award_velocity",
                        "severity": "medium",
                        "description": f"3 awards in {gap1 + gap2} days",
                        "awards": [
                            {"date": str(e.date), "description": e.description, "amount": e.amount}
                            for e in window
                        ],
                    })

    # 4. Large first-time vendor award
    for vendor, count in vendor_counts.items():
        if count == 1:
            value = vendor_totals.get(vendor, 0)
            if value > 500_000:
                alerts.append({
                    "pattern": "new_vendor_large_award",
                    "severity": "low",
                    "vendor": vendor,
                    "value": value,
                    "description": f"First-time vendor received ${value:,.0f} contract",
                })

    return alerts
