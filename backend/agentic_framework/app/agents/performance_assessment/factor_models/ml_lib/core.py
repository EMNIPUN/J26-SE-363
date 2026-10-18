"""Shared machinery for the regression factors (Consistency, Task Complexity): data, splits,
metrics, bootstrap, logging. Effort has its own earlier copy in 01_effort/training/common.py;
this module is the same logic made independent of the factor.
"""

import hashlib
import platform
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.stats import kendalltau, pearsonr, spearmanr

SEED = 20261018
GROUPS = ["A", "B", "C", "D", "E"]


@dataclass(frozen=True)
class Factor:
    key: str  # "consistency"
    title: str  # "Consistency"
    folder: Path  # the factor's folder, e.g. factor_models/02_consistency
    dataset_file: str  # "consistency_dataset.csv"
    label: str  # name of the rater column in the dataset
    activity: str  # column for "active" subsets (commits > 0)

    @property
    def data(self):
        return self.folder / "dataset" / self.dataset_file

    @property
    def splits(self):
        return self.folder / "dataset" / "splits.csv"

    @property
    def results(self):
        path = self.folder / "training" / "results"
        path.mkdir(parents=True, exist_ok=True)
        return path


def load(f):
    return pd.read_csv(f.data, low_memory=False).set_index("record_id", drop=False)


def log_signed(x):
    return np.sign(x) * np.log1p(np.abs(x))


# --- splits ----------------------------------------------------------------------------------------

def make_splits(d):
    """Role of every record in every (outer test group, inner validation group) combination.

    Synthetic records are training-only, and only when both parents are in training groups.
    """
    group_of = dict(zip(d.record_id, d.group))
    rows = []
    for test in GROUPS:
        others = [g for g in GROUPS if g != test]
        for val in others:
            train = [g for g in others if g != val]
            for r in d.itertuples():
                if r.source == "real":
                    role = "test" if r.group == test else "val" if r.group == val else "train"
                else:
                    pa, pb = r.parents.split()
                    role = "train" if group_of[pa] in train and group_of[pb] in train else "excluded"
                rows.append((test, val, r.record_id, role))
    return pd.DataFrame(rows, columns=["outer_test", "inner_val", "record_id", "role"])


# --- metrics -------------------------------------------------------------------------------------

def icc(y, p, kind):
    x = np.column_stack([y, p])
    n, k = x.shape
    grand = x.mean()
    ssr = k * ((x.mean(axis=1) - grand) ** 2).sum()
    ssc = n * ((x.mean(axis=0) - grand) ** 2).sum()
    sse = ((x - grand) ** 2).sum() - ssr - ssc
    msr, msc, mse = ssr / (n - 1), ssc / (k - 1), sse / ((n - 1) * (k - 1))
    if kind == 2:
        return (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
    return (msr - mse) / (msr + (k - 1) * mse)


def ccc(y, p):
    cov = np.cov(y, p, bias=True)[0, 1]
    return 2 * cov / (y.var() + p.var() + (y.mean() - p.mean()) ** 2)


def band(x):
    return np.clip(np.rint(1 + 4 * np.asarray(x)), 1, 5).astype(int)


def qwk(a, b, k=5):
    o = np.zeros((k, k))
    for i, j in zip(a, b):
        o[i - 1, j - 1] += 1
    w = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    e = np.outer(o.sum(1), o.sum(0)) / o.sum()
    return 1 - (w * o).sum() / (w * e).sum() if (w * e).sum() else float("nan")


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    err = p - y
    ss_res, ss_tot = (err ** 2).sum(), ((y - y.mean()) ** 2).sum()
    by, bp = band(y), band(p)
    const = np.std(p) == 0 or np.std(y) == 0
    slope = np.polyfit(p, y, 1) if np.std(p) > 0 else (float("nan"), float("nan"))
    return {
        "n": len(y), "MAE": float(np.abs(err).mean()), "RMSE": float(np.sqrt((err ** 2).mean())), "MedAE": float(np.median(np.abs(err))),
        "bias": float(err.mean()), "R2": float(1 - ss_res / ss_tot) if ss_tot else float("nan"),
        "pearson": float("nan") if const else float(pearsonr(y, p)[0]),
        "spearman": float("nan") if const else float(spearmanr(y, p)[0]),
        "kendall": float("nan") if const else float(kendalltau(y, p)[0]),
        "CCC": float("nan") if const else float(ccc(y, p)),
        "ICC2_1": float("nan") if const else float(icc(y, p, 2)), "ICC3_1": float("nan") if const else float(icc(y, p, 3)),
        "calib_slope": float(slope[0]), "calib_intercept": float(slope[1]),
        "within_0.1": float((np.abs(err) <= 0.1).mean()), "band_exact": float((by == bp).mean()),
        "band_within_1": float((np.abs(by - bp) <= 1).mean()), "band_qwk": float(qwk(by, bp)),
    }


def group_bootstrap(y, p, groups, stat, n=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    y, p, g = np.asarray(y), np.asarray(p), np.asarray(groups)
    names = np.unique(g)
    out = []
    for _ in range(n):
        pick = rng.choice(names, len(names), replace=True)
        idx = np.concatenate([np.where(g == k)[0] for k in pick])
        out.append(stat(y[idx], p[idx]))
    out = np.array(out, float)
    return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))


def paired_diff_bootstrap(y, p_a, p_b, groups, n=2000, seed=SEED):
    """95% interval of MAE(a) - MAE(b); above 0 means b is better."""
    rng = np.random.default_rng(seed)
    y, a, b, g = map(np.asarray, (y, p_a, p_b, groups))
    ea, eb = np.abs(a - y), np.abs(b - y)
    names = np.unique(g)
    out = []
    for _ in range(n):
        pick = rng.choice(names, len(names), replace=True)
        idx = np.concatenate([np.where(g == k)[0] for k in pick])
        out.append(ea[idx].mean() - eb[idx].mean())
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


# --- logging ---------------------------------------------------------------------------------------

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def environment(f):
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
            "sklearn": sklearn.__version__, "seed": SEED, "data_hash": file_hash(f.data),
            "splits_hash": file_hash(f.splits) if f.splits.exists() else ""}


def log_run(f, notebook, model, scope, values):
    """Append one result row to the factor's results/runs.csv."""
    row = {"time": datetime.now().isoformat(timespec="seconds"), "notebook": notebook, "model": model, "scope": scope,
           **environment(f), **values}
    path = f.results / "runs.csv"
    frame = pd.DataFrame([row])
    if path.exists():
        frame = pd.concat([pd.read_csv(path), frame], ignore_index=True)
    frame.to_csv(path, index=False)


def md_table(df, fmt="{:.3f}"):
    head = "| " + " | ".join(["", *map(str, df.columns)]) + " |"
    rule = "|---" * (len(df.columns) + 1) + "|"
    body = ["| " + " | ".join([str(i), *[fmt.format(v) if isinstance(v, float) else str(v) for v in row]]) + " |" for i, row in df.iterrows()]
    return "\n".join([head, rule, *body])
