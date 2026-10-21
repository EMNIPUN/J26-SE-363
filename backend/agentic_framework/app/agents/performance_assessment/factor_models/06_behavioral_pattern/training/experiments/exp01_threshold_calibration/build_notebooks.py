"""Builds the Behavioral Pattern notebooks of training/PROTOCOL.md next to this file.

    python build_notebooks.py [1 2 3 4 5]

01_data_audit              the inputs, how much Collaboration is available, the labels
02_threshold_calibration   the calibrated cut points from the training cohort (rule fixed in the protocol); writes thresholds.json
03_firing_and_agreement    how often each rule fires, agreement with the assistant labels (pipeline check only), for both threshold sets
04_sensitivity             how many patterns change when all thresholds move
05_modifier_effect         what the modifier does to the final scores and the ranking

A cell "Reading the results" is filled from reading_N.md when it exists.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n").splitlines(keepends=True)}


def write(path, cells):
    for i, c in enumerate(cells):
        c["id"] = f"c{i:03d}"
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Collaboration model (SELVIA)", "language": "python", "name": "collab-model"}, "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    Path(path).write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def reading(n):
    p = HERE / f"reading_{n}.md"
    return md(p.read_text(encoding="utf-8") if p.exists() else "_Reading of the results: written after the run._")


SETUP = """
import sys, warnings, json, importlib.util
from pathlib import Path
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, seaborn as sns
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score, confusion_matrix
sns.set_theme(style="whitegrid")
pd.set_option("display.width", 170); pd.set_option("display.max_columns", 30)
ROOT = Path("../../..").resolve()
spec = importlib.util.spec_from_file_location("bp_rules_nb", ROOT / "rules.py")
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
RESULTS = Path("results"); RESULTS.mkdir(exist_ok=True)
d = pd.read_csv(Path("../../dataset/bp_inputs.csv"))
PATTERNS = list(R.PATTERNS) + ["Balanced contributor"]
def run(thresholds, frame=None):
    frame = d if frame is None else frame
    out = []
    for r in frame.itertuples():
        co = None if pd.isna(r.Co) else float(r.Co)
        bim = None if pd.isna(r.bimodal) else int(r.bimodal)
        lc = None if pd.isna(r.late_churn) else float(r.late_churn)
        out.append(R.classify({"E": float(r.E), "C": float(r.C), "Co": co}, bim, thresholds, lc))
    return out
"""


def nb1():
    return [
        md("""
# Behavioral Pattern, notebook 1: the data audit

Protocol: [PROTOCOL.md](../../PROTOCOL.md). The rules are not trained; this notebook looks at what they will be run on. Effort and Consistency are the marks of
`dataset/clean/final_dataset_clean.csv` (models fitted on 20 anchor ratings by one assistant rater). Collaboration is the new fixed Collaboration score and is **missing** when the
Collaboration factor says "not available" (nobody in the team reviewed in the sprint).
"""),
        code(SETUP),
        md("## 1. Size and availability"),
        code("""
t = d.groupby("source").agg(student_sprints=("record_id", "size"), collaboration_available=("Co_available", "sum"), bimodal_flag_1=("bimodal", "sum"))
t["collaboration_missing"] = t.student_sprints - t.collaboration_available
t
"""),
        md("## 2. The three scores the rules read"),
        code("""
print(d.groupby("source")[["E", "C", "Co"]].describe().T.round(3).to_string())
fig, axes = plt.subplots(1, 3, figsize=(12, 3))
for ax, c in zip(axes, ("E", "C", "Co")):
    sns.histplot(data=d, x=c, hue="source", bins=20, ax=ax, element="step")
    for t_ in (0.3, 0.7):
        ax.axvline(t_, color="k", ls=":", lw=1)
plt.tight_layout(); plt.show()
"""),
        md("Share of student-sprints that pass the proposal's cut points (vertical dotted lines above):"),
        code("""
