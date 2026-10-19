"""Builds the Code Ownership notebooks of training/PROTOCOL.md next to this file.

    python build_notebooks.py [1 2 3 4 5 6 7]

01_data_audit                  the dataset, the label, the length confound, rater agreement, the splits
02_splits_and_baselines        simple baselines on the development folds
03_encoders_and_features       frozen encoders, the feature sets, a first look at the embeddings
04_hyperparameter_tuning       every encoder x feature set x head, tuned without selection bias
05_model_comparison            tables, paired bootstrap, the complexity rule, the production rule, the choice
06_final_test                  the chosen model on the final test functions (once), label sensitivity, the production artifact
07_robustness_and_gaming       attacks (code paste, question echo, filler, answer to another function, padding), guards, an out-of-domain check

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
import sys, warnings, json, pickle
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path("../../helpers").resolve()))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, seaborn as sns
from scipy.stats import spearmanr
import ko_data as K, ko_models as M
from core import metrics, group_bootstrap, paired_diff_bootstrap, qwk, band
sns.set_theme(style="whitegrid")
pd.set_option("display.width", 170); pd.set_option("display.max_columns", 30); pd.set_option("display.max_colwidth", 90)
RESULTS = Path("results"); RESULTS.mkdir(exist_ok=True)
d = K.load()
dev = d[d.role == "dev"].reset_index(drop=True)
test = d[d.role == "test"].reset_index(drop=True)
y, groups, folds = dev.score.to_numpy(), dev.snippet_id.to_numpy(), dev.fold.to_numpy()
def ci(p, stat):
    return group_bootstrap(y, p, groups, stat, n=1000)
def sp(a, b):
    return spearmanr(a, b).correlation
def mae(a, b):
    return float(np.mean(np.abs(a - b)))
def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))
"""


def nb1():
    return [
        md("""
# Code Ownership, notebook 1: the data audit

Protocol: [PROTOCOL.md](../../PROTOCOL.md). The data: 36 real Python standard-library functions, one generated question each, 216 answers **written by the assistant at five
rubric levels** (no student wrote any of it, no human rated it). Nothing is fitted in this notebook.
"""),
        code(SETUP),
        md("## 1. Size and structure"),
        code("""
sizes = d.groupby("role").agg(answers=("item_id", "size"), functions=("snippet_id", "nunique"))
sizes.loc["total"] = sizes.sum()
print(sizes)
pd.crosstab(d.question_type, d.rating, margins=True)
"""),
        md("## 2. The length confound\n\nA scorer that only learns 'longer is better' would look good here and mean nothing. The first version of the answers had Spearman 0.83 between length and level; short correct and long weak answers were added (answers_extra.txt) before any model was fitted."),
        code("""
d["words"] = d.answer.str.split().str.len()
print("Spearman words vs written level, all answers:", round(sp(d.words, d.rating), 3))
print(d.groupby("question_type").apply(lambda g: round(sp(g.words, g.rating), 3)).to_dict())
fig, ax = plt.subplots(figsize=(7, 3.2)); sns.boxplot(data=d, x="rating", y="words", ax=ax); ax.set_ylabel("words in the answer"); plt.show()
"""),
        md("## 3. How well do the written level and an independent rating agree?\n\n`rating_independent` was given by a separate Claude instance that saw only a shuffled sheet without the levels. Both are model ratings, so agreement shows the levels are consistent and readable, not that humans would agree."),
        code("""
from sklearn.metrics import cohen_kappa_score
a, b = d.rating, d.rating_independent
agree = {"QWK": cohen_kappa_score(a, b, weights="quadratic"), "Spearman": sp(a, b), "exact": float((a == b).mean()), "within one": float((abs(a - b) <= 1).mean())}
print({k: round(v, 3) for k, v in agree.items()})
pd.crosstab(a, b, rownames=["written level"], colnames=["independent"])
"""),
        code("""
d[abs(a - b) >= 2][["item_id", "question_type", "rating", "rating_independent", "answer"]]
"""),
        md("## 4. The splits\n\nGrouped by function. The final test functions are fixed by hash (one per question type) and are not looked at again until notebook 6."),
        code("""
print(d[d.role == "test"].groupby("question_type").snippet_id.first().to_dict())
dev.groupby("fold").agg(answers=("item_id", "size"), functions=("snippet_id", "nunique"))
"""),
        md("## 5. Reading the results"), reading(1),
    ]


