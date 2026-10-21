"""Step 15: training files whose labels are ratings only, no propagation.

Every real record now has a rubric rating: the 20 in ``ground_truth/human_ratings.csv`` and 124 in
``reference_ratings/reference_ratings.csv``; every simulated record has one in the second file. All of them were written by the
assistant against ``ground_truth/EVALUATION_FORM.md`` (see ``reference_ratings/README.md``), none by a person.

A factor's label is the mean of its criteria rescaled to 0-1, as in step 12. Written to ``<factor>/clean_ref/dataset/`` in the
same shape as ``<factor>/clean/dataset/`` so the same training code reads both:

- real rows: ``label_source = rater`` (all of them), ``rating_source`` = ``protocol-20`` or ``reference``;
- simulated rows: ``label_source = reference_sim`` with their own rating as the label, training only.

    python scripts/15_reference_label_datasets.py
"""

import csv
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from identity import DATASET

HERE = Path(__file__).resolve().parent
FM = DATASET.parent


def load_module(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


step12 = load_module("step12", "12_refit_labels_clean.py")
step13 = load_module("step13", "13_extract_clean_datasets.py")
CRITERIA = {k: v[1] for k, v in step12.FACTORS.items()}


def main():
    protocol = pd.read_csv(DATASET / "ground_truth" / "human_ratings.csv").set_index("record_id")
    reference = pd.read_csv(DATASET / "reference_ratings" / "reference_ratings.csv").set_index("record_id")
    ratings = pd.concat([protocol.assign(rating_source="protocol-20"), reference.assign(rating_source="reference")])
    assert not ratings.index.duplicated().any()

    final = pd.read_csv(DATASET / "clean" / "final_dataset_clean.csv", low_memory=False)
    missing = set(final.record_id) - set(ratings.index)
    assert not missing, f"records without a rating: {sorted(missing)[:5]}"
    real = final[final.source == "real"]
    team_group = step13.effort_extract.groups(real)

    for name, cfg in step13.FACTORS.items():
        crit = CRITERIA[cfg["score"]]
        label = ((ratings[crit].astype(float).mean(axis=1) - 1) / 4).round(4)
        rows = []
        for r in final.to_dict("records"):
            is_real = r["source"] == "real"
            y = float(label[r["record_id"]])
            row = {
                "record_id": r["record_id"], "source": "real" if is_real else "synthetic", "group": team_group[r["team_id"]] if is_real else "SIM",
                "team_id": r["team_id"], "sprint_id": r["sprint_id"], "student_id": r["student_id"], "team_size": r["team_size"],
                "profile": "" if is_real else r["behaviour_class_written"], "parents": "", "parents_in_group": "",
                **{c: r[c] for c in cfg["features"] + cfg["support"]},
                "label_source": "rater" if is_real else "reference_sim",
                "rating_source": ratings.rating_source[r["record_id"]],
                "label": y, cfg["label_name"]: y,
            }
            if name == "effort":
                row["no_activity"] = int(r["E_CC"] == 0)
                row["rd_not_applicable"] = int(r["Co_team_uses_prs"] == 0)
            rows.append(row)
        out = pd.DataFrame(rows)
        target = FM / cfg["folder"] / "clean_ref" / "dataset"
        target.mkdir(parents=True, exist_ok=True)
        out.to_csv(target / cfg["file"], index=False)
        real_rows = out[out.source == "real"]
        print(f"{name}: {len(out)} rows -> {target / cfg['file']}")
        print(f"  real {len(real_rows)} (protocol-20 {int((real_rows.rating_source == 'protocol-20').sum())}, reference {int((real_rows.rating_source == 'reference').sum())}),"
              f" simulated {int((out.source == 'synthetic').sum())}; label mean real {real_rows.label.mean():.3f} sd {real_rows.label.std():.3f}"
              f" | sim mean {out[out.source == 'synthetic'].label.mean():.3f}")
        print("  real rows per group:", real_rows.groupby("group").size().to_dict())


if __name__ == "__main__":
    main()
