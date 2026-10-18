"""Step 6: marks for every record from 20 rated records (anchor-based label propagation).

For each factor, the assessor's rubric ratings of the 20 ground-truth records (averaged over the
factor's criteria and rescaled to 0-1, exactly as the proposal's Factor_GT) are regressed on that
factor's features with ridge regression. The penalty is chosen by leave-one-out cross-validation,
so every reported error is measured on a record the model did not see. The fitted model then
marks every real and synthetic record; a bootstrap over the 20 anchors gives each mark a 90%
interval, and records whose features fall outside the anchors' range are flagged.

Behavioral Pattern is the proposal's rule set applied to the propagated scores and checked against
the assessor's pattern judgement. Fusion weights are learned from the assessor's overall marks
(non-negative least squares), as in proposal 3.1.9.

    python scripts/06_propagate_marks.py
"""

import csv
import json
import math

import numpy as np
from scipy.optimize import nnls
from scipy.stats import pearsonr, spearmanr

from identity import DATASET

GT = DATASET / "ground_truth"
BOOTSTRAP = 1000
ALPHAS = np.logspace(-2, 3, 26)
RNG = np.random.default_rng(42)

LOG = lambda x: math.copysign(math.log1p(abs(x)), x)  # noqa: E731  (skewed counts and line totals)
INV = lambda x: 1 - x  # noqa: E731

# factor -> (features with their transform, rubric criteria in human_ratings.csv)
FACTORS = {
    "E": ([("E_CC", LOG), ("E_LOC_net_capped", LOG), ("E_FC", LOG), ("E_CT", None), ("E_RD", LOG)],
          ["E_responsibility_engagement", "E_work_investment", "E_responsibility_fulfillment", "E_initiative", "E_persistence"]),
    "C": ([("C_AWR", None), ("C_DC", INV), ("C_LI_norm", INV), ("C_CV_norm", INV)],
          ["C_steady_engagement", "C_early_contribution", "C_continuity", "C_predictable_rhythm"]),
    "RF": ([("RF_llm_score", None), ("RF_completion_rate", None), ("RF_ac_ratio", None), ("RF_untracked_ratio", INV)],
           ["RF_task_alignment", "RF_acceptance_criteria", "RF_completeness"]),
    "Co": ([("Co_PRC_depth", None), ("Co_IC_depth", None), ("Co_MC", LOG), ("Co_PCount", LOG), ("Co_CCount", LOG), ("Co_IR", None),
            ("Co_shared_file_ratio", None), ("Co_prs_merged_for_others", LOG)],
           ["Co_review_engagement", "Co_discussion_substance", "Co_team_interaction", "Co_follow_through"]),
    "TC": ([("TC_SP", None), ("TC_SC", None), ("TC_FI", LOG), ("TC_DR", LOG), ("TC_CB", None)],
           ["TC_technical_difficulty", "TC_scope_breadth", "TC_dependency_impact", "TC_architectural_impact", "TC_uncertainty"]),
    "KO": ([("KO_survival", None), ("KO_primary_owner_share", None), ("KO_snippet_candidates", LOG)],
           ["KO_authorship_depth", "KO_code_durability", "KO_self_maintenance"]),
}
ADDITIVE = ["E", "C", "RF", "Co", "TC", "KO"]
BP_MODIFIER = {"consistent_deep_contributor": 1.15, "last_minute_rusher": 0.925, "reviewer_coordinator": 1.025,
               "burst_worker": 0.975, "free_rider": 0.825, "no_specific_pattern": 1.0}


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def value(r, name, fn):
    v = r.get(name, "")
    if v in ("", None):
        return math.nan
    x = float(v)
    return fn(x) if fn else x


class Factor:
    """Standardise with the real cohort, impute with the cohort median, then ridge."""

    def __init__(self, features, cohort):
        self.features = features
        raw = np.array([[value(r, n, fn) for n, fn in features] for r in cohort])
        self.median = np.nanmedian(raw, axis=0)
        self.median = np.where(np.isnan(self.median), 0.0, self.median)
        filled = np.where(np.isnan(raw), self.median, raw)
        self.mu, self.sd = filled.mean(axis=0), filled.std(axis=0)
        self.sd[self.sd == 0] = 1.0

    def matrix(self, records):
        raw = np.array([[value(r, n, fn) for n, fn in self.features] for r in records])
        missing = np.isnan(raw)
        return (np.where(missing, self.median, raw) - self.mu) / self.sd, missing


def ridge(X, y, alpha):
    Xc = np.column_stack([np.ones(len(X)), X])
    penalty = alpha * np.eye(Xc.shape[1])
    penalty[0, 0] = 0  # the intercept is not shrunk
    return np.linalg.solve(Xc.T @ Xc + penalty, Xc.T @ y)


