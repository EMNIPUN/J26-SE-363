"""Fits and exports the production models of the three regression factors (Effort, Consistency, Task Complexity) as small JSON cards.

    python fit_production.py [effort consistency task_complexity]      (run from ml_lib/; needs pandas, scikit-learn, scipy)

Why this exists: the exp04 notebooks of these factors only plot result files, and two of their selected models use features that are defined nowhere in the repository
(C_early_pace, C_DC_penalty, TC_reach_density), so they cannot be reproduced. Every candidate here uses only columns that the factor's own ``featurize`` returns.

Procedure (fixed here, before looking at results):
- data: the 144 real student-sprints with their rubric rating (reference ratings, written by the assistant: not human ratings); the 175 simulated ones are not used;
- evaluation: the five student-disjoint groups A-E of the project; each group is predicted by a model fitted on the other four; ridge penalty by leave-one-out inside the training rows;
- every candidate and the single-feature baseline are evaluated the same way; the paired grouped bootstrap (resampling students) gives the interval of the MAE gain over the baseline;
- Effort candidates must also pass the earlier protocol's invariants on the final model (zero commits <= 0.05, micro-commit spam and library dump <= 0.35, more work never
  lowers the score); the shipped model is the lowest-MAE candidate that passes them, and if none passes the lowest-MAE one ships with the failure written in its card;
- otherwise the shipped model is the candidate with the lowest out-of-fold MAE; the card states whether it beats the baseline with an interval above 0 (if not, it ships anyway as the proposal's
  design and says so);
- Effort keeps the earlier protocol's guard (commits credited only with enough lines, files capped per commit, zero commits give zero) and its invariant checks on the final model.

The exported card is evaluated without scikit-learn by factor_models/evidence/linear_model.py.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from evidence.linear_model import LinearCard  # noqa: E402
from core import SEED, group_bootstrap, log_signed, metrics, paired_diff_bootstrap  # noqa: E402
from retrain import EFFORT_CASES, EFFORT_GUARD, apply_guard  # noqa: E402

FM = HERE.parent
ALPHAS = np.logspace(-2, 3, 21)

FACTORS = {
    "effort": {
        "folder": "01_effort", "dataset": "effort_dataset.csv", "label": "rater_effort", "version": "effort-linear/1", "guard": True,
        "candidates": {
            "log5 (proposal)": [("E_CC", "log"), ("E_LOC_net_capped", "log"), ("E_FC", "log"), ("E_CT", "log"), ("E_RD", "log")],
            "log4 (no review discussions)": [("E_CC", "log"), ("E_LOC_net_capped", "log"), ("E_FC", "log"), ("E_CT", "log")],
            "log3 (commits, lines, files)": [("E_CC", "log"), ("E_LOC_net_capped", "log"), ("E_FC", "log")],
        },
        "baseline": ("commit count (log, linear)", [("E_CC", "log")]),
        # extra candidates: the same features with a stricter cap on files credited per commit (the earlier protocol's guard allowed 20; it does not pass its own library-dump invariant)
        "guard_variants": {"files<=10": {**EFFORT_GUARD, "files_per_commit": 10}, "files<=5": {**EFFORT_GUARD, "files_per_commit": 5}, "files<=3": {**EFFORT_GUARD, "files_per_commit": 3}},
    },
    "consistency": {
        "folder": "02_consistency", "dataset": "consistency_dataset.csv", "label": "rater_consistency", "version": "consistency-linear/1", "guard": False,
        "candidates": {
            "proposal 4": [("C_AWR", "raw"), ("C_DC", "one_minus"), ("C_LI_norm", "one_minus"), ("C_CV_norm", "one_minus")],
            "proposal 4 + first active day": [("C_AWR", "raw"), ("C_DC", "one_minus"), ("C_LI_norm", "one_minus"), ("C_CV_norm", "one_minus"), ("C_first_active_day", "raw")],
            "active days + first active day": [("C_AWR", "raw"), ("C_first_active_day", "raw")],
        },
        "baseline": ("active days (linear)", [("C_AWR", "raw")]),
    },
    "task_complexity": {
        "folder": "05_task_complexity", "dataset": "task_complexity_dataset.csv", "label": "rater_task_complexity", "version": "task-complexity-linear/1", "guard": False,
        "candidates": {
            "proposal 5": [("TC_SP", "raw"), ("TC_SC", "raw"), ("TC_FI", "log"), ("TC_DR", "log"), ("TC_CB", "log")],
            "proposal 5 + story points of the sprint": [("TC_SP", "raw"), ("TC_SC", "raw"), ("TC_FI", "log"), ("TC_DR", "log"), ("TC_CB", "log"), ("TC_SP_total", "log")],
            "board only (SP, SC, SP total)": [("TC_SP", "raw"), ("TC_SC", "raw"), ("TC_SP_total", "log")],
        },
        "baseline": ("story points of the sprint (log, linear)", [("TC_SP_total", "log")]),
    },
}


ZERO_RULES = {"effort": {"column": "E_CC", "equals": 0}, "consistency": {"column": "C_no_activity", "equals": 1}}  # a student who did nothing scores 0


def tf(x, kind):
    x = np.asarray(x, float)
    return {"raw": x, "log": log_signed(x), "one_minus": 1.0 - x}[kind]


def design(frame, spec):
    return np.column_stack([tf(frame[c].to_numpy(dtype=float), t) for c, t in spec])


def fit_ridge(X, y):
    """Median imputation, standardisation, ridge with the penalty chosen by leave-one-out (closed form). Returns the parameters as plain lists."""
    med = np.nanmedian(X, axis=0)
    med = np.where(np.isnan(med), 0.0, med)
    Xi = np.where(np.isnan(X), med, X)
    mean, scale = Xi.mean(0), Xi.std(0)
    scale = np.where(scale < 1e-12, 1.0, scale)
    Z = (Xi - mean) / scale
    yc = y - y.mean()
    n, p = Z.shape
    best, best_err = None, np.inf
    for a in ALPHAS:
        A = np.linalg.solve(Z.T @ Z + a * np.eye(p), Z.T)
        H = Z @ A + 1.0 / n
        res = (y - (y.mean() + Z @ (A @ yc))) / (1.0 - np.diag(H))
        err = float(np.abs(res).mean())
        if err < best_err:
            best, best_err = a, err
    coef = np.linalg.solve(Z.T @ Z + best * np.eye(p), Z.T @ yc)
    return {"medians": med.tolist(), "mean": mean.tolist(), "scale": scale.tolist(), "coef": coef.tolist(), "intercept": float(y.mean()), "alpha": float(best)}


def predict(model, X):
    med, mean, scale, coef = (np.array(model[k]) for k in ("medians", "mean", "scale", "coef"))
    Xi = np.where(np.isnan(X), med, X)
    return model["intercept"] + ((Xi - mean) / scale) @ coef


def prepare(frame, guarded):
    if isinstance(guarded, dict):
        return apply_guard(frame, guarded)
    return apply_guard(frame) if guarded else frame


def cross_validate(real, spec, label, guarded, zero_col=None):
    """Out-of-fold predictions for the five student-disjoint groups."""
    frame = prepare(real, guarded)
    X, y = design(frame, spec), real[label].to_numpy(dtype=float)
    pred = np.zeros(len(y))
    for g in sorted(real.group.unique()):
        te = (real.group == g).to_numpy()
        pred[te] = np.clip(predict(fit_ridge(X[~te], y[~te]), X[te]), 0, 1)
    if zero_col:
        pred = np.where(real[zero_col].to_numpy() == 0, 0.0, pred)
    return y, pred


def invariants(card):
    """(zero_ok, spam_ok, monotone_ok, worst drop, scores) of an Effort card, on the earlier protocol's cases."""
    lc = LinearCard(card)
    sc = {k: lc.predict(v)[0] for k, v in EFFORT_CASES.items() if k in ("zero commits", "micro-commit spam", "library dump")}
    base = EFFORT_CASES["typical active student"]
    worst = 0.0
    for col, values in (("E_CC", range(1, 61)), ("E_LOC_net_capped", range(0, 6001, 100)), ("E_FC", range(0, 121, 2))):
        ps = [lc.predict({**base, col: v})[0] for v in values]
        worst = max(worst, max(a - b for a, b in zip(ps, ps[1:])))
    return sc["zero commits"] <= 0.05, max(sc["micro-commit spam"], sc["library dump"]) <= 0.35, worst <= 0.005, worst, sc


