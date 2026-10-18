"""Retraining engine for the regression factors on the clean data. Implements RETRAIN_PROTOCOL.md for any factor config.

    run_validation(cfg)   baselines, variants, label sources, tuning of Ridge / Random Forest / Gradient Boosting   -> results/*.csv
    choose(cfg)           selection without bias, the protocol's rule for a complex model                           -> results/model_choice.json
    run_final(cfg)        per-fold final models, the final test (once), criteria                                    -> results/final_*.csv

Everything that learns from data (imputer, scaler, label model, models) is fitted on training rows of one combination only.
"""

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

os.environ.setdefault("OMP_NUM_THREADS", "1")

from core import GROUPS, SEED, Factor, group_bootstrap, load, make_splits, metrics, paired_diff_bootstrap  # noqa: E402
from features import ALPHAS, LABEL_SOURCES, SIM_OWN, design, fit_model, fit_ridge_loo, make_model, training_set  # noqa: E402

LABEL_CONFIGS = [("rated only", 1.0), (LABEL_SOURCES[1], 1.0), (LABEL_SOURCES[1], 0.3), (LABEL_SOURCES[2], 1.0), (LABEL_SOURCES[2], 0.3)]
REF_CONFIGS = [("rated only", 1.0), (SIM_OWN, 0.3), (SIM_OWN, 1.0)]  # clean_ref data: every real row is rated; simulated rows add their own ratings
N_SETTINGS = 30


@dataclass
class Cfg:
    key: str
    title: str
    folder: object                  # <factor>/clean
    dataset_file: str
    label: str                      # rater column
    activity: str                   # column that is 0 when the student did nothing
    proposal: list                  # the proposal's features as (column, transform)
    variants: dict                  # name -> spec
    tuning_variants: list           # variant names the tuned models are run on
    baselines: list                 # dicts: name, kind (mean | median | linear | ridge), col, tf, zero
    reference: str                  # baseline a model must beat
    criteria: dict
    zero_rule: bool = False
    extra: dict = field(default_factory=dict)
    label_configs: list = field(default_factory=lambda: list(LABEL_CONFIGS))

    def factor(self):
        return Factor(key=self.key, title=self.title, folder=self.folder, dataset_file=self.dataset_file, label=self.label, activity=self.activity)


# --- settings -----------------------------------------------------------------------------------------

def make_settings():
    rng = np.random.default_rng(SEED)
    out = {"Ridge": [{"alpha": float(a)} for a in ALPHAS], "Random Forest": [], "Gradient Boosting": []}
    for _ in range(N_SETTINGS):
        depth = rng.choice([2, 3, 4, 6, 0])
        out["Random Forest"].append({"n_estimators": int(rng.choice([100, 200, 300])), "max_depth": None if depth == 0 else int(depth),
                                     "min_samples_leaf": int(rng.choice([1, 2, 3, 5, 8, 12])), "max_features": float(rng.choice([0.5, 0.75, 1.0]))})
        out["Gradient Boosting"].append({"learning_rate": float(rng.choice([0.02, 0.04, 0.08, 0.15])), "max_iter": int(rng.choice([40, 80, 150, 250])),
                                         "max_depth": int(rng.choice([2, 3, 4])), "min_samples_leaf": int(rng.choice([5, 10, 20])),
                                         "l2_regularization": float(rng.choice([0.0, 0.5, 2.0])), "monotonic": bool(rng.choice([True, False]))})
    return out


def complexity(model, params):
    """Smaller is simpler (used to break ties and for the one-standard-error rule)."""
    if model == "Ridge":
        return (-np.log10(params["alpha"]),)
    if model == "Random Forest":
        return ((params["max_depth"] or 12) * params["n_estimators"] / 100, -params["min_samples_leaf"])
    return (params["max_iter"] * params["max_depth"] * params["learning_rate"], -params["min_samples_leaf"])


# --- worker -------------------------------------------------------------------------------------------

_G = {}