def predict(beta, X):
    return np.clip(beta[0] + X @ beta[1:], 0, 1)


def loo(X, y, alpha):
    out = np.empty(len(y))
    for i in range(len(y)):
        keep = np.arange(len(y)) != i
        out[i] = predict(ridge(X[keep], y[keep], alpha), X[i:i + 1])[0]
    return out


HIGH_FLOOR = 0.35
PROPOSAL_THRESHOLDS = {"high": {"E": 0.7, "C": 0.7, "Co": 0.7}, "low": {"E": 0.3, "C": 0.3, "Co": 0.3}, "low_e_coordinator": 0.4}


def bp_pattern(s, bimodal, t):
    """Proposal 3.1.7, applied to the propagated scores with thresholds ``t``."""
    e, c, co = s["E"], s["C"], s["Co"]
    hi, lo = t["high"], t["low"]
    if e < lo["E"] and co < lo["Co"]:
        return "free_rider"
    if e > hi["E"] and bimodal:
        return "burst_worker"
    if e > hi["E"] and c > hi["C"]:
        return "consistent_deep_contributor"
    if e > hi["E"] and c < lo["C"]:
        return "last_minute_rusher"
    if e < t["low_e_coordinator"] and co > hi["Co"]:
        return "reviewer_coordinator"
    return "no_specific_pattern"


def cohort_thresholds(scores, q_high=70):
    """Thresholds for the proposal's rules on the rubric-calibrated scale.

    "Low" keeps the proposal's absolute 0.3 (and 0.4 for the coordinator's effort): doing almost
    nothing is low in any cohort. "High" is relative - the cohort's 70th percentile among students
    with some work - because calibrated scores rarely reach 0.7, but never below 0.35 (about 2.4
    of 5), so a cohort in which nobody reviews does not crown a reviewer. Set from the score
    distribution, not from the assessor's pattern labels."""
    active = [s for s in scores if s["E"] > 0.05]
    pct = lambda k: float(np.percentile([s[k] for s in active], q_high))  # noqa: E731
    return {"high": {k: round(max(HIGH_FLOOR, pct(k)), 4) for k in ("E", "C", "Co")},
            "low": dict(PROPOSAL_THRESHOLDS["low"]), "low_e_coordinator": PROPOSAL_THRESHOLDS["low_e_coordinator"]}


