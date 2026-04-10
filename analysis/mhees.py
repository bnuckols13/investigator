"""MHEES (Memory Hole Evidence Evaluation System) auto-coding.

Generates MHEES notation: P[1-6] - R[A-F]† - C[1-5] - I[1-6]† - D[1-4] - F[1-4]

† marks judgment axes — auto-generated justifications serve as initial drafts
that the journalist reviews and adjusts before publication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .smoking_gun import DetectedPattern


# Source reliability mapping (Axis R)
SOURCE_RELIABILITY = {
    "sec_edgar": "A",      # Mandatory regulatory filings, legally binding
    "usaspending": "A",    # Official federal award records
    "courtlistener": "A",  # Federal court records, public proceedings
    "opensanctions": "B",  # Compiled from authoritative govt lists, high accuracy
    "openfec": "B",        # Self-reported campaign finance, generally reliable
    "aleph": "B",          # OCCRP-curated corporate registries + leaked docs
}

# Source provenance mapping (Axis P)
SOURCE_PROVENANCE = {
    "sec_edgar": "P1",     # Verified public record
    "usaspending": "P1",
    "courtlistener": "P1",
    "opensanctions": "P1", # Compiled from public government lists
    "openfec": "P1",
    "aleph": "P2",         # Institutional document (corporate registries, some leaks)
}


def auto_code(pattern: DetectedPattern) -> str:
    """Generate an MHEES notation code for a detected pattern.

    This is an initial machine assessment. Judgment axes (R†, I†) are
    flagged for mandatory human review before publication.
    """
    p = _assess_provenance(pattern)
    r = _assess_reliability(pattern)
    c = _assess_corroboration(pattern)
    i = _assess_credibility(pattern)
    d = _assess_inference_distance(pattern)
    f = _assess_defeasibility(pattern)

    return f"{p}-{r}\u2020-{c}-{i}\u2020-{d}-{f}"


def _assess_provenance(pattern: DetectedPattern) -> str:
    """P axis: What kind of sources produced this evidence?"""
    sources = {e.source for e in pattern.evidence}

    # If any source is analytical (network analysis, scoring), it's P6
    if pattern.tier == "indicator":
        return "P6"

    # Best provenance among contributing sources
    best = "P6"
    for source in sources:
        p = SOURCE_PROVENANCE.get(source, "P6")
        if p < best:
            best = p
    return best


def _assess_reliability(pattern: DetectedPattern) -> str:
    """R† axis: How reliable are the sources historically? (judgment axis)"""
    sources = {e.source for e in pattern.evidence}
    reliabilities = [SOURCE_RELIABILITY.get(s, "F") for s in sources]

    if not reliabilities:
        return "F"

    # Use the most reliable source's rating
    return min(reliabilities)


def _assess_corroboration(pattern: DetectedPattern) -> str:
    """C axis: How many independent sources confirm this?"""
    sources = {e.source for e in pattern.evidence}
    n = len(sources)

    if n >= 3:
        return "C1"
    if n == 2:
        return "C2"

    # Single source — check if entity match provides echo
    has_entity_match = any(e.evidence_type == "ownership_layer" for e in pattern.evidence)
    if has_entity_match:
        return "C3"
    return "C4"


def _assess_credibility(pattern: DetectedPattern) -> str:
    """I† axis: How credible is this specific finding? (judgment axis)"""
    sources = {e.source for e in pattern.evidence}
    score = pattern.final_score

    # Cross-source corroboration of specific fact = confirmed
    if len(sources) >= 3 and score >= 70:
        return "I1"
    if score >= 70:
        return "I2"
    if score >= 40:
        return "I3"
    if score >= 20:
        return "I4"
    return "I5"


def _assess_inference_distance(pattern: DetectedPattern) -> str:
    """D axis: How far is this from direct evidence?"""
    # Direct flags (entity IS on sanctions list) = D1
    has_direct = any(e.evidence_type == "flag" for e in pattern.evidence)
    has_connection = any(e.evidence_type in ("connection", "event") for e in pattern.evidence)
    has_ownership = any(e.evidence_type == "ownership_layer" for e in pattern.evidence)
    has_network = any(e.evidence_type == "network_position" for e in pattern.evidence)

    if has_direct and not has_ownership and not has_network:
        return "D1"
    if has_direct and has_connection and not has_ownership:
        return "D2"
    if has_ownership or (has_connection and has_network):
        return "D3"
    return "D4"


def _assess_defeasibility(pattern: DetectedPattern) -> str:
    """F axis: How falsifiable is this finding?"""
    # Patterns with specific, checkable claims = F2
    # Most auto-detections have implicit falsification = F3
    if pattern.tier == "smoking_gun":
        return "F2"  # Falsification conditions can be specified
    if pattern.tier == "strong":
        return "F2"
    return "F3"


def generate_justification(pattern: DetectedPattern, axis: str) -> str:
    """Generate a draft justification for a judgment axis (R† or I†).

    These are machine-generated drafts for the journalist to review and
    refine before publication. They should never be published as-is.
    """
    if axis == "R":
        sources = {e.source for e in pattern.evidence}
        parts = []
        for source in sorted(sources):
            if source in ("sec_edgar", "usaspending", "courtlistener"):
                parts.append(f"{source}: mandatory public filings with legal penalties for misreporting. High reliability.")
            elif source == "opensanctions":
                parts.append("opensanctions: compiled from authoritative government sanctions lists (OFAC, EU, UN). Regularly updated. High reliability for designation status.")
            elif source == "openfec":
                parts.append("openfec: self-reported campaign finance data. Generally reliable but subject to late amendments. Check for updated filings.")
            elif source == "aleph":
                parts.append("aleph: OCCRP-curated corporate registries and leaked documents. Registry data is authoritative; leaked documents vary in context.")
        return " ".join(parts)

    if axis == "I":
        sources = {e.source for e in pattern.evidence}
        n_sources = len(sources)
        score = pattern.final_score

        parts = [f"Pattern '{pattern.display_name}' scored {score:.0f}/100."]
        if n_sources >= 2:
            parts.append(f"Corroborated across {n_sources} independent databases ({', '.join(sorted(sources))}).")
        else:
            parts.append("Single-source finding. Additional corroboration recommended.")

        if pattern.tier == "smoking_gun":
            parts.append("The combination of signals makes an innocent explanation implausible without additional context.")
        elif pattern.tier == "strong":
            parts.append("Strong circumstantial evidence. Warrants active investigation but does not constitute proof.")
        else:
            parts.append("Indicator-level finding. Useful as context but insufficient alone for reporting.")

        return " ".join(parts)

    return ""


def mhees_to_confidence_badge(code: str) -> str:
    """Convert MHEES code to a plain-language confidence label.

    For reader-facing output in memos and evidence files.
    """
    parts = code.replace("\u2020", "").split("-")
    if len(parts) < 6:
        return "Insufficient data for assessment"

    i_code = parts[3].strip()
    c_code = parts[2].strip()
    d_code = parts[4].strip()

    # Build confidence description
    credibility = {
        "I1": "Confirmed",
        "I2": "Probable",
        "I3": "Possible",
        "I4": "Doubtful",
        "I5": "Improbable",
        "I6": "Unassessed",
    }.get(i_code, "Unknown")

    corroboration = {
        "C1": "multiple independent sources",
        "C2": "dual-source corroboration",
        "C3": "single source with supporting data",
        "C4": "single source only",
        "C5": "contested (conflicting sources)",
    }.get(c_code, "")

    inference = {
        "D1": "direct evidence",
        "D2": "one inference step",
        "D3": "analytical inference",
        "D4": "interpretive assessment",
    }.get(d_code, "")

    return f"{credibility} ({corroboration}, {inference})"


def generate_evidence_file(pattern: DetectedPattern, evidence_id: str) -> str:
    """Generate a Markdown evidence file for a detected pattern.

    Follows the MHEES assessment sheet format with all required fields.
    """
    code = pattern.mhees_code or auto_code(pattern)
    r_justification = generate_justification(pattern, "R")
    i_justification = generate_justification(pattern, "I")
    badge = mhees_to_confidence_badge(code)

    evidence_list = "\n".join(
        f"{i+1}. {e.source}: {e.description}"
        + (f" ({e.date})" if e.date else "")
        + (f" [${e.amount:,.0f}]" if e.amount else "")
        for i, e in enumerate(pattern.evidence)
    )

    next_steps_list = "\n".join(f"- {s}" for s in pattern.next_steps)

    return f"""---
id: {evidence_id}
mhees: {code}
confidence: {badge}
pattern: {pattern.pattern_name}
tier: {pattern.tier}
score: {pattern.final_score:.1f}
generated: {__import__('datetime').datetime.now().isoformat()}
---

## Claim

{pattern.narrative}

## MHEES Assessment: {code}

## Evidence Chain

{evidence_list}

## R\u2020 Justification (DRAFT -- review before publication)

{r_justification}

## I\u2020 Justification (DRAFT -- review before publication)

{i_justification}

## Falsification Conditions

{next_steps_list}

## Adversarial Counter-Reading

*[To be completed by journalist: what is the strongest case against this finding?]*
"""