def nb2():
    return [
        md("""
# Code Ownership, notebook 2: baselines on the development folds

Every baseline is evaluated out of fold: for each of the five development folds it is fitted on the other four (functions never shared). Single-feature baselines are
mapped to a score by a straight line fitted on the training folds; the hand-feature models are tuned with the same nested procedure as the encoder models.
"""),
        code(SETUP),
        code("""
from sklearn.linear_model import LinearRegression
from sklearn.feature_extraction.text import TfidfVectorizer
H = K.hand_features(dev)
OOF = {}
OOF["training mean"] = np.array([y[folds != f].mean() for f in folds])
def line(x):
    x = np.asarray(x, float).reshape(-1, 1); p = np.zeros(len(y))
    for f in sorted(set(folds)):
        te = folds == f
        p[te] = np.clip(LinearRegression().fit(x[~te], y[~te]).predict(x[te]), 0, 1)
    return p
for col, name in (("n_words", "answer length (words)"), ("identifier_recall", "identifier recall"), ("fact_overlap", "overlap with all facts"), ("focus_overlap", "overlap with the asked-about fact")):
    OOF[name] = line(H[col])
sim = np.zeros(len(y))
for f in sorted(set(folds)):
    te = folds == f
    tf = TfidfVectorizer().fit(pd.concat([dev.answer[~te], dev.reference[~te]]))
    A, R = tf.transform(dev.answer), tf.transform(dev.reference)
    sim[te] = np.asarray(A[te].multiply(R[te]).sum(1)).ravel()
OOF["TF-IDF similarity to the reference"] = line(sim)
for head in ("ridge", "forest", "boosting"):
    OOF[f"hand-built features, {head}"], _ = M.nested(head, H.to_numpy(float), y, groups, folds, workers=10)
pickle.dump(OOF, open(RESULTS / "baselines_oof.pkl", "wb"))
rows = []
for name, p in OOF.items():
    m = metrics(y, p)
    rows.append({"baseline": name, "MAE": m["MAE"], "RMSE": m["RMSE"], "Spearman": m["spearman"], "Pearson": m["pearson"], "QWK (rounded to 1-5)": m["band_qwk"]})
base = pd.DataFrame(rows).set_index("baseline").round(3)
base.to_csv(RESULTS / "baselines.csv")
base
"""),
        md("Intervals (grouped bootstrap over functions, 1,000 resamples) for the two reference points:"),
        code("""
for name in ("answer length (words)", "hand-built features, ridge"):
    p = OOF[name]
    print(name, "Spearman", np.round(ci(p, lambda a, b: sp(a, b)), 3), "MAE", np.round(ci(p, mae), 3))
"""),
        md("## Reading the results"), reading(2),
    ]


def nb3():
    return [
        md("""
# Code Ownership, notebook 3: the encoders and the feature sets

Frozen encoders (no weights are changed), mean-pooled and L2-normalised: UniXcoder-base and CodeBERT-base (the proposal's choices) and all-mpnet-base-v2 (a general text
encoder as a control). Feature sets A-D (answer; + similarities; + answer-times-reference; joint question+answer) with and without the hand-built features.
"""),
        code(SETUP),
        code("""
import time
from embedder import Encoder
available = {}
for key in ("unixcoder", "codebert", "mpnet"):
    local = Encoder._local(key)
    available[key] = local or "hub cache"
print(available)
ENCODERS = [k for k in ("unixcoder", "codebert", "mpnet") if (Encoder._local(k) or k == "mpnet")]
print("encoders used:", ENCODERS)
"""),
        code("""
H = K.hand_features(dev)
info = []
EMB = {}
for key in ENCODERS:
    t = time.time(); E = K.embeddings(key, dev); EMB[key] = E
    sets = K.feature_sets(E, H)
    info.append({"encoder": key, "embedding dim": E["ans"].shape[1], **{f"dim {s}": v.shape[1] for s, v in sets.items()}, "seconds": round(time.time() - t, 1)})
pd.DataFrame(info).set_index("encoder")
"""),
        md("A first look: cosine similarity between the answer and the reference explanation, by written level. If the embeddings carried the 'is it right' signal this would climb with the level."),
        code("""
rows = []
for key, E in EMB.items():
    for part in ("ref", "code", "ques"):
        c = (E["ans"] * E[part]).sum(1)
        rows.append({"encoder": key, "answer vs": part, "Spearman with level": round(sp(c, dev.rating), 3), **{f"level {r}": round(float(c[dev.rating == r].mean()), 3) for r in range(1, 6)}})
pd.DataFrame(rows)
"""),
        md("## Reading the results"), reading(3),
    ]


