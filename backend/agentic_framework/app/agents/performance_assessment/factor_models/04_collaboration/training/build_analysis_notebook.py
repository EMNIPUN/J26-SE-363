"""Builds 04_collaboration/training/00_DATASET_ANALYSIS.ipynb: is the CRScore human-rated data suitable for training the comment-substance scorer?

    python build_analysis_notebook.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_notebooks import code, md, write  # noqa: E402

reading = (HERE / "reading_0.md").read_text(encoding="utf-8") if (HERE / "reading_0.md").exists() else "_Reading of the results: written after the run._"

cells = [
    md("""
# Is the CRScore human-rated data suitable for training the comment-substance scorer? (analysis before any training)

Data: the phase-2 human study of CRScore (MIT). People rated code review comments from 1 to 5 on **conciseness**, **comprehensiveness** and **relevance**. About 90% of the rated comments were written by nine
models and about 10% (`msg`) are the original human reviewer comments. Questions answered here, in order, before a scorer is trained:

1. How many ratings are there and how are they spread (is there something to learn)?
2. How reliable are the ratings (how well do two people agree; this is the ceiling for any model)?
3. Do the model-written comments leak "who wrote it" into the ratings (would a scorer learn the writer's style instead of substance)?
4. Does comment length alone explain the ratings (length bias)?
5. How much signal does plain text carry (a cheap pilot, grouped by diff), including the transfer from model-written to human-written comments?
6. Is the number of human-written comments enough (learning curve)?
"""),
    code("""
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(".").resolve()))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, seaborn as sns
from scipy.stats import spearmanr
import crscore, substance
sns.set_theme(style="whitegrid"); pd.set_option("display.width", 170)
d = crscore.load_main(); pairs = crscore.load_pairs()
d["words"] = d.clean.str.split().str.len()
print("rated comments:", len(d), "| human-written:", int(d.human.sum()), "| diffs:", d.group.nunique(), "| comments rated by both annotators:", len(pairs))
display(d.groupby("system").agg(n=("rel", "size"), rel=("rel", "mean"), comp=("comp", "mean"), con=("con", "mean"), words=("words", "median")).round(2).sort_values("rel"))
"""),
    md("## 1. Spread of the ratings"),
    code("""
fig, ax = plt.subplots(1, 3, figsize=(11, 3), sharey=True)
for a, c in zip(ax, ("rel", "comp", "con")):
    sns.countplot(data=d.assign(h=d.human.map({True: "human-written", False: "model-written"})), x=c, hue="h", ax=a); a.set_title({"rel": "relevance", "comp": "comprehensiveness", "con": "conciseness"}[c])
fig.tight_layout(); plt.show()
print("Spearman between the three ratings:"); display(d[["rel", "comp", "con"]].corr(method="spearman").round(2))
print("share of ratings at 1 / at 5:", {c: (round((d[c] == 1).mean(), 2), round((d[c] == 5).mean(), 2)) for c in ("rel", "comp", "con")})
"""),
    md("""
## 2. Reliability of the ratings (the ceiling)

The four agreement files hold comments rated by both annotators. Quadratic-weighted kappa and Spearman measure how well two people agree; ICC(2,1) is the usual reliability figure. A model cannot be expected to
agree with a person better than people agree with each other.
"""),
    code("""
import sys
sys.path.insert(0, str(Path("../../ml_lib").resolve()))
from core import qwk, icc
rows = {}
for c, name in (("rel", "relevance"), ("comp", "comprehensiveness"), ("con", "conciseness")):
    a, m = pairs[c + "_a"].to_numpy(float), pairs[c + "_m"].to_numpy(float)
    rows[name] = {"pairs": len(a), "Spearman": spearmanr(a, m)[0], "weighted kappa": qwk(a.astype(int), m.astype(int)), "ICC(2,1)": icc(a, m, 2), "exact agreement": float((a == m).mean()), "within 1": float((abs(a - m) <= 1).mean())}
rel = pd.DataFrame(rows).T; display(rel.round(2))
h = pairs[pairs.system == "msg"]; print("human-written comments rated by both:", len(h))
print("ceiling for a perfect predictor against one rater (about sqrt of the reliability):", {k: round(float(np.sqrt(max(v, 0))), 2) for k, v in rel["ICC(2,1)"].items()})
display(d.groupby(["rater"]).agg(rel=("rel", "mean"), comp=("comp", "mean"), con=("con", "mean")).round(2).rename_axis("rater leniency"))
"""),
    md("""