def _init(cfg_getter_name):
    from retrain_configs import CONFIGS
    cfg = CONFIGS[cfg_getter_name]()
    d = load(cfg.factor())
    splits = make_splits(d)
    _G.update(cfg=cfg, d=d, combos=[(o, v, g[["record_id", "role"]]) for (o, v), g in splits.groupby(["outer_test", "inner_val"])])


def _run(task):
    model, variant, lab, weight, sid, params = task
    cfg, d = _G["cfg"], _G["d"]
    spec = cfg.variants[variant]
    feat = lambda f: design(f, spec)  # noqa: E731
    rows = []
    for o, v, roles in _G["combos"]:
        X, y, w, _ = training_set(d, roles, feat, cfg.label, cfg.proposal, lab, weight)
        m = make_model(model, params, X.shape[1])
        fit_model(m, model, X, y, w)
        val = d.loc[roles[roles.role == "val"].record_id]
        val = val[val.label_source == "rater"]
        if not len(val):
            continue
        p = np.clip(m.predict(feat(val)), 0, 1)
        rows += list(zip([o] * len(val), [v] * len(val), val.record_id, val[cfg.label], p))
    return task, rows


def run_validation(cfg_name, results, workers=11):
    """Tune every model on every (variant, label configuration, setting); write one predictions file."""
    from retrain_configs import CONFIGS
    cfg = CONFIGS[cfg_name]()
    settings = make_settings()
    tasks = []
    for variant in cfg.tuning_variants:
        for model, plist in settings.items():
            for lab, weight in cfg.label_configs:
                if lab == "rated only" and weight != 1.0:
                    continue
                for sid, params in enumerate(plist):
                    tasks.append((model, variant, lab, weight, sid, params))
    t0 = time.time()
    out = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(cfg_name,)) as ex:
        for i, (task, rows) in enumerate(ex.map(_run, tasks, chunksize=4)):
            model, variant, lab, weight, sid, _ = task
            out += [(model, variant, lab, weight, sid, *r) for r in rows]
            if (i + 1) % 200 == 0:
                print(f"  {i + 1}/{len(tasks)} settings ({time.time() - t0:.0f}s)", flush=True)
    df = pd.DataFrame(out, columns=["model", "variant", "lab", "weight", "sid", "outer_test", "inner_val", "record_id", "y", "pred"])
    results.mkdir(parents=True, exist_ok=True)
    df.to_csv(results / "tuning_predictions.csv", index=False)
    json.dump(settings, open(results / "settings.json", "w"))
    print(f"tuning: {len(tasks)} settings, {len(df)} predictions, {time.time() - t0:.0f}s")
    return df


# --- baselines ------------------------------------------------------------------------------------------

def baseline_predict(cfg, b, train, test):
    y = train[cfg.label].to_numpy()
    if b["kind"] == "mean":
        p = np.full(len(test), y.mean())
    elif b["kind"] == "median":
        p = np.full(len(test), np.median(y))
    elif b["kind"] == "linear":
        from core import log_signed
        from features import transform
        x, xt = transform(train[b["col"]], b["tf"]), transform(test[b["col"]], b["tf"])
        ok = ~np.isnan(x)
        if ok.sum() < 3 or np.std(x[ok]) == 0:
            p = np.full(len(test), y.mean())
        else:
            a, c = np.polyfit(x[ok], y[ok], 1)
            p = np.where(np.isnan(xt), y.mean(), a * xt + c)
    else:  # ridge on the proposal features, penalty by leave-one-out, rated labels only
        model, _ = fit_ridge_loo(design(train, cfg.proposal), y)
        p = model.predict(design(test, cfg.proposal))
    p = np.clip(p, 0, 1)
    if b.get("zero") and cfg.zero_rule:
        p = np.where(test[cfg.activity].to_numpy() == 0, 0.0, p)
    return p