def nb4():
    return [
        md("""
# Code Ownership, notebook 4: hyperparameter tuning without selection bias

Every encoder x feature set x head is tuned inside each outer training set by 4 inner folds grouped by function; the outer fold's prediction comes from a head refit on the
whole outer training set. Grids are in `helpers/ko_models.py` (fixed before the run). The runner is resumable and takes a while; finished combinations are kept in
`results/tuning_preds.pkl`.
"""),
        code(SETUP),
        code("""
import run_tuning
from embedder import Encoder
ENCODERS = [k for k in ("unixcoder", "codebert", "mpnet") if (Encoder._local(k) or k == "mpnet")]
P = run_tuning.run(ENCODERS, workers=10)
print(len(P), "combinations")
"""),
        code("""
rows = []
for key, v in P.items():
    e, s, h = key.split("|"); p = v["pred"]
    rows.append({"encoder": e, "feature set": s, "head": h, "RMSE": rmse(p, y), "MAE": mae(p, y), "Spearman": sp(p, y)})
T = pd.DataFrame(rows)
T.to_csv(RESULTS / "tuning.csv", index=False)
T.pivot_table(index=["encoder", "feature set"], columns="head", values="RMSE").round(3)
"""),
        code("""
fig, axes = plt.subplots(1, len(ENCODERS), figsize=(5 * len(ENCODERS), 4), sharey=True, squeeze=False)
for ax, e in zip(axes[0], ENCODERS):
    sns.heatmap(T[T.encoder == e].pivot(index="feature set", columns="head", values="RMSE"), annot=True, fmt=".2f", cmap="viridis_r", ax=ax, cbar=False); ax.set_title(e)
plt.tight_layout(); plt.show()
"""),
        md("Settings chosen in each outer fold for the ridge heads (stability of the choice):"),
        code("""
ch = []
for key, v in P.items():
    e, s, h = key.split("|")
    if h == "ridge":
        ch.append({"encoder": e, "feature set": s, **{f"fold {f}": p["alpha"] for f, p in v["chosen"].items()}})
pd.DataFrame(ch)
"""),
        md("## Reading the results"), reading(4),
    ]


