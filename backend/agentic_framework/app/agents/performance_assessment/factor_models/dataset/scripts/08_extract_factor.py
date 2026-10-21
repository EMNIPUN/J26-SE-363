"""Step 8 (any regression factor): one training file per factor from final_dataset.csv.

    python scripts/08_extract_factor.py consistency
    python scripts/08_extract_factor.py task_complexity

Keeps identifiers, the factor's features and support columns, the factor score with its interval,
the rater's label and the split group (teams that share a student are one group, so no student is
in two groups; same groups as the Effort dataset). Synthetic rows take the group of their parents
and `parents_in_group` says whether both agree.
"""

import importlib.util
import sys
from pathlib import Path

import pandas as pd

from identity import DATASET

spec = importlib.util.spec_from_file_location("effort_extract", Path(__file__).with_name("08_extract_effort.py"))
effort_extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(effort_extract)

FACTORS = {
    "consistency": {
        "folder": "02_consistency", "file": "consistency_dataset.csv", "prefix": "C", "gt": "GT_C", "score": "C",
        "features": ["C_AWR", "C_DC", "C_LI_norm", "C_CV_norm"],
        "support": ["C_first_active_day", "C_bimodal", "C_no_activity", "E_CC"],
        "source": "features_real.csv",
    },
    "task_complexity": {
        "folder": "05_task_complexity", "file": "task_complexity_dataset.csv", "prefix": "TC", "gt": "GT_TC", "score": "TC",
        "features": ["TC_SP", "TC_SC", "TC_FI", "TC_DR", "TC_CB"],
        "support": ["TC_SP_total", "RF_tasks_assigned", "RF_tasks_done", "E_CC"],
        "source": "features_real.csv",
    },
}


def main(name):
    cfg = FACTORS[name]
    target = DATASET.parent / cfg["folder"] / "dataset"
    final = pd.read_csv(DATASET / "final_dataset.csv", low_memory=False)
    real_src = pd.read_csv(DATASET / cfg["source"], low_memory=False)
    syn_src = pd.read_csv(DATASET / "synthetic_dataset.csv", low_memory=False)
    feats = cfg["features"] + cfg["support"]

    # the factor's columns must equal the source files, or final_dataset.csv is stale
    chk = final[final.source == "real"].set_index("record_id")[feats].astype(float)
    ref = real_src.set_index("record_id")[feats].astype(float).reindex(chk.index)
    assert ((chk - ref).abs().fillna(0).max().max()) < 1e-6, "final_dataset.csv real columns differ from features_real.csv"

    real = final[final.source == "real"]
    team_group = effort_extract.groups(real)
    group_of = {r.record_id: team_group[r.team_id] for r in real.itertuples()}
    parents = syn_src.set_index("synthetic_id")[["parent_a", "parent_b"]]

    rows = []
    for r in final.itertuples(index=False):
        d = r._asdict()
        is_real = d["source"] == "real"
        if is_real:
            group, both, par = team_group[d["team_id"]], "", ""
        else:
            a, b = parents.loc[d["record_id"]]
            group, both, par = group_of[a], int(group_of[a] == group_of[b]), f"{a} {b}"
        rated = r.in_ground_truth == 1
        rows.append({
            "record_id": d["record_id"], "source": d["source"], "group": group,
            "team_id": d["team_id"] if is_real else "", "sprint_id": d["sprint_id"] if is_real else "",
            "student_id": d["student_id"] if is_real else "", "team_size": d["team_size"] if is_real else "",
            "profile": d["profile_or_parent"] if not is_real else "", "parents": par, "parents_in_group": both,
            **{c: d[c] for c in feats},
            "score": d[f"{cfg['score']}_score"], "score_lo": d[f"{cfg['score']}_score_lo"], "score_hi": d[f"{cfg['score']}_score_hi"],
            "extrapolated": d[f"{cfg['score']}_extrapolated"],
            "label_source": "rater" if rated else "propagated",
            "label": d[cfg["gt"]] if rated else d[f"{cfg['score']}_score"],
            f"rater_{name}": d[cfg["gt"]] if rated else "",
        })
    out = pd.DataFrame(rows)
    target.mkdir(parents=True, exist_ok=True)
    out.to_csv(target / cfg["file"], index=False)
    print(f"{target / cfg['file']}: {len(out)} rows")
    print(out.groupby(["source", "group"]).size().unstack(fill_value=0))
    print("rated:", out[out.label_source == "rater"].groupby("group").size().to_dict())


if __name__ == "__main__":
    main(sys.argv[1])