def run_baselines(cfg, results):
    d = load(cfg.factor())
    splits = make_splits(d)
    rows = []
    for (o, v), roles in splits.groupby(["outer_test", "inner_val"]):
        train = d.loc[roles[roles.role == "train"].record_id]
        train = train[(train.source == "real") & (train.label_source == "rater")]
        val = d.loc[roles[roles.role == "val"].record_id]
        val = val[val.label_source == "rater"]
        if not len(val):
            continue
        for b in cfg.baselines:
            p = baseline_predict(cfg, b, train, val)
            rows += [(b["name"], o, v, r, y, pp) for r, y, pp in zip(val.record_id, val[cfg.label], p)]
    df = pd.DataFrame(rows, columns=["name", "outer_test", "inner_val", "record_id", "y", "pred"])
    df.to_csv(results / "baseline_predictions.csv", index=False)
    return df


# --- selection without bias ----------------------------------------------------------------------------------

def config_errors(tp):
    """Mean absolute error of every configuration in every (outer, inner) combination."""
    tp = tp.assign(err=(tp.pred - tp.y).abs())
    return tp.groupby(["lab", "weight", "sid", "outer_test", "inner_val"]).err.mean().unstack(["outer_test", "inner_val"])


def bias_free(tp):
    """Predictions where each combination uses the configuration chosen on the other three validation groups of its outer fold."""
    M = config_errors(tp)
    keys = tp.set_index(["lab", "weight", "sid", "outer_test", "inner_val"]).sort_index()
    out, chosen = [], {}
    for o in sorted({c[0] for c in M.columns}):
        for v in sorted({c[1] for c in M.columns if c[0] == o}):
            others = [c for c in M.columns if c[0] == o and c[1] != v]
            pick = M[others].mean(axis=1).idxmin()
            chosen[(o, v)] = pick
            if (pick + (o, v)) in keys.index:
                out.append(keys.loc[[pick + (o, v)]].reset_index()[["outer_test", "inner_val", "record_id", "y", "pred"]])
    return pd.concat(out, ignore_index=True), chosen


def group_of(d):
    return dict(zip(d.record_id, d.group))


def pooled(df):
    return metrics(df.y, df.pred)


def per_fold_mae(df):
    return df.assign(err=(df.pred - df.y).abs()).groupby("outer_test").err.mean()


def decide(cfg, tuned, baselines, d, results):
    """Selection-bias-free comparison and the protocol's rule. Returns the choice dict."""
    gmap = group_of(d)
    pools, picks = {}, {}
    for (model, variant), g in tuned.groupby(["model", "variant"]):
        pools[(model, variant)], picks[(model, variant)] = bias_free(g)
    ridge_loo = baselines[baselines.name == [b["name"] for b in cfg.baselines if b["kind"] == "ridge"][0]]
    rows = []
    for (model, variant), p in pools.items():
        rows.append({"model": model, "variant": variant, **{k: v for k, v in pooled(p).items() if k in ("MAE", "pearson", "spearman", "bias")}})
    rows.append({"model": "Ridge (rated only, LOO alpha)", "variant": "proposal", **{k: v for k, v in pooled(ridge_loo).items() if k in ("MAE", "pearson", "spearman", "bias")}})
    table = pd.DataFrame(rows).sort_values("MAE").reset_index(drop=True)
    table.to_csv(results / "validation_comparison.csv", index=False)

    def best(models):
        t = table[table.model.isin(models)]
        return t.iloc[0]

    ridge_best = best(["Ridge", "Ridge (rated only, LOO alpha)"])
    trees = table[table.model.isin(["Random Forest", "Gradient Boosting"])]
    complex_best = trees.iloc[0]

    def pool_of(row):
        return ridge_loo if row.model.startswith("Ridge (rated") else pools[(row.model, row.variant)]

    pr, pc = pool_of(ridge_best), pool_of(complex_best)
    key = ["outer_test", "inner_val", "record_id"]
    m = pr.merge(pc, on=key, suffixes=("_r", "_c"))
    gain = float((m.pred_r - m.y_r).abs().mean() - (m.pred_c - m.y_c).abs().mean())
    lo, hi = paired_diff_bootstrap(m.y_r, m.pred_r, m.pred_c, [gmap[r] for r in m.record_id])
    fr, fc = per_fold_mae(pr), per_fold_mae(pc)
    wins = int((fc < fr).sum())
    rule = {"ridge": f"{ridge_best.model} | {ridge_best.variant}", "complex": f"{complex_best.model} | {complex_best.variant}",
            "gain_mae": gain, "ci": [lo, hi], "folds_better": wins, "passes_1_3": bool(gain >= 0.01 and lo > 0 and wins >= 4)}
    choice = {"ridge_best": ridge_best.to_dict(), "complex_best": complex_best.to_dict(), "rule": rule}
    return choice, table, pools, picks



