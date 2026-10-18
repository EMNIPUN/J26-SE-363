"""Builds <factor>/clean/RETRAIN_clean.ipynb for Effort, Consistency and Task Complexity from the retrain engine.

    python build_retrain_notebooks.py [effort consistency task_complexity]

The reading of the results (the markdown cell at the end) is taken from <factor>/clean/reading.md when it exists, so the notebook
can be rebuilt after the results have been read. The notebooks do the decision, the final test and the comparison with the earlier
(uncleaned) experiments; the heavy tuning is run by run_validation.py and read from its output.
"""

import json
import sys
from pathlib import Path

from retrain_configs import CONFIGS

FM = Path(__file__).resolve().parents[1]
OLD_FINAL = {"effort": "01_effort", "consistency": "02_consistency", "task_complexity": "05_task_complexity"}


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n").splitlines(keepends=True)}


def write(path, cells):
    for i, c in enumerate(cells):
        c["id"] = f"c{i:03d}"
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Effort model (SELVIA)", "language": "python", "name": "effort-model"},
                                        "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    Path(path).write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


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

cfg = CONFIGS["%%KEY%%"]()
F = cfg.factor()
RES = F.results
d = load(F)
real, sim = d[d.source == "real"], d[d.source == "synthetic"]
gold = real[real.label_source == "rater"]
LABEL, ACT = cfg.label, cfg.activity
print(cfg.title, "| real", len(real), "| rated", len(gold), "| simulated (training only)", len(sim))
'''


def build(key):
    cfg = CONFIGS[key]()
    folder = cfg.folder
    old_folder = FM / OLD_FINAL[key]
    effort = key == "effort"
    sub = lambda t: t.replace("%%KEY%%", key).replace("%%TITLE%%", cfg.title).replace("%%OLD%%", OLD_FINAL[key])  # noqa: E731
    reading = (folder / "reading.md").read_text(encoding="utf-8") if (folder / "reading.md").exists() else "_Reading of the results: written after the run._"
    cells = [
        md(sub("""
# Retraining on the clean data: %%TITLE%%

**Goal.** Ask the earlier questions again, on the features recomputed through the factor package's cleaning code (see
[ARCHITECTURE.md](../../ARCHITECTURE.md)): which preprocessing and model, how good, and does it meet the criteria. The rules were fixed
before any of this ran in [RETRAIN_PROTOCOL.md](../../RETRAIN_PROTOCOL.md); the decision rules and success criteria are the earlier protocol's own.

**Disclosure.** Each group was a test group once in the earlier experiments, scored on the old features with the same 20 labels. This
notebook scores them again on changed features. Every choice here is made on validation groups only, and the new test result is
reported **beside** the earlier one. It shows the effect of cleaning on the same 20 students, not fresh independent evidence.

**Data.** 144 real student-sprints (20 rated) plus 175 simulated student-sprints, **training only**: never validated, never tested, labels are
estimates from the label model.
""")),
        code(sub(SETUP)),
        md("## 1. What cleaning changed in the data"),
        code(sub('''
old = pd.read_csv(Path("../dataset") / cfg.dataset_file, low_memory=False)
old = old[old.source == "real"].set_index("record_id")
cols = [c for c, _ in cfg.proposal]
rows = []
for c in cols:
    new_v = real.set_index("record_id")[c].astype(float)
    old_v = old[c].astype(float).reindex(new_v.index)
    ok = new_v.notna() & old_v.notna()
    rows.append({"feature": c, "median before": old_v.median(), "median now": new_v.median(),
                 "total now / before": new_v[ok].sum() / old_v[ok].sum() if old_v[ok].sum() else np.nan,
                 "rank agreement": new_v[ok].corr(old_v[ok], method="spearman")})
print("Real student-sprints: the proposal's features before and after cleaning")
display(pd.DataFrame(rows).set_index("feature").round(3))
rows = []
for c in cols:
    for name, frame in (("real", real), ("simulated", sim)):
        x = frame[c].astype(float).dropna()
        rows.append({"feature": c, "group": name, "p10": x.quantile(.1), "median": x.median(), "p90": x.quantile(.9), "missing": frame[c].isna().mean()})
print("Simulated students against real students (clean features)")
pd.DataFrame(rows).set_index(["feature", "group"]).round(3)
''')),
        md("## 2. Splits and baselines (validation)"),
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
        md("## 3. Preprocessing: variants and label sources (Ridge, validation, selection without bias)"),
        code(sub('''
tuned = pd.read_csv(RES / "tuning_predictions.csv")
settings = json.load(open(RES / "settings.json"))
tuned.attrs["settings_path"] = str(RES / "settings.json")
rows = []
for (variant, lab, weight), g in tuned[tuned.model == "Ridge"].groupby(["variant", "lab", "weight"]):
    p, _ = R.bias_free(g)
    m = metrics(p.y, p.pred)
    rows.append({"variant": variant, "label source": lab, "weight": weight, "MAE": m["MAE"], "pearson": m["pearson"]})
prep = pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True)
prep.round(3)
''')),
        md("## 4. Ridge, Random Forest and Gradient Boosting, tuned, compared without selection bias"),
        code(sub('''
choice, table, pools, picks = R.decide(cfg, tuned, base, d, RES)
table.round(3)
''')),
        code(sub('''
fig, ax = plt.subplots(figsize=(10, 0.45 * len(table) + 1.5))
labels = table.model + " | " + table.variant
ax.barh(labels[::-1], table.MAE[::-1], color=["#c53030" if "Forest" in l or "Boosting" in l else "#2b6cb0" for l in labels[::-1]])
for name, g in base.groupby("name"):
    if name in ("mean",):
        ax.axvline(metrics(g.y, g.pred)["MAE"], color="grey", ls="--", lw=1)
