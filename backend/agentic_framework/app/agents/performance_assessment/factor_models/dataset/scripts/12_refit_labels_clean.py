"""Step 12: refit the label model on the clean features and mark every real and simulated record.

The 20 rated records and their ratings do not change; what changes is the features that predict them. For each factor the
ratings (mean of the factor's criteria, rescaled to 0-1) are regressed on the clean features with ridge regression (penalty by
leave-one-out), exactly as in step 6, and the fitted model marks every real and simulated record with a 90% interval. Records
whose features fall outside what the 20 anchors cover are flagged, which is most of what to expect for simulated students.

Written to ``clean/final_dataset_clean.csv`` and ``clean/marks_report_clean.json`` (with the earlier dirty-feature figures
beside the new ones). Simulated students' marks are estimates from this model, never ratings.

    python scripts/12_refit_labels_clean.py
"""

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import nnls
from scipy.stats import pearsonr, spearmanr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from identity import DATASET  # noqa: E402

spec = importlib.util.spec_from_file_location("propagate06", HERE / "06_propagate_marks.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

CLEAN = DATASET / "clean"
LOG, INV = P.LOG, P.INV
FACTORS = {
    "E": ([("E_CC", LOG), ("E_LOC_net_capped", LOG), ("E_FC", LOG), ("E_CT", None), ("E_RD", LOG)], P.FACTORS["E"][1]),
    "C": P.FACTORS["C"],
    "RF": P.FACTORS["RF"],
    # shared-file ratio left out: it depends on what teammates do, not on the student
    "Co": ([("Co_PRC_depth", None), ("Co_IC_depth", None), ("Co_MC", LOG), ("Co_PCount", LOG), ("Co_CCount", LOG), ("Co_IR", None),
            ("Co_prs_merged_for_others", LOG)], P.FACTORS["Co"][1]),
    "TC": P.FACTORS["TC"],
    "KO": P.FACTORS["KO"],
}
ADDITIVE = P.ADDITIVE


def main():
    real = P.read(CLEAN / "features_real_clean.csv")
    sim = P.read(CLEAN / "features_simulated_clean.csv") if (CLEAN / "features_simulated_clean.csv").exists() else P.read(DATASET / "synthetic_students" / "out" / "features_simulated_clean.csv")
    classes = {r["student_id"]: r["behaviour_class"] for r in P.read(DATASET / "synthetic_students" / "out" / "students_simulated.csv")}
    ratings = P.read(P.GT / "human_ratings.csv")
    by_id = {r["record_id"]: r for r in real}
    anchors = [by_id[g["record_id"]] for g in ratings]
    old = json.loads((DATASET / "marks_report.json").read_text(encoding="utf-8"))
    report = {"n_anchors": len(anchors), "factors": {}}
    scores = {"real": {r["record_id"]: {} for r in real}, "sim": {r["record_id"]: {} for r in sim}}
    loo_scores = {}

    for name, (features, criteria) in FACTORS.items():
        factor = P.Factor(features, real)
        Xa, _ = factor.matrix(anchors)
        y = np.array([(np.mean([float(g[c]) for c in criteria]) - 1) / 4 for g in ratings])
        errors = [np.mean((P.loo(Xa, y, a) - y) ** 2) for a in P.ALPHAS]
        alpha = float(P.ALPHAS[int(np.argmin(errors))])
        cv = P.loo(Xa, y, alpha)
        loo_scores[name] = cv
        baseline = np.array([np.mean(np.delete(y, i)) for i in range(len(y))])
        beta = P.ridge(Xa, y, alpha)
        boot = []
        for _ in range(P.BOOTSTRAP):
            idx = P.RNG.integers(0, len(y), len(y))
            boot.append(P.ridge(Xa[idx], y[idx], alpha))
        lo_range, hi_range = Xa.min(axis=0), Xa.max(axis=0)
        span = hi_range - lo_range

        for group, records in (("real", real), ("sim", sim)):
            X, _ = factor.matrix(records)
            point = P.predict(beta, X)
            draws = np.array([P.predict(b, X) for b in boot])
            lo, hi = np.percentile(draws, 5, axis=0), np.percentile(draws, 95, axis=0)
            used = np.abs(beta[1:]) > 0.01
            outside = (((X < lo_range - 0.25 * span) | (X > hi_range + 0.25 * span)) & used).any(axis=1)
            for r, p, a, b, o in zip(records, point, lo, hi, outside):
                s = scores[group][r["record_id"]]
                s[name], s[f"{name}_lo"], s[f"{name}_hi"], s[f"{name}_extrapolated"] = float(p), float(a), float(b), int(bool(o))
        r_p = pearsonr(cv, y)[0] if np.std(cv) > 0 else float("nan")
        old_f = old["factors"].get(name, {})
        report["factors"][name] = {
            "features": [n for n, _ in features], "alpha": alpha,
            "loocv_mae": round(float(np.mean(np.abs(cv - y))), 4), "loocv_pearson": round(float(r_p), 4),
            "baseline_mae_predict_mean": round(float(np.mean(np.abs(baseline - y))), 4),
            "coefficients": {n: round(float(b), 4) for (n, _), b in zip(features, beta[1:])},
            "earlier_dirty_features": {"loocv_mae": old_f.get("loocv_mae"), "loocv_pearson": old_f.get("loocv_pearson")},
            "simulated_records_outside_anchor_range": round(float(np.mean([scores["sim"][r["record_id"]][f"{name}_extrapolated"] for r in sim])), 3),
        }

    # Behavioral Pattern on the clean scores
    thresholds = P.cohort_thresholds(list(scores["real"].values()))
    judged = [g["BP_pattern"] for g in ratings]
    rule = [P.bp_pattern(scores["real"][g["record_id"]], by_id[g["record_id"]]["C_bimodal"] == "1", thresholds) for g in ratings]
    report["behavioral_pattern"] = {"thresholds": thresholds, "agreement": round(sum(a == b for a, b in zip(rule, judged)) / len(judged), 4),
                                    "cohen_kappa": round(P.kappa(rule, judged), 4)}
    for group, records in (("real", real), ("sim", sim)):
        for r in records:
            scores[group][r["record_id"]]["BP_pattern"] = P.bp_pattern(scores[group][r["record_id"]], r.get("C_bimodal") == "1", thresholds)

    # fusion weights from the assessor's overall marks
    F = np.array([[(np.mean([float(g[c]) for c in FACTORS[f][1]]) - 1) / 4 for f in ADDITIVE] for g in ratings])
    overall = np.array([float(g["overall_mark"]) / 100 / P.BP_MODIFIER[g["BP_pattern"]] for g in ratings])
    w, _ = nnls(F, overall)
    w = w / w.sum()
    report["fusion"] = {"weights": {f: round(float(x), 4) for f, x in zip(ADDITIVE, w)}, "earlier_weights": old["fusion"]["weights"]}

    def fuse(s):
        return round(min(100.0, max(0.0, 100 * P.BP_MODIFIER[s["BP_pattern"]] * sum(w[i] * s[f] for i, f in enumerate(ADDITIVE)))), 2)

    for group in scores.values():
        for s in group.values():
            s["BP_modifier"] = P.BP_MODIFIER[s["BP_pattern"]]
            s["final_mark"] = fuse(s)

    # end to end, leave one out
    e2e = []
    for i, g in enumerate(ratings):
        keep = np.arange(len(ratings)) != i
        wi, _ = nnls(F[keep], overall[keep])
        wi = wi / wi.sum() if wi.sum() else np.full(len(ADDITIVE), 1 / len(ADDITIVE))
        s_i = {f: float(loo_scores[f][i]) for f in FACTORS}
        pattern = P.bp_pattern(s_i, by_id[g["record_id"]]["C_bimodal"] == "1", thresholds)
        e2e.append(min(100.0, 100 * P.BP_MODIFIER[pattern] * sum(wi[k] * s_i[f] for k, f in enumerate(ADDITIVE))))
    om = np.array([float(g["overall_mark"]) for g in ratings])
    e2e = np.array(e2e)
    report["final_mark_loocv"] = {"mae_0_100": round(float(np.mean(np.abs(e2e - om))), 2), "pearson": round(float(pearsonr(e2e, om)[0]), 4),
                                  "spearman": round(float(spearmanr(e2e, om)[0]), 4), "earlier": old["final_mark_loocv"]}
    (CLEAN / "marks_report_clean.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # final dataset
    gt = {g["record_id"]: g for g in ratings}
    id_cols = ["record_id", "team_id", "sprint_id", "student_id", "project_domain", "team_size"]
    feature_cols = [c for c in {**{k: 1 for r in (real[0], sim[0]) for k in r}} if c not in id_cols]
    score_cols = [c for f in FACTORS for c in (f"{f}_score", f"{f}_score_lo", f"{f}_score_hi", f"{f}_extrapolated")]
    header = (["source", "behaviour_class_written"] + id_cols + feature_cols + score_cols + ["BP_pattern", "BP_modifier", "final_mark", "in_ground_truth"]
              + [f"GT_{f}" for f in FACTORS] + ["GT_BP_pattern", "GT_overall_mark"])
    with open(CLEAN / "final_dataset_clean.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for src, records, key in (("real", real, "real"), ("simulated", sim, "sim")):
            for r in records:
                s = scores[key][r["record_id"]]
                row = {"source": src, "behaviour_class_written": classes.get(r["student_id"], "") if src == "simulated" else ""}
                row.update({c: r.get(c, "") for c in id_cols + feature_cols})
                for fct in FACTORS:
                    row[f"{fct}_score"], row[f"{fct}_score_lo"], row[f"{fct}_score_hi"] = round(s[fct], 4), round(s[f"{fct}_lo"], 4), round(s[f"{fct}_hi"], 4)
                    row[f"{fct}_extrapolated"] = s[f"{fct}_extrapolated"]
                row.update({"BP_pattern": s["BP_pattern"], "BP_modifier": s["BP_modifier"], "final_mark": s["final_mark"]})
                g = gt.get(r["record_id"])
                row["in_ground_truth"] = int(bool(g))
                for fct in FACTORS:
                    row[f"GT_{fct}"] = round((np.mean([float(g[c]) for c in FACTORS[fct][1]]) - 1) / 4, 4) if g else ""
                row["GT_BP_pattern"] = g["BP_pattern"] if g else ""
                row["GT_overall_mark"] = g["overall_mark"] if g else ""
                writer.writerow(row)
    summary = {f: {k: v[k] for k in ("alpha", "loocv_mae", "loocv_pearson", "baseline_mae_predict_mean", "earlier_dirty_features", "simulated_records_outside_anchor_range")}
               for f, v in report["factors"].items()}
    print(json.dumps({"factors": summary, "bp": report["behavioral_pattern"]["agreement"], "fusion": report["fusion"], "final_mark_loocv": report["final_mark_loocv"]}, indent=1))


if __name__ == "__main__":
    main()
