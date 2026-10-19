"""Builds the three Collaboration notebooks of SUBSTANCE_PROTOCOL.md next to this file.

    python build_notebooks.py [1 2 3]

01_DATA_AND_BASELINES.ipynb   the public data, cleaning, the guard layer, baselines
02_ENCODER_TUNING.ipynb       frozen encoders + heads, tuning without selection bias, the external test
03_COLLABORATION_SCORE.ipynb  the scorer on student texts, then the six features -> Collaboration (a pipeline test)
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
import sys, warnings, json
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(".").resolve()))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, seaborn as sns
from scipy.stats import spearmanr
sns.set_theme(style="whitegrid")
pd.set_option("display.width", 170); pd.set_option("display.max_colwidth", 80); pd.set_option("display.max_columns", 30)
import data, substance
from cleaning import substance as rule_score, clean_text, is_padding, APPROVAL_ONLY
RESULTS = Path("results"); RESULTS.mkdir(exist_ok=True)
od, rh = data.public_pool()
od = od.reset_index(drop=True); rh = rh.reset_index(drop=True)
CS = substance.combos(od.group.to_numpy())
OUTER = {}
for o, i, tr, va, te in CS:
    OUTER[o] = (np.setdiff1d(np.arange(len(od)), te), te)
def guarded(original):
    c = clean_text(original)
    return len(c.split()) < 3 or bool(APPROVAL_ONLY.match(c)) or is_padding(c)
"""


def nb1():
    return [
        md("""
# Collaboration step 1, notebook 1: the public data, cleaning, the guard layer and the baselines

Protocol: [SUBSTANCE_PROTOCOL.md](../SUBSTANCE_PROTOCOL.md). The student dataset is far too small to train a comment scorer on (the real students wrote 12 reviews and 1 comment, none
over 10 words), so the scorer is trained on public labeled review comments and the student texts are only scored.

**What the labels mean.** Both public sets label a comment *useful* when the code author acted on it (OpenStack Nova, Gerrit). That is related to, not the same as, "substantive", and it depends on the code the
comment was about, which a text-only scorer does not see. Results are therefore about *usefulness in a professional project*, not about collaboration among students.
"""),
        code(SETUP),
        md("## 1. The data"),
        code("""
rows = []
for name, d in (("OpenDev", od), ("RevHelper", rh)):
    w = d.clean.str.split().str.len()
    rows.append({"set": name, "comments": len(d), "useful": int(d.y.sum()), "not useful": int((1 - d.y).sum()), "useful share": d.y.mean(), "median words": w.median(),
                 "empty after cleaning": int((w == 0).sum()), "groups (changes)": d.group.nunique(), "guarded (would score 0)": int(sum(guarded(t) for t in d.text))})
display(pd.DataFrame(rows).set_index("set").round(3))
fig, ax = plt.subplots(1, 2, figsize=(10, 3.2), sharey=True)
for a, (n, d) in zip(ax, (("OpenDev", od), ("RevHelper", rh))):
    sns.histplot(data=d.assign(words=d.clean.str.split().str.len().clip(upper=80), label=d.y.map({1: "useful", 0: "not useful"})), x="words", hue="label", bins=40, ax=a, element="step")
    a.set_title(n + ": words per comment")
fig.tight_layout(); plt.show()
"""),
        md("""
## 2. The guard layer

Approval-only text ("LGTM", "ok"), text under 3 words after cleaning, and padding score 0 in the pipeline and never reach the model. This protects against comment spam, but in the public sets some very short
comments ("Ditto.") *are* labeled useful, so the guard costs some agreement with the public labels. The table shows how many and what.
"""),
        code("""
for name, d in (("OpenDev", od), ("RevHelper", rh)):
    g = np.array([guarded(t) for t in d.text])
    print(f"{name}: guarded {g.sum()} comments ({g.mean():.1%}); of them labeled useful: {d.y[g].mean():.1%} (all comments: {d.y.mean():.1%})")
display(od[[guarded(t) for t in od.text]].sample(8, random_state=1)[["text", "y"]])
"""),
        md("""
## 3. Baselines on the protocol's folds

Five outer folds grouped by code change (the same folds notebook 2 uses). Baselines: a constant, comment length alone, the rule-based score of `cleaning.py`, and TF-IDF with logistic regression.
The two external directions are train OpenDev / test RevHelper and the reverse.
"""),
        code("""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

def tfidf():
    return make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000))

def predict(kind, Xtr, ytr, Xte):
    if kind == "constant":
        return np.full(len(Xte), float(np.mean(ytr)))
    if kind == "length only":
        f = lambda X: np.log1p([len(t.split()) for t in X])[:, None]
        return LogisticRegression(class_weight="balanced").fit(f(Xtr), ytr).predict_proba(f(Xte))[:, 1]
    if kind == "rules (cleaning.py)":
        return np.array([rule_score(t) for t in Xte])
    return tfidf().fit(list(Xtr), ytr).predict_proba(list(Xte))[:, 1]

KINDS = ["constant", "length only", "rules (cleaning.py)", "TF-IDF + logistic"]
def view(kind, d, idx=None):
    col = d.text if kind == "rules (cleaning.py)" else d.clean   # the rule score reads the original text, the others the cleaned text
    return (col if idx is None else col.iloc[idx]).to_numpy()
oof = {k: np.zeros(len(od)) for k in KINDS}
for o, (tr, te) in OUTER.items():
    for k in KINDS:
        oof[k][te] = predict(k, view(k, od, tr), od.y.iloc[tr].to_numpy(), view(k, od, te))
rows = {}
for k in KINDS:
    s = substance.auc_scores(od.y, oof[k]); lo, hi = substance.group_bootstrap_auc(od.y, oof[k], od.group)
    ext1 = predict(k, view(k, od), od.y.to_numpy(), view(k, rh))
    ext2 = predict(k, view(k, rh), rh.y.to_numpy(), view(k, od))
    rows[k] = {"OpenDev grouped CV AUC": s["AUC"], "95% low": lo, "95% high": hi, "OpenDev -> RevHelper AUC": substance.auc_scores(rh.y, ext1)["AUC"],
               "RevHelper -> OpenDev AUC": substance.auc_scores(od.y, ext2)["AUC"], "Brier (CV)": s["Brier"]}
base = pd.DataFrame(rows).T
base.round(3)
"""),
        code("""
base.to_csv(RESULTS / "baselines.csv")
pd.DataFrame({k: oof[k] for k in KINDS}).assign(y=od.y.to_numpy(), group=od.group.to_numpy()).to_csv(RESULTS / "baseline_oof.csv", index=False)
fig, ax = plt.subplots(figsize=(7, 3)); base[["OpenDev grouped CV AUC", "OpenDev -> RevHelper AUC", "RevHelper -> OpenDev AUC"]].plot.barh(ax=ax)
ax.axvline(0.5, color="grey", ls="--", lw=1); ax.set_xlim(0.4, 0.9); ax.set_title("Baselines: ROC-AUC (0.5 = no signal)"); fig.tight_layout(); plt.show()
"""),
        md("## 4. Reading the results"),
        reading(1),
    ]


