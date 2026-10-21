"""Fit the chosen Effort model for one outer fold, on every group except the test group.

Used by the robustness tests (notebook 07), the guard layer (07b) and the final test (08), so all
use the same fitting. Settings (label source, weight, hyperparameters) come from the nested tuning
in notebook 04, chosen for each outer fold using only its inner validation groups.
"""

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import RESULTS, SEED
from features import feature_matrix, training_set


def roles_for(d, outer):
    """Training on every group except ``outer``; the outer group is the test group."""
    group_of = dict(zip(d.record_id, d.group))
    rows = []
    for r in d.itertuples():
        if r.source == "real":
            rows.append((r.record_id, "test" if r.group == outer else "train"))
        else:
            pa, pb = r.parents.split()
            rows.append((r.record_id, "train" if outer not in (group_of[pa], group_of[pb]) else "excluded"))
    return pd.DataFrame(rows, columns=["record_id", "role"])


def make_model(name, p, n_features, seed=SEED):
    if name == "Ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=p["alpha"]))
    if name == "Random Forest":
        return RandomForestRegressor(random_state=seed, n_jobs=1, **p)
    q = {k: v for k, v in p.items() if k != "monotonic"}
    return HistGradientBoostingRegressor(random_state=seed, early_stopping=False, monotonic_cst=[1] * n_features if p["monotonic"] else None, **q)


def fit_chosen(d, outer, model, feature_set, seed=SEED):
    """Returns (fitted model, kind, settings, training rows) for one outer fold."""
    choices = json.loads((RESULTS / "tuning_choices.json").read_text())
    pick = choices[model][feature_set][outer]
    kind = "linear" if model == "Ridge" else "tree"
    roles = roles_for(d, outer)
    X, y, w, ids = training_set(d, roles, lambda f: feature_matrix(f, feature_set, kind), pick["label_source"], pick["weight"], real_only=False)
    m = make_model(model, pick["params"], X.shape[1], seed)
    m.fit(X, y, **({"ridge__sample_weight": w} if model == "Ridge" else {"sample_weight": w}))
    return m, kind, pick, len(y)


# --- deterministic guard layer ----------------------------------------------------------------------------

GUARD_FILE = RESULTS / "guard_choice.json"


def apply_guard(frame, guard):
    """Counts are credited only as far as the evidence supports them (before the model sees them).

    ``lines_per_commit``: a commit is counted only when it carries at least that many lines, so
    ``E_CC`` becomes ``min(commits, lines / lines_per_commit)``.
    ``files_per_commit``: files are counted up to that many per commit, so ``E_FC`` becomes
    ``min(files, files_per_commit * max(commits, 1))``.
    """
    f = frame.copy()
    cc = f.E_CC.astype(float)
    if guard.get("lines_per_commit"):
        f["E_CC"] = np.minimum(cc, f.E_LOC_net_capped.astype(float).clip(lower=0) / guard["lines_per_commit"])
    if guard.get("files_per_commit"):
        f["E_FC"] = np.minimum(f.E_FC.astype(float), guard["files_per_commit"] * np.maximum(cc, 1))
    return f


def predict_guarded(model, frame, feature_set, kind, guard):
    """Prediction with the guard layer: caps first, then the model, then the zero-commit rule."""
    p = np.clip(model.predict(feature_matrix(apply_guard(frame, guard), feature_set, kind)), 0, 1)
    if guard.get("zero_rule", True):
        p = np.where(frame.E_CC.to_numpy() == 0, 0.0, p)
    return p
