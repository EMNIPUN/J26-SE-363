"""What stops the agent, and what a bad day looks like: a factor that never returns, a student that never finishes, a run that is too long, a database that refuses writes."""
import asyncio
import time

import pytest

from app.agents.performance_assessment.assessment import audit, events as events_mod, factors, graph as graph_mod, runner
from app.agents.performance_assessment.assessment.memory_store import MemoryStore
from app.agents.performance_assessment.assessment.tests.test_pipeline import events, new_run, repo, world, ws  # noqa: F401  (fixtures)


# ---- the run always ends -------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_factor_that_never_returns_is_stopped_and_the_run_still_ends(world, monkeypatch):
    sv = world
    monkeypatch.setattr(graph_mod, "FACTOR_TIMEOUT", 1.5)
    real = factors.run_factor

    async def hang(name, evidence, **kw):
        if name == "task_complexity":
            await asyncio.sleep(3600)
        return await real(name, evidence, **kw)

    monkeypatch.setattr(factors, "run_factor", hang)
    rid = new_run(sv)
    t0 = time.time()
    out = await asyncio.wait_for(runner.run_assessment(sv, rid), 240)
    assert out["status"] == "succeeded" and time.time() - t0 < 200
    amy = {r["student_id"]: r for r in sv.store.latest_results("T9", "T9-S1")}["STU-1"]
    assert amy["factors"]["task_complexity"]["status"] == "fallback"
    assert amy["mark"] is not None  # the other factors still make a mark; the stopped one is left out, not counted as 0
    assert any("did not finish within" in w for r in sv.store.list_factor_results(rid, "STU-1") for w in r["warnings"] if r["factor"] == "task_complexity")


@pytest.mark.asyncio
async def test_a_student_pipeline_that_never_finishes_is_stopped_and_reported(world, monkeypatch):
    sv = world
    monkeypatch.setattr(graph_mod, "STUDENT_TIMEOUT", 2.0)
    original = graph_mod.StudentPipeline.check

    async def slow(self, state, n):
        if self.sid == "STU-3":
            await asyncio.sleep(3600)
        return await original(self, state, n)

    monkeypatch.setattr(graph_mod.StudentPipeline, "check", slow)
    rid = new_run(sv)
    assert (await asyncio.wait_for(runner.run_assessment(sv, rid), 240))["status"] == "succeeded"
    assert {r["student_id"] for r in sv.store.latest_results("T9", "T9-S1")} == {"STU-1", "STU-2"}
    assert any("did not finish within" in e["message"] and e["node_path"] == "student:STU-3" for e in events(sv, rid, "node_error"))
    assert "could not be assessed" in sv.store.get_run(rid)["summary"]["report_markdown"]


@pytest.mark.asyncio
async def test_a_run_that_takes_too_long_is_marked_failed(world, monkeypatch):
    sv = world
    monkeypatch.setattr(runner, "RUN_TIMEOUT", 3.0)
    original = graph_mod.TeamGraph.prepare_workspace

    async def slow(self, state, n, ev):
        await asyncio.sleep(3600)

    monkeypatch.setattr(graph_mod.TeamGraph, "prepare_workspace", slow)
    rid = new_run(sv)
    out = await asyncio.wait_for(runner.run_assessment(sv, rid), 60)
    run = sv.store.get_run(rid)
    assert out["status"] == "failed" and run["status"] == "failed" and run["error"]["type"] == "Timeout"
    assert events(sv, rid, "run_end")[-1]["level"] == "error"
    assert original is not None


# ---- the event log -------------------------------------------------------------------------------------------------------------------

def test_events_are_written_in_order_in_batches_and_flushed():
    class Counting(MemoryStore):
        def __init__(self):
            super().__init__()
            self.batches = []

        def add_events(self, run_id, evs):
            self.batches.append(len(evs))
            time.sleep(0.05)  # a database that is a little slow
            return super().add_events(run_id, evs)

    store = Counting()
    run = store.create_run("T", "S", "final")
    ev = events_mod.Events(store, run["id"])
    t0 = time.time()
    for i in range(300):
        ev.emit("log", f"m{i}", node_path="team/x")
    assert time.time() - t0 < 1.0  # emitting never waits for the database
    assert ev.flush(10)
    got = [e["message"] for e in store.list_events(run["id"])]
    assert got == [f"m{i}" for i in range(300)]
    assert len(store.batches) < 30  # many events per round trip
    events_mod.close(store, run["id"])


def test_a_database_that_refuses_writes_does_not_stop_the_run():
    class Flaky(MemoryStore):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def add_events(self, run_id, evs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("max clients reached")
            return super().add_events(run_id, evs)

    store = Flaky()
    run = store.create_run("T", "S", "final")
    ev = events_mod.Events(store, run["id"])
    ev.emit("log", "first")
    assert ev.flush(10)  # the first write failed and was tried again
    assert [e["message"] for e in store.list_events(run["id"])] == ["first"]
    events_mod.close(store, run["id"])


# ---- findings that said the wrong thing --------------------------------------------------------------------------------------------

def res(name, score, status="completed"):
    return {"factor": name, "score": score, "status": status, "interval": None, "warnings": [], "versions": {}, "features": {}, "provisional": False, "removed": {}, "tasks": None, "model": None}


def test_commits_that_only_touch_configuration_are_not_blamed_on_an_unmapped_email():
    ev = {"student_id": "S", "commits": [{"id": "a"}] * 19, "tasks": [{"status": "Done", "completed_by": "S"}], "pull_requests": []}
    found = audit.findings({"effort": res("effort", 0.0)}, ev)
    assert [f["code"] for f in found if f["severity"] != "info"] == ["commits_not_counted"]
    assert "19 commits" in found[0]["message"] and "does not mean the student did nothing" in found[0]["message"]
    assert audit.decide(found, None)[0]["action"] == "accept"  # a warning to read, not a reason to stop the lecturer
    ev["commits"] = []
    assert [f["code"] for f in audit.findings({"effort": res("effort", 0.0)}, ev)] == ["silent_but_visible"]


def test_a_model_that_proposes_a_retry_that_cannot_help_gets_a_clear_reason():
    found = audit.findings({"effort": res("effort", 0.0)}, {"student_id": "S", "commits": [], "tasks": [{"status": "Done", "completed_by": "S"}]})
    out = audit.decide(found, {"decisions": {found[0]["id"]: {"action": "retry", "reason": "The score is 0 but work is visible."}}})
    assert out[0]["action"] == "escalate" and out[0]["reason"].startswith("The score is 0") and "cannot fix this" in out[0]["reason"]
