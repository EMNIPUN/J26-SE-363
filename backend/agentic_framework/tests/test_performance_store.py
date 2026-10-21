"""PerformanceStore against a throwaway local PostgreSQL (SELVIA_TEST_DSN, default: the docker container on port 55432). Skipped when it is not reachable.

    docker run -d --name selvia-test-pg -e POSTGRES_PASSWORD=test -e POSTGRES_DB=selvia -p 55432:5432 postgres:16-alpine
"""
import os
import threading
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from shared.performance import PerformanceStore, RunAlreadyActive, thread_id_for

DSN = os.environ.get("SELVIA_TEST_DSN", "postgresql://postgres:test@localhost:55432/selvia")


def _reachable():
    try:
        psycopg.connect(DSN, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="no local test PostgreSQL")


@pytest.fixture()
def store():
    s = PerformanceStore(DSN)
    s.ensure_schema()
    with psycopg.connect(DSN, autocommit=True) as c:
        c.execute("TRUNCATE perf_runs, perf_tracked_teams, perf_snapshots, perf_quizzes CASCADE")
    yield s
    s.close()


def test_schema_is_idempotent(store):
    store.ensure_schema()
    store.ensure_schema()


def test_tracked_team_upsert_and_status(store):
    t = store.upsert_tracked_team("T01", "https://github.com/org/repo", "board-1", {"sync_hours": 2}, "lecturer-1")
    assert t["team_ref"] == "T01" and t["status"] == "active"
    again = store.upsert_tracked_team("T01", "https://github.com/org/repo2")
    assert again["id"] == t["id"] and again["repo_url"].endswith("repo2")
    assert store.set_tracking_status("T01", "paused")["status"] == "paused"
    assert [x["team_ref"] for x in store.list_tracked_teams("paused")] == ["T01"]
    assert store.list_tracked_teams("active") == []


def test_run_lifecycle_and_duplicate_guard(store):
    run = store.create_run("T01", "T01-S1", "final", requested_by="u1")
    assert run["status"] == "queued" and run["thread_id"] == thread_id_for("T01", "T01-S1")
    with pytest.raises(RunAlreadyActive) as e:
        store.create_run("T01", "T01-S1", "final")
    assert e.value.run["id"] == run["id"]
    assert store.create_run("T01", "T01-S1", "snapshot")["id"] != run["id"]  # another mode is allowed
    r = store.update_run(run["id"], status="running", current_node="prepare_workspace")
    assert r["status"] == "running" and r["started_at"] is not None and r["current_node"] == "prepare_workspace"
    r = store.update_run(run["id"], status="succeeded", summary={"students": 4})
    assert r["finished_at"] is not None and r["summary"] == {"students": 4}
    assert store.create_run("T01", "T01-S1", "final")["status"] == "queued"  # allowed again once the first finished
    with pytest.raises(ValueError):
        store.update_run(run["id"], status="exploded")


