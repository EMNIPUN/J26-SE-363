"""Watch an assessment run from the terminal and keep a clean log of it.

    cd backend/agentic_framework
    ../.venv/Scripts/python.exe scripts/watch_run.py <run id>          # follow a run until it ends
    ../.venv/Scripts/python.exe scripts/watch_run.py --latest          # the newest run
    ../.venv/Scripts/python.exe scripts/watch_run.py <run id> --once   # print what exists now and stop

Prints one line per event as it happens (time, where, what), then a summary: how long each step took, every student's mark with its factors, flags, and the open reviews.
Everything printed is also written, without colours, to logs/run-<id>.log; the report and the results are saved next to it (run-<id>-report.md, run-<id>-results.json).
Events never contain tokens, e-mail addresses or students' answers; the log is safe to share inside the team.
"""
import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

COL = {"red": "31", "green": "32", "yellow": "33", "blue": "34", "magenta": "35", "cyan": "36", "grey": "90", "bold": "1"}
FINISHED = ("succeeded", "failed", "cancelled")
FACTORS = ("effort", "consistency", "requirement_fulfillment", "collaboration", "task_complexity", "code_ownership")
SHORT = {"effort": "Effort", "consistency": "Consist", "requirement_fulfillment": "ReqFulf", "collaboration": "Collab", "task_complexity": "TaskCx", "code_ownership": "CodeOwn"}


class Out:
    def __init__(self, path: Path, color: bool):
        self.file = open(path, "a", encoding="utf-8")
        self.color = color

    def line(self, text: str, color: str | None = None):
        print(f"\033[{COL[color]}m{text}\033[0m" if color and self.color else text, flush=True)
        self.file.write(text + "\n")
        self.file.flush()


def load_database_url(env_file: str) -> None:
    m = re.search(r"^SERVER_DIRECT_URL=(.*)$", Path(env_file).read_text(encoding="utf-8"), re.M)
    if not m or not m.group(1).strip():
        sys.exit(f"no SERVER_DIRECT_URL in {env_file}")
    os.environ["SERVER_DIRECT_URL"] = m.group(1).strip().strip('"').strip("'")


def where(path: str) -> tuple[str, str]:
    if path.startswith("student:"):
        who, _, node = path.partition("/")
        return who.split(":", 1)[1], node
    if path.startswith("team/"):
        return "team", path[5:]
    return "run", path


def clock(ts) -> str:
    return ts.astimezone().strftime("%H:%M:%S") if hasattr(ts, "astimezone") else str(ts)[11:19]


def show_event(out: Out, e: dict, timings: dict, started: dict):
    who, node = where(e["node_path"])
    t, msg = e["type"], e["message"]
    head = f"{clock(e['ts'])}  {who:<8} {node:<24}"
    if t == "node_start":
        started[e["node_path"]] = e["ts"]
        out.line(f"{head} > start", "cyan")
    elif t == "node_end":
        secs = (e.get("payload") or {}).get("seconds")
        timings[e["node_path"]] = secs or 0
        extra = {k: v for k, v in (e.get("payload") or {}).items() if k != "seconds" and v is not None}
        out.line(f"{head} ok done {secs:.1f}s" + (f"  {json.dumps(extra, default=str)[:110]}" if extra else ""), "green")
    elif t == "node_error":
        out.line(f"{head} X ERROR {msg}", "red")
    elif t == "node_wait":
        out.line(f"{head} || waiting for a person", "yellow")
    elif t == "tool":
        out.line(f"{head}   tool  {msg}", "magenta")
    elif t == "llm":
        out.line(f"{head}   llm   {msg}", "magenta")
    elif t in ("run_start", "run_resume", "run_end", "run_waiting"):
        out.line(f"{head} {'#' if t == 'run_end' else '*'} {t.replace('_', ' ')}: {msg}", "bold" if t != "run_end" else ("green" if msg == "succeeded" else "red"))
    else:
        c = {"error": "red", "warn": "yellow"}.get(e["level"], "grey")
        out.line(f"{head}   {msg}", c)


def fmt(f):
    if not f:
        return "-"
    if f["status"] == "completed" and f["score"] is not None:
        return f"{f['score']:.2f}{'*' if f.get('provisional') else ''}"
    return {"not_available": "n/a", "pending": "pend", "fallback": "FAIL"}.get(f["status"], f["status"])


