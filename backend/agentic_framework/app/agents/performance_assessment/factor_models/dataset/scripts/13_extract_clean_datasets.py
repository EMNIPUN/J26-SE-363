"""Step 13: one training file per factor from the clean data (Effort, Consistency, Task Complexity).

Reads ``clean/final_dataset_clean.csv`` and writes ``<factor>/clean/dataset/<factor>_dataset.csv`` in the same shape as the earlier
per-factor files, so the same training code reads both. Real rows keep the split group (teams that share a student are one group);
simulated students carry source ``synthetic`` and group ``SIM`` with no parents: they are training-only in every fold.

    python scripts/13_extract_clean_datasets.py
"""

import importlib.util
from pathlib import Path

import pandas as pd

from identity import DATASET

FM = DATASET.parent
spec = importlib.util.spec_from_file_location("effort_extract", Path(__file__).with_name("08_extract_effort.py"))
effort_extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(effort_extract)

FACTORS = {
    "effort": {"folder": "01_effort", "file": "effort_dataset.csv", "score": "E", "gt": "GT_E",
               "features": ["E_CC", "E_LOC_net", "E_LOC_net_capped", "E_FC", "E_CT", "E_RD"],
               "support": ["E_LOC_added", "E_LOC_deleted", "E_test_lines"], "label_name": "rater_effort"},
    "consistency": {"folder": "02_consistency", "file": "consistency_dataset.csv", "score": "C", "gt": "GT_C",
                    "features": ["C_AWR", "C_DC", "C_LI_norm", "C_CV_norm"],
                    "support": ["C_first_active_day", "C_bimodal", "C_no_activity", "E_CC"], "label_name": "rater_consistency"},
    "task_complexity": {"folder": "05_task_complexity", "file": "task_complexity_dataset.csv", "score": "TC", "gt": "GT_TC",
                        "features": ["TC_SP", "TC_SC", "TC_FI", "TC_DR", "TC_CB"],
                        "support": ["TC_SP_total", "RF_tasks_assigned", "RF_tasks_done", "E_CC"], "label_name": "rater_task_complexity"},
}


def main():
    final = pd.read_csv(DATASET / "clean" / "final_dataset_clean.csv", low_memory=False)
    real = final[final.source == "real"]
    team_group = effort_extract.groups(real)
    for name, cfg in FACTORS.items():
        rows = []
        for r in final.to_dict("records"):
            is_real = r["source"] == "real"
            rated = r["in_ground_truth"] == 1
            row = {
                "record_id": r["record_id"], "source": "real" if is_real else "synthetic", "group": team_group[r["team_id"]] if is_real else "SIM",
                "team_id": r["team_id"], "sprint_id": r["sprint_id"], "student_id": r["student_id"], "team_size": r["team_size"],
                "profile": "" if is_real else r["behaviour_class_written"], "parents": "", "parents_in_group": "",
                **{c: r[c] for c in cfg["features"] + cfg["support"]},
                "score": r[f"{cfg['score']}_score"], "score_lo": r[f"{cfg['score']}_score_lo"], "score_hi": r[f"{cfg['score']}_score_hi"],
                "extrapolated": r[f"{cfg['score']}_extrapolated"],
                "label_source": "rater" if rated else "propagated",
                "label": r[cfg["gt"]] if rated else r[f"{cfg['score']}_score"],
                cfg["label_name"]: r[cfg["gt"]] if rated else "",
            }
            if name == "effort":
                row["no_activity"] = int(r["E_CC"] == 0)
                row["rd_not_applicable"] = int(r["Co_team_uses_prs"] == 0)
            rows.append(row)
        out = pd.DataFrame(rows)
        target = FM / cfg["folder"] / "clean" / "dataset"
        target.mkdir(parents=True, exist_ok=True)
        out.to_csv(target / cfg["file"], index=False)
        print(f"{name}: {len(out)} rows -> {target / cfg['file']}")
        print("  real by group:", out[out.source == "real"].groupby("group").size().to_dict(), "| simulated:", int((out.source == "synthetic").sum()),
              "| rated by group:", out[out.label_source == "rater"].groupby("group").size().to_dict())


if __name__ == "__main__":
    main()
