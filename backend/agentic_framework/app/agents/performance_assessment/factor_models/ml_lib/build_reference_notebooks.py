"""Builds <factor>/clean_ref/RETRAIN_reference.ipynb: the retrain on rubric ratings only (no propagation).

    python build_reference_notebooks.py [effort consistency task_complexity]

Heavy tuning is run by ``run_validation.py <factor>_ref``; the notebook reads its output, takes the decision, runs the final test and
sets the result beside the first clean run and the earlier uncleaned experiments. The reading of the results is taken from
<factor>/clean_ref/reading.md when it exists.
"""

import sys
from pathlib import Path

from build_retrain_notebooks import FM, OLD_FINAL, code, md, write
from retrain_configs import CONFIGS

SETUP = '''
import json
import os
import sys
import warnings
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
sys.path.insert(0, str(Path("../../ml_lib").resolve()))
warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import retrain as R
from core import GROUPS, group_bootstrap, load, make_splits, md_table, metrics, paired_diff_bootstrap
from retrain_configs import CONFIGS

sns.set_theme(style="whitegrid", context="notebook")
pd.set_option("display.width", 180)
pd.set_option("display.max_columns", 40)

cfg = CONFIGS["%%KEY%%_ref"]()
F = cfg.factor()
RES = F.results
d = load(F)
real, sim = d[d.source == "real"], d[d.source == "synthetic"]
gold = real[real.label_source == "rater"]
P20 = set(real[real.rating_source == "protocol-20"].record_id)
LABEL, ACT = cfg.label, cfg.activity
print(cfg.title, "| real", len(real), "all rated (protocol-20:", len(P20), "+ reference:", len(real) - len(P20), ") | simulated", len(sim), "training only, own ratings")
'''


