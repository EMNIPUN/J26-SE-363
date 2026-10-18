"""Feature variants, label construction and leak-proof training sets, independent of the factor.

A *variant* is a list of ``(column, transform)`` pairs. Missing values stay missing here: linear
models get a median imputer (fitted on the training rows only, with missing-value flags), tree
models read them directly. Nothing that learns from data is fitted outside a training set.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from core import SEED, log_signed

ALPHAS = np.logspace(-2, 3, 11)
LABEL_SOURCES = ["rated only", "rated + propagated (real)", "rated + propagated (real + synthetic)"]


def transform(x, tf):
    x = np.asarray(x, dtype=float)
    if tf == "raw":
        return x
    if tf == "log":
        return log_signed(x)
    if tf == "one_minus":
        return 1.0 - x
    raise ValueError(tf)


def design(d, spec):
    """Matrix for a list of (column, transform); missing values are kept as NaN."""
    return np.column_stack([transform(d[c].to_numpy(), tf) for c, tf in spec])


def linear_model(alpha):
    return make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True), StandardScaler(), Ridge(alpha=alpha))


def fit_linear(model, X, y, w):
    model.fit(X, y, ridge__sample_weight=w)
    return model


def fit_ridge_loo(X, y, alphas=ALPHAS):
    """Choose alpha by leave-one-out on (X, y); return the fitted pipeline and alpha."""
    best, best_err = None, np.inf
    for a in alphas:
        err = 0.0
        for i in range(len(y)):
            keep = np.arange(len(y)) != i
            m = linear_model(a).fit(X[keep], y[keep])
            err += abs(m.predict(X[i:i + 1])[0] - y[i])
        if err < best_err:
            best, best_err = a, err
    return linear_model(best).fit(X, y), float(best)


class Propagator:
    """Labels for unrated rows, learned from the rated rows of the training groups only."""

    def __init__(self, gold, spec, label):
        self.spec = spec
        self.model, self.alpha = fit_ridge_loo(design(gold, spec), gold[label].to_numpy())

    def predict(self, frame):
        return np.clip(self.model.predict(design(frame, self.spec)), 0, 1)


def training_set(d, roles, featurize, label, base_spec, label_source, pseudo_weight=1.0, real_only=False):
    """(X, y, weights, ids) for one split combination.

    ``featurize`` maps a frame to a matrix; ``base_spec`` is the fixed variant used by the label model.
    """
    t = d.loc[roles[roles.role == "train"].record_id]
    gold = t[(t.source == "real") & (t.label_source == "rater")]
    parts = [(gold, gold[label].to_numpy(), 1.0)]
    if label_source != "rated only":
        prop = Propagator(gold, base_spec, label)
        unrated = t[(t.source == "real") & (t.label_source != "rater")]
        parts.append((unrated, prop.predict(unrated), pseudo_weight))
        if label_source == LABEL_SOURCES[2] and not real_only:
            syn = t[t.source == "synthetic"]
            if len(syn):
                parts.append((syn, prop.predict(syn), pseudo_weight))
    X = np.vstack([featurize(f) for f, _, _ in parts])
    y = np.concatenate([lab for _, lab, _ in parts])
    w = np.concatenate([np.full(len(lab), wt) for _, lab, wt in parts])
    ids = np.concatenate([f.record_id.to_numpy() for f, _, _ in parts])
    return X, y, w, ids


# --- model families ------------------------------------------------------------------------------------

def make_model(name, params, n_features):
    if name == "Ridge":
        return linear_model(params["alpha"])
    if name == "Random Forest":
        return RandomForestRegressor(random_state=SEED, n_jobs=1, **params)
    q = {k: v for k, v in params.items() if k != "monotonic"}
    return HistGradientBoostingRegressor(random_state=SEED, early_stopping=False,
                                         monotonic_cst=[1] * n_features if params.get("monotonic") else None, **q)


def fit_model(model, name, X, y, w):
    model.fit(X, y, **({"ridge__sample_weight": w} if name == "Ridge" else {"sample_weight": w}))
    return model
