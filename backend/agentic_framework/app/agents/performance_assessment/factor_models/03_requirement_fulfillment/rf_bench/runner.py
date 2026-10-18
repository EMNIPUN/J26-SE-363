"""One runner and one report for every experiment.

    python -m rf_bench.runner run    --exp experiments.single_prompt:SinglePrompt --split dev --per-bucket 6 --runs 1 --out runs/exp1_dev
    python -m rf_bench.runner report --out runs/exp1_dev

An experiment is a class with ``name``, ``config()`` and ``assess(bench, task_id, scope, llm) -> dict``; everything else (items, pacing,
resume, scoring, the report) is shared, so every experiment is run and scored the same way (plan.md, section 13).
``--dry`` replaces the model with a scripted one, to test a pipeline without a key.
"""

import argparse
import hashlib
import importlib
import json
import math
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import metrics
from .bench import Bench, build_manifest, load_manifest
from .llm import GroqPool, Reply, ScriptedLLM
from .schema import BUCKETS
from .scope import Scope

RF = Path(__file__).resolve().parents[1]


class Usage:
    """Adds up the cost of the calls one assessment makes."""

    def __init__(self):
        self.calls = self.prompt_tokens = self.completion_tokens = 0
        self.t0 = time.time()
        self.failures = []

    def add(self, reply: Reply):
        self.calls += 1
        self.prompt_tokens += reply.prompt_tokens
        self.completion_tokens += reply.completion_tokens
        if not reply.ok:
            self.failures.append(reply.error_kind)
        return reply

    def as_dict(self):
        return {"calls": self.calls, "prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens,
                "total_tokens": self.prompt_tokens + self.completion_tokens, "seconds": round(time.time() - self.t0, 2), "failed_calls": self.failures}


def load_experiment(spec):
    mod, cls = spec.split(":")
    sys.path.insert(0, str(RF))
    return getattr(importlib.import_module(mod), cls)()


def pick_items(manifest, split, per_bucket, seed=11, verifiable=True):
    tasks = [(tid, m) for tid, m in sorted(manifest["tasks"].items()) if m["split"] == split and (m["verifiable"] or not verifiable)]
    out = []
    for b in BUCKETS:
        pool = [tid for tid, m in tasks if m["bucket"] == b]
        random.Random(f"{seed}:{b}:{split}").shuffle(pool)
        out += pool if per_bucket in (None, 0) else pool[:per_bucket]
    return sorted(out)


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=RF).stdout.strip()
    except Exception:
        return ""


