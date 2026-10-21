"""Feature variants, label construction and the leak-proof training-set builder for Effort.

Everything that learns from data (the scaler, the propagation model) is fitted on the training
rows of one split combination only. Row-level features that need no labels (the team context) are
computed from the features of the same team and sprint, which is information available at
prediction time.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import log_signed

BASE = ["E_CC", "E_LOC_net_capped", "E_FC", "E_CT", "E_RD"]
CORE4 = ["E_CC", "E_LOC_net_capped", "E_FC", "E_CT"]
TEAM_COLS = ["E_CC", "E_LOC_net_capped", "E_FC", "E_CT"]
ALPHAS = np.logspace(-2, 3, 11)

# variant -> list of (column, transform)
VARIANTS = {
    "raw5": [(c, "raw") for c in BASE],
    "log5": [(c, "log") for c in BASE],
    "log4 (no RD)": [(c, "log") for c in CORE4],
    "log3 (commits, lines, files)": [(c, "log") for c in ["E_CC", "E_LOC_net_capped", "E_FC"]],
    # review activity counts only where a review was possible: E_RD is 0 and a flag marks teams that had no pull requests
    "log5, RD marked n/a": [(c, "log") for c in BASE] + [("rd_not_applicable", "raw")],
    "log4 + RD marked n/a": [(c, "log") for c in CORE4] + [("E_RD", "log"), ("rd_not_applicable", "raw")],
    "log3 + RD marked n/a": [(c, "log") for c in ["E_CC", "E_LOC_net_capped", "E_FC"]] + [("E_RD", "log"), ("rd_not_applicable", "raw")],
    "log4 + no-activity flag": [(c, "log") for c in CORE4] + [("no_activity", "raw")],
    "log4, uncapped lines": [("E_CC", "log"), ("E_LOC_net", "log"), ("E_FC", "log"), ("E_CT", "log")],
    "log4 + team z-scores": [(c, "log") for c in CORE4] + [(f"{c}_team_z", "raw") for c in TEAM_COLS],
    "team z-scores only": [(f"{c}_team_z", "raw") for c in TEAM_COLS],
    "team shares only": [(f"{c}_team_share", "raw") for c in TEAM_COLS],
}
# the team context exists only for real records (synthetic rows have no team)
REAL_ONLY = {"log4 + team z-scores", "team z-scores only", "team shares only"}
LABEL_SOURCES = ["rated only", "rated + propagated (real)", "rated + propagated (real + synthetic)"]


def add_team_context(d):
    """Team-relative features from the features of the same team and sprint (no labels)."""
    d = d.copy()
    real = d.source == "real"
    keys = [d.loc[real, "team_id"], d.loc[real, "sprint_id"]]
    for col in TEAM_COLS:
        raw = d.loc[real, col].astype(float)
        lg = pd.Series(log_signed(raw.to_numpy()), index=raw.index)
        mu = lg.groupby(keys).transform("mean")
        sd = lg.groupby(keys).transform("std").replace(0, np.nan)
        d.loc[real, f"{col}_team_z"] = ((lg - mu) / sd).fillna(0.0)
        total = raw.clip(lower=0).groupby(keys).transform("sum").replace(0, np.nan)
        d.loc[real, f"{col}_team_share"] = (raw.clip(lower=0) / total).fillna(0.0)
    return d


def design(d, variant):
    """Feature matrix for a variant (stateless transforms only)."""
    cols = []
    for c, tf in VARIANTS[variant]:
        x = d[c].astype(float).to_numpy()
        cols.append(log_signed(x) if tf == "log" else x)
    return np.column_stack(cols)


def fit_ridge_loo(X, y, alphas=ALPHAS):
    """Standardise, choose alpha by leave-one-out on (X, y), return (scaler, model, alpha)."""
    scaler = StandardScaler().fit(X)
    Z = scaler.transform(X)
    errors = []
    for a in alphas:
        e = 0.0
        for i in range(len(y)):
            keep = np.arange(len(y)) != i
            e += abs(Ridge(alpha=a).fit(Z[keep], y[keep]).predict(Z[i:i + 1])[0] - y[i])
        errors.append(e)
    alpha = float(alphas[int(np.argmin(errors))])
    return scaler, Ridge(alpha=alpha).fit(Z, y), alpha


class Propagator:
    """Labels for unrated rows, learned from the rated rows of the training groups only."""

    def __init__(self, gold):
        self.scaler, self.model, self.alpha = fit_ridge_loo(design(gold, "log5"), gold.rater_effort.to_numpy())

    def predict(self, frame):
        return np.clip(self.model.predict(self.scaler.transform(design(frame, "log5"))), 0, 1)


def training_set(d, roles, variant, label_source, pseudo_weight=1.0, real_only=None):
    """(X, y, weights, ids) for one split combination. ``roles`` has record_id and role columns.

    ``variant`` is a name from VARIANTS or a function frame -> matrix (then pass ``real_only``).
    """
    featurize = variant if callable(variant) else (lambda f: design(f, variant))
    real_only = (variant in REAL_ONLY) if real_only is None else real_only
    t = d.loc[roles[roles.role == "train"].record_id]
    gold = t[(t.source == "real") & (t.label_source == "rater")]
    parts = [(gold, gold.rater_effort.to_numpy(), 1.0)]
    if label_source != "rated only":
        prop = Propagator(gold)
        unrated = t[(t.source == "real") & (t.label_source != "rater")]
        parts.append((unrated, prop.predict(unrated), pseudo_weight))
        if label_source == "rated + propagated (real + synthetic)" and not real_only:
            syn = t[t.source == "synthetic"]
            if len(syn):
                parts.append((syn, prop.predict(syn), pseudo_weight))
    X = np.vstack([featurize(f) for f, _, _ in parts])
    y = np.concatenate([lab for _, lab, _ in parts])
    w = np.concatenate([np.full(len(lab), wt) for _, lab, wt in parts])
    ids = np.concatenate([f.record_id.to_numpy() for f, _, _ in parts])
    return X, y, w, ids


def fit_predict_ridge(X, y, w, X_val, alpha):
    pipe = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    pipe.fit(X, y, ridge__sample_weight=w)
    return np.clip(pipe.predict(X_val), 0, 1), pipe


# --- feature sets used when comparing model families (notebook 04 onwards) -----------------------

FEATURE_SETS = ["5 features (proposal)", "5 features, review n/a", "3 features (chosen)"]


def feature_matrix(d, feature_set, kind):
    """Matrix for a feature set. ``kind`` is "linear" (review n/a becomes 0 plus a flag) or "tree"
    (review n/a becomes a missing value, which the tree models read directly)."""
    if feature_set == "5 features (proposal)":
        return design(d, "log5")
    if feature_set == "3 features (chosen)":
        return design(d, "log3 (commits, lines, files)")
    if feature_set == "5 features, review n/a":
        if kind == "linear":
            return design(d, "log5, RD marked n/a")
        X = design(d, "log5")
        X[d.rd_not_applicable.to_numpy() == 1, 4] = np.nan
        return X
    raise ValueError(feature_set)