def nb5():
    return [
        md("""
# Code Ownership, notebook 5: model comparison and the choice

Rules fixed in the protocol: (1) a head more complex than ridge is kept only if it beats the best ridge by a paired grouped-bootstrap interval that excludes 0 and wins in
at least 4 of 5 folds; (2) the encoder model is used in production only if it beats the best hand-built-feature baseline by an interval that excludes 0, otherwise production
uses the hand-feature head (rule added before the final test, see the amendment log).
"""),
        code(SETUP),
        code("""
P = pickle.load(open(RESULTS / "tuning_preds.pkl", "rb")); B = pickle.load(open(RESULTS / "baselines_oof.pkl", "rb"))
def fold_wins(p_a, p_b):
    return int(sum(mae(p_a[folds == f], y[folds == f]) < mae(p_b[folds == f], y[folds == f]) for f in sorted(set(folds))))
rows = []
for key, v in P.items():
    e, s, h = key.split("|"); m = metrics(y, v["pred"])
    rows.append({"key": key, "encoder": e, "set": s, "head": h, "MAE": m["MAE"], "RMSE": m["RMSE"], "Spearman": m["spearman"], "QWK": m["band_qwk"]})
T = pd.DataFrame(rows)
best_ridge = T[T["head"] == "ridge"].sort_values("MAE").iloc[0]
best_complex = T[T["head"] != "ridge"].sort_values("MAE").iloc[0]
print("best ridge:   ", best_ridge.key, round(best_ridge.MAE, 3))
print("best complex: ", best_complex.key, round(best_complex.MAE, 3))
"""),
        code("""
# rule 1: complexity
pr, pc = P[best_ridge.key]["pred"], P[best_complex.key]["pred"]
lo, hi = paired_diff_bootstrap(y, pr, pc, groups, n=2000)
wins = fold_wins(pc, pr)
keep_complex = bool(lo > 0 and wins >= 4)
print(f"MAE(ridge) - MAE(complex): 95% interval [{lo:.3f}, {hi:.3f}]; complex wins {wins} of 5 folds -> keep complex head: {keep_complex}")
chosen = best_complex if keep_complex else best_ridge
chosen_pred = P[chosen.key]["pred"]
print("chosen encoder model:", chosen.key)
"""),
        code("""
# rule 2: does the encoder model beat the best hand-built-feature baseline?
hand = {k: v for k, v in B.items() if k.startswith("hand-built")}
best_hand = min(hand, key=lambda k: mae(hand[k], y))
lo2, hi2 = paired_diff_bootstrap(y, hand[best_hand], chosen_pred, groups, n=2000)
wins2 = fold_wins(chosen_pred, hand[best_hand])
encoder_helps = bool(lo2 > 0)
print(f"best hand-feature baseline: {best_hand} (MAE {mae(hand[best_hand], y):.3f}); chosen encoder model MAE {mae(chosen_pred, y):.3f}")
print(f"MAE(hand) - MAE(encoder model): 95% interval [{lo2:.3f}, {hi2:.3f}]; encoder model wins {wins2} of 5 folds -> encoder helps: {encoder_helps}")
"""),
        code("""
# comparison table: baselines and the best of each encoder/head
tab = []
for name, p in B.items():
    m = metrics(y, p); tab.append({"model": name, "kind": "baseline", "MAE": m["MAE"], "RMSE": m["RMSE"], "Spearman": m["spearman"], "QWK": m["band_qwk"]})
for e in sorted(T.encoder.unique()):
    for h in ("ridge", "svr", "kernel_ridge", "forest", "boosting", "mlp"):
        r = T[(T.encoder == e) & (T["head"] == h)].sort_values("MAE").iloc[0]
        tab.append({"model": f"{e} / {r.set} / {h}", "kind": "encoder", "MAE": r.MAE, "RMSE": r.RMSE, "Spearman": r.Spearman, "QWK": r.QWK})
tab = pd.DataFrame(tab).sort_values("MAE").round(3)
tab.to_csv(RESULTS / "comparison.csv", index=False)
tab
"""),
        code("""
# intervals for the main candidates
cands = {"training mean": B["training mean"], "answer length (words)": B["answer length (words)"], best_hand: hand[best_hand], chosen.key: chosen_pred}
for name, p in cands.items():
    print(f"{name:45s} MAE {mae(p, y):.3f} {np.round(ci(p, mae), 3)}   Spearman {sp(p, y):.3f} {np.round(ci(p, lambda a, b: sp(a, b)), 3)}")
"""),
        code("""
if encoder_helps:
    production = {"kind": "encoder", "key": chosen.key, "encoder": chosen.encoder, "feature_set": chosen.set, "head": chosen["head"]}
else:
    production = {"kind": "hand", "key": best_hand, "encoder": None, "feature_set": "H", "head": best_hand.split(", ")[1]}
choice = {"production": production, "encoder_model": chosen.key, "keep_complex_head": keep_complex, "complex_vs_ridge_interval": [lo, hi], "complex_folds_won": wins,
          "encoder_helps": encoder_helps, "encoder_vs_hand_interval": [lo2, hi2], "encoder_folds_won": wins2, "best_hand_baseline": best_hand,
          "dev_MAE": {"production": mae(chosen_pred if encoder_helps else hand[best_hand], y), "mean": mae(B["training mean"], y), "length": mae(B["answer length (words)"], y)}}
(RESULTS / "model_choice.json").write_text(json.dumps(choice, indent=1, default=float), encoding="utf-8")
choice["production"]
"""),
        md("## Reading the results"), reading(5),
    ]