ax.set_xlabel("validation MAE (pooled over 20 combinations)")
fig.tight_layout(); plt.show()
''')),
        md("## 5. The rule for keeping a complex model"),
        code(sub('''
rule = choice["rule"]
print(f"best Ridge-type model : {rule['ridge']}  (MAE {choice['ridge_best']['MAE']:.3f})")
print(f"best tree model       : {rule['complex']}  (MAE {choice['complex_best']['MAE']:.3f})")
print(f"gain {rule['gain_mae']:+.3f} MAE, 95% interval {rule['ci'][0]:+.3f} to {rule['ci'][1]:+.3f}, better in {rule['folds_better']} of 5 folds")
chosen_name = choice["complex_best"]["model"] if rule["passes_1_3"] else choice["ridge_best"]["model"]
chosen_variant = choice["complex_best"]["variant"] if rule["passes_1_3"] else choice["ridge_best"]["variant"]
%%INVARIANT_NOTE%%
print("\\nmodel for the final test:", chosen_name, "|", chosen_variant)
json.dump({**choice, "chosen": [chosen_name, chosen_variant]}, open(RES / "model_choice.json", "w"), indent=1, default=float)
''')),
    ]
    if effort:
        cells[-1] = code(sub('''
rule = choice["rule"]
print(f"best Ridge-type model : {rule['ridge']}  (MAE {choice['ridge_best']['MAE']:.3f})")
print(f"best tree model       : {rule['complex']}  (MAE {choice['complex_best']['MAE']:.3f})")
print(f"gain {rule['gain_mae']:+.3f} MAE, 95% interval {rule['ci'][0]:+.3f} to {rule['ci'][1]:+.3f}, better in {rule['folds_better']} of 5 folds")
# provisional choice by rules 1-3; rule 4 (invariants) is checked in section 6 on the fitted fold models
chosen_name = choice["complex_best"]["model"] if rule["passes_1_3"] else choice["ridge_best"]["model"]
chosen_variant = choice["complex_best"]["variant"] if rule["passes_1_3"] else choice["ridge_best"]["variant"]
ridge_name, ridge_variant = choice["ridge_best"]["model"], choice["ridge_best"]["variant"]
print("provisional model:", chosen_name, "|", chosen_variant)
'''))
        cells += [
            md("## 6. Effort only: invariants and the guard layer (rule 4)"),
            code(sub('''
final_all, fits = R.final_test(cfg, d, chosen_name, chosen_variant, tuned, settings,
                               extra_models=[(ridge_name, ridge_variant)])
rows = []
for (model, variant) in sorted({(m, v) for (m, v, _) in fits}):
    for guarded in (False, True):
        z, mo, sp, t = R.effort_invariants(fits, model, variant, guarded)
        rows.append({"model": f"{model} | {variant}", "guard": guarded, "zero commits ~ 0": z, "never lowered by more": mo, "spam and dump <= 0.35": sp})
inv = pd.DataFrame(rows)
display(inv)
z, mo, sp, t = R.effort_invariants(fits, chosen_name, chosen_variant, True)
display(t.round(3))
''')),
            code(sub('''
# rule 4: a complex model replaces Ridge only if it passes every invariant that Ridge passes (with the guard, the pipeline's form)
def passes(model, variant):
    z, mo, sp, _ = R.effort_invariants(fits, model, variant, True)
    return z and mo and sp
if chosen_name != ridge_name and not (passes(chosen_name, chosen_variant) or not passes(ridge_name, ridge_variant)):
    print("the tree model fails an invariant that Ridge passes: Ridge is kept")
    chosen_name, chosen_variant = ridge_name, ridge_variant
print("model for the final test:", chosen_name, "|", chosen_variant)
json.dump({**choice, "chosen": [chosen_name, chosen_variant]}, open(RES / "model_choice.json", "w"), indent=1, default=float)
''')),
        ]
    cells += [
        md("## %s. Final test, scored once" % ("7" if effort else "6")),
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
display(crit.round(3))
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
ax.scatter(f.y, f.pred, c=np.where(f.activity > 0, "#2b6cb0", "#c53030"), s=40)
ax.plot([0, 1], [0, 1], color="grey", lw=1)
ax.set_xlabel("rated"); ax.set_ylabel("predicted"); ax.set_title(MAIN, fontsize=8)
fig.tight_layout(); plt.show()
''')),
        md("## %s. Beside the earlier result (old features, same 20 students)" % ("8" if effort else "7")),
        code(sub('''
oldp = pd.read_csv(Path("../training/results/final_test_predictions.csv"))
mo, mn = metrics(oldp.y, oldp.pred), metrics(f.y, f.pred)
cmp = pd.DataFrame({"earlier (old features)": mo, "now (clean features)": mn}).loc[["n", "MAE", "RMSE", "bias", "pearson", "spearman", "calib_slope", "band_within_1", "band_exact"]]
display(cmp.round(3))
oldc = pd.read_csv(Path("../training/results/final_test_criteria.csv"))
print("Earlier criteria table (old features):")
display(oldc)
''')),
        md("## %s. Reading the results" % ("9" if effort else "8")),
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
        c["source"] = [s.replace("%%GUARD_APPLY%%", guard_apply).replace("%%INVARIANT_NOTE%%", "") for s in c["source"]]
    path = folder / "RETRAIN_clean.ipynb"
    write(path, cells)
    print("wrote", path)


if __name__ == "__main__":
    for name in sys.argv[1:] or list(CONFIGS):
        build(name)