def nb2():
    return [
        md("""
# Collaboration step 1, notebook 2: frozen encoders, heads, tuning without selection bias, the external test

Transfer learning by feature extraction: a pretrained encoder is kept **frozen**; only the head learns from the public labels. Everything follows [SUBSTANCE_PROTOCOL.md](../SUBSTANCE_PROTOCOL.md),
written before any model was trained: nested grouped folds, selection without bias, the rule for keeping a complex head, the external test scored once.
"""),
        code(SETUP),
        md("## 1. Embeddings (computed once per encoder, cached)"),
        code("""
import time
EMB, VARIANTS = {}, ["emb", "emb+meta"]
texts_od, texts_rh = od.clean.tolist(), rh.clean.tolist()
M_od, M_rh = substance.meta(od.text.tolist(), texts_od), substance.meta(rh.text.tolist(), texts_rh)
for enc in substance.ENCODERS:
    t0 = time.time()
    E = substance.embed(enc, texts_od + texts_rh)
    EMB[enc] = (E[:len(od)], E[len(od):])
    print(f"{enc}: {E.shape}  ({time.time() - t0:.0f}s)")
def matrix(enc, variant, part):
    E = EMB[enc][0 if part == "od" else 1]
    if variant == "emb":
        return E
    M = M_od if part == "od" else M_rh
    return np.hstack([E, (M - M_od.mean(0)) / (M_od.std(0) + 1e-9)])   # standardised with OpenDev statistics only
"""),
        md("""
## 2. Tuning on OpenDev: 3 encoders x 2 text variants x 3 head families (logistic 9 settings, forest 8, boosting 8)

Every configuration is scored on every (outer, inner) combination (5 x 4 = 20); nothing from RevHelper is used. This takes a while on CPU the first time; the result is cached.
"""),
        code("""
embs = {(enc, v): matrix(enc, v, "od") for enc in substance.ENCODERS for v in VARIANTS}
t0 = time.time()
tuned, preds = substance.run_tuning(embs, od.y.to_numpy(), od.group.to_numpy(), RESULTS / "tuning.csv", workers=10)
print(len(tuned), "scored configurations x combinations;", f"{time.time() - t0:.0f}s")
st = json.load(open(RESULTS / "tuning.settings.json"))
tuned.groupby(["encoder", "variant", "family"]).auc.mean().unstack("family").round(3)
"""),
        md("""
## 3. Selection without bias: which encoder, text variant and head family

For every (outer, inner) combination the configuration is chosen on the other three inner folds of the same outer fold and scored on the held-out one. The pooled predictions compare the options.
"""),
        code("""
rows = []
for enc in substance.ENCODERS:
    for fam in ("logistic", "forest", "boosting"):
        sub = tuned[(tuned.encoder == enc) & (tuned.family == fam)]
        y, p, g, perfold, pick = substance.pooled_bias_free(sub, preds, od.y.to_numpy(), od.group.to_numpy(), CS)
        rows.append({"encoder": enc, "head": fam, "pooled AUC": substance.auc_scores(y, p)["AUC"], "folds": [round(v, 3) for v in perfold.values()]})
sel = pd.DataFrame(rows).sort_values("pooled AUC", ascending=False).reset_index(drop=True)
sel.round(3)
"""),
        md("## 4. The rule for keeping a complex head"),
        code("""
best_log = sel[sel["head"] == "logistic"].iloc[0]; best_cx = sel[sel["head"] != "logistic"].iloc[0]
def pooled_for(enc, fam):
    sub = tuned[(tuned.encoder == enc) & (tuned.family == fam)]
    return substance.pooled_bias_free(sub, preds, od.y.to_numpy(), od.group.to_numpy(), CS)
yl, pl, gl, fl, _ = pooled_for(best_log.encoder, "logistic")
yc, pc, gc, fc, _ = pooled_for(best_cx.encoder, best_cx["head"])
# both pools cover the same validation rows in the same order only when the encoders' picks are over the same combinations: align by building the same order
order_l = np.lexsort((pl, gl)); order_c = np.lexsort((pc, gc))
gain = best_cx["pooled AUC"] - best_log["pooled AUC"]
folds_better = sum(1 for o in fl if fc[o] > fl[o])
# paired interval: the pooled predictions are produced combination by combination in the same order, so they align row for row
lo, hi = substance.paired_auc_diff(yl, pc, pl, gl) if len(pl) == len(pc) and (yl == yc).all() else (np.nan, np.nan)
rule = {"best logistic": f"{best_log.encoder}", "best complex": f"{best_cx.encoder} + {best_cx['head']}", "AUC gain": round(gain, 4), "95% interval": (round(lo, 4), round(hi, 4)), "folds better (of 5)": folds_better,
        "keep complex head": bool(gain >= 0.01 and lo > 0 and folds_better >= 4)}
print(json.dumps(rule, indent=1))
CHOICE_FAMILY = best_cx["head"] if rule["keep complex head"] else "logistic"
CHOICE_ENC = best_cx.encoder if rule["keep complex head"] else best_log.encoder
print("head family kept:", CHOICE_FAMILY, "| encoder:", CHOICE_ENC)
"""),
        md("""
## 5. Within-OpenDev estimate of the chosen design, and the final configuration

For each outer fold the simplest configuration within one standard error of the best (on that fold's inner folds) is trained on the whole outer training set and scored on the outer test fold, so the
estimate never sees the fold it is scored on. The final configuration (for the external test and for scoring student text) is chosen the same way on all folds and trained on all of OpenDev.
"""),
        code("""
sub = tuned[(tuned.encoder == CHOICE_ENC) & (tuned.family == CHOICE_FAMILY)]
_, piv = substance.bias_free_choice(sub)
oof_final = np.zeros(len(od)); chosen = {}
for o, (tr, te) in OUTER.items():
    cfg = substance.one_se_config(piv, o, st)
    chosen[o] = cfg
    X = matrix(cfg[0], cfg[1], "od")
    m = substance.fit_head(cfg[2], st[cfg[2]][cfg[3]], X[tr], od.y.to_numpy()[tr])
    oof_final[te] = m.predict_proba(X[te])[:, 1]
cv = substance.auc_scores(od.y, oof_final); lo, hi = substance.group_bootstrap_auc(od.y, oof_final, od.group)
b = pd.read_csv(RESULTS / "baseline_oof.csv")
dl, dh = substance.paired_auc_diff(b.y.to_numpy(), oof_final, b["TF-IDF + logistic"].to_numpy(), b.group.to_numpy())
print(f"grouped CV AUC {cv['AUC']:.3f} (95% {lo:.3f} to {hi:.3f}); Brier {cv['Brier']:.3f}")
print(f"gain over TF-IDF + logistic: {cv['AUC'] - substance.auc_scores(b.y, b['TF-IDF + logistic'])['AUC']:+.3f} (95% {dl:+.3f} to {dh:+.3f})")
print("configuration chosen per outer fold:", chosen)
pd.DataFrame({"y": od.y, "p": oof_final, "group": od.group}).to_csv(RESULTS / "final_oof.csv", index=False)
"""),
        code("""
# the final configuration: simplest within one standard error over all outer folds' inner folds
cols = list(piv.columns); mean = piv.mean(axis=1); best = mean.idxmax(); se = substance.row_of(piv, best).std(ddof=1) / np.sqrt(len(cols))
near = [k for k in mean.index if mean[k] >= mean[best] - se]
FINAL = min(near, key=lambda k: substance.complexity(k[2], st[k[2]][k[3]]))
print("final configuration:", FINAL, st[FINAL[2]][FINAL[3]])
Xod, Xrh = matrix(FINAL[0], FINAL[1], "od"), matrix(FINAL[0], FINAL[1], "rh")
head = substance.fit_head(FINAL[2], st[FINAL[2]][FINAL[3]], Xod, od.y.to_numpy())
"""),
        md("""
## 6. The external test, scored once

The final configuration, trained on all of OpenDev, scored on RevHelper (nothing was tuned on RevHelper). The reverse direction uses the same configuration trained on RevHelper and is reported beside it.
"""),
        code("""
p_ext = head.predict_proba(Xrh)[:, 1]
ext = substance.auc_scores(rh.y, p_ext); elo, ehi = substance.group_bootstrap_auc(rh.y, p_ext, rh.group)
head_rev = substance.fit_head(FINAL[2], st[FINAL[2]][FINAL[3]], Xrh, rh.y.to_numpy())
p_rev = head_rev.predict_proba(Xod)[:, 1]; rev = substance.auc_scores(od.y, p_rev)
tf = base_tf = pd.read_csv(RESULTS / "baselines.csv", index_col=0).loc["TF-IDF + logistic"]
ps = np.array([guarded(t) for t in rh.text]); p_guard = np.where(ps, 0.0, p_ext)
res = pd.DataFrame([{"test": "OpenDev -> RevHelper (once)", "AUC": ext["AUC"], "95% low": elo, "95% high": ehi, "Brier": ext["Brier"], "TF-IDF AUC": tf["OpenDev -> RevHelper AUC"]},
                    {"test": "RevHelper -> OpenDev (same configuration)", "AUC": rev["AUC"], "TF-IDF AUC": tf["RevHelper -> OpenDev AUC"]},
                    {"test": "OpenDev -> RevHelper with the guard layer", "AUC": substance.auc_scores(rh.y, p_guard)["AUC"]}]).set_index("test")
res.round(3)
"""),
        md("## 7. Success criteria of the protocol"),
        code("""
crit = pd.DataFrame([
    {"criterion": "External AUC (OpenDev -> RevHelper)", "value": ext["AUC"], "minimum": ">= 0.70", "target": ">= 0.75", "verdict": "target met" if ext["AUC"] >= 0.75 else "minimum met" if ext["AUC"] >= 0.70 else "NOT MET"},
    {"criterion": "Grouped CV AUC within OpenDev", "value": cv["AUC"], "minimum": ">= 0.70", "target": ">= 0.75", "verdict": "target met" if cv["AUC"] >= 0.75 else "minimum met" if cv["AUC"] >= 0.70 else "NOT MET"},
    {"criterion": "Beats TF-IDF + logistic (CV, paired interval)", "value": f"{cv['AUC'] - substance.auc_scores(b.y, b['TF-IDF + logistic'])['AUC']:+.3f} ({dl:+.3f} to {dh:+.3f})", "minimum": "interval excludes 0", "target": "gain >= 0.03",
     "verdict": "target met" if dl > 0 and cv["AUC"] - substance.auc_scores(b.y, b['TF-IDF + logistic'])['AUC'] >= 0.03 else "minimum met" if dl > 0 else "NOT MET"},
    {"criterion": "Guard: approval-only / one-word texts score 0", "value": float(np.mean([0.0 if guarded(t) else 1 for t in ["LGTM", "ok", "good.", "All good.", "+1", "👍", "Done"]]) == 0), "minimum": "all", "target": "all", "verdict": "target met" if all(guarded(t) for t in ["LGTM", "ok", "good.", "All good.", "+1", "👍", "Done"]) else "NOT MET"},
]).set_index("criterion")
crit.to_csv(RESULTS / "criteria.csv"); crit
"""),
        code("""
import joblib
joblib.dump({"encoder": FINAL[0], "variant": FINAL[1], "family": FINAL[2], "params": st[FINAL[2]][FINAL[3]], "head": head, "meta_mean": M_od.mean(0), "meta_std": M_od.std(0)}, RESULTS / "substance_scorer.joblib")
json.dump({"final": list(map(str, FINAL)), "params": st[FINAL[2]][FINAL[3]], "rule": rule, "external_auc": ext["AUC"], "cv_auc": cv["AUC"]}, open(RESULTS / "choice.json", "w"), indent=1)
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
for a, (n, y, p) in zip(ax, (("OpenDev, grouped CV", od.y, oof_final), ("RevHelper, external", rh.y, p_ext))):
    sns.kdeplot(x=p[y == 1], ax=a, label="useful", fill=True, alpha=.3); sns.kdeplot(x=p[y == 0], ax=a, label="not useful", fill=True, alpha=.3); a.set_title(n + ": predicted score"); a.legend()
fig.tight_layout(); plt.show()
"""),
        md("## 8. Reading the results"),
        reading(2),
    ]