rows = []
for c in ("E", "C", "Co"):
    x = d[c].dropna()
    rows.append({"score": c, "n": len(x), "> 0.7": (x > 0.7).mean(), "< 0.3": (x < 0.3).mean(), "< 0.4": (x < 0.4).mean()})
pd.DataFrame(rows).set_index("score").round(3)
"""),
        md("## 3. The labels (all written by the assistant)"),
        code("""
lab = {c: d[c].value_counts() for c in ("sim_class", "ref_pattern", "gt_pattern")}
pd.DataFrame(lab).fillna(0).astype(int)
"""),
        md("## Reading the results"), reading(1),
    ]


def nb2():
    return [
        md("""
# Behavioral Pattern, notebook 2: threshold calibration

Rule fixed in the protocol before any agreement was computed: the proposal's cut points read as cohort quantiles. 0.7 becomes the 70th percentile, 0.3 the 30th, 0.4 the 40th.
E and C use the 144 real student-sprints. Collaboration uses the sprints where it is available, real and simulated together (the real students alone give 8). The numbers are
written to `thresholds.json` next to `rules.py` so the agent uses fixed numbers.
"""),
        code(SETUP),
        code("""
real = d[d.source == "real"]
co = d[d.Co_available].Co.dropna()
cal = {"E_high": real.E.quantile(0.70), "C_high": real.C.quantile(0.70), "C_low": real.C.quantile(0.30), "E_mid": real.E.quantile(0.40), "E_low": real.E.quantile(0.30),
       "Co_high": R.PROPOSAL["Co_high"], "Co_low": R.PROPOSAL["Co_low"]}   # amendment 1 in PROTOCOL.md: the quantile reading gave Co_high = Co_low = 0.25 (ties)
cal = {k: round(float(v), 4) for k, v in cal.items()}
quantile_co = (round(float(co.quantile(0.70)), 4), round(float(co.quantile(0.30)), 4))
print("Collaboration cut points the quantile reading would have given (not used):", quantile_co)
pd.DataFrame({"proposal": {k: v for k, v in R.PROPOSAL.items() if k != "name"}, "calibrated": cal})
"""),
        code("""
print("n for E and C:", len(real), "; n for Collaboration:", len(co), "; distinct Collaboration values:", co.round(4).nunique())
print(co.round(3).value_counts().head(6).to_dict())
print("quantile reading degenerate (tied values):", quantile_co[0] <= quantile_co[1] + 0.02)
"""),
        code("""
active = real[real.late_churn.notna()]
ext = {"E_med": round(float(real.E.quantile(0.50)), 4), "DC_high": round(float(active.late_churn.quantile(0.70)), 4), "ext_rusher": True, "ext_free_rider": True}   # amendments A and B in PROTOCOL.md; the decision below (notebook 3) selects what "calibrated" keeps
print("extension cut points:", ext, "(late-churn share from", len(active), "active real student-sprints)")
decision = json.loads((RESULTS / "extension_decision.json").read_text(encoding="utf-8")) if (RESULTS / "extension_decision.json").exists() else {"A kept": False, "B kept": True}
adopted = {**cal, "E_med": ext["E_med"], "DC_high": ext["DC_high"], "ext_rusher": bool(decision.get("A kept")), "ext_free_rider": bool(decision.get("B kept"))}
print("decision used for the stored default set:", {"ext_rusher": adopted["ext_rusher"], "ext_free_rider": adopted["ext_free_rider"]})
meta = {"sets": {"calibrated_v1": cal, "calibrated_AB": {**cal, **ext}, "calibrated": adopted}, "calibrated_from": {"E_C": f"{len(real)} real student-sprints (marks in dataset/clean/final_dataset_clean.csv)", "Co": "the proposal's absolute 0.7 / 0.3 (the quantile reading was degenerate, see the amendment log)",
        "rule": "Effort and Consistency: proposal cut points read as cohort quantiles (0.7 -> P70, 0.3 -> P30, 0.4 -> P40); Collaboration: the proposal's own 0.7 / 0.3", "date": "2026-10-19", "extensions": "calibrated_v1 = original rules; calibrated_AB = both extensions of the protocol; calibrated = the extensions that passed the keep/revert check of notebook 3 (results/extension_decision.json)"}}
