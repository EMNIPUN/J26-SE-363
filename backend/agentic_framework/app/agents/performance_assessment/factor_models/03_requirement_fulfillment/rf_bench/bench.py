"""The mock benchmark: repositories built from the simulated dataset, with known truth.

Source: ``dataset/synthetic_students/out`` (219 tasks of 50 simulated students in 10 teams). What the simulation knows and a rater would not:
for every task, which acceptance criteria its code meets (``criteria_met``) and the few lines of code that decide that. This module
turns that into repositories a tool can browse:

- every commit of the team's sprint (the student's and the teammates'), with message, files and cleaned hunks;
- the deciding lines of each task embedded in a commit of its author, among generic filler code, scaled so that the cleaned diff
  of a task follows the **real** size distribution (median ~800 changed lines, 90th percentile ~3,300, maximum ~23,000; see
  plan.md, section 13). Only the size is taken from the real data; no real code is used.
- a share of the commit messages names the task, the rest does not, so mapping commits to tasks needs reading code;
- work finished by a teammate sits in the teammate's commit and is not credited to the assignee.

The truth the experiments are scored against is the simulation's ``criteria_met`` (credited to the assignee only for the code the
assignee wrote). The board status (Done / Partially Done) is **withheld** from every experiment: the simulator derives it from the
truth, so showing it would leak the answer.

Nothing is stored except ``benchmark/manifest.json``; the repositories are regenerated deterministically and checked against the
manifest's hash.
"""

import csv
import hashlib
import json
import math
import random
import re
import statistics
import sys
from pathlib import Path

from .codegen import lines_for, strip_snippet
from .schema import BUCKETS, bucket_of, est_tokens

HERE = Path(__file__).resolve().parent
RF = HERE.parent
FM = RF.parent
SIM = FM / "dataset" / "synthetic_students" / "out"
MANIFEST = RF / "benchmark" / "manifest.json"
sys.path.insert(0, str(FM))
from evidence.lines import classify_path  # noqa: E402

BENCH_VERSION = "rf-bench/1"
SEED = "rf-bench-20261019"
# real cleaned changed lines per task (plan.md, section 1): median ~800, p90 ~3,300, maximum ~23,000
MEDIAN_LINES, P90_LINES, MAX_LINES, MIN_LINES = 800, 3300, 23000, 12
SIGMA = math.log(P90_LINES / MEDIAN_LINES) / 1.2815515655446004
NAMED_SHARE = 0.45  # share of commit messages that carry the task key


