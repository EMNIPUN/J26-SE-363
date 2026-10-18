"""Step 4: a balanced synthetic set derived from the real records.

Each synthetic record is an interpolation between two real records of the same provisional
profile (SMOTE, Chawla et al. 2002) plus small noise, then repaired so it stays a possible sprint:
whole numbers stay whole, ratios stay in 0-1, no commits means no code, tasks done never exceed
tasks assigned, and so on. Nothing is invented from scratch: every value lies between two real
students' values. Records that look perfect on every factor are rejected, because no real
student in the cohort is.

    python scripts/04_synthesize.py --per-profile 100 --seed 7
"""

import argparse
import csv
import math
import random

from identity import DATASET
from profiles import PROFILES, indices, profile

ID_COLUMNS = ("record_id", "team_id", "sprint_id", "student_id", "project_domain")
INTEGER = {
    "team_size", "E_CC", "E_LOC_net", "E_LOC_added", "E_LOC_deleted", "E_LOC_net_capped", "E_FC", "E_CT", "E_RD",
    "E_merge_commits", "E_bulk_commits", "E_bulk_lines", "E_test_lines", "C_first_active_day", "C_bimodal", "C_no_activity",
    "RF_tasks_assigned", "RF_tasks_done", "RF_tasks_partial", "RF_tasks_not_started", "RF_done_by_teammate", "RF_ac_total",
    "RF_ac_met", "RF_carried_over", "Co_MC", "Co_PCount", "Co_CCount", "Co_prs_opened", "Co_prs_merged",
    "Co_prs_merged_for_others", "Co_team_uses_prs", "TC_SP_total", "KO_lines_added_code", "KO_snippet_candidates",
}
BINARY = {"C_bimodal", "C_no_activity", "Co_team_uses_prs"}
UNIT = {
    "C_AWR", "C_DC", "C_LI_norm", "C_CV_norm", "RF_completion_rate", "RF_ac_ratio", "RF_llm_score", "RF_untracked_ratio",
    "Co_PRC_depth", "Co_IC_depth", "Co_IR", "Co_shared_file_ratio", "KO_survival", "KO_primary_owner_share",
}


def num(v):
    if v in ("", None):
        return None
    x = float(v)
    return None if math.isnan(x) else x


def blend(a, b, lam, sd, rng):
    if a is None and b is None:
        return None
    if a is None or b is None:
        return a if b is None else b
    return a + lam * (b - a) + rng.gauss(0, 0.05 * sd)


def repair(r):
    """Make a blended record internally consistent."""
    for k in UNIT:
        if r.get(k) is not None:
            r[k] = min(1.0, max(0.0, r[k]))
    for k in INTEGER:
        if r.get(k) is not None:
            r[k] = int(round(r[k])) if k in ("E_LOC_net", "E_LOC_net_capped") else max(0, int(round(r[k])))
    for k in BINARY:
        if r.get(k) is not None:
            r[k] = 1 if r[k] >= 0.5 else 0
    if r["E_CC"] == 0:  # no commits: no code, no consistency signal
        for k in ("E_LOC_net", "E_LOC_added", "E_LOC_deleted", "E_LOC_net_capped", "E_FC", "E_bulk_commits", "E_bulk_lines",
                  "E_test_lines", "KO_lines_added_code", "KO_snippet_candidates"):
            r[k] = 0
        r.update({"C_AWR": 0.0, "C_DC": 1.0, "C_LI_norm": 1.0, "C_CV_norm": 1.0, "C_first_active_day": None,
                  "C_bimodal": 0, "C_no_activity": 1, "RF_untracked_ratio": None, "KO_survival": None,
                  "KO_primary_owner_share": None, "Co_shared_file_ratio": 0.0})
    else:
        r["C_no_activity"] = 0
        r["C_AWR"] = max(r["C_AWR"], 1 / 14)
        r["E_LOC_net"] = r["E_LOC_added"] - r["E_LOC_deleted"]
        r["E_FC"] = max(1, r["E_FC"])
        if r.get("C_first_active_day") is None:
            r["C_first_active_day"] = 0
        r["C_first_active_day"] = min(13, r["C_first_active_day"])
    for k, floor in (("TC_SP", 1), ("TC_SC", 1), ("TC_FI", 0), ("TC_DR", 0), ("TC_CB", 0)):
        if r.get(k) is not None:
            r[k] = round(max(floor, r[k]), 3)
    n = r["RF_tasks_assigned"]
    r["RF_tasks_done"] = min(r["RF_tasks_done"], n)
    r["E_CT"] = r["RF_tasks_done"]
    r["RF_tasks_partial"] = min(r["RF_tasks_partial"], n - r["RF_tasks_done"])
    r["RF_tasks_not_started"] = n - r["RF_tasks_done"] - r["RF_tasks_partial"]
    r["RF_done_by_teammate"] = min(r["RF_done_by_teammate"], r["RF_tasks_not_started"] + r["RF_tasks_partial"])
    r["RF_carried_over"] = min(r["RF_carried_over"], n)
    r["RF_completion_rate"] = round(r["RF_tasks_done"] / n, 4) if n else None
    r["RF_ac_met"] = min(r["RF_ac_met"], r["RF_ac_total"])
    r["RF_ac_ratio"] = round(r["RF_ac_met"] / r["RF_ac_total"], 4) if r["RF_ac_total"] else None
    if n == 0:
        r.update({"RF_llm_score": None, "TC_SP": None, "TC_SC": None, "TC_SP_total": 0, "TC_FI": None, "TC_DR": None, "TC_CB": None})
    r["Co_prs_merged"] = min(r["Co_prs_merged"], r["Co_prs_opened"])
    if r["Co_prs_opened"] == 0:
        r["Co_IR"] = None
    r["Co_CCount"] = max(r["Co_CCount"], 0)
    r["E_RD"] = max(r["E_RD"], r["Co_prs_merged_for_others"])
    return r


