"""Builds 04_FIXED_SCORE_AND_SENSITIVITY.ipynb (PROTOCOL.md: the specified score, the data audit, the sensitivity analysis).

    python build_score_notebook.py
"""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "exp02_substance_scorer"))
from build_notebooks import code, md, write

HERE = Path(__file__).resolve().parent


def reading():
    p = HERE / "reading_4.md"
    return md(p.read_text(encoding="utf-8") if p.exists() else "_Reading of the results: written after the run._")


SETUP = """
import sys, warnings, json, importlib.util
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path("../../helpers").resolve()))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, seaborn as sns
from scipy.stats import spearmanr
sns.set_theme(style="whitegrid")
pd.set_option("display.width", 170); pd.set_option("display.max_columns", 30)
import student_evidence as se
spec = importlib.util.spec_from_file_location("collab_score_nb", Path("../../..") / "score.py")
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
RESULTS = Path("results"); RESULTS.mkdir(exist_ok=True)
"""

BUILD = """
rows = []
for meta, ev in se.real() + se.simulated():
    r = S.assess(ev)
    rows.append({**meta, "score": r["score"], "available": r["score"] is not None, "interval_lo": (r["interval"] or [None, None])[0], "interval_hi": (r["interval"] or [None, None])[1],
                 "team_activity": ev["team"]["reviews_and_comments"], **{k: v for k, v in r["features"].items()}})
res = pd.DataFrame(rows)
print(len(res), "student-sprints:", res.groupby("source").size().to_dict())
"""

GATE = """
def summary(d):
    n = len(d); a = int(d.available.sum())
    return pd.Series({"student-sprints": n, "team reviewed (score available)": a, "not available (team never reviewed)": n - a,
                      "available and score = 0": int((d.score == 0).sum()), "available and score > 0": int((d.score > 0).sum()),
                      "student wrote any review or comment text": int(((d.Co_count_review_texts + d.Co_count_discussion_texts) > 0).sum())})
gate = res.groupby("source").apply(summary).T
gate
"""

DIST = """
print("Real student-sprints with a score:")
display(res[(res.source == "real") & res.available][["student", "team", "sprint", "score", "interval_lo", "interval_hi", "Co_count_substantive_texts", "Co_count_trivial_texts", "Co_count_reviewed_prs"]].round(3))
sim = res[(res.source == "simulated") & res.available]
print("Simulated student-sprints with a score: n =", len(sim)); display(sim.score.describe().round(3).to_frame().T)
fig, ax = plt.subplots(figsize=(7, 3)); sns.histplot(sim.score, bins=20, ax=ax); ax.set_xlabel("Collaboration score (simulated students, team reviewing)"); plt.show()
"""

SENS = '''
caps_scales = (0.5, 1.0, 2.0)
N_WEIGHTS = 1000
rng = np.random.default_rng(7)
W = rng.dirichlet(np.ones(len(S.MEASURES)), size=N_WEIGHTS)            # equal on average

def score_matrix(ev_list, scale, weights_list):
    """scores[i, j]: student-sprint i under weighting j and the caps scaled by `scale`."""
    ms = [S.measures(ev, {k: v * scale for k, v in S.CAPS.items()})[0] for ev in ev_list]
    return np.array([[S.combine(m, dict(zip(S.MEASURES, w))) for w in weights_list] for m in ms], dtype=float), ms

def rank_corr(a, b):
    ok = ~(np.isnan(a) | np.isnan(b))
    if ok.sum() < 3 or np.ptp(a[ok]) == 0 or np.ptp(b[ok]) == 0:
        return np.nan
    return spearmanr(a[ok], b[ok]).correlation

equal = [np.full(len(S.MEASURES), 1 / len(S.MEASURES))]
out, per_source = [], {}
for source, items in (("real", se.real()), ("simulated", se.simulated())):
    items = [(m, e) for m, e in items if S.assess(e)["score"] is not None]
    evs = [e for _, e in items]
    base, _ = score_matrix(evs, 1.0, equal)
    base = base[:, 0]
    for scale in caps_scales:
        mat, _ = score_matrix(evs, scale, list(W) if scale == 1.0 else equal)
        if scale == 1.0:
            rs = [rank_corr(base, mat[:, j]) for j in range(N_WEIGHTS)]
            out.append({"source": source, "variant": f"{N_WEIGHTS} random weightings (caps 1x)", "n": len(evs), "median": np.nanmedian(rs), "p5": np.nanpercentile(rs, 5), "min": np.nanmin(rs)})
        else:
            # caps scaled, combined with the same random weightings as well, to cover both assumptions together
            mat2, _ = score_matrix(evs, scale, list(W[:200]))
            rs = [rank_corr(base, mat2[:, j]) for j in range(mat2.shape[1])]
            out.append({"source": source, "variant": f"caps x{scale} with equal weights", "n": len(evs), "median": rank_corr(base, mat[:, 0]), "p5": np.nan, "min": rank_corr(base, mat[:, 0])})
            out.append({"source": source, "variant": f"caps x{scale} with 200 random weightings", "n": len(evs), "median": np.nanmedian(rs), "p5": np.nanpercentile(rs, 5), "min": np.nanmin(rs)})
sens = pd.DataFrame(out).round(3)
sens["meets target (median >= 0.90, min >= 0.80)"] = (sens["median"] >= 0.90) & (sens["min"] >= 0.80)
sens.to_csv(RESULTS / "fixed_score_sensitivity.csv", index=False)
sens
'''