def test_events_are_ordered_filtered_and_numbered_even_when_written_concurrently(store):
    run = store.create_run("T02", "T02-S1", "final")
    store.add_event(run["id"], "node_start", "start", node_path="team/load")
    store.add_event(run["id"], "log", "hello", node_path="team/student:STU-1/effort", payload={"x": 1})

    def burst():
        for _ in range(10):
            store.add_event(run["id"], "log", "c")

    threads = [threading.Thread(target=burst) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    ev = store.list_events(run["id"])
    assert [e["seq"] for e in ev] == list(range(1, 53))
    assert store.list_events(run["id"], after=50)[0]["seq"] == 51
    sub = store.list_events(run["id"], node_path="team/student:STU-1")
    assert [e["message"] for e in sub] == ["hello"] and sub[0]["payload"] == {"x": 1}


def test_factor_and_assessment_results_upsert(store):
    run = store.create_run("T03", "T03-S1", "final")
    f = store.save_factor_result(run["id"], "STU-1", "effort", score=0.61, status="completed", interval=[0.5, 0.7], features={"E_CC": 12}, warnings=["w"], versions={"cleaning": "1.0.0"})
    assert f["score"] == 0.61 and f["interval"] == [0.5, 0.7]
    store.save_factor_result(run["id"], "STU-1", "effort", score=0.7, status="completed")
    store.save_factor_result(run["id"], "STU-1", "collaboration", score=None, status="not_available", warnings=["nobody reviewed"])
    assert {x["factor"]: x["score"] for x in store.list_factor_results(run["id"], "STU-1")} == {"effort": 0.7, "collaboration": None}
    store.save_assessment_result(run["id"], "T03", "T03-S1", "STU-1", mark=61.0, status="provisional", factors={"effort": 0.7})
    store.save_assessment_result(run["id"], "T03", "T03-S1", "STU-2", mark=40.0, status="final")
    r2 = store.create_run("T03", "T03-S1", "snapshot")
    store.save_assessment_result(r2["id"], "T03", "T03-S1", "STU-2", mark=45.0, status="provisional")
    latest = {r["student_id"]: r for r in store.latest_results("T03", "T03-S1")}
    assert latest["STU-2"]["status"] == "final" and latest["STU-2"]["mark"] == 40.0  # a final result is not replaced by a later provisional one
    assert store.set_override(run["id"], "STU-1", {"mark": 70, "reason": "x"})["override"]["mark"] == 70


def test_snapshots_form_a_trajectory(store):
    for day in (1, 2, 3):
        store.add_snapshot("T04", "T04-S1", "STU-1", f"2026-03-0{day}T00:00:00Z", day / 14, mark=10.0 * day, factors={"effort": day / 10})
    store.add_snapshot("T04", "T04-S1", "STU-1", "2026-03-03T00:00:00Z", 3 / 14, mark=31.0)  # same moment: replaced
    tr = store.trajectory("T04", "T04-S1", "STU-1")
    assert [round(t["sprint_elapsed"], 3) for t in tr] == [0.071, 0.143, 0.214] and tr[-1]["mark"] == 31.0


def test_reviews_are_decided_once(store):
    run = store.create_run("T05", "T05-S1", "final")
    rv = store.create_review(run["id"], "critical_flag", "ghostwriter suspicion", student_id="STU-1", evidence={"alerts": 1})
    assert [r["id"] for r in store.list_reviews("open")] == [rv["id"]]
    assert store.decide_review(rv["id"], {"action": "accept"}, "lecturer-1")["status"] == "decided"
    assert store.decide_review(rv["id"], {"action": "override"}) is None  # already decided
    assert store.list_reviews("open") == [] and len(store.list_reviews("decided")) == 1


def _quiz(store, hours=48):
    t0 = datetime(2026, 3, 20, tzinfo=timezone.utc)
    q = store.create_quiz("T9", "T9-S1", "STU-1", question="What does a2 do?", snippet="def a2(): ...", file_path="a.py", line_range=[1, 9], meta={"facts": {"x": 1}}, deadline_at=t0 + timedelta(hours=hours))
    return q, t0


def test_one_quiz_per_student_and_sprint(store):
    q, _ = _quiz(store)
    again = store.create_quiz("T9", "T9-S1", "STU-1", question="Another?", snippet="x", file_path=None, line_range=None, meta={}, deadline_at=q["deadline_at"])
    assert again["id"] == q["id"] and again["question"] == "What does a2 do?"
    assert store.get_quiz("T9", "T9-S1", "STU-1")["status"] == "open"
    assert [x["id"] for x in store.list_student_quizzes("STU-1", "open")] == [q["id"]] and store.list_student_quizzes("STU-2") == []


def test_answer_in_first_window_then_refused(store):
    q, t0 = _quiz(store)
    row = store.submit_quiz_answer(q["id"], "it adds", now=t0 + timedelta(hours=10))
    assert row["status"] == "answered" and row["in_extension"] is False and row["answer"] == "it adds"
    assert store.submit_quiz_answer(q["id"], "again", now=t0 + timedelta(hours=11)) is None
    assert store.set_quiz_result(q["id"], {"score": 0.5})["result"] == {"score": 0.5}


def test_windows_extend_then_expire_and_late_answers_are_refused(store):
    q, t0 = _quiz(store, hours=48)
    deadline = q["deadline_at"]
    assert store.submit_quiz_answer(q["id"], "late", now=deadline + timedelta(hours=1)) is None  # first window over, not yet moved to the second
    assert store.advance_quiz_windows(48, now=deadline - timedelta(hours=1)) == []
    moved = store.advance_quiz_windows(48, now=deadline + timedelta(hours=1))
    assert [m["status"] for m in moved] == ["extended"]
    row = store.submit_quiz_answer(q["id"], "in the second window", now=deadline + timedelta(hours=5))
    assert row["in_extension"] is True and row["status"] == "answered"
    q2 = store.create_quiz("T9", "T9-S1", "STU-2", question="q", snippet="s", file_path=None, line_range=None, meta={}, deadline_at=deadline)
    store.advance_quiz_windows(48, now=deadline + timedelta(hours=1))
    gone = store.advance_quiz_windows(48, now=deadline + timedelta(hours=60))
    assert [m["id"] for m in gone] == [q2["id"]] and gone[0]["status"] == "expired"
    assert store.submit_quiz_answer(q2["id"], "too late", now=deadline + timedelta(hours=61)) is None