# --- final models and the final test ---------------------------------------------------------------------------

RANK = {cfg_: i for i, cfg_ in enumerate(LABEL_CONFIGS)}
RANK_REF = {cfg_: i for i, cfg_ in enumerate(REF_CONFIGS)}


def pick_final_config(tp, model, variant, o, settings, rank=None):
    """Simplest configuration within one standard error of the best, from the four validation groups of outer fold ``o``."""
    M = config_errors(tp[(tp.model == model) & (tp.variant == variant)])
    sub = M[[c for c in M.columns if c[0] == o]]
    mean = sub.mean(axis=1)
    best = mean.idxmin()
    se = sub.loc[best].std(ddof=1) / np.sqrt(sub.shape[1])
    near = sorted(mean[mean <= mean[best] + se].index, key=lambda k: ((rank or RANK)[(k[0], float(k[1]))], complexity(model, settings[model][int(k[2])])))
    lab, weight, sid = near[0]
    return lab, float(weight), int(sid), settings[model][int(sid)]


def roles_final(d, o):
    rows = [(r.record_id, "test" if (r.source == "real" and r.group == o) else "train") for r in d.itertuples()]
    return pd.DataFrame(rows, columns=["record_id", "role"])


def fit_final(cfg, d, model, variant, lab, weight, params, o):
    spec = cfg.variants[variant]
    feat = lambda f: design(f, spec)  # noqa: E731
    X, y, w, _ = training_set(d, roles_final(d, o), feat, cfg.label, cfg.proposal, lab, weight)
    m = make_model(model, params, X.shape[1])
    fit_model(m, model, X, y, w)
    return m, feat


def final_test(cfg, d, chosen, variant, tuned, settings, extra_models=()):
    """Pooled predictions for the rated records, each from a model fitted without that student's group.

    chosen: model name ("Ridge (rated only, LOO alpha)" or a tuned family). extra_models: more (model, variant) pairs to score too.
    Returns (predictions frame, fitted models per (name, outer fold))."""
    gold = d[(d.source == "real") & (d.label_source == "rater")]
    rows, fits = [], {}
    names = [(chosen, variant)] + [x for x in extra_models if x != (chosen, variant)]
    for o in GROUPS:
        test, train_gold = gold[gold.group == o], gold[gold.group != o]
        for model, var in names:
            spec = cfg.variants[var] if var in cfg.variants else cfg.proposal
            if model.startswith("Ridge (rated"):
                m, alpha = fit_ridge_loo(design(train_gold, spec), train_gold[cfg.label].to_numpy())
                feat, info = (lambda f, s=spec: design(f, s)), {"alpha": alpha, "label_config": "rated only"}
            else:
                lab, weight, sid, params = pick_final_config(tuned, model, var, o, settings, RANK_REF if cfg.label_configs == REF_CONFIGS else None)
                m, feat = fit_final(cfg, d, model, var, lab, weight, params, o)
                info = {"label_config": f"{lab} (weight {weight})", **params}
            p = np.clip(m.predict(feat(test)), 0, 1)
            fits[(model, var, o)] = (m, feat, info)
            rows += [(f"{model} | {var}", o, r, y, pp, a) for r, y, pp, a in zip(test.record_id, test[cfg.label], p, test[cfg.activity])]
        for b in cfg.baselines:
            if b["kind"] == "ridge":
                continue
            p = baseline_predict(cfg, b, train_gold, test)
            rows += [(b["name"], o, r, y, pp, a) for r, y, pp, a in zip(test.record_id, test[cfg.label], p, test[cfg.activity])]
    return pd.DataFrame(rows, columns=["name", "outer_test", "record_id", "y", "pred", "activity"]), fits


