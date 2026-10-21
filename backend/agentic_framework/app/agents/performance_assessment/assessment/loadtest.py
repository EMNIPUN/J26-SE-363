"""Load test of the student stage: many students at one deadline, a slow database, a model that is slow too.

    python scripts/load_test.py --students 250 --parallel 8 --db-latency 0.05

Builds synthetic evidence for N students (no repository, no network, no language model), runs every student's pipeline through the real team-graph dispatcher and the real factors (Effort, Consistency,
Task Complexity, Collaboration, behavioural pattern, fusion, audit, justification, export), with an in-memory store that waits ``db_latency`` seconds on every write (a far-away database) and a stand-in
for Requirement Fulfillment that waits ``rf_seconds`` (the model). It reports whether everything finished, how many students ran at once at most, the time, the peak memory and the number of events.
What it does not test: GitHub, git, the Scrum MCP server, Groq's rate limits, Postgres itself.
"""
import asyncio
import time
import tracemalloc
from pathlib import Path

from app.agents.performance_assessment.assessment import factors
from app.agents.performance_assessment.assessment import events as events_mod
from app.agents.performance_assessment.assessment.events import Events, NodeLog
from app.agents.performance_assessment.assessment.graph import TeamGraph
from app.agents.performance_assessment.assessment.services import Services
from shared.performance.memory_store import MemoryStore


def synthetic_evidence(i: int) -> dict:
    sid = f"STU-{i:04d}"
    days = list(range(0, 14, 1 + i % 3))
    commits = [{"id": f"{i:03d}{d:02d}", "authored_at": f"2026-03-{2 + d:02d}T10:00:00+05:30", "is_merge": False, "subject": f"work {d}",
                "files": [{"path": f"src/m{i % 7}/f{d}.py", "kind": "code", "added": 40 + i % 30, "deleted": 5,
                           "line_stats": {"added": {"code": 40 + i % 30, "comment": 3, "blank": 4, "format_only": 0}, "deleted": {"code": 5, "comment": 0, "blank": 0, "format_only": 0}}}]} for d in days]
    tasks = [{"id": f"T{i}-1", "title": "task", "description": "", "acceptance_criteria": ["it works"], "story_points": 3 + i % 3, "subtask_count": 2, "assignee": sid, "status": "Done", "completed_by": sid,
              "commit_ids": [c["id"] for c in commits[:2]]}]
    return {"schema": "evidence/1", "student_id": sid, "team_id": "TL", "sprint": {"id": "TL-S1", "start": "2026-03-02", "days": 14}, "commits": commits, "tasks": tasks, "task_commits": [],
            "repo": {"reach_before": {}}, "pull_requests": [], "reviews": [], "comments": [], "merged_for_others": 0, "team": {"reviews_and_comments": 0}}


class SlowStore(MemoryStore):
    def __init__(self, latency):
        super().__init__()
        self.latency = latency
        self.writes = 0

    def _wait(self):
        self.writes += 1
        time.sleep(self.latency)

    def add_events(self, run_id, evs):
        self._wait()
        return super().add_events(run_id, evs)

    def save_factor_result(self, *a, **k):
        self._wait()
        return super().save_factor_result(*a, **k)

    def save_assessment_result(self, *a, **k):
        self._wait()
        return super().save_assessment_result(*a, **k)

    def list_reviews(self, *a, **k):
        self._wait()
        return super().list_reviews(*a, **k)


async def run_load(students=250, parallel=8, db_latency=0.05, rf_seconds=0.3, work_dir=None) -> dict:
    store = SlowStore(db_latency)
    run = store.create_run("TL", "TL-S1", "snapshot")
    rid = run["id"]
    sv = Services(store=store, ws=None, scrum=lambda: None, llm=None, work_dir=Path(work_dir or "."), parallel_students=parallel)
    d = sv.data(rid)
    d.evidence = {e["student_id"]: e for e in (synthetic_evidence(i) for i in range(students))}
    for e in d.evidence.values():
        e["as_of"] = "2026-03-12T12:00:00Z"
    real, running, peak = factors.run_factor, {"now": 0, "max": 0}, {}

    async def stand_in(name, evidence, **kw):
        if name == "requirement_fulfillment":
            running["now"] += 1
            running["max"] = max(running["max"], running["now"])
            try:
                await asyncio.sleep(rf_seconds)
            finally:
                running["now"] -= 1
            return {"factor": name, "score": None, "status": "not_available", "interval": None, "warnings": ["load test: model stood in"], "versions": {}, "features": {}, "provisional": True,
                    "removed": {}, "tasks": None, "model": None}
        return await real(name, evidence, **kw)

    factors.run_factor = stand_in
    tracemalloc.start()
    t0 = time.time()
    try:
        ev = Events(store, rid)
        state = {"run_id": rid, "team_ref": "TL", "sprint_id": "TL-S1", "mode": "snapshot", "repo_url": "x", "students": list(d.evidence)}
        out = await TeamGraph(sv).dispatch_students(state, NodeLog(ev, "team/dispatch_students"), ev)
        await asyncio.to_thread(events_mod.flush, store, rid, 600)
    finally:
        factors.run_factor = real
        _, peak["bytes"] = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        events_mod.close(store, rid)
    outcomes = out["outcomes"]
    return {"students": students, "assessed": sum(1 for o in outcomes.values() if o["status"] != "failed"), "failed": sum(1 for o in outcomes.values() if o["status"] == "failed"),
            "seconds": round(time.time() - t0, 1), "peak_memory_mb": round(peak["bytes"] / 1e6, 1), "max_students_at_once": running["max"], "events": len(store.events[rid]), "db_writes": store.writes,
            "results_saved": len(store.results), "marks_present": sum(1 for o in outcomes.values() if o["mark"] is not None)}