def kappa(a, b):
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(lab) / n) * (b.count(lab) / n) for lab in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    real = read(DATASET / "features_real.csv")
    synthetic = read(DATASET / "synthetic_dataset.csv")
    ratings = read(GT / "human_ratings.csv")
    by_id = {r["record_id"]: r for r in real}
    anchors = [by_id[g["record_id"]] for g in ratings]
    report = {"n_anchors": len(anchors), "factors": {}}
    scores_real = {r["record_id"]: {} for r in real}
    scores_syn = {r["synthetic_id"]: {} for r in synthetic}
    loo_scores = {}  # factor -> leave-one-out prediction for each anchor

    for name, (features, criteria) in FACTORS.items():
        factor = Factor(features, real)
        Xa, _ = factor.matrix(anchors)
        y = np.array([(np.mean([float(g[c]) for c in criteria]) - 1) / 4 for g in ratings])
        errors = [np.mean((loo(Xa, y, a) - y) ** 2) for a in ALPHAS]
        alpha = float(ALPHAS[int(np.argmin(errors))])
        cv = loo(Xa, y, alpha)
        loo_scores[name] = cv
        baseline = np.array([np.mean(np.delete(y, i)) for i in range(len(y))])
        beta = ridge(Xa, y, alpha)
        boot = []
        for _ in range(BOOTSTRAP):
            idx = RNG.integers(0, len(y), len(y))
            boot.append(ridge(Xa[idx], y[idx], alpha))
        lo_range, hi_range = Xa.min(axis=0), Xa.max(axis=0)
        span = hi_range - lo_range

        def mark(records, key, store):
            X, missing = factor.matrix(records)
            point = predict(beta, X)
            draws = np.array([predict(b, X) for b in boot])
            lo, hi = np.percentile(draws, 5, axis=0), np.percentile(draws, 95, axis=0)
            used = np.abs(beta[1:]) > 0.01  # a feature the model ignores cannot make it extrapolate
            outside = (((X < lo_range - 0.25 * span) | (X > hi_range + 0.25 * span)) & used).any(axis=1)
            for r, p, a, b, o, m in zip(records, point, lo, hi, outside, missing.all(axis=1)):
                store[r[key]][name] = float(p)
                store[r[key]][f"{name}_lo"] = float(a)
                store[r[key]][f"{name}_hi"] = float(b)
                store[r[key]][f"{name}_extrapolated"] = int(bool(o))

        mark(real, "record_id", scores_real)
        mark(synthetic, "synthetic_id", scores_syn)
        r_p = pearsonr(cv, y)[0] if np.std(cv) > 0 else float("nan")
        r_s = spearmanr(cv, y)[0] if np.std(cv) > 0 else float("nan")
        report["factors"][name] = {
            "features": [n for n, _ in features], "criteria": criteria, "alpha": alpha,
            "intercept": round(float(beta[0]), 4),
            "coefficients": {n: round(float(b), 4) for (n, _), b in zip(features, beta[1:])},
            "loocv_mae": round(float(np.mean(np.abs(cv - y))), 4),
            "loocv_rmse": round(float(np.sqrt(np.mean((cv - y) ** 2))), 4),
            "loocv_pearson": round(float(r_p), 4), "loocv_spearman": round(float(r_s), 4),
            "baseline_mae_predict_mean": round(float(np.mean(np.abs(baseline - y))), 4),
            "target_mean": round(float(y.mean()), 4), "target_sd": round(float(y.std()), 4),
        }

    # --- Behavioral Pattern: rules on propagated scores vs the assessor's judgement ---------------
    thresholds = cohort_thresholds(list(scores_real.values()))
    judged = [g["BP_pattern"] for g in ratings]
    comparison = {}
    for label, t in (("proposal_fixed_thresholds", PROPOSAL_THRESHOLDS), ("cohort_percentile_thresholds", thresholds)):
        rule = [bp_pattern(scores_real[g["record_id"]], by_id[g["record_id"]]["C_bimodal"] == "1", t) for g in ratings]
        comparison[label] = {"thresholds": t, "agreement": round(sum(a == b for a, b in zip(rule, judged)) / len(judged), 4),
                             "cohen_kappa": round(kappa(rule, judged), 4),
                             "pairs": [{"record_id": g["record_id"], "rule": a, "assessor": b} for g, a, b in zip(ratings, rule, judged)]}
    for r in real:
        scores_real[r["record_id"]]["BP_pattern"] = bp_pattern(scores_real[r["record_id"]], r.get("C_bimodal") == "1", thresholds)
    for r in synthetic:
        scores_syn[r["synthetic_id"]]["BP_pattern"] = bp_pattern(scores_syn[r["synthetic_id"]], r.get("C_bimodal") == "1", thresholds)
    report["behavioral_pattern"] = comparison | {"used_for_marks": "cohort_percentile_thresholds"}

    # --- Fusion weights from the assessor's overall marks (NNLS, sum to 1) -----------------------
    F = np.array([[(np.mean([float(g[c]) for c in FACTORS[f][1]]) - 1) / 4 for f in ADDITIVE] for g in ratings])
    overall = np.array([float(g["overall_mark"]) / 100 / BP_MODIFIER[g["BP_pattern"]] for g in ratings])
    w, _ = nnls(F, overall)
    w = w / w.sum()
    loo_fused = []
    for i in range(len(overall)):
        keep = np.arange(len(overall)) != i
        wi, _ = nnls(F[keep], overall[keep])
        wi = wi / wi.sum() if wi.sum() else np.full(len(ADDITIVE), 1 / len(ADDITIVE))
        loo_fused.append(F[i] @ wi)
    equal = F.mean(axis=1)
    report["fusion"] = {
        "weights": {f: round(float(x), 4) for f, x in zip(ADDITIVE, w)},
        "loocv_mae_learned_weights_0_100": round(float(np.mean(np.abs(np.array(loo_fused) - overall)) * 100), 2),
        "mae_equal_weights_0_100": round(float(np.mean(np.abs(equal - overall)) * 100), 2),
        "bp_modifiers": BP_MODIFIER,
    }

    def fuse(s):
        base = sum(w[i] * s[f] for i, f in enumerate(ADDITIVE))
        return round(min(100.0, max(0.0, 100 * BP_MODIFIER[s["BP_pattern"]] * base)), 2)

    for store in (scores_real, scores_syn):
        for s in store.values():
            s["BP_modifier"] = BP_MODIFIER[s["BP_pattern"]]
            s["final_mark"] = fuse(s)

    # end to end, leave one out: factor scores, weights and pattern all come from the other 19
    end_to_end = []
    for i, g in enumerate(ratings):
        keep = np.arange(len(ratings)) != i
        wi, _ = nnls(F[keep], overall[keep])
        wi = wi / wi.sum() if wi.sum() else np.full(len(ADDITIVE), 1 / len(ADDITIVE))
        s_i = {f: float(loo_scores[f][i]) for f in FACTORS}
        pattern = bp_pattern(s_i, by_id[g["record_id"]]["C_bimodal"] == "1", thresholds)
        end_to_end.append(min(100.0, 100 * BP_MODIFIER[pattern] * sum(wi[k] * s_i[f] for k, f in enumerate(ADDITIVE))))
    om_all = np.array([float(g["overall_mark"]) for g in ratings])
    e2e = np.array(end_to_end)
    report["final_mark_loocv"] = {"mae_0_100": round(float(np.mean(np.abs(e2e - om_all))), 2),
                                  "rmse_0_100": round(float(np.sqrt(np.mean((e2e - om_all) ** 2))), 2),
                                  "pearson": round(float(pearsonr(e2e, om_all)[0]), 4),
                                  "spearman": round(float(spearmanr(e2e, om_all)[0]), 4),
                                  "mean_bias_0_100": round(float(np.mean(e2e - om_all)), 2)}

    # final mark of the 20 anchors against the assessor's overall mark (in-sample, for reference)
    fm = np.array([scores_real[g["record_id"]]["final_mark"] for g in ratings])
    om = np.array([float(g["overall_mark"]) for g in ratings])
    report["final_mark_vs_assessor_overall"] = {"mae": round(float(np.mean(np.abs(fm - om))), 2),
                                                "pearson": round(float(pearsonr(fm, om)[0]), 4),
                                                "note": "uses factor models fitted on these same anchors; LOOCV figures above are the honest estimate"}
    (DATASET / "marks_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump({"real": scores_real, "synthetic": scores_syn}, open(DATASET / "private" / "scores_cache.json", "w"))

    # --- final dataset ------------------------------------------------------------------------------
    gt = {g["record_id"]: g for g in ratings}
    score_cols = [c for f in FACTORS for c in (f"{f}_score", f"{f}_score_lo", f"{f}_score_hi", f"{f}_extrapolated")]
    feature_cols = [c for c in real[0] if c not in ("record_id", "team_id", "sprint_id", "student_id", "project_domain", "team_size")]
    header = (["source", "record_id", "team_id", "sprint_id", "student_id", "project_domain", "team_size", "profile_or_parent"]
              + feature_cols + score_cols + ["BP_pattern", "BP_modifier", "final_mark", "in_ground_truth"]
              + [f"GT_{f}" for f in FACTORS] + ["GT_BP_pattern", "GT_overall_mark"])

    def row(src, r, s, key):
        out = {"source": src, "record_id": r[key], "team_id": r.get("team_id", ""), "sprint_id": r.get("sprint_id", ""),
               "student_id": r.get("student_id", ""), "project_domain": r.get("project_domain", ""), "team_size": r.get("team_size", ""),
               "profile_or_parent": r.get("profile", "") if src == "synthetic" else ""}
        out.update({c: r.get(c, "") for c in feature_cols})
        for f in FACTORS:
            out[f"{f}_score"] = round(s[f], 4)
            out[f"{f}_score_lo"] = round(s[f"{f}_lo"], 4)
            out[f"{f}_score_hi"] = round(s[f"{f}_hi"], 4)
            out[f"{f}_extrapolated"] = s[f"{f}_extrapolated"]
        out.update({"BP_pattern": s["BP_pattern"], "BP_modifier": s["BP_modifier"], "final_mark": s["final_mark"]})
        g = gt.get(r[key])
        out["in_ground_truth"] = int(bool(g))
        for f in FACTORS:
            out[f"GT_{f}"] = round((np.mean([float(g[c]) for c in FACTORS[f][1]]) - 1) / 4, 4) if g else ""
        out["GT_BP_pattern"] = g["BP_pattern"] if g else ""
        out["GT_overall_mark"] = g["overall_mark"] if g else ""
        return out

    with open(DATASET / "final_dataset.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in real:
            writer.writerow(row("real", r, scores_real[r["record_id"]], "record_id"))
        for r in synthetic:
            writer.writerow(row("synthetic", r, scores_syn[r["synthetic_id"]], "synthetic_id"))
    summary = {f: {k: v[k] for k in ("alpha", "loocv_mae", "loocv_pearson", "baseline_mae_predict_mean")} for f, v in report["factors"].items()}
    bp_summary = {k: {"agreement": v["agreement"], "kappa": v["cohen_kappa"]} for k, v in report["behavioral_pattern"].items() if isinstance(v, dict)}
    print(json.dumps({"factors": summary, "bp": bp_summary, "fusion": report["fusion"], "final_mark_loocv": report["final_mark_loocv"],
                      "final_vs_overall_in_sample": report["final_mark_vs_assessor_overall"]}, indent=1))


if __name__ == "__main__":
    main()
