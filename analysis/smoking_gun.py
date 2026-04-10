"""Smoking gun composite pattern detection.

Each detector looks for a multi-source pattern where the intersection
of independent data points makes the innocent explanation implausible.
Scoring is multiplicative, temporal, and auditable.

Scoring formula: final_score = min(raw_score * temporal * sources * concealment * recency, 100)
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import date, timedelta
from enum import Enum
from typing import Any, Optional

import networkx as nx
from pydantic import BaseModel, Field

from models import Connection, Entity, SourceEnum, TimelineEvent


# --- Secrecy jurisdictions ---

SECRECY_JURISDICTIONS = {
    "vg", "ky", "pa", "sc", "bz", "vu", "ws", "mh",  # offshore
    "je", "gg", "im",  # Crown dependencies
    "li", "lu", "mt", "cy",  # EU secrecy
    "ae",  # UAE
}
# US shell-company states (checked against entity properties, not country codes)
SHELL_STATES = {"delaware", "nevada", "wyoming", "de", "nv", "wy"}


# --- Data Models ---

class PatternEvidence(BaseModel):
    entity_id: str
    entity_name: str
    evidence_type: str  # flag, connection, event, ownership_layer, network_position
    description: str
    source: str
    date: Optional[date] = None
    amount: Optional[float] = None


class DetectedPattern(BaseModel):
    pattern_name: str
    display_name: str
    tier: str  # smoking_gun, strong, indicator
    raw_score: float
    multipliers: dict[str, float] = Field(default_factory=dict)
    final_score: float = 0
    evidence: list[PatternEvidence] = Field(default_factory=list)
    mhees_code: str = ""
    narrative: str = ""
    next_steps: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)


class SmokingGunReport(BaseModel):
    patterns: list[DetectedPattern] = Field(default_factory=list)
    heat_score: float = 0
    scan_summary: dict = Field(default_factory=dict)
    top_narrative: str = ""


# --- Multiplier Functions ---

def temporal_multiplier(gap_days: int) -> float:
    if gap_days <= 2:
        return 1.8
    if gap_days <= 7:
        return 1.5
    if gap_days <= 30:
        return 1.2
    if gap_days <= 90:
        return 1.0
    if gap_days <= 365:
        return 0.8
    return 0.6


def source_independence_multiplier(sources: set[str]) -> float:
    n = len(sources)
    if n >= 4:
        return 1.7
    if n == 3:
        return 1.5
    if n == 2:
        return 1.3
    return 1.0


def concealment_multiplier(
    intermediaries: int = 0,
    circular: bool = False,
    secrecy_count: int = 0,
) -> float:
    if intermediaries == 0:
        base = 1.0
    elif intermediaries == 1:
        base = 1.15
    elif intermediaries == 2:
        base = 1.3
    else:
        base = 1.5
    if circular:
        base += 0.2
    base += min(secrecy_count * 0.1, 0.3)
    return base


def recency_multiplier(most_recent: Optional[date]) -> float:
    if not most_recent:
        return 0.8
    age = (date.today() - most_recent).days
    if age <= 30:
        return 1.3
    if age <= 90:
        return 1.2
    if age <= 365:
        return 1.0
    return 0.8


def compute_final_score(raw: float, multipliers: dict[str, float]) -> float:
    result = raw
    for m in multipliers.values():
        result *= m
    return min(result, 100.0)


# --- Detection Context ---

class DetectionContext:
    """Pre-computed indexes over the investigation data."""

    def __init__(
        self,
        entities: list[Entity],
        connections: list[Connection],
        events: list[TimelineEvent],
        graph: nx.DiGraph,
    ):
        self.entities = entities
        self.connections = connections
        self.events = events
        self.graph = graph

        # Indexes
        self.entity_index: dict[str, Entity] = {e.id: e for e in entities}
        self.flag_index: dict[str, list[Entity]] = {}
        self.source_index: dict[str, list[Entity]] = {}
        self.conn_index: dict[str, list[Connection]] = {}
        self.event_index: dict[str, list[TimelineEvent]] = {}

        for e in entities:
            for flag in e.flags:
                self.flag_index.setdefault(flag, []).append(e)
            self.source_index.setdefault(e.source.value, []).append(e)

        for c in connections:
            self.conn_index.setdefault(c.source_entity_id, []).append(c)
            self.conn_index.setdefault(c.target_entity_id, []).append(c)

        for ev in events:
            for eid in ev.entity_ids:
                self.event_index.setdefault(eid, []).append(ev)

    def get_flagged(self, *flag_names: str) -> list[Entity]:
        result = []
        for f in flag_names:
            result.extend(self.flag_index.get(f, []))
        return list({e.id: e for e in result}.values())

    def get_connections_for(self, entity_id: str, rel_type: str = None) -> list[Connection]:
        conns = self.conn_index.get(entity_id, [])
        if rel_type:
            conns = [c for c in conns if c.relation_type == rel_type]
        return conns

    def get_events_for(self, entity_id: str) -> list[TimelineEvent]:
        return self.event_index.get(entity_id, [])

    def sources_for_entity(self, entity_id: str) -> set[str]:
        """Find all sources that have data on this entity."""
        sources = set()
        ent = self.entity_index.get(entity_id)
        if ent:
            sources.add(ent.source.value)
        for c in self.conn_index.get(entity_id, []):
            sources.add(c.source.value)
        for e in self.event_index.get(entity_id, []):
            sources.add(e.source.value)
        return sources

    def has_secrecy_jurisdiction(self, entity: Entity) -> int:
        """Count secrecy jurisdictions for an entity."""
        count = 0
        for country in entity.countries:
            if country.lower() in SECRECY_JURISDICTIONS:
                count += 1
        # Check state properties
        state = entity.properties.get("stateOfIncorporation", [""])[0].lower()
        if state in SHELL_STATES:
            count += 1
        return count


# --- Base Detector ---

class BaseDetector(ABC):
    name: str
    display_name: str
    tier: str

    @abstractmethod
    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        ...


# --- Tier 1: Direct Smoking Guns ---

class SanctionsEvasionChainDetector(BaseDetector):
    name = "sanctions_evasion_chain"
    display_name = "Sanctions Evasion Chain"
    tier = "smoking_gun"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        sanctioned = ctx.get_flagged("sanctioned", "ofac", "eu_sanctioned", "debarred")
        contractors = [e for e in ctx.entities if "govt_contractor" in e.flags]

        if not sanctioned or not contractors:
            return patterns

        for s_ent in sanctioned:
            for c_ent in contractors:
                if s_ent.id == c_ent.id:
                    continue
                try:
                    if not nx.has_path(ctx.graph, s_ent.id, c_ent.id):
                        continue
                    path = nx.shortest_path(ctx.graph, s_ent.id, c_ent.id)
                except (nx.NodeNotFound, nx.NetworkXError):
                    continue

                intermediaries = len(path) - 2
                secrecy = sum(
                    ctx.has_secrecy_jurisdiction(ctx.entity_index[nid])
                    for nid in path if nid in ctx.entity_index
                )
                circular = False
                try:
                    cycles = list(nx.simple_cycles(ctx.graph.subgraph(path)))
                    circular = len(cycles) > 0
                except Exception:
                    pass

                contract_conns = ctx.get_connections_for(c_ent.id, "contract")
                total_contract_value = sum(c.weight or 0 for c in contract_conns)

                sources = ctx.sources_for_entity(s_ent.id) | ctx.sources_for_entity(c_ent.id)
                contract_dates = [e.date for e in ctx.get_events_for(c_ent.id) if e.event_type in ("award", "contract")]
                most_recent = max(contract_dates) if contract_dates else None

                mults = {
                    "concealment": concealment_multiplier(intermediaries, circular, secrecy),
                    "sources": source_independence_multiplier(sources),
                    "recency": recency_multiplier(most_recent),
                }
                final = compute_final_score(85, mults)

                chain_desc = " -> ".join(
                    ctx.entity_index[nid].name if nid in ctx.entity_index else nid
                    for nid in path
                )
                evidence = [
                    PatternEvidence(
                        entity_id=s_ent.id, entity_name=s_ent.name,
                        evidence_type="flag", description=f"Sanctioned: {', '.join(s_ent.flags)}",
                        source=s_ent.source.value,
                    ),
                    PatternEvidence(
                        entity_id=c_ent.id, entity_name=c_ent.name,
                        evidence_type="connection", description=f"Govt contractor: ${total_contract_value:,.0f}",
                        source=c_ent.source.value,
                    ),
                ]
                for nid in path[1:-1]:
                    ent = ctx.entity_index.get(nid)
                    if ent:
                        evidence.append(PatternEvidence(
                            entity_id=nid, entity_name=ent.name,
                            evidence_type="ownership_layer",
                            description=f"Intermediary ({ent.entity_type.value})",
                            source=ent.source.value,
                        ))

                patterns.append(DetectedPattern(
                    pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                    raw_score=85, multipliers=mults, final_score=final,
                    evidence=evidence, entity_ids=[n for n in path],
                    narrative=(
                        f"{s_ent.name} (sanctions: {', '.join(s_ent.flags)}) connects to "
                        f"{c_ent.name} via {intermediaries} intermediary entities: {chain_desc}. "
                        f"{c_ent.name} holds ${total_contract_value:,.0f} in federal contracts. "
                        f"This ownership chain suggests potential sanctions evasion."
                    ),
                    next_steps=[
                        f"Trace full ownership chain for {c_ent.name} via Aleph/SEC",
                        "FOIA contracting officer's due diligence records at awarding agency",
                        "Check OFAC compliance filings for the contractor",
                        f"Search PACER for prior enforcement against {s_ent.name}",
                    ],
                ))
        return patterns


class QuidProQuoDetector(BaseDetector):
    name = "quid_pro_quo"
    display_name = "Quid Pro Quo"
    tier = "smoking_gun"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        contribution_conns = [c for c in ctx.connections if c.relation_type == "contribution"]
        contract_conns = [c for c in ctx.connections if c.relation_type == "contract"]

        if not contribution_conns or not contract_conns:
            return patterns

        for contrib in contribution_conns:
            donor_id = contrib.source_entity_id
            recipient_id = contrib.target_entity_id
            donation_amount = contrib.weight or 0
            donation_date_str = contrib.properties.get("receipt_date", "")
            if not donation_date_str:
                continue
            try:
                donation_date = date.fromisoformat(str(donation_date_str)[:10])
            except (ValueError, TypeError):
                continue

            # Check if donor or donor-connected entities got contracts
            donor_conns = ctx.get_connections_for(donor_id)
            donor_network = {donor_id}
            for dc in donor_conns:
                if dc.relation_type in ("ownership", "directorship", "employment"):
                    donor_network.add(dc.source_entity_id)
                    donor_network.add(dc.target_entity_id)

            for contract in contract_conns:
                contractor_id = contract.target_entity_id
                if contractor_id not in donor_network and contract.source_entity_id not in donor_network:
                    continue

                contract_events = [
                    e for e in ctx.events
                    if e.event_type in ("award", "contract")
                    and any(eid in donor_network for eid in e.entity_ids)
                ]
                for award_event in contract_events:
                    gap = (award_event.date - donation_date).days
                    if 0 < gap <= 365:
                        donor = ctx.entity_index.get(donor_id)
                        contractor = ctx.entity_index.get(contractor_id)
                        if not donor or not contractor:
                            continue

                        sources = ctx.sources_for_entity(donor_id) | ctx.sources_for_entity(contractor_id)
                        mults = {
                            "temporal": temporal_multiplier(gap),
                            "sources": source_independence_multiplier(sources),
                            "recency": recency_multiplier(award_event.date),
                        }
                        raw = 80 if gap <= 90 else (75 if gap <= 180 else 70)
                        final = compute_final_score(raw, mults)

                        patterns.append(DetectedPattern(
                            pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                            raw_score=raw, multipliers=mults, final_score=final,
                            evidence=[
                                PatternEvidence(
                                    entity_id=donor_id, entity_name=donor.name,
                                    evidence_type="connection",
                                    description=f"Donated ${donation_amount:,.0f} on {donation_date}",
                                    source="openfec", date=donation_date, amount=donation_amount,
                                ),
                                PatternEvidence(
                                    entity_id=contractor_id, entity_name=contractor.name,
                                    evidence_type="event",
                                    description=f"Contract awarded {gap} days later: ${award_event.amount or 0:,.0f}",
                                    source=award_event.source.value, date=award_event.date,
                                    amount=award_event.amount,
                                ),
                            ],
                            entity_ids=[donor_id, contractor_id, recipient_id],
                            narrative=(
                                f"{donor.name} donated ${donation_amount:,.0f} on {donation_date}. "
                                f"{gap} days later, {contractor.name} received a "
                                f"${award_event.amount or 0:,.0f} contract. "
                                f"This temporal sequence warrants pay-to-play investigation."
                            ),
                            next_steps=[
                                "Obtain solicitation docs (competitive vs sole-source?)",
                                f"Check if {donor.name} had a role at the awarding agency",
                                "Compare pre/post-donation contract award patterns",
                                "File state-level campaign finance cross-reference",
                            ],
                        ))
        return patterns


class InsiderTradingSignalDetector(BaseDetector):
    name = "insider_trading_signal"
    display_name = "Insider Trading Signal"
    tier = "smoking_gun"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        trade_keywords = {"form 4", "insider", "trade", "acquisition", "disposition"}
        material_keywords = {"8-k", "material", "acquisition", "merger", "restructuring"}

        for entity in ctx.entities:
            events = ctx.get_events_for(entity.id)
            trades = [e for e in events if any(k in e.description.lower() for k in trade_keywords)]
            materials = [e for e in events if any(k in e.description.lower() for k in material_keywords)]

            for trade in trades:
                for material in materials:
                    gap = abs((material.date - trade.date).days)
                    if gap > 14:
                        continue
                    before_event = trade.date <= material.date

                    raw = 85 if gap <= 3 else (80 if gap <= 7 else 75)
                    if not before_event:
                        raw -= 15  # less suspicious if trade after event

                    sources = {trade.source.value, material.source.value}
                    mults = {
                        "temporal": temporal_multiplier(gap),
                        "sources": source_independence_multiplier(sources),
                        "recency": recency_multiplier(max(trade.date, material.date)),
                    }
                    final = compute_final_score(raw, mults)

                    patterns.append(DetectedPattern(
                        pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                        raw_score=raw, multipliers=mults, final_score=final,
                        evidence=[
                            PatternEvidence(
                                entity_id=entity.id, entity_name=entity.name,
                                evidence_type="event",
                                description=f"Trade: {trade.description}",
                                source=trade.source.value, date=trade.date, amount=trade.amount,
                            ),
                            PatternEvidence(
                                entity_id=entity.id, entity_name=entity.name,
                                evidence_type="event",
                                description=f"Material event: {material.description}",
                                source=material.source.value, date=material.date,
                            ),
                        ],
                        entity_ids=[entity.id],
                        narrative=(
                            f"{entity.name}: stock trade on {trade.date} occurred "
                            f"{'before' if before_event else 'after'} material event on {material.date} "
                            f"({gap} day gap). {'Potential foreknowledge.' if before_event else 'Post-event reaction.'}"
                        ),
                        next_steps=[
                            f"Pull Form 4 filing for {entity.name} from SEC EDGAR",
                            "Check 8-K filing details for materiality",
                            "Cross-reference with short interest data",
                            "Search CourtListener for SEC enforcement actions",
                        ],
                    ))
        return patterns


class RevolvingDoorContractDetector(BaseDetector):
    name = "revolving_door_contract"
    display_name = "Revolving Door Contract"
    tier = "smoking_gun"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        peps = ctx.get_flagged("pep", "political_candidate")
        contractors = [e for e in ctx.entities if "govt_contractor" in e.flags]

        if not peps or not contractors:
            return patterns

        for pep in peps:
            pep_conns = ctx.get_connections_for(pep.id)
            corporate_links = [
                c for c in pep_conns
                if c.relation_type in ("directorship", "employment", "ownership")
            ]
            for link in corporate_links:
                linked_id = link.target_entity_id if link.source_entity_id == pep.id else link.source_entity_id
                linked_ent = ctx.entity_index.get(linked_id)
                if not linked_ent or "govt_contractor" not in linked_ent.flags:
                    continue

                contract_conns = ctx.get_connections_for(linked_id, "contract")
                if not contract_conns:
                    continue

                total_value = sum(c.weight or 0 for c in contract_conns)
                sources = ctx.sources_for_entity(pep.id) | ctx.sources_for_entity(linked_id)
                events = ctx.get_events_for(linked_id)
                most_recent = max((e.date for e in events), default=None) if events else None

                mults = {
                    "sources": source_independence_multiplier(sources),
                    "recency": recency_multiplier(most_recent),
                }
                final = compute_final_score(85, mults)

                patterns.append(DetectedPattern(
                    pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                    raw_score=85, multipliers=mults, final_score=final,
                    evidence=[
                        PatternEvidence(
                            entity_id=pep.id, entity_name=pep.name,
                            evidence_type="flag", description=f"PEP/political figure: {', '.join(pep.flags)}",
                            source=pep.source.value,
                        ),
                        PatternEvidence(
                            entity_id=linked_id, entity_name=linked_ent.name,
                            evidence_type="connection",
                            description=f"{link.relation_type} + ${total_value:,.0f} in contracts",
                            source=linked_ent.source.value,
                        ),
                    ],
                    entity_ids=[pep.id, linked_id],
                    narrative=(
                        f"{pep.name} (PEP/political figure) has a {link.relation_type} connection to "
                        f"{linked_ent.name}, which holds ${total_value:,.0f} in federal contracts. "
                        f"This combination of political access and government contracting warrants scrutiny."
                    ),
                    next_steps=[
                        f"Timeline {pep.name}'s government service dates vs. contract award dates",
                        f"FOIA conflict-of-interest disclosures for {pep.name}",
                        f"Check lobbying registrations connecting {pep.name} to {linked_ent.name}",
                        "Search for ethics waivers or recusals",
                    ],
                ))
        return patterns


# --- Tier 2: Strong Circumstantial ---

class ConcurrentContradictionDetector(BaseDetector):
    name = "concurrent_contradiction"
    display_name = "Concurrent Contradiction"
    tier = "strong"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        sanctioned = ctx.get_flagged("sanctioned", "ofac", "eu_sanctioned", "debarred")

        for entity in sanctioned:
            if "govt_contractor" in entity.flags:
                sources = ctx.sources_for_entity(entity.id)
                contract_conns = ctx.get_connections_for(entity.id, "contract")
                total_value = sum(c.weight or 0 for c in contract_conns)

                mults = {"sources": source_independence_multiplier(sources)}
                final = compute_final_score(75, mults)

                patterns.append(DetectedPattern(
                    pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                    raw_score=75, multipliers=mults, final_score=final,
                    evidence=[
                        PatternEvidence(
                            entity_id=entity.id, entity_name=entity.name,
                            evidence_type="flag",
                            description=f"Sanctioned/debarred: {', '.join(f for f in entity.flags if f in ('sanctioned', 'ofac', 'eu_sanctioned', 'debarred'))}",
                            source=entity.source.value,
                        ),
                        PatternEvidence(
                            entity_id=entity.id, entity_name=entity.name,
                            evidence_type="flag",
                            description=f"Active govt contractor: ${total_value:,.0f}",
                            source="usaspending",
                        ),
                    ],
                    entity_ids=[entity.id],
                    narrative=(
                        f"{entity.name} appears on sanctions/debarment lists while simultaneously "
                        f"holding ${total_value:,.0f} in federal contracts. This is a direct compliance "
                        f"violation that should be impossible if screening procedures are functioning."
                    ),
                    next_steps=[
                        "Verify sanctions listing is current (not historical)",
                        "Check SAM.gov exclusion status",
                        "FOIA the contracting officer's responsibility determination",
                        "Report to relevant Inspector General",
                    ],
                ))
        return patterns


class ShellCompanyObfuscationDetector(BaseDetector):
    name = "shell_company_obfuscation"
    display_name = "Shell Company Obfuscation"
    tier = "strong"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        for entity in ctx.entities:
            secrecy = ctx.has_secrecy_jurisdiction(entity)
            if secrecy == 0:
                continue

            ownership_conns = ctx.get_connections_for(entity.id, "ownership")
            directorship_conns = ctx.get_connections_for(entity.id, "directorship")
            contract_conns = ctx.get_connections_for(entity.id, "contract")

            if not (ownership_conns or directorship_conns):
                continue

            # Check for circular patterns in local subgraph
            circular = False
            try:
                sub = nx.ego_graph(ctx.graph, entity.id, radius=3)
                cycles = list(nx.simple_cycles(sub))
                circular = len(cycles) > 0
            except Exception:
                pass

            layers = len(ownership_conns) + len(directorship_conns)
            has_contracts = len(contract_conns) > 0

            if layers < 2 and not circular:
                continue

            mults = {
                "concealment": concealment_multiplier(layers, circular, secrecy),
                "sources": source_independence_multiplier(ctx.sources_for_entity(entity.id)),
            }
            raw = 55 if not has_contracts else 65
            if circular:
                raw += 5
            final = compute_final_score(raw, mults)

            patterns.append(DetectedPattern(
                pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                raw_score=raw, multipliers=mults, final_score=final,
                evidence=[
                    PatternEvidence(
                        entity_id=entity.id, entity_name=entity.name,
                        evidence_type="ownership_layer",
                        description=f"{layers} ownership/directorship links, {secrecy} secrecy jurisdictions, circular: {circular}",
                        source=entity.source.value,
                    ),
                ],
                entity_ids=[entity.id],
                narrative=(
                    f"{entity.name} operates through {layers} ownership/directorship layers "
                    f"involving {secrecy} secrecy jurisdiction(s). "
                    f"{'Circular ownership detected. ' if circular else ''}"
                    f"{'Holds active government contracts. ' if has_contracts else ''}"
                    f"This structure suggests deliberate concealment of beneficial ownership."
                ),
                next_steps=[
                    f"Trace ultimate beneficial owners of {entity.name}",
                    "Check corporate registry for nominee directors",
                    "Cross-reference registered agents across entities",
                    "Search for related entities at same registered address",
                ],
            ))
        return patterns


class ThresholdGamingDetector(BaseDetector):
    name = "threshold_gaming"
    display_name = "Threshold Gaming"
    tier = "strong"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        from analysis.procurement import detect_procurement_anomalies
        anomalies = detect_procurement_anomalies(ctx.connections, ctx.events)
        patterns = []

        for anomaly in anomalies:
            if anomaly["pattern"] != "just_under_threshold":
                continue
            raw = 55 + min(anomaly.get("count", 0) * 5, 20)
            mults = {"recency": 1.0}
            final = compute_final_score(raw, mults)

            patterns.append(DetectedPattern(
                pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                raw_score=raw, multipliers=mults, final_score=final,
                evidence=[PatternEvidence(
                    entity_id="", entity_name="Multiple vendors",
                    evidence_type="connection",
                    description=anomaly["description"],
                    source="usaspending",
                )],
                entity_ids=[],
                narrative=anomaly["description"] + " This pattern is consistent with deliberate contract splitting to avoid oversight thresholds.",
                next_steps=[
                    "Compare vendor addresses and registered agents",
                    "Check if vendors share beneficial owners",
                    "FOIA the justification for each sub-threshold award",
                ],
            ))
        return patterns


class GhostContractorDetector(BaseDetector):
    name = "ghost_contractor"
    display_name = "Ghost Contractor"
    tier = "strong"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        from analysis.procurement import detect_procurement_anomalies
        anomalies = detect_procurement_anomalies(ctx.connections, ctx.events)
        patterns = []

        for anomaly in anomalies:
            if anomaly["pattern"] != "new_vendor_large_award":
                continue
            vendor_id = anomaly.get("vendor", "")
            vendor_ent = ctx.entity_index.get(vendor_id)

            # Check if connected to flagged entity within 3 hops
            connected_to_flagged = False
            if vendor_id in ctx.graph:
                flagged_ids = {e.id for e in ctx.get_flagged("sanctioned", "pep", "criminal", "debarred")}
                for flagged_id in flagged_ids:
                    if flagged_id in ctx.graph:
                        try:
                            if nx.has_path(ctx.graph, vendor_id, flagged_id):
                                path = nx.shortest_path(ctx.graph, vendor_id, flagged_id)
                                if len(path) <= 4:
                                    connected_to_flagged = True
                                    break
                        except nx.NetworkXError:
                            pass

            raw = 60 if connected_to_flagged else 50
            mults = {"sources": source_independence_multiplier(ctx.sources_for_entity(vendor_id))}
            final = compute_final_score(raw, mults)

            patterns.append(DetectedPattern(
                pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                raw_score=raw, multipliers=mults, final_score=final,
                evidence=[PatternEvidence(
                    entity_id=vendor_id,
                    entity_name=vendor_ent.name if vendor_ent else vendor_id,
                    evidence_type="connection",
                    description=f"New vendor, ${anomaly.get('value', 0):,.0f} first contract" +
                                (" + connected to flagged entity" if connected_to_flagged else ""),
                    source="usaspending",
                    amount=anomaly.get("value"),
                )],
                entity_ids=[vendor_id],
                narrative=(
                    f"First-time vendor received ${anomaly.get('value', 0):,.0f} contract with no prior "
                    f"federal contracting history."
                    + (" Connected within 3 hops to a flagged entity." if connected_to_flagged else "")
                ),
                next_steps=[
                    "Check corporate registration date vs. contract date",
                    "Verify physical business address exists",
                    "Search for related entities with same registered agent",
                ],
            ))
        return patterns


# --- Tier 3: Indicators ---

class JurisdictionAnomalyDetector(BaseDetector):
    name = "jurisdiction_anomaly"
    display_name = "Jurisdiction Anomaly"
    tier = "indicator"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        for entity in ctx.entities:
            if len(entity.countries) < 3:
                continue
            secrecy = ctx.has_secrecy_jurisdiction(entity)
            if secrecy == 0:
                continue
            has_flags = bool(entity.flags)

            raw = 25 + (secrecy * 5) + (10 if has_flags else 0)
            raw = min(raw, 49)
            mults = {"sources": source_independence_multiplier(ctx.sources_for_entity(entity.id))}
            final = compute_final_score(raw, mults)

            patterns.append(DetectedPattern(
                pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                raw_score=raw, multipliers=mults, final_score=final,
                evidence=[PatternEvidence(
                    entity_id=entity.id, entity_name=entity.name,
                    evidence_type="flag",
                    description=f"{len(entity.countries)} countries incl. {secrecy} secrecy jurisdictions",
                    source=entity.source.value,
                )],
                entity_ids=[entity.id],
                narrative=f"{entity.name} operates across {len(entity.countries)} jurisdictions including {secrecy} secrecy jurisdictions.",
                next_steps=[f"Trace corporate registrations for {entity.name} in each jurisdiction"],
            ))
        return patterns


class NetworkBridgeDetector(BaseDetector):
    name = "network_bridge"
    display_name = "Network Bridge Entity"
    tier = "indicator"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        if len(ctx.graph) < 4:
            return patterns

        try:
            betweenness = nx.betweenness_centrality(ctx.graph.to_undirected())
        except Exception:
            return patterns

        flagged_ids = {e.id for e in ctx.get_flagged("sanctioned", "pep", "criminal", "debarred", "ofac")}

        for node_id, score in betweenness.items():
            if score < 0.2:
                continue
            entity = ctx.entity_index.get(node_id)
            if not entity:
                continue

            # Check if this bridge connects flagged clusters
            neighbors = set(ctx.graph.predecessors(node_id)) | set(ctx.graph.successors(node_id))
            flagged_neighbors = neighbors & flagged_ids

            raw = 30 + (10 if flagged_neighbors else 0)
            mults = {"sources": source_independence_multiplier(ctx.sources_for_entity(node_id))}
            final = compute_final_score(raw, mults)

            patterns.append(DetectedPattern(
                pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                raw_score=raw, multipliers=mults, final_score=final,
                evidence=[PatternEvidence(
                    entity_id=node_id, entity_name=entity.name,
                    evidence_type="network_position",
                    description=f"Betweenness centrality: {score:.3f}, bridges {len(neighbors)} entities",
                    source=entity.source.value,
                )],
                entity_ids=[node_id],
                narrative=f"{entity.name} is a bridge entity (centrality {score:.3f}) connecting otherwise separate network clusters.",
                next_steps=[f"Investigate {entity.name}'s role connecting these groups"],
            ))
        return patterns


class TemporalClusteringDetector(BaseDetector):
    name = "temporal_clustering"
    display_name = "Temporal Event Clustering"
    tier = "indicator"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        if len(ctx.events) < 3:
            return patterns

        sorted_events = sorted(ctx.events, key=lambda e: e.date)

        # Sliding 7-day window
        for i in range(len(sorted_events) - 2):
            window = [sorted_events[i]]
            for j in range(i + 1, len(sorted_events)):
                if (sorted_events[j].date - sorted_events[i].date).days <= 7:
                    window.append(sorted_events[j])
                else:
                    break

            if len(window) < 3:
                continue

            sources = {e.source.value for e in window}
            if len(sources) < 2:
                continue

            raw = min(25 + len(window) * 3 + len(sources) * 5, 49)
            mults = {
                "sources": source_independence_multiplier(sources),
                "recency": recency_multiplier(window[-1].date),
            }
            final = compute_final_score(raw, mults)

            patterns.append(DetectedPattern(
                pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                raw_score=raw, multipliers=mults, final_score=final,
                evidence=[PatternEvidence(
                    entity_id="", entity_name="cluster",
                    evidence_type="event",
                    description=f"{len(window)} events from {len(sources)} sources in 7-day window ({window[0].date} to {window[-1].date})",
                    source=", ".join(sources),
                    date=window[0].date,
                )],
                entity_ids=list({eid for e in window for eid in e.entity_ids}),
                narrative=f"{len(window)} events from {len(sources)} independent sources clustered within 7 days ({window[0].date} to {window[-1].date}).",
                next_steps=["Investigate whether these events are coordinated"],
            ))
            break  # Only report the densest cluster
        return patterns


class FinancialOutlierDetector(BaseDetector):
    name = "financial_outlier"
    display_name = "Financial Outlier"
    tier = "indicator"

    def detect(self, ctx: DetectionContext) -> list[DetectedPattern]:
        patterns = []
        for entity in ctx.entities:
            contract_conns = ctx.get_connections_for(entity.id, "contract")
            if len(contract_conns) < 2:
                continue

            amounts = [c.weight for c in contract_conns if c.weight and c.weight > 0]
            if len(amounts) < 2:
                continue

            median = sorted(amounts)[len(amounts) // 2]
            for conn in contract_conns:
                if conn.weight and conn.weight > median * 3 and conn.weight > 100_000:
                    raw = min(25 + int((conn.weight / median - 3) * 3), 49)
                    mults = {"recency": 1.0}
                    final = compute_final_score(raw, mults)

                    patterns.append(DetectedPattern(
                        pattern_name=self.name, display_name=self.display_name, tier=self.tier,
                        raw_score=raw, multipliers=mults, final_score=final,
                        evidence=[PatternEvidence(
                            entity_id=entity.id, entity_name=entity.name,
                            evidence_type="connection",
                            description=f"Contract ${conn.weight:,.0f} is {conn.weight/median:.1f}x median (${median:,.0f})",
                            source="usaspending", amount=conn.weight,
                        )],
                        entity_ids=[entity.id],
                        narrative=f"{entity.name} received a ${conn.weight:,.0f} contract, {conn.weight/median:.1f}x their median contract value of ${median:,.0f}.",
                        next_steps=[f"Review justification for this outsized award to {entity.name}"],
                    ))
                    break  # One outlier per entity
        return patterns


# --- Orchestration ---

ALL_DETECTORS: list[type[BaseDetector]] = [
    # Tier 1
    SanctionsEvasionChainDetector,
    QuidProQuoDetector,
    InsiderTradingSignalDetector,
    RevolvingDoorContractDetector,
    # Tier 2
    ConcurrentContradictionDetector,
    ShellCompanyObfuscationDetector,
    ThresholdGamingDetector,
    GhostContractorDetector,
    # Tier 3
    JurisdictionAnomalyDetector,
    NetworkBridgeDetector,
    TemporalClusteringDetector,
    FinancialOutlierDetector,
]


def detect_all(
    entities: list[Entity],
    connections: list[Connection],
    events: list[TimelineEvent],
    graph: nx.DiGraph,
) -> SmokingGunReport:
    """Run all 12 composite detectors and return a scored report."""
    ctx = DetectionContext(entities, connections, events, graph)

    all_patterns: list[DetectedPattern] = []

    for detector_cls in ALL_DETECTORS:
        detector = detector_cls()
        try:
            found = detector.detect(ctx)
            all_patterns.extend(found)
        except Exception:
            pass  # Individual detector failure does not block others

    # Deduplicate: if two patterns share >50% entity_ids, keep higher score
    deduped = _deduplicate(all_patterns)

    # Sort by final score
    deduped.sort(key=lambda p: p.final_score, reverse=True)

    # Compute heat score
    heat = _compute_heat(deduped)

    # Top narrative
    top_narrative = ""
    if deduped:
        top = deduped[0]
        top_narrative = f"HEAT SCORE: {heat:.0f}/100. {top.narrative}"

    return SmokingGunReport(
        patterns=deduped,
        heat_score=heat,
        scan_summary={
            "entities_scanned": len(entities),
            "patterns_tested": len(ALL_DETECTORS),
            "patterns_fired": len(deduped),
            "sources_represented": list({e.source.value for e in entities}),
        },
        top_narrative=top_narrative,
    )


def _deduplicate(patterns: list[DetectedPattern]) -> list[DetectedPattern]:
    if len(patterns) <= 1:
        return patterns

    keep = []
    seen_entity_sets: list[set[str]] = []

    sorted_p = sorted(patterns, key=lambda p: p.final_score, reverse=True)
    for p in sorted_p:
        p_set = set(p.entity_ids)
        if not p_set:
            keep.append(p)
            continue

        duplicate = False
        for existing_set in seen_entity_sets:
            if not existing_set:
                continue
            overlap = len(p_set & existing_set) / max(len(p_set | existing_set), 1)
            if overlap > 0.5:
                # Merge next_steps from lower-scoring duplicate
                for k in keep:
                    if set(k.entity_ids) == existing_set:
                        for step in p.next_steps:
                            if step not in k.next_steps:
                                k.next_steps.append(step)
                        break
                duplicate = True
                break

        if not duplicate:
            keep.append(p)
            seen_entity_sets.append(p_set)

    return keep


def _compute_heat(patterns: list[DetectedPattern]) -> float:
    if not patterns:
        return 0
    scores = [p.final_score for p in patterns]
    top = scores[0]
    second = scores[1] if len(scores) > 1 else 0
    remaining = scores[2:] if len(scores) > 2 else []
    avg_remaining = sum(remaining) / len(remaining) if remaining else 0
    return min(top * 0.6 + second * 0.25 + avg_remaining * 0.15, 100)