FACE = """
sim = res[(res.source == "simulated")]
face = sim.groupby("behaviour").agg(student_sprints=("score", "size"), available=("available", "sum"), mean_score=("score", "mean"),
                                    mean_review_texts=("Co_count_review_texts", "mean"), mean_trivial=("Co_count_trivial_texts", "mean")).round(3).sort_values("mean_score", ascending=False)
face
"""

INV = """
import subprocess
r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "04_collaboration/tests"], cwd=str(Path("../../../..").resolve()), capture_output=True, text=True)
print((r.stdout + r.stderr).strip().splitlines()[-4:])
"""

SAVE = """
res.to_csv(RESULTS / "fixed_score_all.csv", index=False)
summary_json = {"gate": gate.to_dict(), "sensitivity_target_met": bool(sens["meets target (median >= 0.90, min >= 0.80)"].all()), "score_version": S.SCORE_VERSION}
(RESULTS / "fixed_score_summary.json").write_text(json.dumps(summary_json, indent=1, default=str), encoding="utf-8")
"""


def main():
    write(HERE / "04_FIXED_SCORE_AND_SENSITIVITY.ipynb", [
        md("""
# Collaboration step 2: the specified score, the data audit and the sensitivity analysis

Protocol: [PROTOCOL.md](../../PROTOCOL.md). The score is the equal-weight mean of six measures with an evidence gate (`score.py`); nothing here is fitted. This notebook
(1) scores every real and simulated student-sprint, (2) reports how many can be scored at all (the audit), (3) measures how much the ranking depends on the two design
assumptions, equal weights and the count caps, and (4) checks the invariants. The simulated students and their texts were written by the assistant: they exercise the
pipeline, they do not measure accuracy.
"""),
        code(SETUP),
        md("## 1. Score every student-sprint"), code(BUILD),
        md("## 2. Data audit: how many student-sprints can be scored"), code(GATE),
        md("## 3. Score distribution"), code(DIST),
        md("## 4. Sensitivity to the design assumptions\n\nSpearman correlation of each variant's ranking with the default ranking. Target (fixed in PROTOCOL.md before the run): median >= 0.90 and minimum >= 0.80."),
        code(SENS),
        md("## 5. Face check on the simulated behaviour classes\n\nThe classes were written to differ in reviewing; a score that does not separate them would be wrong. This checks the direction only (assistant-written data)."),
        code(FACE),
        md("## 6. Invariants\n\nRun of the unit tests (gate, approvals/padding/self/bot do not raise the score, monotonic in substantive reviews, determinism, weights renormalise)."),
        code(INV),
        md("## 7. Reading the results"), reading(), code(SAVE),
    ])


if __name__ == "__main__":
    main()
