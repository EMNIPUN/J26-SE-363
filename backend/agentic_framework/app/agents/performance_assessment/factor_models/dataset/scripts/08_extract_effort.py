"""Step 8: the Effort dataset, one file for model training.

Reads final_dataset.csv and keeps what Effort needs: identifiers, the five proposal features and
their supporting columns, the Effort score with its interval, the rater's Effort label, and the
split group. Writes ../01_effort/dataset/effort_dataset.csv.

`group` is the unit for splitting: teams that share a student are one group, so no student is in
two groups (16 of 26 students belong to more than one team). Synthetic records take the group of
their parents, and `parents_in_group` says whether both parents agree.

    python scripts/08_extract_effort.py
"""

import csv
from pathlib import Path

import pandas as pd

from identity import DATASET

TARGET = DATASET.parent / "01_effort" / "dataset"
FEATURES = ["E_CC", "E_LOC_net", "E_LOC_net_capped", "E_FC", "E_CT", "E_RD"]
SUPPORT = ["E_LOC_added", "E_LOC_deleted", "E_merge_commits", "E_bulk_commits", "E_bulk_lines", "E_test_lines"]


def groups(real):
    """Connected components of teams linked by a shared student."""
    parent = {t: t for t in real.team_id.unique()}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _, g in real.groupby("student_id"):
        teams = list(g.team_id.unique())
        for t in teams[1:]:
            parent[find(t)] = find(teams[0])
    # largest first (by number of teams); ties broken by the smallest team id, so letters never change between runs
    roots = sorted({find(t) for t in parent}, key=lambda r: (-sum(find(t) == r for t in parent), min(t for t in parent if find(t) == r)))
    name = {r: chr(ord("A") + i) for i, r in enumerate(roots)}
    return {t: name[find(t)] for t in parent}


def main():
    final = pd.read_csv(DATASET / "final_dataset.csv", low_memory=False)
    real_src = pd.read_csv(DATASET / "features_real.csv", low_memory=False)
    syn_src = pd.read_csv(DATASET / "synthetic_dataset.csv", low_memory=False)

    # the Effort columns in the final file must equal the source files, or it is stale
    check = final[final.source == "real"].set_index("record_id")[FEATURES].astype(float)
    ref = real_src.set_index("record_id")[FEATURES].astype(float).reindex(check.index)
    assert (check - ref).abs().max().max() < 1e-6, "final_dataset.csv real Effort columns differ from features_real.csv"
    schk = final[final.source == "synthetic"].set_index("record_id")[FEATURES].astype(float)
    sref = syn_src.set_index("synthetic_id")[FEATURES].astype(float).reindex(schk.index)
    assert (schk - sref).abs().max().max() < 1e-3, "final_dataset.csv synthetic Effort columns differ from synthetic_dataset.csv"

    real = final[final.source == "real"]
    team_group = groups(real)
    student_group = {r.record_id: team_group[r.team_id] for r in real.itertuples()}

    rows = []
    for r in final.itertuples(index=False):
        d = r._asdict()
        if d["source"] == "real":
            group, both = team_group[d["team_id"]], ""
            parents = ""
        else:
            a, b = syn_src.loc[syn_src.synthetic_id == d["record_id"], ["parent_a", "parent_b"]].iloc[0]
            ga, gb = student_group[a], student_group[b]
            group, both = ga, int(ga == gb)
            parents = f"{a} {b}"
        rows.append({
            "record_id": d["record_id"], "source": d["source"], "group": group,
            "team_id": d["team_id"] if d["source"] == "real" else "", "sprint_id": d["sprint_id"] if d["source"] == "real" else "",
            "student_id": d["student_id"] if d["source"] == "real" else "", "team_size": d["team_size"] if d["source"] == "real" else "",
            "profile": d["profile_or_parent"] if d["source"] == "synthetic" else "", "parents": parents, "parents_in_group": both,
            **{c: getattr(r, c) for c in FEATURES}, **{c: getattr(r, c) for c in SUPPORT},
            "no_activity": int(r.E_CC == 0),
            # 1 when the team opened no pull requests that sprint, so a review was not possible (E_RD = 0 is then "not applicable")
            "rd_not_applicable": int(r.Co_team_uses_prs == 0),
            "effort_score": r.E_score, "effort_score_lo": r.E_score_lo, "effort_score_hi": r.E_score_hi, "effort_extrapolated": r.E_extrapolated,
            "label_source": ("rater" if r.in_ground_truth == 1 else "propagated"),
            "effort_label": r.GT_E if r.in_ground_truth == 1 else r.E_score,
            "rater_effort": r.GT_E if r.in_ground_truth == 1 else "",
        })
    out = pd.DataFrame(rows)
    TARGET.mkdir(parents=True, exist_ok=True)
    out.to_csv(TARGET / "effort_dataset.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"{TARGET / 'effort_dataset.csv'}: {len(out)} rows")
    print(out.groupby(["source", "group"]).size().unstack(fill_value=0))
    print("rated:", out[out.label_source == "rater"].groupby("group").size().to_dict())


if __name__ == "__main__":
    main()