def card_for(name, cfg, spec, real, label, preds, best_name, guard):
    frame = prepare(real, guard)
    X, y = design(frame, spec), real[label].to_numpy(dtype=float)
    model = fit_ridge(X, y)
    resid = y - preds[best_name]
    return {"factor": name, "version": cfg["version"], "model": "ridge (median imputation, standardised, penalty by leave-one-out)", "candidate": best_name,
            "features": [{"name": c, "transform": t} for c, t in spec], **model, "guard": (guard if isinstance(guard, dict) else (EFFORT_GUARD if guard else None)), "zero_rule": ZERO_RULES.get(name),
            "residual_quantiles": [float(np.percentile(resid, 10)), float(np.percentile(resid, 90))]}, y


def main(names):
    out = {}
    for name in names:
        cfg = FACTORS[name]
        d = pd.read_csv(FM / cfg["folder"] / "training" / "dataset" / cfg["dataset"], low_memory=False)
        real = d[d.source == "real"].reset_index(drop=True)
        label = cfg["label"]
        zero_col = "E_CC" if name in ("effort", "consistency") else None
        groups = real["student_id"].to_numpy() if "student_id" in real else real.group.to_numpy()
        bname, bspec = cfg["baseline"]
        cand = {c: (spec, cfg["guard"]) for c, spec in cfg["candidates"].items()}
        for gname, g in cfg.get("guard_variants", {}).items():
            for c in ("log5 (proposal)", "log4 (no review discussions)"):
                cand[f"{c} | {gname}"] = (cfg["candidates"][c], g)
        yb, pb = cross_validate(real, bspec, label, False, zero_col)
        rows, preds = [], {}
        for cname, (spec, guard) in cand.items():
            y, p = cross_validate(real, spec, label, guard, zero_col)
            preds[cname] = p
            m = metrics(y, p)
            lo, hi = paired_diff_bootstrap(y, pb, p, groups, n=2000)
            rows.append({"candidate": cname, "MAE": m["MAE"], "Pearson": m["pearson"], "Spearman": m["spearman"], "band within 1": m["band_within_1"], "gain over baseline": float(np.abs(pb - y).mean() - np.abs(p - y).mean()),
                         "gain 95% low": lo, "gain 95% high": hi})
        tab = pd.DataFrame(rows).set_index("candidate")
        mb = metrics(yb, pb)
        print(f"\n== {name}: baseline {bname}: MAE {mb['MAE']:.4f}, Pearson {mb['pearson']:.3f}; mean predictor MAE {np.abs(yb - yb.mean()).mean():.4f}")
        print(tab.round(4).to_string())
        cards = {c: card_for(name, cfg, spec, real, label, preds, c, guard) for c, (spec, guard) in cand.items()}
        if name == "effort":
            inv = {c: invariants(cards[c][0]) for c, _ in cards.items()}
            tab["invariants ok"] = [all(inv[c][:3]) for c in tab.index]
            tab["library dump / spam max"] = [max(inv[c][4]["micro-commit spam"], inv[c][4]["library dump"]) for c in tab.index]
            print(tab[["MAE", "invariants ok", "library dump / spam max"]].round(4).to_string())
            cfg_guard_note = "files per commit credited: " + str(cards[tab[tab["invariants ok"]].MAE.idxmin()][0]["guard"]["files_per_commit"]) if tab["invariants ok"].any() else "no candidate passes the invariants"
            print(cfg_guard_note)
            ok = tab[tab["invariants ok"]]
            best = ok.MAE.idxmin() if len(ok) else tab.MAE.idxmin()
        else:
            best = tab.MAE.idxmin()
        card, y = cards[best]
        card.update({"cv": {"MAE": float(tab.loc[best, "MAE"]), "Pearson": float(tab.loc[best, "Pearson"]), "Spearman": float(tab.loc[best, "Spearman"]), "band_within_1": float(tab.loc[best, "band within 1"]),
                            "baseline": bname, "baseline_MAE": float(mb["MAE"]), "gain_over_baseline": float(tab.loc[best, "gain over baseline"]),
                            "gain_95": [float(tab.loc[best, "gain 95% low"]), float(tab.loc[best, "gain 95% high"])], "beats_baseline": bool(tab.loc[best, "gain 95% low"] > 0),
                            "mean_predictor_MAE": float(np.abs(yb - yb.mean()).mean()), "n": int(len(y)), "folds": "5 student-disjoint groups A-E"},
                     "trained_on": f"{len(y)} real student-sprints rated on the project rubric by the assistant (not human ratings)", "seed": SEED})
        if name == "effort":
            z, sp, mo, worst, sc = invariants(card)
            card["invariants"] = {"zero_commits_ok": bool(z), "spam_and_dump_ok": bool(sp), "monotone_ok": bool(mo), "largest_drop": float(worst), "scores": {k: float(v) for k, v in sc.items()},
                                  "all_candidates": {c: bool(all(inv[c][:3])) for c in inv}}
        out[name] = (card, tab)
        folder = FM / cfg["folder"] / "model"
        folder.mkdir(exist_ok=True)
        (folder / f"{name}_model.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
        (folder / "candidates.csv").write_text(tab.to_csv(), encoding="utf-8")
        print(f"-> {best}; beats baseline: {card['cv']['beats_baseline']}; written to {folder}")
    return out


if __name__ == "__main__":
    main(sys.argv[1:] or list(FACTORS))