def cmd_run(a):
    bench, manifest = build_manifest(write=False)
    frozen = load_manifest()
    if frozen["sha256"] != manifest["sha256"]:
        sys.exit("the regenerated benchmark does not match benchmark/manifest.json: refusing to run")
    exp = load_experiment(a.exp)
    items = pick_items(manifest, a.split, a.per_bucket)
    out = RF / a.out
    out.mkdir(parents=True, exist_ok=True)
    results_path = out / "results.jsonl"
    done = set()
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["task_id"], r["run"]))
    llm = ScriptedLLM(exp.dry_responder, model="scripted") if a.dry else GroqPool(model=a.model, fallback=a.fallback, effort=a.effort)
    meta = {"experiment": exp.name, "config": exp.config(), "model": llm.model, "split": a.split, "per_bucket": a.per_bucket, "runs": a.runs,
            "items": len(items), "benchmark_sha256": manifest["sha256"], "code_commit": git_commit(), "dry": a.dry, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    jobs = [(tid, k) for k in range(a.runs) for tid in items if (tid, k) not in done]
    lock = threading.Lock()
    counter = {"n": 0}

    def work(job):
        tid, k = job
        t = bench.tasks[tid]
        scope = Scope(bench, t["sprint"], t["student"])
        usage = Usage()
        try:
            res = exp.assess(bench, tid, scope, llm, usage, run=k)
        except Exception as e:  # a bug or an unexpected reply is a failure of this item, recorded
            res = {"error": f"{type(e).__name__}: {str(e)[:200]}", "error_kind": "exception"}
        row = {"task_id": tid, "run": k, "usage": usage.as_dict(), **res}
        row.setdefault("coverage", round(scope.coverage(), 4))
        with lock:
            with open(results_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            counter["n"] += 1
            if counter["n"] % 5 == 0 or counter["n"] == len(jobs):
                print(f"  {counter['n']}/{len(jobs)} done", flush=True)

    print(f"{exp.name}: {len(jobs)} jobs ({len(items)} tasks x {a.runs} runs), model {llm.model}", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(work, jobs))
    print("run finished ->", results_path)


def fmt(x, d=3):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{d}f}" if isinstance(x, float) else str(x)


def cmd_report(a):
    bench, manifest = build_manifest(write=False)
    out = RF / a.out
    meta = json.loads((out / "run_meta.json").read_text(encoding="utf-8"))
    results = [json.loads(x) for x in (out / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = metrics.task_rows(results, bench, manifest)
    first = [r for r in rows if r["run"] == 0]
    sc, bk, iv, rep = metrics.score(first), metrics.by_bucket(first), metrics.with_intervals(first), metrics.repeatability(rows)
    share = {b: sum(1 for m in manifest["tasks"].values() if m["bucket"] == b and m["verifiable"]) for b in BUCKETS}
    tot = sum(share.values())
    w_mae = sum(share[b] / tot * v["task_MAE_no_credit"] for b, v in bk.items() if v["task_MAE_no_credit"] == v["task_MAE_no_credit"]) / (sum(share[b] / tot for b in bk) or 1)
    report = {"meta": meta, "overall": sc, "intervals": iv, "by_bucket": bk, "real_share_weighted_task_MAE_no_credit": w_mae, "repeatability": rep}
    (out / "report.json").write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    lines = [f"# {meta['experiment']}: {meta['split']} ({meta['model']})", "",
             f"Tasks {sc['tasks']}, completed {sc['completed']}, failure rate {fmt(sc['failure_rate'])}. Benchmark {meta['benchmark_sha256'][:12]}, code {meta['code_commit']}.", "",
             "| view | n | MAE | RMSE | bias | Pearson | Spearman | weighted kappa | within 1 band |", "|---|---|---|---|---|---|---|---|---|"]
    for name, key in (("task, completed only", sc["completed_only"]["task"]), ("task, failures as no credit", sc["failures_as_no_credit"]["task"]), ("sprint", sc["sprint_level"])):
        lines.append(f"| {name} | {key.get('n')} | " + " | ".join(fmt(key.get(k)) for k in ("MAE", "RMSE", "bias", "pearson", "spearman", "kappa_w", "band_within_1")) + " |")
    ci = lambda k: f"{fmt(iv[k][0])} ({fmt(iv[k][1])} to {fmt(iv[k][2])})"  # noqa: E731
    lines += ["", f"Task MAE (failures as no credit) {ci('task_MAE_no_credit')}; completed only {ci('task_MAE_completed')}; criterion accuracy {ci('criterion_accuracy_all')}; Pearson {ci('pearson_completed')}.",
              f"Real-share-weighted task MAE (failures as no credit): {fmt(w_mae)}.", "", "By task size (tokens of the cleaned diff):", "",
              "| bucket | tasks | failure rate | MAE completed | MAE no credit | criterion acc completed | criterion acc all |", "|---|---|---|---|---|---|---|"]
    for b, v in bk.items():
        lines.append(f"| {b} | {v['tasks']} | {fmt(v['failure_rate'])} | {fmt(v['task_MAE_completed'])} | {fmt(v['task_MAE_no_credit'])} | {fmt(v['criterion_accuracy_completed'])} | {fmt(v['criterion_accuracy_all'])} |")
    c = sc["completed_only"]["criterion"]
    lines += ["", f"Criterion verdicts (completed): accuracy {fmt(c.get('accuracy'))}, not-met precision {fmt(c.get('not_met_precision'))}, recall {fmt(c.get('not_met_recall'))}, shares {c.get('verdict_share')}.",
              f"Cost per task: {fmt(sc['cost']['tokens_per_task'], 0)} tokens, {fmt(sc['cost']['calls_per_task'], 1)} calls, {fmt(sc['cost']['seconds_per_task'], 1)} s; failures by kind {sc['cost']['error_kinds']}.", ""]
    if rep.get("items"):
        lines += [f"Repeatability over {rep['runs']} runs, {rep['items']} items: mean SD {fmt(rep['mean_sd'])}, share moving a band {fmt(rep['share_moving_a_band'])}, ICC {fmt(rep['icc'])}, MAE of the median of runs {fmt(rep['median_of_runs_MAE'])}.", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def cmd_compare(a):
    """Paired comparison of two runs on the tasks they share: differences in task MAE and criterion accuracy (failures count as no credit)."""
    bench, manifest = build_manifest(write=False)

    def load(path):
        res = [json.loads(x) for x in (RF / path / "results.jsonl").read_text(encoding="utf-8").splitlines()]
        return {r["task_id"]: r for r in metrics.task_rows(res, bench, manifest, run=0)}

    def acc(r):
        return sum((v == "met") == bool(t) for v, t in zip(r["verdicts"], r["truth"])) / len(r["truth"])

    A, B = load(a.a), load(a.b)
    ids = sorted(set(A) & set(B))
    rows = [{"student": A[t]["student"], "mae": abs(A[t]["pred_rf"] - A[t]["truth_rf"]) - abs(B[t]["pred_rf"] - B[t]["truth_rf"]), "acc": acc(A[t]) - acc(B[t])} for t in ids]
    out = {"tasks": len(ids), "a": a.a, "b": a.b}
    for key, name in (("mae", "MAE_a_minus_MAE_b"), ("acc", "criterion_accuracy_a_minus_b")):
        stat = lambda rs, k=key: metrics.mean(r[k] for r in rs)  # noqa: E731
        out[name] = [stat(rows), *metrics.cluster_bootstrap(rows, stat)]
    print(json.dumps(out, indent=1, default=float))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--exp", required=True)
    r.add_argument("--split", choices=["dev", "held_out"], required=True)
    r.add_argument("--per-bucket", type=int, default=0, help="tasks per size bucket (0 = all)")
    r.add_argument("--runs", type=int, default=1)
    r.add_argument("--out", required=True)
    r.add_argument("--workers", type=int, default=5)
    r.add_argument("--model", default=None)
    r.add_argument("--fallback", default=None)
    r.add_argument("--effort", default="low")
    r.add_argument("--dry", action="store_true")
    r.set_defaults(fn=cmd_run)
    c = sub.add_parser("compare")
    c.add_argument("--a", required=True)
    c.add_argument("--b", required=True)
    c.set_defaults(fn=cmd_compare)
    q = sub.add_parser("report")
    q.add_argument("--out", required=True)
    q.set_defaults(fn=cmd_report)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
