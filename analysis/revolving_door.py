"""Revolving door analysis — government to private sector transitions."""

from __future__ import annotations

from datetime import date
from typing import Any

from models import Connection, Entity, SourceEnum, TimelineEvent


async def detect_revolving_door(
    entity: Entity,
    connections: list[Connection],
    events: list[TimelineEvent],
) -> dict:
    """Analyze an entity for revolving door indicators.

    Looks for:
    - PEP status (politically exposed person) combined with corporate roles
    - Government employment followed by private sector roles
    - Lobbying connections
    - Campaign finance to officials who awarded contracts
    """
    findings = {
        "entity": entity.name,
        "pep_status": "pep" in entity.flags,
        "govt_connections": [],
        "corporate_connections": [],
        "suspicious_transitions": [],
        "campaign_contract_links": [],
        "risk_score": 0,
    }

    # Separate connections by type
    for conn in connections:
        if conn.relation_type in ("employment", "directorship"):
            # Check if government or corporate
            target = conn.target_entity_id
            if any(kw in target.lower() for kw in ["govt", "government", "agency", "department", "commission"]):
                findings["govt_connections"].append({
                    "target": conn.target_entity_id,
                    "type": conn.relation_type,
                    "label": conn.label,
                })
            else:
                findings["corporate_connections"].append({
                    "target": conn.target_entity_id,
                    "type": conn.relation_type,
                    "label": conn.label,
                })
        elif conn.relation_type == "contribution":
            findings["campaign_contract_links"].append({
                "from": conn.source_entity_id,
                "to": conn.target_entity_id,
                "amount": conn.weight,
            })

    # Check for government-to-corporate transitions in timeline
    govt_events = [e for e in events if _is_govt_event(e)]
    corporate_events = [e for e in events if _is_corporate_event(e)]

    for govt_event in govt_events:
        for corp_event in corporate_events:
            if corp_event.date > govt_event.date:
                gap_days = (corp_event.date - govt_event.date).days
                if gap_days <= 730:  # Within 2 years
                    findings["suspicious_transitions"].append({
                        "govt_role": govt_event.description,
                        "corporate_role": corp_event.description,
                        "gap_days": gap_days,
                        "severity": "high" if gap_days <= 180 else "medium",
                    })

    # Campaign donation to official who awards contracts
    contribution_conns = [c for c in connections if c.relation_type == "contribution"]
    contract_conns = [c for c in connections if c.relation_type == "contract"]

    if contribution_conns and contract_conns:
        findings["campaign_contract_links"].append({
            "pattern": "donor_contractor",
            "donations": len(contribution_conns),
            "contracts": len(contract_conns),
            "total_donated": sum(c.weight or 0 for c in contribution_conns),
            "total_contracts": sum(c.weight or 0 for c in contract_conns),
        })

    # Compute risk score
    risk = 0
    if findings["pep_status"]:
        risk += 30
    risk += len(findings["suspicious_transitions"]) * 25
    risk += min(len(findings["campaign_contract_links"]) * 15, 45)
    if findings["govt_connections"] and findings["corporate_connections"]:
        risk += 20
    findings["risk_score"] = min(risk, 100)

    return findings


def _is_govt_event(event: TimelineEvent) -> bool:
    desc = event.description.lower()
    return any(kw in desc for kw in [
        "government", "appointed", "commission", "agency", "department",
        "senate", "congress", "federal", "regulatory", "public body",
    ])


def _is_corporate_event(event: TimelineEvent) -> bool:
    desc = event.description.lower()
    return any(kw in desc for kw in [
        "director", "officer", "ceo", "president", "advisor",
        "consultant", "board", "hired", "joined", "corp", "inc",
    ])
