"""Heads, their grids, and the tuning loop without selection bias (PROTOCOL.md).

Every setting is chosen on inner folds of the outer training set only; the outer fold's prediction comes from a head refit on the whole outer training set.
The grids are fixed here, before any run.
"""
import sys
import warnings
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ko_blocks import Blocks  # noqa: E402  (the production module, so a saved head can be loaded by the agent)

GRIDS = {
    "ridge": [{"alpha": a} for a in (0.1, 1, 10, 100, 1000)],
    "svr": [{"C": c, "epsilon": 0.05, "gamma": g} for c in (0.3, 1, 3, 10) for g in ("scale", 0.1 / 1000)],
    "kernel_ridge": [{"alpha": a, "gamma": g} for a in (0.03, 0.3, 3) for g in (None, 0.001)],
    "forest": [{"n_estimators": 300, "max_depth": md, "min_samples_leaf": ml, "pca": 24} for md in (3, 6) for ml in (2, 5)],
    "boosting": [{"n_estimators": n, "learning_rate": lr, "max_depth": 2, "subsample": 0.8, "pca": 24} for n in (100, 300) for lr in (0.03, 0.1)],
    "mlp": [{"hidden": h, "alpha": a, "pca": 32} for h in (16, 48) for a in (0.01, 1.0)],
}


def grid(head, n_hand=0):
    """The settings tried for a head. n_hand: how many trailing columns are hand-built features (0 when the matrix is a single block).
    With a hand-built block, the linear and kernel heads also try a weight hw on that block (1 = as scaled, larger = more influence)."""
    base = GRIDS[head]
    if n_hand and head in ("ridge", "svr", "kernel_ridge"):
        return [{**p, "n_hand": n_hand, "hw": hw} for p in base for hw in (1, 5, 20)]
    return [{**p, "n_hand": n_hand} for p in base]


def make(head, p, seed=0):
    p = dict(p)
    pca, n_hand, hw = p.pop("pca", None), p.pop("n_hand", 0), p.pop("hw", 1.0)
    steps = [StandardScaler()]
    if n_hand:
        steps.append(Blocks(n_hand=n_hand, pca=pca, hw=hw, seed=seed))
    elif pca:
        steps.append(PCA(n_components=pca, random_state=seed))
    if head == "ridge":
        m = Ridge(**p)
    elif head == "svr":
        m = SVR(kernel="rbf", **p)
    elif head == "kernel_ridge":
        m = KernelRidge(kernel="rbf", **p)
    elif head == "forest":
        m = RandomForestRegressor(random_state=seed, n_jobs=1, **p)
    elif head == "boosting":
        m = GradientBoostingRegressor(random_state=seed, **p)
    elif head == "mlp":
        m = MLPRegressor(hidden_layer_sizes=(p.pop("hidden"),), alpha=p.pop("alpha"), max_iter=800, early_stopping=False, random_state=seed)
    else:
        raise ValueError(head)
    return make_pipeline(*steps, m)


def fit_predict(head, p, Xtr, ytr, Xte, seed=0):
    p = dict(p)
    if p.get("pca"):  # never more components than the matrix has columns or rows (the hand-feature matrices are narrow)
        p["pca"] = min(p["pca"], Xtr.shape[1], len(Xtr) - 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = make(head, p, seed).fit(Xtr, ytr)
        return np.clip(m.predict(Xte), 0.0, 1.0)


def inner_folds(groups, k=4, seed=0):
    names = np.array(sorted(set(groups)))
    rng = np.random.default_rng(seed)
    rng.shuffle(names)
    return [set(names[i::k]) for i in range(k)]


def _inner_score(args):
    head, p, X, y, groups, seed = args
    folds = inner_folds(groups, seed=seed)
    err = []
    for held in folds:
        te = np.array([g in held for g in groups])
        pred = fit_predict(head, p, X[~te], y[~te], X[te], seed)
        err.append(np.mean((pred - y[te]) ** 2))
    return float(np.mean(err))


def tune_one(head, X, y, groups, seed=0, pool=None, n_hand=0):
    """Best setting by inner-fold MSE. Returns (params, table of (params, mse))."""
    settings = grid(head, n_hand)
    jobs = [(head, p, X, y, groups, seed) for p in settings]
    scores = list(pool.map(_inner_score, jobs)) if pool else [_inner_score(j) for j in jobs]
    best = int(np.argmin(scores))
    return settings[best], list(zip(settings, scores))


def nested(head, X, y, groups, folds, workers=8, seed=0, n_hand=0):
    """Out-of-fold predictions on the development set with settings chosen inside each outer training set. Returns (pred, chosen params per fold)."""
    pred = np.full(len(y), np.nan)
    chosen = {}
    with ProcessPoolExecutor(workers) as pool:
        for f in sorted(set(folds)):
            te = folds == f
            p, _ = tune_one(head, X[~te], y[~te], groups[~te], seed, pool, n_hand)
            chosen[int(f)] = p
            pred[te] = fit_predict(head, p, X[~te], y[~te], X[te], seed)
    return pred, chosen
