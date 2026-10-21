"""The one scorer for every experiment (plan.md, section 6). Pure Python so it runs in any environment.

Input: result rows from the runner (one per task and run) and the benchmark's truth. Output: agreement with the truth at criterion,
task and sprint level, by task-size bucket, with 95% intervals that resample whole students, plus repeatability across runs and cost.
"""

import math
import random
import statistics
from collections import defaultdict

from .schema import BUCKETS, VERDICT_VALUE, band, sprint_score, task_fulfilment


def mean(x):
    x = list(x)
    return sum(x) / len(x) if x else float("nan")


def pearson(a, b):
    if len(a) < 3:
        return float("nan")
    ma, mb = mean(a), mean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    if sa == 0 or sb == 0:
        return float("nan")
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    return pearson(ranks(a), ranks(b)) if len(a) >= 3 else float("nan")


def weighted_kappa(a, b, k=5):
    """Quadratic weighted kappa of two lists of bands 1..k."""
    n = len(a)
    if n == 0:
        return float("nan")
    o = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        o[x - 1][y - 1] += 1
    ra, rb = [sum(r) for r in o], [sum(o[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * o[i][j]
            den += w * ra[i] * rb[j] / n
    return 1 - num / den if den else float("nan")


def agreement(truth, pred):
    """Agreement of predicted and true values in [0, 1]."""
    if not truth:
        return {"n": 0}
    err = [p - t for p, t in zip(pred, truth)]
    mt, mp = mean(truth), mean(pred)
    var = sum((p - mp) ** 2 for p in pred)
    slope = sum((p - mp) * (t - mt) for p, t in zip(pred, truth)) / var if var else float("nan")
    return {"n": len(truth), "MAE": mean(abs(e) for e in err), "RMSE": math.sqrt(mean(e * e for e in err)), "bias": mean(err),
            "pearson": pearson(truth, pred), "spearman": spearman(truth, pred), "calib_slope": slope,
            "kappa_w": weighted_kappa([band(t) for t in truth], [band(p) for p in pred]),
            "band_within_1": mean(abs(band(t) - band(p)) <= 1 for t, p in zip(truth, pred))}


def cluster_bootstrap(rows, stat, key="student", n=1000, seed=7):
    """95% interval of ``stat(rows)`` resampling whole students."""
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    names = sorted(groups)
    if len(names) < 3:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        pick = [rng.choice(names) for _ in names]
        sample = [r for g in pick for r in groups[g]]
        v = stat(sample)
        if v == v:
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    vals.sort()
    return (vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))])


# --- scoring of runner output -------------------------------------------------------------------------------------------

def task_rows(results, bench, manifest, verifiable_only=True, run=None):
    """One row per (task, run) with truth, prediction and size. Failed rows are marked ``failed``."""
    rows = []
    for r in results:
        if run is not None and r.get("run", 0) != run:
            continue
        t = bench.tasks[r["task_id"]]
        m = manifest["tasks"][r["task_id"]]
        if verifiable_only and not m["verifiable"]:
            continue
        truth = t["truth"]["credited"]
        ok = not r.get("error") and r.get("verdicts") and len(r["verdicts"]) == len(truth)
        rows.append({"task_id": r["task_id"], "student": t["student"], "sprint": t["sprint"], "bucket": m["bucket"], "tokens": m["tokens"], "failed": not ok,
                     "truth": truth, "verdicts": r.get("verdicts") if ok else ["cannot_tell"] * len(truth),
                     "truth_rf": mean(truth), "pred_rf": task_fulfilment(r["verdicts"]) if ok else 0.0, "run": r.get("run", 0),
                     "usage": r.get("usage", {}), "error_kind": r.get("error_kind", ""), "coverage": r.get("coverage"), "cites_ok": r.get("cites_ok")})
    return rows


def criterion_scores(rows):
    t, p = [], []
    for r in rows:
        for a, v in zip(r["truth"], r["verdicts"]):
            t.append(a)
            p.append(v)
    if not t:
        return {"n": 0}
    pred_met = [v == "met" for v in p]
    tp_nm = sum(1 for a, m in zip(t, pred_met) if a == 0 and not m)
    pred_nm = sum(1 for m in pred_met if not m)
    true_nm = sum(1 for a in t if a == 0)
    counts = defaultdict(int)
    for v in p:
        counts[v] += 1
    return {"n": len(t), "accuracy": mean(m == bool(a) for a, m in zip(t, pred_met)),
            "not_met_precision": tp_nm / pred_nm if pred_nm else float("nan"), "not_met_recall": tp_nm / true_nm if true_nm else float("nan"),
            "verdict_share": {k: counts[k] / len(p) for k in ("met", "partly", "not_met", "cannot_tell")}}


