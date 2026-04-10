"""Population-level nonprofit anomaly scoring.

Computes anomaly scores for every nonprofit in IRS bulk data.
Higher score = more anomalous = more worth investigating.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


# NTEE major group prefixes
NTEE_GROUPS = {
    "A": "Arts, Culture & Humanities",
    "B": "Education",
    "C": "Environment",
    "D": "Animal-Related",
    "E": "Health",
    "F": "Mental Health",
    "G": "Disease/Disorders",
    "H": "Medical Research",
    "I": "Crime & Legal",
    "J": "Employment",
    "K": "Food, Agriculture",
    "L": "Housing & Shelter",
    "M": "Public Safety",
    "N": "Recreation & Sports",
    "O": "Youth Development",
    "P": "Human Services",
    "Q": "International",
    "R": "Civil Rights & Advocacy",
    "S": "Community Improvement",
    "T": "Philanthropy & Voluntarism",
    "U": "Science & Technology",
    "V": "Social Science",
    "W": "Public & Societal Benefit",
    "X": "Religion Related",
    "Y": "Mutual/Membership",
    "Z": "Unknown",
}

# Beat name to NTEE prefix mapping
BEAT_FILTERS = {
    "health": ["E", "F", "G", "H"],
    "political": ["R", "S", "W"],
    "religious": ["X"],
    "education": ["B"],
    "human_services": ["P", "O"],
    "arts": ["A"],
    "veterans": ["W"],
    "environment": ["C", "D"],
    "international": ["Q"],
}


def scan_population(
    df: pd.DataFrame,
    min_revenue: int = 100_000,
    state: Optional[str] = None,
    ntee_prefixes: Optional[list[str]] = None,
    beat: Optional[str] = None,
) -> pd.DataFrame:
    """Score every nonprofit in the dataset for anomalies.

    Args:
        df: SOI Tax Stats DataFrame (from downloader.load_soi)
        min_revenue: Skip orgs below this revenue threshold
        state: Filter to a specific state (2-letter code)
        ntee_prefixes: Filter to specific NTEE major groups
        beat: Named beat filter (health, political, religious, etc.)

    Returns:
        DataFrame sorted by anomaly_score descending, with columns:
        ein, name, state, ntee, revenue, expenses, officer_comp,
        anomaly_score, flags, propublica_url
    """
    # Apply filters
    filtered = df.copy()

    if "totrevenue" in filtered.columns:
        filtered = filtered[filtered["totrevenue"] >= min_revenue]

    if state and "state" in filtered.columns:
        filtered = filtered[filtered["state"].str.upper() == state.upper()]

    if beat and beat in BEAT_FILTERS:
        ntee_prefixes = BEAT_FILTERS[beat]

    if ntee_prefixes and "ntee_cd" in filtered.columns:
        mask = filtered["ntee_cd"].fillna("").str[0].isin(ntee_prefixes)
        filtered = filtered[mask]

    if len(filtered) == 0:
        return pd.DataFrame()

    # Compute anomaly metrics
    result = pd.DataFrame()
    result["ein"] = filtered["ein"].astype(str)
    # SOI extract uses different column names; try multiple
    name_col = None
    for col in ["name", "orgname", "taxpayer_name", "NAME"]:
        if col in filtered.columns:
            name_col = col
            break
    result["name"] = filtered[name_col] if name_col else "EIN:" + result["ein"]
    result["state"] = filtered.get("state", filtered.get("STATE", ""))
    result["ntee"] = filtered.get("ntee_cd", "")
    result["revenue"] = filtered.get("totrevenue", 0)
    result["expenses"] = filtered.get("totfuncexpns", 0)
    result["officer_comp"] = filtered.get("compnsatncurrofcr", 0)
    result["other_salaries"] = filtered.get("othrsalwages", 0)
    result["contributions"] = filtered.get("totcntrbgfts", 0)
    result["program_revenue"] = filtered.get("totprgmrevnue", 0)
    result["assets"] = filtered.get("totassetsend", 0)
    result["liabilities"] = filtered.get("totliabend", 0)
    result["fundraising_exp"] = filtered.get("profndraising", 0)

    # Compute individual anomaly scores (each 0-100)
    scores = pd.DataFrame(index=result.index)

    # 1. Executive compensation ratio (weight 15)
    comp_ratio = result["officer_comp"] / result["expenses"].replace(0, 1)
    scores["exec_comp_ratio"] = (comp_ratio.clip(0, 0.5) / 0.5 * 100).clip(0, 100) * 0.15

    # 2. Executive compensation absolute (weight 10)
    scores["exec_comp_absolute"] = 0
    scores.loc[result["officer_comp"] > 500_000, "exec_comp_absolute"] = 50 * 0.10
    scores.loc[result["officer_comp"] > 1_000_000, "exec_comp_absolute"] = 75 * 0.10
    scores.loc[result["officer_comp"] > 2_000_000, "exec_comp_absolute"] = 100 * 0.10

    # 3. Program ratio (weight 15) — lower program ratio = higher score
    prog_ratio = result["program_revenue"] / result["revenue"].replace(0, 1)
    scores["program_ratio"] = ((1 - prog_ratio.clip(0, 1)) * 100).clip(0, 100) * 0.15

    # 4. Overhead ratio (weight 10)
    overhead = 1 - (result["program_revenue"] / result["expenses"].replace(0, 1)).clip(0, 1)
    scores["overhead_ratio"] = (overhead * 100).clip(0, 100) * 0.10

    # 5. Fundraising efficiency (weight 10)
    fund_ratio = result["fundraising_exp"] / result["contributions"].replace(0, 1)
    scores["fundraising_eff"] = (fund_ratio.clip(0, 1) * 100).clip(0, 100) * 0.10

    # 6. Deficit spending (weight 5)
    deficit = (result["expenses"] - result["revenue"]) / result["revenue"].replace(0, 1)
    scores["deficit_spending"] = 0
    scores.loc[deficit > 0.2, "deficit_spending"] = 50 * 0.05
    scores.loc[deficit > 0.5, "deficit_spending"] = 100 * 0.05

    # 7. Asset hoarding (weight 5)
    asset_ratio = result["assets"] / result["revenue"].replace(0, 1)
    scores["asset_hoarding"] = 0
    scores.loc[asset_ratio > 5, "asset_hoarding"] = 50 * 0.05
    scores.loc[asset_ratio > 10, "asset_hoarding"] = 100 * 0.05

    # 8. Comp growth vs revenue growth (weight 10) — requires multi-year data
    # Placeholder: flag if comp > 10% of total expenses
    comp_expense_ratio = result["officer_comp"] / result["expenses"].replace(0, 1)
    scores["comp_vs_revenue"] = 0
    scores.loc[comp_expense_ratio > 0.10, "comp_vs_revenue"] = 50 * 0.10
    scores.loc[comp_expense_ratio > 0.20, "comp_vs_revenue"] = 100 * 0.10

    # Composite score
    result["anomaly_score"] = scores.sum(axis=1).round(1)

    # Generate flag list
    result["flags"] = ""
    flag_conditions = [
        (result["officer_comp"] > 1_000_000, "high_exec_comp"),
        (comp_ratio > 0.10, "exec_comp_ratio_high"),
        (prog_ratio < 0.65, "low_program_ratio"),
        (fund_ratio > 0.50, "high_fundraising_cost"),
        (deficit > 0.20, "deficit_spending"),
        (asset_ratio > 5, "asset_hoarding"),
        (result["officer_comp"] > result["revenue"] * 0.05, "comp_exceeds_5pct_revenue"),
    ]
    for mask, flag in flag_conditions:
        result.loc[mask, "flags"] = result.loc[mask, "flags"] + f"{flag}, "
    result["flags"] = result["flags"].str.rstrip(", ")

    # Add ProPublica URL
    result["propublica_url"] = "https://projects.propublica.org/nonprofits/organizations/" + result["ein"]

    # Sort by anomaly score
    result = result.sort_values("anomaly_score", ascending=False).reset_index(drop=True)

    return result


def get_beat_name(ntee_code: str) -> str:
    """Get human-readable category from NTEE code."""
    if not ntee_code:
        return "Unknown"
    prefix = str(ntee_code)[0].upper()
    return NTEE_GROUPS.get(prefix, "Unknown")