def build(key):
    cfg = CONFIGS[f"{key}_ref"]()
    folder = cfg.folder
    effort = key == "effort"
    sub = lambda t: t.replace("%%KEY%%", key).replace("%%TITLE%%", cfg.title)  # noqa: E731
    reading = (folder / "reading.md").read_text(encoding="utf-8") if (folder / "reading.md").exists() else "_Reading of the results: written after the run._"
    n = iter(range(1, 20))
    cells = [
        md(sub("""
# %%TITLE%%: retraining on rubric ratings only

**What changed from the first clean run.** The first run had 20 rated records; the labels of the other 124 real records and of the 175
simulated records were estimates from a model fitted on those 20. Here the statistical propagation is gone: every real and every
simulated record has a rubric rating (`dataset/reference_ratings/`), the factor's label is the mean of its criteria rescaled to 0-1,
and the models are trained and tested on those ratings. The protocol is the same ([RETRAIN_PROTOCOL.md](../../RETRAIN_PROTOCOL.md),
amendment log); the success criteria were not touched.

**Who rated, plainly.** The 20 protocol ratings and the 299 new ones were all written by the assistant against the rubric. No person rated
anything, and the simulated students' ratings share an author with their data. A good result below shows that the models reproduce the
rubric as the assistant applies it. It is **not** human validation and not independent ground truth.

**Evaluation.** Primary: pooled over all 144 real records, each predicted by a model that never saw that student's group. Secondary: the
original 20 records only, for comparison with the first run. Simulated students are training only.
""")),
        code(sub(SETUP)),
        md(f"## {next(n)}. The labels"),
        code(sub('''
rows = []
for name, frame in (("real, protocol-20", real[real.rating_source == "protocol-20"]), ("real, reference", real[real.rating_source == "reference"]),
                    ("simulated", sim)):
    y = frame[LABEL].astype(float)
    rows.append({"records": name, "n": len(y), "mean": y.mean(), "sd": y.std(), "p10": y.quantile(.1), "median": y.median(), "p90": y.quantile(.9)})
display(pd.DataFrame(rows).set_index("records").round(3))
first = pd.read_csv(Path("../clean/dataset") / cfg.dataset_file, low_memory=False).set_index("record_id")
prop = first[(first.source == "real") & (first.label_source == "propagated")]
both = prop.label.astype(float).to_frame("propagated (first run)").join(real[LABEL].rename("rubric rating"))
print("The 124 real records whose label was an estimate in the first run: estimate against rubric rating")
print("  correlation %.3f | mean abs difference %.3f" % (both.corr().iloc[0, 1], (both.iloc[:, 0] - both.iloc[:, 1]).abs().mean()))
fig, ax = plt.subplots(figsize=(4.6, 4.4))
ax.scatter(both["rubric rating"], both["propagated (first run)"], s=18, c="#2b6cb0")
ax.plot([0, 1], [0, 1], color="grey", lw=1); ax.set_xlabel("rubric rating"); ax.set_ylabel("first-run estimate"); fig.tight_layout(); plt.show()
''')),
        md(f"## {next(n)}. Splits and baselines (validation)"),
        code(sub('''
splits = make_splits(d)
splits.to_csv(F.splits, index=False)
role = splits.join(d[["source", "label_source"]], on="record_id")
chk = role.groupby(["outer_test", "inner_val", "role"]).size().unstack(fill_value=0)
assert not ((role.role == "val") & (role.source == "synthetic")).any() and not ((role.role == "test") & (role.source == "synthetic")).any()
print("20 combinations; simulated rows are never in validation or test. Records per role (first rows):")
display(chk.head(8))
base = pd.read_csv(RES / "baseline_predictions.csv")
rows = []
for name, g in base.groupby("name"):
    m = metrics(g.y, g.pred)
    rows.append({"baseline": name, "MAE": m["MAE"], "pearson": m["pearson"], "spearman": m["spearman"], "bias": m["bias"]})
display(pd.DataFrame(rows).set_index("baseline").sort_values("MAE").round(3))
''')),
        md(f"## {next(n)}. Preprocessing: variants and label sources (Ridge, validation, selection without bias)"),
        code(sub('''
tuned = pd.read_csv(RES / "tuning_predictions.csv")
settings = json.load(open(RES / "settings.json"))
rows = []
for (variant, lab, weight), g in tuned[tuned.model == "Ridge"].groupby(["variant", "lab", "weight"]):
    p, _ = R.bias_free(g)
    m = metrics(p.y, p.pred)
    rows.append({"variant": variant, "label source": lab, "weight": weight, "MAE": m["MAE"], "pearson": m["pearson"]})
pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True).round(3)
''')),
        md(f"## {next(n)}. Ridge, Random Forest and Gradient Boosting, tuned, compared without selection bias"),
        code(sub('''
choice, table, pools, picks = R.decide(cfg, tuned, base, d, RES)
table.round(3)
''')),
        md(f"## {next(n)}. The rule for keeping a complex model"),
        code(sub('''
rule = choice["rule"]
print(f"best Ridge-type model : {rule['ridge']}  (MAE {choice['ridge_best']['MAE']:.3f})")
print(f"best tree model       : {rule['complex']}  (MAE {choice['complex_best']['MAE']:.3f})")
print(f"gain {rule['gain_mae']:+.3f} MAE, 95% interval {rule['ci'][0]:+.3f} to {rule['ci'][1]:+.3f}, better in {rule['folds_better']} of 5 folds")
chosen_name = choice["complex_best"]["model"] if rule["passes_1_3"] else choice["ridge_best"]["model"]
chosen_variant = choice["complex_best"]["variant"] if rule["passes_1_3"] else choice["ridge_best"]["variant"]
ridge_name, ridge_variant = choice["ridge_best"]["model"], choice["ridge_best"]["variant"]
print("model after rules 1-3:", chosen_name, "|", chosen_variant)
''')),
    ]
    if effort:
        cells += [
            md(f"## {next(n)}. Effort only: invariants and the guard layer (rule 4)"),
            code(sub('''
final_all, fits = R.final_test(cfg, d, chosen_name, chosen_variant, tuned, settings, extra_models=[(ridge_name, ridge_variant)])
rows = []
for (model, variant) in sorted({(m, v) for (m, v, _) in fits}):
    for guarded in (False, True):
        z, mo, sp, t = R.effort_invariants(fits, model, variant, guarded)
        rows.append({"model": f"{model} | {variant}", "guard": guarded, "zero commits ~ 0": z, "never lowered by more": mo, "spam and dump <= 0.35": sp})
display(pd.DataFrame(rows))
z, mo, sp, t = R.effort_invariants(fits, chosen_name, chosen_variant, True)
display(t.round(3))
def passes(model, variant):
    z, mo, sp, _ = R.effort_invariants(fits, model, variant, True)
    return z and mo and sp
if chosen_name != ridge_name and not (passes(chosen_name, chosen_variant) or not passes(ridge_name, ridge_variant)):
    print("the tree model fails an invariant that Ridge passes: Ridge is kept")
    chosen_name, chosen_variant = ridge_name, ridge_variant
print("model for the final test:", chosen_name, "|", chosen_variant)
''')),
        ]
    cells += [
        code(sub('''
json.dump({**choice, "chosen": [chosen_name, chosen_variant]}, open(RES / "model_choice.json", "w"), indent=1, default=float)
print("model for the final test:", chosen_name, "|", chosen_variant)
''')),
        md(f"## {next(n)}. Final test, scored once"),
        code(sub('''
final, fits = R.final_test(cfg, d, chosen_name, chosen_variant, tuned, settings)
final.to_csv(RES / "final_test_predictions_unguarded.csv", index=False)
MAIN = f"{chosen_name} | {chosen_variant}"
%%GUARD_APPLY%%
fold_info = pd.DataFrame({o: fits[(chosen_name, chosen_variant, o)][2] for o in GROUPS}).T
display(fold_info)
print(len(final[final.name == MAIN]), "test predictions from", len(GROUPS), "models, each made by a model that never saw that student")
''')),
        code(sub('''
crit, m = R.criteria_table(cfg, final, MAIN, d)
crit.to_csv(RES / "final_test_criteria.csv", index=False)
print("PRIMARY: all %d real records" % len(final[final.name == MAIN]))
display(crit.round(3))
f20 = final[final.record_id.isin(P20)]
crit20, m20 = R.criteria_table(cfg, f20, MAIN, d)
crit20.to_csv(RES / "final_test_criteria_original20.csv", index=False)
print("SECONDARY: the original 20 records only (%d)" % len(f20[f20.name == MAIN]))
display(crit20.round(3))
''')),
        code(sub('''
rows = []
for name, g in final.groupby("name"):
    mm = metrics(g.y, g.pred)
    rows.append({"model": name, "MAE": mm["MAE"], "pearson": mm["pearson"], "spearman": mm["spearman"], "bias": mm["bias"]})
display(pd.DataFrame(rows).set_index("model").sort_values("MAE").round(3))
pf = final[final.name == MAIN].assign(err=lambda x: (x.pred - x.y).abs())
display(pf.groupby("outer_test").agg(n=("err", "size"), MAE=("err", "mean")).round(3).T)
f = final[final.name == MAIN]
fig, ax = plt.subplots(figsize=(4.8, 4.4))
ax.scatter(f.y, f.pred, c=np.where(f.activity > 0, "#2b6cb0", "#c53030"), s=24)
ax.plot([0, 1], [0, 1], color="grey", lw=1)
ax.set_xlabel("rubric rating"); ax.set_ylabel("predicted"); ax.set_title(MAIN, fontsize=8)
fig.tight_layout(); plt.show()
''')),
        md(f"## {next(n)}. Beside the first clean run and the uncleaned experiments"),
        code(sub('''
print("First clean run (labels: 20 ratings + estimates), criteria table:")
display(pd.read_csv(Path("../clean/training/results/final_test_criteria.csv")).round(3))
print("Uncleaned experiments (old features, 20 ratings), criteria table:")
display(pd.read_csv(Path("../training/results/final_test_criteria.csv")).round(3))
''')),
        md(f"## {next(n)}. Reading the results"),
        md(reading),
    ]
    guard_apply = ""
    if effort:
        guard_apply = '''GUARDED = MAIN + " + guard"
fg = final[final.name == MAIN].copy()
fg["name"] = GUARDED
fg["pred"] = np.concatenate([R.predict_with(fits[(chosen_name, chosen_variant, o)], d.loc[fg[fg.outer_test == o].record_id], True) for o in GROUPS])
final = pd.concat([final, fg], ignore_index=True)
final.to_csv(RES / "final_test_predictions.csv", index=False)
print("the pipeline's form is the guarded one (protocol); unguarded results are in the table below")
MAIN = GUARDED'''
    for c in cells:
        c["source"] = [s.replace("%%GUARD_APPLY%%", guard_apply) for s in c["source"]]
    path = folder / "RETRAIN_reference.ipynb"
    write(path, cells)
    print("wrote", path)


if __name__ == "__main__":
    for name in sys.argv[1:] or ["effort", "consistency", "task_complexity"]:
        build(name)