def nb3():
    return [
        md("""
# Collaboration step 1, notebook 3: the scorer on student texts, then the six features

The scorer trained in notebook 2 is applied to the texts students wrote. **There are no human labels for these texts**, so this is a sanity check of behaviour, not a validation. The second part builds the six
features of the proposal for every student-sprint and compares heads on the four-criterion Collaboration ratings. Those ratings were written by the assistant (see `dataset/reference_ratings/README.md`),
and the simulated students were written by the assistant too, so the second part is a **pipeline test**, not evidence of accuracy.
"""),
        code(SETUP + """
import joblib
bundle = joblib.load(RESULTS / "substance_scorer.joblib")
def score_texts(originals):
    clean = [clean_text(t) for t in originals]
    E = substance.embed(bundle["encoder"], clean)
    if bundle["variant"] == "emb+meta":
        M = substance.meta(list(originals), clean); E = np.hstack([E, (M - bundle["meta_mean"]) / (bundle["meta_std"] + 1e-9)])
    p = bundle["head"].predict_proba(E)[:, 1]
    return np.where([guarded(t) for t in originals], 0.0, p)
"""),
        md("## 1. Student texts"),
        code("""
st_ = data.student_texts()
st_["score"] = score_texts(st_.text.tolist()); st_["rule score"] = [rule_score(t) for t in st_.text]; st_["words"] = st_.clean.str.split().str.len()
display(st_.groupby(["source", "kind"]).agg(texts=("score", "size"), mean_score=("score", "mean"), zero_share=("score", lambda s: (s == 0).mean())).round(3))
display(st_[st_.source == "real"][["kind", "text", "words", "score"]].round(3))
"""),
        code("""
sim = st_[st_.source == "simulated"]
print("simulated texts:", len(sim), "| Spearman of the model score with the rule score:", round(float(spearmanr(sim.score, sim["rule score"])[0]), 2))
display(sim.groupby(pd.cut(sim.words, [-1, 2, 6, 15, 30, 400]))["score"].agg(["count", "mean"]).round(3))
display(sim.sort_values("score")[["text", "words", "score"]].round(3).iloc[[0, 1, 2, 3, -4, -3, -2, -1]])
"""),
        md("""
## 2. The six features per student-sprint

`Co_PRC_depth` is now the mean model score of the student's reviews on other people's pull requests (0 when there are none); `Co_IC_depth` the same for discussion comments; `Co_MC`, `Co_PCount`, `Co_CCount`, `Co_IR`
as defined in `cleaning.py` and stored in the clean dataset. The label is the mean of the four Collaboration criteria of the ratings, rescaled to 0-1.
"""),
        code("""
FM = data.FM
final = pd.read_csv(FM / "dataset" / "clean" / "final_dataset_clean.csv", low_memory=False)
ref = pd.read_csv(FM / "dataset" / "reference_ratings" / "reference_ratings.csv"); hum = pd.read_csv(FM / "dataset" / "ground_truth" / "human_ratings.csv")
CO = ["Co_review_engagement", "Co_discussion_substance", "Co_team_interaction", "Co_follow_through"]
rate = pd.concat([ref, hum]).drop_duplicates("record_id").set_index("record_id")
final = final[final.record_id.isin(rate.index)].copy()
final["y"] = ((rate.loc[final.record_id, CO].astype(float).mean(axis=1) - 1) / 4).to_numpy()
# model-based depth per (student, sprint)
rv = pd.concat([pd.read_csv(data.SIM / "reviews_simulated.csv").assign(src="simulated"), pd.read_csv(data.EVID / "pr_reviews.csv").assign(src="real")]).fillna("")
rv = rv[rv.body.str.strip() != ""]
rv["score"] = score_texts(rv.body.tolist())
depth = rv.groupby(["sprint_id", "reviewer_id"]).score.mean()
final["PRC_model"] = [float(depth.get((s, u), 0.0)) for s, u in zip(final.sprint_id, final.student_id)]
final["PRC_rule"] = final.Co_PRC_depth
feat_model = ["PRC_model", "Co_IC_depth", "Co_MC", "Co_PCount", "Co_CCount", "Co_IR"]
print(final.groupby("source").agg(records=("y", "size"), with_reviews=("PRC_model", lambda s: int((s > 0).sum())), label_mean=("y", "mean"), label_sd=("y", "std")).round(3))
"""),
        md("""
## 3. Heads on the six features (grouped by student)

Ridge, Random Forest and Gradient Boosting against two baselines: the review count alone and the mean. Grouped five-fold CV by student. Reported separately for the real students (almost nothing varies) and
the simulated ones (a pipeline test).
"""),
        code("""
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
def cv_mae(d, cols, make):
    p = np.zeros(len(d))
    for tr, te in GroupKFold(5).split(d, groups=d.student_id):
        m = make(); m.fit(d[cols].iloc[tr], d.y.iloc[tr]); p[te] = np.clip(m.predict(d[cols].iloc[te]), 0, 1)
    return float(np.abs(p - d.y).mean()), float(spearmanr(p, d.y)[0]) if p.std() > 0 else float("nan")
from sklearn.impute import SimpleImputer
imp = lambda: SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)   # the response rate is undefined for students with no own pull request
HEADS = {"mean": lambda: make_pipeline(imp(), StandardScaler(), Ridge(alpha=1e9)), "Ridge (6 features)": lambda: make_pipeline(imp(), StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 11))),
         "Random Forest": lambda: make_pipeline(imp(), RandomForestRegressor(200, min_samples_leaf=3, random_state=0, n_jobs=1)),
         "Gradient Boosting": lambda: make_pipeline(imp(), GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05, random_state=0))}
rows = []
for src in ("real", "simulated"):
    d = final[final.source == src].reset_index(drop=True)
    if len(d) < 20:
        continue
    for name, mk in HEADS.items():
        mae, rho = cv_mae(d, feat_model, mk); rows.append({"students": src, "head": name, "features": "model depth + 5", "MAE": mae, "Spearman": rho})
    for label, cols in (("review count only (Co_PCount)", ["Co_PCount"]),):
        mae, rho = cv_mae(d, cols, HEADS["Ridge (6 features)"]); rows.append({"students": src, "head": "Ridge", "features": label, "MAE": mae, "Spearman": rho})
    mae, rho = cv_mae(d.assign(PRC_model=d.PRC_rule), ["PRC_model"] + feat_model[1:], HEADS["Ridge (6 features)"]); rows.append({"students": src, "head": "Ridge", "features": "rule depth + 5 (old)", "MAE": mae, "Spearman": rho})
pd.DataFrame(rows).round(3)
"""),
        md("## 4. Reading the results"),
        reading(3),
    ]


if __name__ == "__main__":
    which = sys.argv[1:] or ["1", "2", "3"]
    for n, (name, fn) in {"1": ("01_DATA_AND_BASELINES", nb1), "2": ("02_ENCODER_TUNING", nb2), "3": ("03_COLLABORATION_SCORE", nb3)}.items():
        if n in which:
            write(HERE / f"{name}.ipynb", fn())
            print("wrote", name)