def criteria_table(cfg, final, name, d):
    """Pass / fail of one model's pooled final-test predictions against the protocol's criteria."""
    c = cfg.criteria
    f = final[final.name == name]
    ref = final[final.name == cfg.reference]
    mean = final[final.name == "mean"]
    m = metrics(f.y, f.pred)
    gmap = group_of(d)
    groups = [gmap[r] for r in f.record_id]
    ci = lambda stat: group_bootstrap(f.y, f.pred, groups, stat)  # noqa: E731
    mae_lo, mae_hi = ci(lambda y, p: np.abs(p - y).mean())
    rows = []

    def add(label, value, minimum, target, ok_min, ok_target, note=""):
        rows.append({"criterion": label, "value": value, "minimum": minimum, "target": target,
                     "verdict": "target met" if ok_target else "minimum met" if ok_min else "NOT MET", "note": note})

    if c["error"][0] == "mae_abs":
        add("MAE", m["MAE"], f"<= {c['error'][1]}", f"<= {c['error'][2]}", m["MAE"] <= c["error"][1], m["MAE"] <= c["error"][2], f"95% interval {mae_lo:.3f}-{mae_hi:.3f}")
    else:
        ratio = m["MAE"] / np.abs(mean.pred - mean.y).mean()
        add("MAE / mean-guess MAE", ratio, f"<= {c['error'][1]}", f"<= {c['error'][2]}", ratio <= c["error"][1], ratio <= c["error"][2], f"MAE {m['MAE']:.3f}, 95% interval {mae_lo:.3f}-{mae_hi:.3f}")
    pmin, ptar, star = c["corr"]
    add("Pearson and Spearman", f"{m['pearson']:.3f} / {m['spearman']:.3f}", f">= {pmin} both", f">= {ptar} / {star}",
        m["pearson"] >= pmin and m["spearman"] >= pmin, m["pearson"] >= ptar and m["spearman"] >= star)
    if len(ref) and name != cfg.reference:
        a = ref.sort_values(["outer_test", "record_id"]).reset_index(drop=True)
        b = f.sort_values(["outer_test", "record_id"]).reset_index(drop=True)
        lo, hi = paired_diff_bootstrap(a.y, a.pred, b.pred, [gmap[r] for r in b.record_id])
        gain = float(np.abs(a.pred - a.y).mean() - np.abs(b.pred - b.y).mean())
        rel = gain / float(np.abs(a.pred - a.y).mean())
        add(f"Beats {cfg.reference}", f"gain {gain:+.3f} ({rel:+.0%})", "interval of the gain excludes 0", f">= {c['beat_gain']:.0%} lower", lo > 0, lo > 0 and rel >= c["beat_gain"], f"95% interval {lo:+.3f} to {hi:+.3f}")
    add("Bias", m["bias"], f"within +-{c['bias'][0]}", f"within +-{c['bias'][1]}", abs(m["bias"]) <= c["bias"][0], abs(m["bias"]) <= c["bias"][1])
    (smin_lo, smin_hi), (st_lo, st_hi) = c["slope"]
    add("Calibration slope", m["calib_slope"], f"{smin_lo}-{smin_hi}", f"{st_lo}-{st_hi}", smin_lo <= m["calib_slope"] <= smin_hi, st_lo <= m["calib_slope"] <= st_hi)
    wmin, wtar = c["band_within"]
    exact_ok = c.get("band_exact") is None or m["band_exact"] >= c["band_exact"]
    add("Rubric bands within one", m["band_within_1"], f">= {wmin:.0%}", f">= {wtar:.0%}" + (f", exact >= {c['band_exact']:.0%}" if c.get("band_exact") else ""),
        m["band_within_1"] >= wmin, m["band_within_1"] >= wtar and exact_ok, f"exact {m['band_exact']:.0%}")
    if c.get("active"):
        act = f[f.activity > 0]
        am = float(np.abs(act.pred - act.y).mean())
        add("MAE, students with activity", am, f"<= {c['active'][0]}", f"<= {c['active'][1]}", am <= c["active"][0], am <= c["active"][1], f"n = {len(act)}")
    return pd.DataFrame(rows), m


