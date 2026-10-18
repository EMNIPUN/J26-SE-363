"""Compare the simulated students with the 26 real students: feature ranges, and whether the rule-based profile
recovers the class each simulated student was written as.

    ../../01_effort/.venv/Scripts/python.exe compare_with_real.py
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DATASET = HERE.parent
sys.path.insert(0, str(DATASET / "scripts"))
import profiles as P  # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)

real = pd.read_csv(DATASET / "features_real.csv")
sim = pd.read_csv(HERE / "out" / "features_simulated.csv")
classes = pd.read_csv(HERE / "out" / "students_simulated.csv")[["student_id", "behaviour_class"]]
sim = sim.merge(classes, on="student_id")

both = pd.concat([real.assign(src="real"), sim.assign(src="simulated")], ignore_index=True)
records = both.to_dict("records")
both["profile"] = [P.profile(ix, r) for ix, r in zip(P.indices(records), records)]

print("Feature ranges of records with at least one commit (10th / 50th / 90th percentile)")
active = both[both.E_CC > 0]
for c in ["E_CC", "E_LOC_net_capped", "E_FC", "TC_FI", "TC_CB", "C_AWR", "C_CV_norm"]:
    q = active.groupby("src")[c].quantile([.1, .5, .9]).unstack().round(2)
    print(f"  {c:18s} real {q.loc['real'].tolist()}   simulated {q.loc['simulated'].tolist()}")

print("\nClass each simulated student was written as (rows) vs rule-based profile of each of their records (columns)")
print(pd.crosstab(both[both.src == "simulated"].behaviour_class, both[both.src == "simulated"].profile).to_string())
print("\nProfile mix (% of records)")
print((pd.crosstab(both.src, both.profile, normalize="index") * 100).round(0).to_string())