def looks_perfect(ix, r):
    return ix["effort_index"] > 0.9 and ix["consistency_index"] > 0.75 and ix["collaboration_index"] > 0.8 and (r.get("RF_completion_rate") or 0) >= 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-profile", type=int, default=100)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    with open(DATASET / "features_real.csv", newline="", encoding="utf-8") as f:
        real = list(csv.DictReader(f))
    columns = [c for c in real[0] if c not in ID_COLUMNS]
    ix = indices(real)
    for r, i in zip(real, ix):
        r.update(i)
        r["profile"] = profile(i, r)
    sds = {}
    for c in columns:
        vals = [num(r[c]) for r in real if num(r[c]) is not None]
        sds[c] = (sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / len(vals)) ** 0.5 if len(vals) > 1 else 0.0
    by_profile = {p: [r for r in real if r["profile"] == p] for p in PROFILES}
    print("real records per profile:", {p: len(v) for p, v in by_profile.items()})

    out, rejected, drifted = [], 0, 0
    for p in PROFILES:
        seeds = by_profile[p]
        if len(seeds) < 2:
            print(f"  {p}: fewer than 2 real records, not synthesised")
            continue
        made = 0
        while made < args.per_profile:
            a, b = rng.sample(seeds, 2)
            lam = rng.random()
            r = {c: blend(num(a[c]), num(b[c]), lam, sds[c], rng) for c in columns if c not in ("effort_index", "consistency_index", "collaboration_index", "profile")}
            r = repair(r)
            check = indices(real + [{k: ("" if v is None else v) for k, v in r.items()}])[-1]
            if looks_perfect(check, r):
                rejected += 1
                continue
            if profile(check, r) != p:  # the blend left the profile it was made for
                drifted += 1
                continue
            made += 1
            r.update({"synthetic_id": f"SYN-{p[:3].upper()}-{made:03d}", "profile": p, "parent_a": a["record_id"],
                      "parent_b": b["record_id"], "lambda": round(lam, 3), "seed_records": len(seeds)})
            out.append(r)
    header = ["synthetic_id", "profile", "parent_a", "parent_b", "lambda", "seed_records"] + [c for c in columns if c not in ("effort_index", "consistency_index", "collaboration_index", "profile")]
    with open(DATASET / "synthetic_dataset.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in out:
            writer.writerow({k: ("" if r.get(k) is None else round(r[k], 4) if isinstance(r[k], float) else r[k]) for k in header})
    with open(DATASET / "features_real_profiles.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", "effort_index", "consistency_index", "collaboration_index", "profile"])
        writer.writeheader()
        for r in real:
            writer.writerow({k: r[k] for k in writer.fieldnames})
    print(f"synthetic_dataset.csv: {len(out)} records ({rejected} near-perfect and {drifted} out-of-profile candidates rejected)")


if __name__ == "__main__":
    main()