def nb6():
    return [
        md("""
# Code Ownership, notebook 6: the final test (once) and the production artifact

The chosen model is refit on all development functions (settings chosen by inner grouped folds over the development set) and scored **once** on the 6 final-test functions.
Then it is refit on all 36 functions for the artifact the agent loads. The test result comes only from the development-fit model.
"""),
        code(SETUP),
        code("""
import joblib
choice = json.loads((RESULTS / "model_choice.json").read_text(encoding="utf-8"))
prod = choice["production"]
print(prod)
Hd, Ht = K.hand_features(dev), K.hand_features(test)
if prod["kind"] == "encoder":
    Xd = K.feature_sets(K.embeddings(prod["encoder"], dev), Hd)[prod["feature_set"]]
    Xt = K.feature_sets(K.embeddings(prod["encoder"], test), Ht)[prod["feature_set"]]
else:
    Xd, Xt = Hd.to_numpy(float), Ht.to_numpy(float)
Xd, Xt = np.asarray(Xd, float), np.asarray(Xt, float)
head = prod["head"]
NH = Hd.shape[1] if prod["feature_set"].endswith("+H") else 0
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor(10) as pool:
    params, _ = M.tune_one(head, Xd, y, groups, 0, pool, NH)
print("settings chosen on the development set:", params)
pt = M.fit_predict(head, params, Xd, y, Xt, 0)
yt = test.score.to_numpy()
"""),
        code("""
tg = test.snippet_id.to_numpy()
def tci(stat):
    return group_bootstrap(yt, pt, tg, stat, n=2000)
m = metrics(yt, pt)
res = {"n answers": len(yt), "n functions": len(set(tg)), "MAE": m["MAE"], "RMSE": m["RMSE"], "Spearman": m["spearman"], "Pearson": m["pearson"], "QWK (1-5 bands)": m["band_qwk"], "ICC(2,1)": m["ICC2_1"]}
print({k: round(v, 3) for k, v in res.items()})
print("95% intervals (grouped bootstrap over the 6 functions): MAE", np.round(tci(mae), 3), "Spearman", np.round(tci(lambda a, b: sp(a, b)), 3))
"""),
        code("""
# the same baselines, fitted on the development functions only, scored on the same test answers
from sklearn.linear_model import LinearRegression
rows = [{"model": "production model", "MAE": mae(pt, yt), "Spearman": sp(pt, yt)}, {"model": "training mean", "MAE": mae(np.full(len(yt), y.mean()), yt), "Spearman": float("nan")}]
for col, name in (("n_words", "answer length"), ("identifier_recall", "identifier recall"), ("focus_overlap", "overlap with the asked-about fact")):
    lr = LinearRegression().fit(Hd[[col]], y); p = np.clip(lr.predict(Ht[[col]]), 0, 1)
    rows.append({"model": name, "MAE": mae(p, yt), "Spearman": sp(p, yt)})
pd.DataFrame(rows).round(3)
"""),
        code("""
t2 = test.assign(pred=pt, err=np.abs(pt - yt))
print(t2.groupby("question_type").agg(n=("err", "size"), MAE=("err", "mean")).round(3))
fig, ax = plt.subplots(figsize=(5, 4)); sns.stripplot(data=t2, x="rating", y=1 + 4 * t2.pred, ax=ax, jitter=0.15); ax.plot([0, 4], [1, 5], "k--", lw=1); ax.set_ylabel("predicted rating (1-5)"); ax.set_xlabel("written level"); plt.show()
"""),
        md("Sensitivity to the label: the same predictions against the independent rating and against the mean of the two ratings."),
        code("""
out = {}
for col in ("score", "score_independent", "score_mean"):
    yy = test[col].to_numpy(); out[col] = {"MAE": mae(pt, yy), "Spearman": sp(pt, yy)}
pd.DataFrame(out).T.round(3)
"""),
        md("## Production artifact\n\nRefit on all 36 functions (settings chosen on all of them), plus the 10th and 90th percentile of the development out-of-fold residuals as the reported band."),
        code("""
allX = np.vstack([Xd, Xt]); ally = np.concatenate([y, yt]); allg = np.concatenate([groups, tg])
with ProcessPoolExecutor(10) as pool:
    params_all, _ = M.tune_one(head, allX, ally, allg, 0, pool, NH)
final = M.make(head, params_all, 0).fit(allX, ally)
P = pickle.load(open(RESULTS / "tuning_preds.pkl", "rb"))
B = pickle.load(open(RESULTS / "baselines_oof.pkl", "rb"))
oof = P[choice["encoder_model"]]["pred"] if prod["kind"] == "encoder" else B[prod["key"]]
resid = y - oof
MODEL = Path("../../../model").resolve(); MODEL.mkdir(exist_ok=True)
joblib.dump(final, MODEL / "ko_head.joblib")
card = {"encoder": prod["encoder"], "feature_set": prod["feature_set"], "head": head, "params": params_all, "features_version": "ko_features/2",
        "trained_on": "36 standard-library functions, 216 assistant-written answers (no student data, no human ratings)",
        "dev_oof": {"MAE": mae(oof, y), "Spearman": sp(oof, y)}, "final_test": {k: float(v) for k, v in res.items()},
        "residual_quantiles": [float(np.percentile(resid, 10)), float(np.percentile(resid, 90))]}
(MODEL / "ko_model.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
card
"""),
        md("## Reading the results"), reading(6),
    ]