def summary(out: Out, store, run: dict, timings: dict, log_dir: Path):
    out.line("")
    out.line(f"== Run {run['id']} | team {run['team_ref']} | sprint {run['sprint_id']} | {run['mode']} | {run['status']} ==", "bold")
    if run.get("started_at") and run.get("finished_at"):
        out.line(f"   took {(run['finished_at'] - run['started_at']).total_seconds():.0f}s")
    if run.get("error"):
        out.line(f"   error: {run['error'].get('type')}: {run['error'].get('message')}", "red")
    team = {k: v for k, v in timings.items() if k.startswith("team/")}
    if team:
        out.line("\nTeam steps:")
        for p, s in team.items():
            out.line(f"   {p[5:]:<26}{s:>7.1f}s")
    lanes = defaultdict(float)
    for p, s in timings.items():
        if p.startswith("student:"):
            lanes[where(p)[0]] += s
    slow = sorted(((s, p) for p, s in timings.items() if p.startswith("student:")), reverse=True)[:4]
    if slow:
        out.line("\nSlowest student steps:")
        for s, p in slow:
            out.line(f"   {where(p)[0]:<8} {where(p)[1]:<24}{s:>7.1f}s")
    results = store.latest_results(run["team_ref"], run["sprint_id"])
    results = [r for r in results if str(r["run_id"]) == str(run["id"])] or results
    json_rows = []
    if results:
        out.line("\nMarks (* provisional, n/a not measurable and left out, pend waiting for the quiz answer):")
        out.line(f"   {'student':<9}{'mark':>5} {'range':>9}  {'status':<15}" + "".join(f"{SHORT[f]:>9}" for f in FACTORS) + "  pattern")
        for r in results:
            rng = f"{r['mark_interval'][0]:.0f}-{r['mark_interval'][1]:.0f}" if r["mark_interval"] else ""
            mark = "n/a" if r["mark"] is None else f"{r['mark']:.0f}"
            bp = (r["factors"].get("behavioral_pattern") or {})
            out.line(f"   {r['student_id']:<9}{mark:>5} {rng:>9}  {r['status']:<15}" + "".join(f"{fmt(r['factors'].get(f)):>9}" for f in FACTORS) + f"  {bp.get('persona') or ''}")
            json_rows.append({k: r[k] for k in ("student_id", "mark", "mark_interval", "status", "factors", "justification", "flags")})
        out.line("\nWhy (first lines of each justification):")
        for r in results:
            j = r["justification"]
            out.line(f"   {r['student_id']}: {j.get('summary', '')}")
            for f in j.get("flags", [])[:4]:
                out.line(f"      ! {f['message']}" + (f" -> {f['action']}: {f['reason']}" if f.get("action") else ""), "yellow")
    reviews = store.list_reviews("open", str(run["id"]))
    if reviews:
        out.line("\nOpen reviews for the lecturer:", "yellow")
        for r in reviews:
            out.line(f"   [{r['kind']}] {r.get('student_id') or 'team'}: {r['reason'][:160]}", "yellow")
    report = (run.get("summary") or {}).get("report_markdown")
    base = log_dir / f"run-{run['id']}"
    if report:
        Path(f"{base}-report.md").write_text(report, encoding="utf-8")
    if json_rows:
        Path(f"{base}-results.json").write_text(json.dumps(json_rows, indent=1, default=str), encoding="utf-8")
    out.line(f"\nlog: {base}.log" + (f"\nreport: {base}-report.md" if report else "") + (f"\nresults: {base}-results.json" if json_rows else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_id", nargs="?")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--env-file", default="../server/.env")
    ap.add_argument("--log-dir", default="logs")
    a = ap.parse_args()

    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    load_database_url(a.env_file)
    from shared.performance import PerformanceStore

    store = PerformanceStore()
    if a.latest or not a.run_id:
        runs = store.list_runs(limit=1)
        if not runs:
            sys.exit("no runs yet")
        a.run_id = str(runs[0]["id"])
    run = store.get_run(a.run_id)
    if run is None:
        sys.exit(f"no run {a.run_id}")
    log_dir = Path(a.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    os.system("")  # lets Windows terminals show colours
    out = Out(log_dir / f"run-{a.run_id}.log", sys.stdout.isatty())
    out.line(f"watching run {a.run_id} | team {run['team_ref']} | sprint {run['sprint_id']} | {run['mode']} | {datetime.now().astimezone():%Y-%m-%d %H:%M:%S}", "bold")

    seq, timings, started, idle = 0, {}, {}, 0
    while True:
        rows = store.list_events(a.run_id, seq, 500)
        for e in rows:
            show_event(out, e, timings, started)
            seq = e["seq"]
        run = store.get_run(a.run_id)
        if rows:
            idle = 0
        else:
            idle += 1
        if run["status"] in FINISHED and not rows:
            break
        if a.once and not rows:
            break
        if idle and idle % 30 == 0:
            out.line(f"{datetime.now():%H:%M:%S}  ... {run['status']}, now at {run.get('current_node') or '-'}", "grey")
        if not rows:
            time.sleep(a.interval)
    summary(out, store, run, timings, log_dir)


if __name__ == "__main__":
    main()