## 3. Does the writer's style leak into the ratings?

If most of the variance in the ratings is explained by *which model wrote the comment*, a scorer can earn its score by recognising the writer's style. A scorer that does well on model-written comments but not on human ones
would be no use for students.
"""),
    code("""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
gm = d.rel.mean(); ss_tot = ((d.rel - gm) ** 2).sum()
r2_sys = 1 - ((d.rel - d.groupby("system").rel.transform("mean")) ** 2).sum() / ss_tot
print(f"share of the variance of relevance explained by the writer (system) alone: {r2_sys:.2f}")
y_h = d.human.astype(int).to_numpy(); oof = np.zeros(len(d))
for tr, te in GroupKFold(5).split(d, groups=d.group):
    m = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), LogisticRegression(C=2, max_iter=2000, class_weight="balanced")).fit(d.clean.iloc[tr], y_h[tr])
    oof[te] = m.predict_proba(d.clean.iloc[te])[:, 1]
print(f"can text alone tell a human-written comment from a model-written one? AUC {roc_auc_score(y_h, oof):.2f} (0.5 = no)")
"""),
    md("## 4. Length bias"),
    code("""
rows = []
for name, sub in (("all comments", d), ("human-written only", d[d.human]), ("model-written only", d[~d.human])):
    rows.append({"subset": name, "n": len(sub), **{c: spearmanr(sub.words, sub[c])[0] for c in ("rel", "comp", "con")}})
display(pd.DataFrame(rows).set_index("subset").round(2).rename(columns={"rel": "Spearman(words, relevance)", "comp": "Spearman(words, comprehensiveness)", "con": "Spearman(words, conciseness)"}))
"""),
    md("""
## 5. A cheap learnability pilot (not the real training)

Ridge regression on (a) length, (b) TF-IDF, (c) MiniLM embeddings, predicting relevance, with five folds **grouped by diff**. Scores: Spearman with the human rating, on all comments and on the
human-written ones only, plus the transfer test: train on model-written comments only, test on human-written ones.
"""),
    code("""
E = substance.embed("MiniLM", d.clean.tolist())
y = d.rel.to_numpy(float); g = d.group.to_numpy(); hmask = d.human.to_numpy()
def feats(kind, tr, te):
    if kind == "length":
        f = lambda ix: np.log1p(d.words.iloc[ix].to_numpy())[:, None]; return f(tr), f(te)
    if kind == "TF-IDF":
        v = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit(d.clean.iloc[tr]); return v.transform(d.clean.iloc[tr]), v.transform(d.clean.iloc[te])
    return E[tr], E[te]
res = {}
for kind in ("length", "TF-IDF", "MiniLM embeddings"):
    oof = np.zeros(len(d))
    for tr, te in GroupKFold(5).split(d, groups=g):
        Xtr, Xte = feats(kind, tr, te); oof[te] = Ridge(alpha=1.0 if kind != "TF-IDF" else 3.0).fit(Xtr, y[tr]).predict(Xte)
    tr = np.where(~hmask)[0]; te = np.where(hmask)[0]; Xtr, Xte = feats(kind, tr, te); tp = Ridge(alpha=1.0 if kind != "TF-IDF" else 3.0).fit(Xtr, y[tr]).predict(Xte)
    res[kind] = {"all comments (CV)": spearmanr(y, oof)[0], "human-written only (CV)": spearmanr(y[hmask], oof[hmask])[0], "train model-written -> test human-written": spearmanr(y[hmask], tp)[0]}
pilot = pd.DataFrame(res).T; display(pilot.round(2))
"""),
    md("## 6. Is the number of human-written comments enough? (learning curve, MiniLM + Ridge, human-written only)"),
    code("""
hi = np.where(hmask)[0]; rng = np.random.default_rng(1); rows = []
for n in (40, 80, 120, 160, 200):
    sc = []
    for r in range(30):
        pick = rng.permutation(hi); tr, te = pick[:n], pick[n:]
        if len(te) < 20: continue
        sc.append(spearmanr(y[te], Ridge(alpha=1.0).fit(E[tr], y[tr]).predict(E[te]))[0])
    rows.append({"human-written training comments": n, "Spearman on the rest": np.mean(sc), "sd": np.std(sc)})
display(pd.DataFrame(rows).set_index("human-written training comments").round(2))
"""),
    md("## 7. Reading the results"),
    md(reading),
]
write(HERE / "00_DATASET_ANALYSIS.ipynb", cells)
print("wrote 00_DATASET_ANALYSIS.ipynb")