def _read(name):
    with open(SIM / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _frac(*parts):
    """A stable number in [0, 1) from strings."""
    h = hashlib.md5(":".join(map(str, (SEED, *parts))).encode()).hexdigest()
    return int(h[:8], 16) / 0x100000000


def parse_criteria(text):
    parts = re.split(r";\s*(?=\d+\.\s)", text.strip())
    return [re.sub(r"^\d+\.\s*", "", p).strip() for p in parts if p.strip()]


def parse_files(text):
    out = []
    for item in [p.strip() for p in text.split(";") if p.strip()]:
        m = re.match(r"^(.*)\(\+(\d+)/-(\d+)\)$", item)
        if m:
            out.append((m.group(1).strip(), int(m.group(2)), int(m.group(3))))
    return out


def size_from_quantile(u):
    z = statistics.NormalDist().inv_cdf(min(max(u, 1e-6), 1 - 1e-6))
    return int(min(MAX_LINES, max(MIN_LINES, math.exp(math.log(MEDIAN_LINES) + SIGMA * z))))


class Bench:
    def __init__(self):
        board, commits, code_rows = _read("scrum_board_simulated.csv"), _read("commits_simulated.csv"), {}
        with open(SIM / "code_examples.jsonl", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                code_rows[r["task_id"]] = r
        self.tasks, self.commits, self.hunk_cache = {}, {}, {}
        self.by_sprint = {}
        for b in board:
            crit = parse_criteria(b["acceptance_criteria"])
            cm = code_rows[b["task_id"]]["criteria_met"]
            assert len(crit) == len(cm) == int(b["ac_total"]), b["task_id"]
            mate = b["completed_by"] not in ("", b["assignee_id"])
            self.tasks[b["task_id"]] = {
                "id": b["task_id"], "team": b["team_id"], "sprint": b["sprint_id"], "student": b["assignee_id"], "title": b["task_title"],
                "description": b["description"], "criteria": crit, "points": int(b["story_points"]), "subtasks": int(b["subtask_count"]),
                "carried_over": bool(b["carried_over_from"]), "completed_by_teammate": mate, "completed_by": b["completed_by"] if mate else "",
                "_snippet": code_rows[b["task_id"]]["code"], "_status": b["status"],
                "truth": {"criteria_met": cm, "credited": [0] * len(cm) if mate else list(cm)},
            }
        for c in commits:
            files = [(p, a, d) for p, a, d in parse_files(c["files"]) if classify_path(p) in ("code", "test")]
            self.commits[c["commit_id"]] = {
                "sha": c["commit_id"], "sprint": c["sprint_id"], "author": c["student_id"], "date": c["authored_at"], "subject": c["subject"],
                "task_key": c["task_key"], "files": [{"path": p, "kind": classify_path(p), "added": a, "deleted": d} for p, a, d in files],
            }
        for sha, c in self.commits.items():
            self.by_sprint.setdefault(c["sprint"], []).append(sha)
        for lst in self.by_sprint.values():
            lst.sort(key=lambda s: (self.commits[s]["date"], s))
        self._scale()
        self._place()
        self._messages()

    # --- sizes -------------------------------------------------------------------------------------------------------------

    def _task_commits(self, tid):
        return [c for c in self.commits.values() if c["task_key"] == tid]

    def _scale(self):
        base = {}
        for tid in self.tasks:
            base[tid] = sum(f["added"] + f["deleted"] for c in self._task_commits(tid) for f in c["files"])
        order = sorted((t for t in base if base[t] > 0), key=lambda t: (base[t], _frac("tie", t)))
        n = len(order)
        self.target, self.factor = {}, {}
        for i, tid in enumerate(order):
            self.target[tid] = size_from_quantile((i + 0.5) / n)
            self.factor[tid] = self.target[tid] / base[tid]
        for tid in self.tasks:
            if tid not in self.target:
                self.target[tid] = size_from_quantile(_frac("size", tid))
        for c in self.commits.values():
            k = self.factor.get(c["task_key"], 1.0)
            for f in c["files"]:
                f["added"] = max(1, round(f["added"] * k))
                f["deleted"] = round(f["deleted"] * k)

    # --- where the deciding code lives -------------------------------------------------------------------------------------

    def _place(self):
        """Embed each task's deciding lines in a commit of the author (or, for work finished by a teammate, of the teammate)."""
        self.place = {}  # (sha, path) -> {"task": id, "lines": [...]}
        for tid, t in self.tasks.items():
            code, hints = strip_snippet(t["_snippet"])
            t["verifiable"] = bool(code) or not t["_snippet"].strip()  # a task whose only evidence was a comment or a document cannot be judged from source
            if not code:
                continue
            extra = [x[1] for x in hints["extra"]]
            block = code + extra
            owner = t["completed_by"] if t["completed_by_teammate"] else t["student"]
            mine = [c for c in self._task_commits(tid) if c["author"] == owner]
            cand = [(f["added"], c["sha"], f) for c in mine for f in c["files"] if f["kind"] == "code"]
            if hints["header"]:
                hit = [x for x in cand if x[2]["path"].split("/")[-1] == hints["header"].split("/")[-1]]
                cand = hit or cand
            if not cand:  # an untracked commit of the owner, or a new one
                pool = [c for c in self.by_sprint.get(t["sprint"], []) if self.commits[c]["author"] == owner and not self.commits[c]["task_key"]]
                pool = [c for c in pool if any(f["kind"] == "code" for f in self.commits[c]["files"])]
                if pool:
                    sha = pool[int(_frac("pool", tid) * len(pool))]
                    self.commits[sha]["task_key"] = tid
                    cand = [(f["added"], sha, f) for f in self.commits[sha]["files"] if f["kind"] == "code"]
                else:
                    sha = self._new_commit(t, owner, hints["header"])
                    cand = [(f["added"], sha, f) for f in self.commits[sha]["files"]]
            cand.sort(key=lambda x: (-x[0], x[1]))
            _, sha, f = cand[0]
            f["added"] = max(f["added"], len(block) + 2)
            self.place[(sha, f["path"])] = {"task": tid, "lines": block}

    def _new_commit(self, t, owner, header):
        ext = (header or "src/app.js").rsplit(".", 1)[-1]
        sha = hashlib.md5(f"{SEED}:new:{t['id']}".encode()).hexdigest()[:10]
        path = header or f"src/{re.sub('[^a-z0-9]+', '_', t['title'].lower())[:24]}.{ext}"
        if "/" not in path:
            path = f"src/{path}"
        size = max(30, self.target[t["id"]])
        sprint_commits = [self.commits[s] for s in self.by_sprint[t["sprint"]]]
        day = max(c["date"] for c in sprint_commits)[:10]
        self.commits[sha] = {"sha": sha, "sprint": t["sprint"], "author": owner, "date": f"{day}T18:00:00", "subject": f"{t['title'].lower()}",
                             "task_key": t["id"], "files": [{"path": path, "kind": classify_path(path), "added": size, "deleted": 0}]}
        self.by_sprint[t["sprint"]].append(sha)
        self.by_sprint[t["sprint"]].sort(key=lambda s: (self.commits[s]["date"], s))
        return sha

    def _messages(self):
        for c in self.commits.values():
            c["message"] = f"{c['task_key']}: {c['subject']}" if c["task_key"] and _frac("msg", c["sha"]) < NAMED_SHARE else c["subject"]

    # --- hunks -------------------------------------------------------------------------------------------------------------

    def hunk(self, sha, path):
        """Cleaned changed lines of one file of one commit: ``["-old", "+new", ...]`` (deleted lines first)."""
        key = (sha, path)
        if key in self.hunk_cache:
            return self.hunk_cache[key]
        c = self.commits[sha]
        f = next(x for x in c["files"] if x["path"] == path)
        is_test = f["kind"] == "test"
        added = lines_for(path, f["added"], f"{SEED}:{sha}:+", is_test)
        p = self.place.get(key)
        if p:
            off = int(_frac("off", sha, path) * (len(added) - len(p["lines"]) + 1))
            added[off:off + len(p["lines"])] = p["lines"]
        removed = lines_for(path, f["deleted"], f"{SEED}:{sha}:-", is_test)
        out = ["-" + x for x in removed] + ["+" + x for x in added]
        if len(self.hunk_cache) < 400:
            self.hunk_cache[key] = out
        return out

    def render_commit(self, sha):
        c = self.commits[sha]
        parts = [f"commit {sha} {c['date'][:10]} {c['message']}"]
        for f in c["files"]:
            parts.append(f"--- {f['path']}\n@@ +{f['added']} -{f['deleted']} @@")
            parts.extend(self.hunk(sha, f["path"]))
        return "\n".join(parts)

    # --- views -------------------------------------------------------------------------------------------------------------

    def student_commits(self, sprint, student):
        return [self.commits[s] for s in self.by_sprint.get(sprint, []) if self.commits[s]["author"] == student]

    def task_commits(self, tid):
        """Truth mapping: the commits of the task's author that belong to the task."""
        t = self.tasks[tid]
        return [c for c in self.student_commits(t["sprint"], t["student"]) if c["task_key"] == tid]

    def task_diff(self, tid):
        """The cleaned diff of a task as the proposal's single prompt would hold it (correct commit mapping given)."""
        return "\n".join(self.render_commit(c["sha"]) for c in self.task_commits(tid))

    def task_public(self, tid):
        t = self.tasks[tid]
        return {k: t[k] for k in ("id", "title", "description", "criteria", "points", "subtasks", "carried_over", "completed_by_teammate")}

    def student_sprints(self):
        keys = sorted({(t["sprint"], t["student"]) for t in self.tasks.values()})
        return keys

    def tasks_of(self, sprint, student):
        return [t["id"] for t in self.tasks.values() if t["sprint"] == sprint and t["student"] == student]


# --- manifest ------------------------------------------------------------------------------------------------------------

def split_students(bench):
    teams = {}
    for t in bench.tasks.values():
        teams.setdefault(t["team"], set()).add(t["student"])
    dev, held = [], []
    for team, studs in sorted(teams.items()):
        order = sorted(studs, key=lambda s: _frac("split", s))
        dev += order[:2]
        held += order[2:]
    return sorted(dev), sorted(held)


def build_manifest(write=True):
    b = Bench()
    dev, held = split_students(b)
    tasks, digest = {}, hashlib.sha256()
    for tid in sorted(b.tasks):
        diff = b.task_diff(tid)
        n = diff.count("\n") + 1 if diff else 0
        toks = est_tokens(diff) if diff else 0
        digest.update(tid.encode())
        digest.update(diff.encode())
        t = b.tasks[tid]
        tasks[tid] = {"student": t["student"], "sprint": t["sprint"], "lines": sum(f["added"] + f["deleted"] for c in b.task_commits(tid) for f in c["files"]),
                      "tokens": toks, "bucket": bucket_of(toks), "criteria": len(t["criteria"]), "credited_met": sum(t["truth"]["credited"]),
                      "verifiable": t["verifiable"],
                      "split": "dev" if t["student"] in dev else "held_out"}
    for sha in sorted(b.commits):
        digest.update(sha.encode())
        digest.update(b.render_commit(sha).encode())
    m = {"version": BENCH_VERSION, "seed": SEED, "sha256": digest.hexdigest(), "n_tasks": len(tasks), "n_commits": len(b.commits),
         "size_model": {"median": MEDIAN_LINES, "p90": P90_LINES, "max": MAX_LINES}, "dev_students": dev, "held_out_students": held, "tasks": tasks}
    if write:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8")
    return b, m


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def summary(m):
    rows = {s: {k: 0 for k in BUCKETS} for s in ("dev", "held_out")}
    for t in m["tasks"].values():
        rows[t["split"]][t["bucket"]] += 1
    lines = sorted(t["lines"] for t in m["tasks"].values() if t["lines"])
    return {"tasks": m["n_tasks"], "buckets": rows, "lines_median": statistics.median(lines), "lines_p90": lines[int(0.9 * len(lines))], "lines_max": lines[-1]}


if __name__ == "__main__":
    bench, man = build_manifest()
    print(json.dumps(summary(man), indent=1))
    print("sha256", man["sha256"][:16])