# --- Effort: guard layer and invariants ----------------------------------------------------------------------------------

EFFORT_GUARD = {"lines_per_commit": 100, "files_per_commit": 20, "zero_rule": True}  # settings of the earlier protocol, not retuned


def apply_guard(frame, guard=EFFORT_GUARD):
    """Counts are credited only as far as the evidence supports them, before the model sees them: a commit counts only when it
    carries at least `lines_per_commit` lines; files are counted up to `files_per_commit` per commit."""
    f = frame.copy()
    cc = f.E_CC.astype(float)
    f["E_CC"] = np.minimum(cc, f.E_LOC_net_capped.astype(float).clip(lower=0) / guard["lines_per_commit"])
    f["E_FC"] = np.minimum(f.E_FC.astype(float), guard["files_per_commit"] * np.maximum(cc, 1))
    return f


def predict_with(fit, frame, guarded):
    m, feat, _ = fit
    f = apply_guard(frame) if guarded else frame
    p = np.clip(m.predict(feat(f)), 0, 1)
    return np.where(frame.E_CC.to_numpy() == 0, 0.0, p) if guarded else p


EFFORT_CASES = {
    "zero commits": {"E_CC": 0, "E_LOC_net_capped": 0, "E_FC": 0, "E_CT": 0, "E_RD": 0},
    "micro-commit spam": {"E_CC": 200, "E_LOC_net_capped": 200, "E_FC": 2, "E_CT": 0, "E_RD": 0},
    "library dump": {"E_CC": 1, "E_LOC_net_capped": 800, "E_FC": 1000, "E_CT": 0, "E_RD": 0},
    "one huge commit": {"E_CC": 1, "E_LOC_net_capped": 800, "E_FC": 40, "E_CT": 1, "E_RD": 0},
    "many tiny real commits": {"E_CC": 40, "E_LOC_net_capped": 600, "E_FC": 12, "E_CT": 2, "E_RD": 0},
    "typical active student": {"E_CC": 5, "E_LOC_net_capped": 1018, "E_FC": 26, "E_CT": 1, "E_RD": 0},
    "heavy contributor": {"E_CC": 40, "E_LOC_net_capped": 6000, "E_FC": 120, "E_CT": 5, "E_RD": 0},
}


def effort_invariants(fits, model, variant, guarded):
    """(zero_ok, monotone_ok, spam_ok, table) over the five fold models."""
    cases = pd.DataFrame(EFFORT_CASES).T
    per_fold = np.array([predict_with(fits[(model, variant, o)], cases, guarded) for o in GROUPS])  # folds x cases
    table = pd.DataFrame({"mean score": per_fold.mean(axis=0), "min over folds": per_fold.min(axis=0), "max over folds": per_fold.max(axis=0)}, index=cases.index)
    zero_ok = bool(table.loc["zero commits", "max over folds"] <= 0.05)
    spam_ok = bool(table.loc[["micro-commit spam", "library dump"], "max over folds"].max() <= 0.35)
    base = EFFORT_CASES["typical active student"]
    sweeps = {"E_CC": np.arange(1, 61), "E_LOC_net_capped": np.arange(0, 6001, 100), "E_FC": np.arange(0, 121, 2)}
    mono_ok, worst = True, 0.0
    for col, values in sweeps.items():
        frame = pd.DataFrame([{**base, col: v} for v in values])
        for o in GROUPS:
            p = predict_with(fits[(model, variant, o)], frame, guarded)
            drop = float(np.max(p[:-1] - p[1:]))
            worst = max(worst, drop)
            mono_ok &= drop <= 0.005
    table.loc["largest drop when one count rises"] = [worst, worst, worst]
    return zero_ok, bool(mono_ok), spam_ok, table
