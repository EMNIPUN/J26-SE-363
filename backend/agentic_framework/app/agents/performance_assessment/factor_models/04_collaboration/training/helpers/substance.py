"""Engine for the comment-substance scorer (SUBSTANCE_PROTOCOL.md): embeddings, heads, tuning with selection without bias, scoring.

Everything that learns from data is fitted on the training rows of one combination only. Embeddings come from frozen encoders and are cached on disk.
"""
import hashlib
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / "dataset" / "cache"
SEED = 20261019
ENCODERS = {"MiniLM": "sentence-transformers/all-MiniLM-L6-v2", "mpnet": "sentence-transformers/all-mpnet-base-v2", "roberta": "roberta-base"}
CODE_FLAG = re.compile(r"`|\.(js|ts|py|java|css)\b|\b(def|function|class|return)\b")


# --- embeddings --------------------------------------------------------------------------------------------------------

def _key(name, texts):
    h = hashlib.sha1(("\n".join(texts) + name).encode()).hexdigest()[:12]
    return CACHE / f"{name}_{len(texts)}_{h}.npy"


def embed(encoder, texts):
    """Frozen encoder embeddings (L2-normalised), cached. ``encoder`` is a key of ENCODERS."""
    texts = list(texts)
    path = _key(encoder, texts)
    if path.exists():
        return np.load(path)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(ENCODERS[encoder], device="cpu")
    vec = model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(path, vec)
    return vec


def meta(original, cleaned):
    """Three cheap features: log words, code present in the original, question mark."""
    return np.column_stack([np.log1p([len(c.split()) for c in cleaned]), [1.0 if CODE_FLAG.search(o or "") else 0.0 for o in original],
                            [1.0 if "?" in (o or "") else 0.0 for o in original]])


# --- heads ----------------------------------------------------------------------------------------------------------------

def settings(seed=SEED):
    rng = np.random.default_rng(seed)
    out = {"logistic": [{"C": float(c)} for c in np.logspace(-2, 2, 9)], "forest": [], "boosting": []}
    for _ in range(8):
        out["forest"].append({"n_estimators": int(rng.choice([100, 200])), "max_depth": rng.choice([6, 12, 0]).item() or None,
                              "min_samples_leaf": int(rng.choice([1, 3, 8])), "max_features": float(rng.choice([0.05, 0.15, 0.3]))})
        out["boosting"].append({"learning_rate": float(rng.choice([0.03, 0.08, 0.15])), "max_iter": int(rng.choice([60, 120, 200])),
                                "max_depth": int(rng.choice([2, 3, 4])), "min_samples_leaf": int(rng.choice([10, 20, 40])), "l2_regularization": float(rng.choice([0.0, 1.0]))})
    return out


def fit_head(family, params, X, y):
    if family == "logistic":
        return LogisticRegression(C=params["C"], class_weight="balanced", max_iter=3000).fit(X, y)
    if family == "forest":
        return RandomForestClassifier(random_state=SEED, n_jobs=1, class_weight="balanced", **params).fit(X, y)
    return HistGradientBoostingClassifier(random_state=SEED, early_stopping=False, **params).fit(X, y)


def complexity(family, p):
    """Smaller is simpler (ties and the one-standard-error rule)."""
    if family == "logistic":
        return (-np.log10(p["C"]),)
    if family == "forest":
        return ((p["max_depth"] or 20) * p["n_estimators"] / 100, -p["min_samples_leaf"])
    return (p["max_iter"] * p["max_depth"] * p["learning_rate"], -p["min_samples_leaf"])


# --- tuning ---------------------------------------------------------------------------------------------------------------

_G = {}


def _init(path):
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)  # one thread per worker process; the encoder in the notebook process keeps all cores
    z = np.load(path, allow_pickle=True)
    _G.update({k: z[k] for k in z.files})


def _task(t):
    enc, variant, family, sid, params = t
    X = _G[f"X_{enc}_{variant}"]
    y, combos = _G["y"], _G["combos"]
    rows = []
    for ci, (o, v) in enumerate(_G["combo_ids"]):
        tr, va = _G[f"tr_{ci}"], _G[f"va_{ci}"]
        m = fit_head(family, params, X[tr], y[tr])
        p = m.predict_proba(X[va])[:, 1]
        rows.append((enc, variant, family, sid, int(o), int(v), roc_auc_score(y[va], p) if 0 < y[va].mean() < 1 else np.nan, len(va), p.astype("float32")))
    return rows


def combos(groups, n_outer=5, n_inner=4):
    """[(outer, inner, train_idx, val_idx, test_idx)] with groups kept whole."""
    out = []
    for o, (tr_o, te) in enumerate(GroupKFold(n_outer).split(groups, groups=groups)):
        for i, (tr_i, va_i) in enumerate(GroupKFold(n_inner).split(tr_o, groups=np.asarray(groups)[tr_o])):
            out.append((o, i, tr_o[tr_i], tr_o[va_i], te))
    return out