def score(rows):
    """Metrics of a set of task rows (completed and failed together; failed rows count as no credit)."""
    done = [r for r in rows if not r["failed"]]
    out = {"tasks": len(rows), "completed": len(done), "failure_rate": 1 - len(done) / len(rows) if rows else float("nan"),
           "completed_only": {"task": agreement([r["truth_rf"] for r in done], [r["pred_rf"] for r in done]), "criterion": criterion_scores(done)},
           "failures_as_no_credit": {"task": agreement([r["truth_rf"] for r in rows], [r["pred_rf"] for r in rows]), "criterion": criterion_scores(rows)}}
    sp = defaultdict(list)
    for r in rows:
        sp[(r["sprint"], r["student"])].append(r)
    full = [(mean(x["truth_rf"] for x in v), sprint_score([x["pred_rf"] for x in v]), v[0]["student"]) for v in sp.values()]
    out["sprint_level"] = agreement([a for a, _, _ in full], [b for _, b, _ in full])
    toks = [r["usage"].get("total_tokens", 0) for r in rows]
    out["cost"] = {"tokens_per_task": mean(toks), "calls_per_task": mean(r["usage"].get("calls", 0) for r in rows),
                   "seconds_per_task": mean(r["usage"].get("seconds", 0) for r in rows),
                   "error_kinds": {k: sum(1 for r in rows if r["error_kind"] == k) for k in {r["error_kind"] for r in rows if r["error_kind"]}}}
    cov = [r["coverage"] for r in rows if r.get("coverage") is not None]
    if cov:
        out["cost"]["coverage_mean"] = mean(cov)
    return out


def by_bucket(rows):
    out = {}
    for b in BUCKETS:
        sub = [r for r in rows if r["bucket"] == b]
        if sub:
            s = score(sub)
            out[b] = {"tasks": s["tasks"], "failure_rate": s["failure_rate"], "task_MAE_completed": s["completed_only"]["task"].get("MAE"),
                      "task_MAE_no_credit": s["failures_as_no_credit"]["task"].get("MAE"), "criterion_accuracy_completed": s["completed_only"]["criterion"].get("accuracy"),
                      "criterion_accuracy_all": s["failures_as_no_credit"]["criterion"].get("accuracy")}
    return out


def with_intervals(rows):
    """Headline numbers with 95% student-level bootstrap intervals."""
    def mae_all(rs):
        return mean(abs(r["pred_rf"] - r["truth_rf"]) for r in rs)

    def mae_done(rs):
        rs = [r for r in rs if not r["failed"]]
        return mean(abs(r["pred_rf"] - r["truth_rf"]) for r in rs) if rs else float("nan")

    def acc_all(rs):
        return criterion_scores(rs).get("accuracy", float("nan"))

    def corr_done(rs):
        rs = [r for r in rs if not r["failed"]]
        return pearson([r["truth_rf"] for r in rs], [r["pred_rf"] for r in rs])

    return {"task_MAE_no_credit": [mae_all(rows), *cluster_bootstrap(rows, mae_all)], "task_MAE_completed": [mae_done(rows), *cluster_bootstrap(rows, mae_done)],
            "criterion_accuracy_all": [acc_all(rows), *cluster_bootstrap(rows, acc_all)], "pearson_completed": [corr_done(rows), *cluster_bootstrap(rows, corr_done)]}


# --- repeatability ------------------------------------------------------------------------------------------------------

def icc_runs(matrix):
    """ICC(2,1)-style one-way agreement of runs. ``matrix``: list of items, each a list of values from k runs."""
    n, k = len(matrix), len(matrix[0]) if matrix else 0
    if n < 3 or k < 2:
        return float("nan")
    gm = mean(v for row in matrix for v in row)
    msb = k * sum((mean(row) - gm) ** 2 for row in matrix) / (n - 1)
    msw = sum((v - mean(row)) ** 2 for row in matrix for v in row) / (n * (k - 1))
    return (msb - msw) / (msb + (k - 1) * msw) if (msb + (k - 1) * msw) else float("nan")


def repeatability(rows):
    by = defaultdict(list)
    for r in rows:
        if not r["failed"]:
            by[r["task_id"]].append(r["pred_rf"])
    multi = {k: v for k, v in by.items() if len(v) >= 2}
    if not multi:
        return {"items": 0}
    k = min(len(v) for v in multi.values())
    mat = [v[:k] for v in multi.values()]
    spread = [statistics.pstdev(v) for v in multi.values()]
    moved = mean(max(band(x) for x in v) - min(band(x) for x in v) >= 1 for v in multi.values())
    truth = {r["task_id"]: r["truth_rf"] for r in rows}
    med = {tid: statistics.median(v) for tid, v in multi.items()}
    return {"items": len(multi), "runs": k, "mean_sd": mean(spread), "share_moving_a_band": moved, "icc": icc_runs(mat),
            "median_of_runs_MAE": mean(abs(med[t] - truth[t]) for t in med)}
