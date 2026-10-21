"""The table the Behavioral Pattern experiments run on: one row per student-sprint with the rule inputs and every available label.

    python bp_data.py        writes ../dataset/bp_inputs.csv

Inputs (E, C): the marks in dataset/clean/final_dataset_clean.csv. Collaboration (Co): the new fixed Collaboration score from 04_collaboration (NaN when the factor is "not available"
because nobody in the team reviewed in the sprint); the old propagated Collaboration mark is kept as ``Co_old`` for comparison only. Labels (all written by the assistant): the
behaviour class the simulated student was written to follow, the pattern given at rating time to each record (reference_ratings), and the pattern given to the 20 anchors.
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FM = HERE.parents[2]
OUT = HERE.parent / "dataset" / "bp_inputs.csv"
NAMES = {"consistent_deep_contributor": "Consistent deep contributor", "last_minute_rusher": "Last-minute rusher", "reviewer_coordinator": "Reviewer or coordinator",
         "burst_worker": "Burst worker", "free_rider": "Free rider", "no_specific_pattern": "Balanced contributor"}


def build():
    d = pd.read_csv(FM / "dataset" / "clean" / "final_dataset_clean.csv", low_memory=False)
    ref = pd.read_csv(FM / "dataset" / "reference_ratings" / "reference_ratings.csv")[["record_id", "BP_pattern"]].rename(columns={"BP_pattern": "ref_pattern"})
    sim = pd.read_csv(FM / "dataset" / "synthetic_students" / "out" / "students_simulated.csv")[["student_id", "behaviour_class"]].rename(columns={"behaviour_class": "sim_class"})
    co = pd.read_csv(FM / "04_collaboration" / "training" / "experiments" / "exp03_fixed_score" / "results" / "fixed_score_all.csv")
    co = co[["source", "student", "sprint", "score", "available"]].rename(columns={"student": "student_id", "sprint": "sprint_id", "score": "Co", "available": "Co_available"})
    d = d.merge(co, on=["source", "student_id", "sprint_id"], how="left").merge(ref, on="record_id", how="left").merge(sim, on="student_id", how="left")
    out = pd.DataFrame({
        "record_id": d.record_id, "source": d.source, "student_id": d.student_id, "team_id": d.team_id, "sprint_id": d.sprint_id,
        "E": d.E_score, "C": d.C_score, "late_churn": d.C_DC.where(d.C_no_activity == 0), "Co": d.Co, "Co_available": d.Co_available.fillna(False).astype(bool), "Co_old": d.Co_score, "bimodal": d.C_bimodal,
        "RF": d.RF_score, "TC": d.TC_score, "KO": d.KO_score,
        "rule_pattern_old": d.BP_pattern, "ref_pattern": d.ref_pattern, "sim_class": d.sim_class.where(d.source == "simulated"),
        "gt_pattern": d.GT_BP_pattern, "in_ground_truth": d.in_ground_truth, "final_mark_old": d.final_mark,
    })
    for c in ("rule_pattern_old", "ref_pattern", "sim_class", "gt_pattern"):
        out[c] = out[c].map(NAMES).where(out[c].notna())
    return out


if __name__ == "__main__":
    t = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT, index=False)
    print(len(t), "rows;", t.groupby("source").size().to_dict(), "; Collaboration available:", int(t.Co_available.sum()))
    print("labels:", {c: int(t[c].notna().sum()) for c in ("ref_pattern", "sim_class", "gt_pattern")})