def run_tuning(embs, y, groups, out_csv, workers=10):
    """Score every (encoder, variant, head, setting) on every (outer, inner) combination. ``embs``: {(encoder, variant): matrix}. Cached in out_csv."""
    out_csv = Path(out_csv)
    pkl = out_csv.with_suffix(".preds.pkl")
    if out_csv.exists() and pkl.exists():
        return pd.read_csv(out_csv), joblib.load(pkl)
    cs = combos(groups)
    payload = {"y": np.asarray(y), "combos": np.array(0), "combo_ids": np.array([(c[0], c[1]) for c in cs])}
    for ci, c in enumerate(cs):
        payload[f"tr_{ci}"], payload[f"va_{ci}"] = c[2], c[3]
    for (enc, variant), X in embs.items():
        payload[f"X_{enc}_{variant}"] = X
    tmp = out_csv.with_suffix(".npz")
    np.savez(tmp, **payload)
    st = settings()
    tasks = [(enc, variant, fam, sid, p) for (enc, variant) in embs for fam, plist in st.items() for sid, p in enumerate(plist)]
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(str(tmp),)) as ex:
        for r in ex.map(_task, tasks, chunksize=2):
            rows += r
    df = pd.DataFrame([r[:8] for r in rows], columns=["encoder", "variant", "family", "sid", "outer", "inner", "auc", "n"])
    preds = {(r[0], r[1], r[2], r[3], r[4], r[5]): r[8] for r in rows}  # (encoder, variant, family, setting, outer, inner) -> validation predictions
    df.to_csv(out_csv, index=False)
    joblib.dump(preds, pkl)
    tmp.unlink()
    json.dump(st, open(out_csv.with_suffix(".settings.json"), "w"))
    return df, preds


def pooled_bias_free(df, preds, y, groups, cs, family_filter=None):
    """Pooled validation predictions where every (outer, inner) uses the configuration chosen on the other inner folds of its outer fold.
    Returns (y, p, groups, per-outer-fold AUC dict, picks)."""
    pick, _ = bias_free_choice(df, family_filter)
    ys, ps, gs, fold = [], [], [], {}
    lookup = {(c[0], c[1]): c[3] for c in cs}
    for (o, i), cfg in pick.items():
        va = lookup[(o, i)]
        p = preds[(*cfg, o, i)]
        ys.append(np.asarray(y)[va]); ps.append(p); gs.append(np.asarray(groups)[va]); fold.setdefault(o, ([], []))[0].append(ys[-1]); fold[o][1].append(p)
    per_fold = {o: roc_auc_score(np.concatenate(a), np.concatenate(b)) for o, (a, b) in fold.items()}
    return np.concatenate(ys), np.concatenate(ps), np.concatenate(gs), per_fold, pick


def bias_free_choice(df, family_filter=None):
    """For every (outer, inner): the configuration with the best mean AUC on the other inner folds of the same outer fold. Returns {(o, i): config}."""
    d = df if family_filter is None else df[df.family.isin(family_filter)]
    d = d.assign(cfg=list(zip(d.encoder, d.variant, d.family, d.sid)))
    piv = d.pivot_table(index="cfg", columns=["outer", "inner"], values="auc")
    pick = {}
    for o in sorted({c[0] for c in piv.columns}):
        for i in sorted({c[1] for c in piv.columns if c[0] == o}):
            others = [c for c in piv.columns if c[0] == o and c[1] != i]
            pick[(o, i)] = piv[others].mean(axis=1).idxmax()
    return pick, piv


def row_of(piv, key):
    """The row of a configuration stored as a tuple in a flat index (``.loc`` would read the tuple as several labels)."""
    return piv.iloc[piv.index.get_loc(key)]


def one_se_config(piv, outer, settings_by_family):
    """Simplest configuration within one standard error of the best mean AUC over the inner folds of one outer fold."""
    cols = [c for c in piv.columns if c[0] == outer]
    mean = piv[cols].mean(axis=1)
    best = mean.idxmax()
    se = row_of(piv[cols], best).std(ddof=1) / np.sqrt(len(cols))
    near = [k for k in mean.index if mean[k] >= mean[best] - se]
    return min(near, key=lambda k: complexity(k[2], settings_by_family[k[2]][k[3]]))


# --- scoring ------------------------------------------------------------------------------------------------------------------

def auc_scores(y, p):
    y, p = np.asarray(y), np.asarray(p)
    return {"AUC": roc_auc_score(y, p) if p.std() > 0 else 0.5, "Brier": brier_score_loss(y, np.clip(p, 0, 1)), "Spearman": float(spearmanr(y, p)[0]) if p.std() > 0 else 0.0}


def group_bootstrap_auc(y, p, groups, n=1000, seed=SEED):
    rng = np.random.default_rng(seed)
    y, p, g = np.asarray(y), np.asarray(p), np.asarray(groups)
    names = np.unique(g)
    idx = {k: np.where(g == k)[0] for k in names}
    vals = []
    for _ in range(n):
        i = np.concatenate([idx[k] for k in rng.choice(names, len(names))])
        if 0 < y[i].mean() < 1 and p[i].std() > 0:
            vals.append(roc_auc_score(y[i], p[i]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def paired_auc_diff(y, p_a, p_b, groups, n=1000, seed=SEED):
    """95% interval of AUC(a) - AUC(b), resampling groups."""
    rng = np.random.default_rng(seed)
    y, a, b, g = map(np.asarray, (y, p_a, p_b, groups))
    names = np.unique(g)
    idx = {k: np.where(g == k)[0] for k in names}
    vals = []
    for _ in range(n):
        i = np.concatenate([idx[k] for k in rng.choice(names, len(names))])
        if 0 < y[i].mean() < 1 and a[i].std() > 0 and b[i].std() > 0:
            vals.append(roc_auc_score(y[i], a[i]) - roc_auc_score(y[i], b[i]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))