def nb7():
    return [
        md("""
# Code Ownership, notebook 7: robustness, gaming and an out-of-domain check

The production path is used end to end (`score.rate`: guards, encoder, head). Attack sets are built from the 36 functions:

| attack | answer |
|---|---|
| code paste | the first lines of the function itself |
| question echo | the question text |
| generic filler | a fluent sentence that fits any function |
| answer to another function | a level-5 answer written for a different function of the same question type |
| padding | a level-5 answer plus 40 filler words |
| too short | 3 words |

Pass criteria, fixed in the protocol: the median predicted rating of each attack set is at most 2.0.
"""),
        code(SETUP),
        code("""
import importlib.util
spec = importlib.util.spec_from_file_location("ko_score_nb", Path("../../../score.py").resolve())
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
card = S.card(); print(card["encoder"], card["feature_set"], card["head"])
enc = S.emb.Encoder(card["encoder"]) if card["encoder"] else None
snips = d.drop_duplicates("snippet_id").set_index("snippet_id")
top = d[d.rating == 5].groupby("snippet_id").first()
FILLER = ["This function takes the input, processes it step by step and returns the correct result, which is then used by the rest of the program.",
          "It checks the values and handles the different cases properly so that everything works as expected without any problems."]
rows = []
def add(name, sid, answer):
    s = snips.loc[sid]
    r = S.rate(answer, s.question, s.code, s.facts, encoder=enc, qtype=s.question_type)
    rows.append({"attack": name, "snippet_id": sid, "rating": r["rating"], "guard": r["guard"] or ""})
ids = sorted(snips.index)
for i, sid in enumerate(ids):
    s = snips.loc[sid]
    add("code paste", sid, " ".join(s.code.splitlines()[:6]))
    add("question echo", sid, s.question)
    add("generic filler", sid, FILLER[i % 2])
    other = [o for o in ids if snips.loc[o].question_type == s.question_type and o != sid]
    add("answer to another function", sid, top.loc[other[i % len(other)]].answer)
    add("padding", sid, top.loc[sid].answer + " " + " ".join(["indeed"] * 40))
    add("too short", sid, "it just works")
    add("genuine level-5 answer (reference)", sid, top.loc[sid].answer)
R = pd.DataFrame(rows)
summ = R.groupby("attack").rating.agg(["median", "mean", "max"]).round(2)
summ["guard fired"] = R.groupby("attack").guard.apply(lambda g: int((g != "").sum()))
summ["pass (median <= 2.0)"] = summ["median"] <= 2.0
summ
"""),
        code("""
R.to_csv(RESULTS / "robustness.csv", index=False)
fig, ax = plt.subplots(figsize=(8, 3.6)); sns.boxplot(data=R, y="attack", x="rating", ax=ax); ax.set_xlabel("predicted rating (1-5)"); plt.tight_layout(); plt.show()
"""),
        md("## Out-of-domain check on the earlier simulated quiz (175 rows)\n\n`quiz_simulated.csv` holds assistant-written answers for the simulated students, but it has a one-line description of the snippet instead of code, and JavaScript/React subjects. It is not the training distribution, so this is only a sanity check of direction; the label is again the assistant's."),
        code("""
q = pd.read_csv(K.KO.parent / "dataset" / "synthetic_students" / "out" / "quiz_simulated.csv")
preds = []
for r in q.itertuples():
    out = S.rate(r.answer, r.question, r.snippet, None, encoder=enc)
    preds.append(out["rating"])
q["pred"] = preds
print("n =", len(q), " Spearman(predicted, written rating) =", round(sp(q.pred, q.rating), 3))
print(q.groupby("rating").pred.agg(["count", "mean"]).round(2))
"""),
        md("## Reading the results"), reading(7),
    ]


def main(which):
    names = {1: ("01_data_audit", nb1), 2: ("02_splits_and_baselines", nb2), 3: ("03_encoders_and_features", nb3), 4: ("04_hyperparameter_tuning", nb4),
             5: ("05_model_comparison", nb5), 6: ("06_final_test", nb6), 7: ("07_robustness_and_gaming", nb7)}
    for n in which:
        name, fn = names[n]
        write(HERE / f"{name}.ipynb", fn())
        print("wrote", name)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6, 7])