(ROOT / "thresholds.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
(RESULTS / "thresholds.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
meta
"""),
        md("## Reading the results"), reading(2),
    ]


def nb3():
    return [
        md("""
# Behavioral Pattern, notebook 3: how often each rule fires, and agreement with the assistant labels

Both threshold sets, side by side. Agreement is a **pipeline check**: the labels were written by the assistant with the same kind of reasoning as the rules, so agreement shows the
rules implement the idea, not that they match instructors. Agreement is also reported only on the student-sprints where Collaboration is available (otherwise the two rules
that need it cannot fire by design).
"""),
        code(SETUP),
        code("""
SETS = {"proposal": R.load_thresholds("proposal"), "calibrated_v1": R.load_thresholds("calibrated_v1"), "calibrated_AB": R.load_thresholds("calibrated_AB"), "calibrated": R.load_thresholds("calibrated")}
OUT = {}
for name, th in SETS.items():
    res = run(th)
    OUT[name] = pd.Series([r["persona"] for r in res], name=name)
    d[f"pattern_{name}"] = OUT[name].values
    d[f"mod_{name}"] = [r["score_modifier"] for r in res]
fire = pd.DataFrame({n: o.value_counts() for n, o in OUT.items()}).reindex(PATTERNS + ["Unclassified"]).fillna(0).astype(int)
fire["old rules in the dataset"] = d.rule_pattern_old.value_counts().reindex(fire.index).fillna(0).astype(int)
fire
"""),
        md("Firing by source and by whether Collaboration was available:"),
        code("""
for name in SETS:
    print(name); print(pd.crosstab(d[f"pattern_{name}"], [d.source, d.Co_available]).reindex(PATTERNS + ["Unclassified"]).fillna(0).astype(int))
"""),
        md("## Agreement with the assistant labels"),
        code("""
def agree(pred, truth, label):
    m = truth.notna()
    p, t = pred[m], truth[m]
    cm = confusion_matrix(t, p, labels=PATTERNS)
    rec = {k: (cm[i, i] / cm[i].sum() if cm[i].sum() else np.nan) for i, k in enumerate(PATTERNS)}
    prec = {k: (cm[i, i] / cm[:, i].sum() if cm[:, i].sum() else np.nan) for i, k in enumerate(PATTERNS)}
    return {"labels": label, "n": int(m.sum()), "accuracy": float((p == t).mean()), "kappa": float(cohen_kappa_score(t, p)), "recall": rec, "precision": prec, "confusion": cm}
rows, details = [], {}
for name in SETS:
    for label, col, mask in (("simulated classes (all)", "sim_class", d.index == d.index), ("reference pattern (all)", "ref_pattern", d.index == d.index), ("reference pattern, Collaboration available", "ref_pattern", d.Co_available),
                             ("anchors (20)", "gt_pattern", d.index == d.index)):
        sub = d[mask]
        a = agree(sub[f"pattern_{name}"], sub[col], label)
        details[(name, label)] = a
        rows.append({"thresholds": name, **{k: a[k] for k in ("labels", "n", "accuracy", "kappa")}})
ag = pd.DataFrame(rows).round(3)
ag.to_csv(RESULTS / "agreement.csv", index=False)
ag
"""),
        code("""
fig, axes = plt.subplots(1, 4, figsize=(25, 4.5))
for ax, name in zip(axes, SETS):
    a = details[(name, "reference pattern (all)")]
    sns.heatmap(a["confusion"], annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax, xticklabels=[p[:12] for p in PATTERNS], yticklabels=[p[:12] for p in PATTERNS])
    ax.set_title(f"{name}: rows = assistant pattern, columns = rule"); ax.tick_params(axis="x", rotation=45)
plt.tight_layout(); plt.show()
"""),
        code("""
rec = pd.DataFrame({name: pd.Series(details[(name, "reference pattern (all)")]["recall"]) for name in SETS}).round(2)
prec = pd.DataFrame({name: pd.Series(details[(name, "reference pattern (all)")]["precision"]) for name in SETS}).round(2)
print("recall per pattern (reference pattern, all records)"); print(rec); print("precision per pattern"); print(prec)
d.to_csv(RESULTS / "patterns_by_record.csv", index=False)
"""),
        md("""
## Keep or revert the two extensions (criteria fixed in the protocol before they were implemented)

A: on the **simulated** records (the extension was designed on the real ones) Last-minute rusher recall at least 0.30 and precision at least 0.50, and no other pattern loses more than 0.05 recall against `calibrated_v1`.
B: Free rider recall on all labelled records rises and its precision stays at least 0.60.
"""),
        code("""
def rp(col, mask, sets=("calibrated_v1", "calibrated_AB", "calibrated")):
    out = {}
    sub = d[mask]
    for name in sets:
        a = agree(sub[f"pattern_{name}"], sub[col], name)
        out[name] = a
    return out
sim_m = d.source == "simulated"
A = rp("sim_class", sim_m)
allm = d.index == d.index
B = rp("ref_pattern", allm)
ru = "Last-minute rusher"
rec = lambda a, k: a["recall"][k]; prc = lambda a, k: a["precision"][k]
a_ok_rusher = rec(A["calibrated_AB"], ru) >= 0.30 and (prc(A["calibrated_AB"], ru) >= 0.50)
a_others = {k: rec(A["calibrated_AB"], k) - rec(A["calibrated_v1"], k) for k in PATTERNS if k != ru}
a_ok_others = all(v >= -0.05 for v in a_others.values())
fr = "Free rider"
b_ok = rec(B["calibrated_AB"], fr) > rec(B["calibrated_v1"], fr) and prc(B["calibrated_AB"], fr) >= 0.60
res = {"A rusher recall (simulated)": round(float(rec(A["calibrated_AB"], ru)), 3), "A rusher precision (simulated)": round(float(prc(A["calibrated_AB"], ru)), 3) if prc(A["calibrated_AB"], ru) == prc(A["calibrated_AB"], ru) else None,
       "A other patterns' recall change (simulated)": {k: round(float(v), 3) for k, v in a_others.items()}, "A kept": bool(a_ok_rusher and a_ok_others),
       "B free rider recall v1 -> with B (all labelled)": [round(float(rec(B["calibrated_v1"], fr)), 3), round(float(rec(B["calibrated_AB"], fr)), 3)], "B free rider precision with B": round(float(prc(B["calibrated_AB"], fr)), 3), "B kept": bool(b_ok)}
(RESULTS / "extension_decision.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
res
"""),
        md("""
## What do the labelled patterns look like in the scores?

Why the rules miss some patterns: the typical scores of the records the assistant gave each pattern, against the rule thresholds.
"""),
        code("""
diag = d.groupby("ref_pattern").agg(n=("E", "size"), E_median=("E", "median"), C_median=("C", "median"), C_p25=("C", lambda x: x.quantile(0.25)),
                                   Co_available=("Co_available", "mean"), Co_median=("Co", "median"), bimodal_share=("bimodal", "mean")).round(3)
diag.to_csv(RESULTS / "label_profiles.csv")
diag
"""),
        md("## Reading the results"), reading(3),
    ]


def nb4():
    return [
        md("""
# Behavioral Pattern, notebook 4: sensitivity to the thresholds

All cut points move together by -0.10, -0.05, +0.05, +0.10 (E_mid, E_low and the others shift the same way; clipped to 0.05-0.95). Target fixed in the protocol: at most 15% of
student-sprints change pattern for a shift of 0.05.
"""),
        code(SETUP),
        code("""
def shifted(th, delta):
    moved = {k: float(np.clip(v + delta, 0.05, 0.95)) for k, v in th.items() if k != "name" and isinstance(v, (int, float)) and not isinstance(v, bool)}
    return {**th, **moved, "name": f"{th['name']}{delta:+.2f}"}   # the on/off switches of the extensions are not thresholds and stay as they are
rows = []
for name in ("proposal", "calibrated_v1", "calibrated"):
    base = th0 = R.load_thresholds(name)
    p0 = np.array([r["persona"] for r in run(th0)])
    for delta in (-0.10, -0.05, 0.05, 0.10):
        p1 = np.array([r["persona"] for r in run(shifted(th0, delta))])
        rows.append({"thresholds": name, "shift": delta, "share changing pattern": float((p0 != p1).mean()), "patterns fired (not balanced/unclassified)": float(np.isin(p1, R.PATTERNS).mean())})
sens = pd.DataFrame(rows).round(3)
sens["meets target (<= 0.15 at +/-0.05)"] = np.where(sens["shift"].abs() == 0.05, sens["share changing pattern"] <= 0.15, np.nan)
sens.to_csv(RESULTS / "sensitivity.csv", index=False)
sens
"""),
        md("## Reading the results"), reading(4),
    ]


def nb5():
    return [
        md("""
# Behavioral Pattern, notebook 5: what the modifier does to the final scores

`S = BP_modifier * sum(w_k * factor_k)` with the fusion weights fitted earlier (README of the dataset: Requirement Fulfillment 0.40, Effort 0.18, Task Complexity 0.16, Code
Ownership 0.16, Collaboration 0.07, Consistency 0.03). The base score uses the factor marks of the dataset table (the old Collaboration mark, since the new one is missing for most
sprints). Targets fixed in the protocol: Spearman between the score with and without the modifier at least 0.95 (the modifier must adjust, not reorder).
"""),
        code(SETUP),
        code("""
W = {"RF": 0.40, "E": 0.18, "TC": 0.16, "KO": 0.16, "Co_old": 0.07, "C": 0.03}
base = 100 * sum(w * d[k] for k, w in W.items())
rows, mods = [], {}
for name in ("proposal", "calibrated"):
    res = run(R.load_thresholds(name))
    m = np.array([r["score_modifier"] for r in res]); mods[name] = m
    s1 = base * m
    rows.append({"thresholds": name, "Spearman with vs without modifier": spearmanr(base, s1).correlation, "largest change (points)": float(np.abs(s1 - base).max()), "mean absolute change (points)": float(np.abs(s1 - base).mean()),
                 "share with modifier != 1": float((m != 1).mean())})
eff = pd.DataFrame(rows).round(3)
eff["meets target (>= 0.95)"] = eff["Spearman with vs without modifier"] >= 0.95
eff.to_csv(RESULTS / "modifier_effect.csv", index=False)
eff
"""),
        code("""
fig, ax = plt.subplots(figsize=(7, 3))
for name, m in mods.items():
    sns.histplot(m, bins=30, label=name, ax=ax, element="step", fill=False)
ax.set_xlabel("score modifier"); ax.legend(); plt.show()
t = d.assign(mod=mods["calibrated"], persona=[r["persona"] for r in run(R.load_thresholds("calibrated"))])
t.groupby("persona").mod.agg(["count", "mean", "min", "max"]).round(3)
"""),
        md("## Reading the results"), reading(5),
    ]


def main(which):
    names = {1: ("01_data_audit", nb1), 2: ("02_threshold_calibration", nb2), 3: ("03_firing_and_agreement", nb3), 4: ("04_sensitivity", nb4), 5: ("05_modifier_effect", nb5)}
    for n in which:
        name, fn = names[n]
        write(HERE / f"{name}.ipynb", fn())
        print("wrote", name)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5])
