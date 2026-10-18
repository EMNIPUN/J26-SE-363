"""Provisional contributor profile of a record, from its features alone.

Used before any marks exist: to balance the synthetic set and to stratify the ground-truth sample.
It mirrors the proposal's Behavioral Pattern rules (3.1.7) with cohort percentiles standing in
for the factor scores. It is not the final BP label, which step 6 derives from the marks.
"""

import math

PROFILES = [
    "consistent_deep_contributor",
    "last_minute_rusher",
    "burst_worker",
    "reviewer_coordinator",
    "free_rider",
    "no_specific_pattern",
]


def _num(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def percentile(values):
    """value -> share of the cohort at or below it."""
    ordered = sorted(values)
    n = len(ordered)

    def rank(v):
        if n == 0:
            return 0.0
        lo = sum(1 for x in ordered if x < v)
        eq = sum(1 for x in ordered if x == v)
        return (lo + 0.5 * eq) / n

    return rank


def indices(records):
    """Effort, consistency and collaboration indices (0-1, cohort percentiles) per record."""
    def col(name):
        return [(_num(r[name]) or 0.0) for r in records]

    ranks = {name: percentile(col(name)) for name in ("E_CC", "E_LOC_net_capped", "E_FC", "E_CT", "E_RD", "Co_PCount", "Co_shared_file_ratio", "Co_prs_merged_for_others")}
    out = []
    for r in records:
        g = lambda k: _num(r[k]) or 0.0  # noqa: E731
        effort = (ranks["E_CC"](g("E_CC")) + ranks["E_LOC_net_capped"](g("E_LOC_net_capped")) + ranks["E_FC"](g("E_FC")) + ranks["E_CT"](g("E_CT"))) / 4
        if g("E_CC") == 0:
            effort = 0.0
        consistency = 0.0 if g("C_no_activity") else (g("C_AWR") + (1 - g("C_DC")) + (1 - g("C_LI_norm")) + (1 - g("C_CV_norm"))) / 4
        collab = (ranks["E_RD"](g("E_RD")) + ranks["Co_PCount"](g("Co_PCount")) + ranks["Co_shared_file_ratio"](g("Co_shared_file_ratio")) + ranks["Co_prs_merged_for_others"](g("Co_prs_merged_for_others"))) / 4
        out.append({"effort_index": round(effort, 4), "consistency_index": round(consistency, 4), "collaboration_index": round(collab, 4)})
    return out


def profile(ix, r):
    """Feature-level reading of the proposal's five patterns; everything else has no pattern."""
    e, co = ix["effort_index"], ix["collaboration_index"]
    awr, dc, gap = (_num(r.get(k)) or 0.0 for k in ("C_AWR", "C_DC", "C_LI_norm"))
    first = _num(r.get("C_first_active_day"))
    bimodal = str(r.get("C_bimodal")) in ("1", "1.0")
    if e < 0.3 and co < 0.45:
        return "free_rider"
    if e < 0.45 and co >= 0.65:
        return "reviewer_coordinator"
    if e >= 0.6 and bimodal:
        return "burst_worker"
    if e >= 0.6 and awr >= 0.3 and dc <= 0.5 and gap <= 0.5:
        return "consistent_deep_contributor"
    if e >= 0.5 and (dc >= 0.6 or (first is not None and first >= 9)):
        return "last_minute_rusher"
    return "no_specific_pattern"
