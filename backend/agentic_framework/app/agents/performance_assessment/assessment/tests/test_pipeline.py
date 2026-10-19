"""The whole pipeline on a throwaway repository: real git, the real Scrum MCP server (a subprocess), fake GitHub, a scripted language model, in-memory storage."""
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.agents.performance_assessment.assessment import graph as graph_mod
from app.agents.performance_assessment.assessment import quiz_flow, runner
from app.agents.performance_assessment.assessment.memory_store import MemoryStore
from app.agents.performance_assessment.assessment.services import Services
from app.agents.performance_assessment.com_agent.ingestion.scrum_mcp_client import RealScrumMCPClient
from app.agents.performance_assessment.evidence_builder.tests.test_builder import PRS, ROSTER, commit, repo, ws  # noqa: F401  (fixtures)

PA = Path(__file__).resolve().parents[2]
for p in (PA / "factor_models", PA / "factor_models" / "03_requirement_fulfillment"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
SERVER = PA / "mcp_servers" / "scrum_board_server.py"

from experiments.agent_critic import AgentCritic  # noqa: E402
from rf_bench.llm import ScriptedLLM  # noqa: E402


def responder(messages, tag):
    if tag == "audit":
        return json.dumps({"decisions": [], "summary": "Nothing here suggests the results are wrong."})
    if tag == "polish":
        return "A short plain summary."
    return AgentCritic.dry_responder(messages, tag)


class FakeGitHub:
    def __init__(self, prs):
        self.prs, self.calls = prs, 0

    async def pulls_bundle(self, repo_url, since=None, max_prs=150):
        self.calls += 1
        return self.prs


REPORT_PY = """def build_report(rows, threshold):
    total = 0
    result = []
    for row in rows:
        if row > threshold:
            total += row
            result.append(row * 2)
        else:
            result.append(0)
    return total, result
"""


def write_board(folder, first_sha):
    (folder / "scrum_board").mkdir(parents=True)

    def w(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)

    w(folder / "sprints.csv", [{"sprint_id": "T9-S1", "team_id": "T9", "start_date": "2026-03-01", "end_date": "2026-03-14", "length_days": 14, "project_domain": "web"}])
    w(folder / "roster.csv", [{"student_id": s, "team_id": "T9"} for s in ("STU-1", "STU-2", "STU-3")])
    base = {"sprint_id": "T9-S1", "story": "", "subtask_count": 2, "completed_by": "", "carried_over_from": "", "description": "feature"}
    w(folder / "scrum_board" / "T9.csv", [
        {**base, "task_id": "T9-1", "assignee_id": "STU-1", "task_title": "Feature A", "story_points": 3, "status": "Done", "completed_by": "STU-1", "linked_commits": first_sha[:10],
         "acceptance_criteria": "1. a1 returns one; 2. a3 returns done"},
        {**base, "task_id": "T9-2", "assignee_id": "STU-2", "task_title": "Feature B", "story_points": 2, "status": "In Progress", "linked_commits": "", "acceptance_criteria": "1. b returns two"},
        {**base, "task_id": "T9-3", "assignee_id": "STU-3", "task_title": "Docs", "story_points": 1, "status": "To Do", "linked_commits": "", "acceptance_criteria": "1. readme exists"}])


@pytest.fixture()
def world(tmp_path, repo, ws):  # noqa: F811
    board = tmp_path / "board"
    write_board(board, repo.first_commit)
    commit(repo.path, {"report.py": REPORT_PY}, "report totals", "amy", "2026-03-12T10:00:00+05:30")  # a function long enough for the code question
    store = MemoryStore()
    store.upsert_tracked_team("T9", str(repo), "T9", {"roster": json.loads(json.dumps(ROSTER.students))})
    clock = {"now": datetime(2026, 3, 20, tzinfo=timezone.utc)}
    sv = Services(store=store, ws=ws, scrum=lambda: RealScrumMCPClient(args=[str(SERVER)], env={"SCRUM_DATA_DIR": str(board)}), github=FakeGitHub(PRS), llm=ScriptedLLM(responder),
                  work_dir=tmp_path / "runs", parallel_students=2, now=lambda: clock["now"])
    sv.clock = clock
    return sv


def new_run(sv, mode="final"):
    return sv.store.create_run("T9", "T9-S1", mode)["id"]


def events(sv, rid, type=None):
    return [e for e in sv.store.list_events(rid) if type is None or e["type"] == type]


@pytest.mark.asyncio
async def test_final_run_produces_a_result_with_a_justification_for_every_student(world):
    sv = world
    rid = new_run(sv)
    out = await runner.run_assessment(sv, rid)
    assert out["status"] == "succeeded", sv.store.get_run(rid)["error"]
    assert not events(sv, rid, "node_error"), [(e["node_path"], e["message"]) for e in events(sv, rid, "node_error")]
    results = {r["student_id"]: r for r in sv.store.latest_results("T9", "T9-S1")}
    assert set(results) == {"STU-1", "STU-2", "STU-3"}
    for sid, r in results.items():
        assert r["status"] in ("provisional", "pending_review", "final")
        j = r["justification"]
        assert j["summary"] and j["factors"] and j["caveats"]
        assert set(r["factors"]) >= {"effort", "consistency", "collaboration", "task_complexity", "requirement_fulfillment", "code_ownership", "behavioral_pattern"}
    amy = results["STU-1"]
    assert amy["mark"] is not None and amy["mark_interval"][0] <= amy["mark"] <= amy["mark_interval"][1]
    assert amy["factors"]["effort"]["status"] == "completed"
    assert amy["factors"]["requirement_fulfillment"]["status"] == "completed"
    # Code Ownership waits for the student's answer (or has no suitable code); either way it is not a number in the mark
    assert amy["factors"]["code_ownership"]["status"] in ("pending", "not_available")
    # factor rows and the report are stored
    assert len(sv.store.list_factor_results(rid, "STU-1")) >= 6
    assert "| STU-1 |" in sv.store.get_run(rid)["summary"]["report_markdown"]
    assert len(sv.store.trajectory("T9", "T9-S1", "STU-1")) == 1


@pytest.mark.asyncio
async def test_events_follow_the_topology(world):
    sv = world
    rid = new_run(sv)
    await runner.run_assessment(sv, rid)
    topo = graph_mod.topology()
    ids = {n["id"] for n in topo["nodes"]}
    started = [e["node_path"] for e in events(sv, rid, "node_start")]
    assert [p for p in started if p.startswith("team/")] == [f"team/{n}" for n, _ in graph_mod.TEAM_NODES]
    for p in started:
        node = p.split("/", 1)[1]
        assert node in ids, p
    lane = [p.split("/", 1)[1] for p in started if p.startswith("student:STU-1/")]
    assert lane[0] == "student_evidence_check" and lane[-1] == "export" and "factor_audit" in lane
    ends = {e["node_path"] for e in events(sv, rid, "node_end")}
    assert set(started) == ends  # every node that started also finished
    assert not events(sv, rid, "node_error")
    # nothing secret or personal in the event stream
    blob = json.dumps(events(sv, rid), default=str)
    assert "amy@x.org" not in blob and "ghp_" not in blob


@pytest.mark.asyncio
async def test_a_snapshot_is_provisional_and_applies_no_behavioral_adjustment(world):
    sv = world
    sv.clock["now"] = datetime(2026, 3, 8, 12, tzinfo=timezone.utc)
    rid = new_run(sv, "snapshot")
    assert (await runner.run_assessment(sv, rid))["status"] == "succeeded"
    for r in sv.store.latest_results("T9", "T9-S1"):
        assert r["status"] in ("provisional", "pending_review")
        assert r["factors"]["behavioral_pattern"]["applied"] is False
        assert r["factors"]["code_ownership"]["status"] == "pending"
    snap = sv.store.trajectory("T9", "T9-S1", "STU-1")
    assert len(snap) == 1 and 0.4 < snap[0]["sprint_elapsed"] < 0.7
    eff = {r["student_id"]: r["factors"]["effort"] for r in sv.store.latest_results("T9", "T9-S1")}["STU-1"]
    assert eff["provisional"] is True


@pytest.mark.asyncio
async def test_unmapped_authors_stop_the_run_until_the_lecturer_maps_them(world):
    sv = world
    team = sv.store.get_tracked_team("T9")
    for s in team["config"]["roster"]:
        if s["student_id"] == "STU-2":
            s["emails"], s["names"] = [], []  # Bob's commits can no longer be attributed
    rid = new_run(sv)
    out = await runner.run_assessment(sv, rid)
    assert out["status"] == "waiting_human" and sv.store.get_run(rid)["status"] == "waiting_human"
    reviews = sv.store.list_reviews("open", rid)
    assert [r["kind"] for r in reviews] == ["identity_mapping"]
    assert any("bob@x.org" in a for a in reviews[0]["evidence"]["unmapped_authors"])
    assert events(sv, rid, "node_wait")
    assert not sv.store.latest_results("T9", "T9-S1")
    out = await runner.run_assessment(sv, rid, resume={"mapping": [{"email": "bob@x.org", "student_id": "STU-2"}]})
    assert out["status"] == "succeeded", sv.store.get_run(rid)["error"]
    bob = {r["student_id"]: r for r in sv.store.latest_results("T9", "T9-S1")}["STU-2"]
    assert bob["factors"]["effort"]["status"] == "completed" and bob["factors"]["effort"]["score"] > 0
    assert "bob@x.org" in json.dumps(sv.store.get_tracked_team("T9")["config"]["roster"])  # the mapping is kept for the next run


@pytest.mark.asyncio
async def test_one_failing_student_does_not_stop_the_team(world, monkeypatch):
    sv = world
    original = graph_mod.StudentPipeline.check

    async def broken(self, state, n):
        if self.sid == "STU-3":
            raise RuntimeError("boom")
        return await original(self, state, n)

    monkeypatch.setattr(graph_mod.StudentPipeline, "check", broken)
    rid = new_run(sv)
    assert (await runner.run_assessment(sv, rid))["status"] == "succeeded"
    got = {r["student_id"] for r in sv.store.latest_results("T9", "T9-S1")}
    assert got == {"STU-1", "STU-2"}
    assert any(e["node_path"].startswith("student:STU-3") for e in events(sv, rid, "node_error"))
    assert "could not be assessed" in sv.store.get_run(rid)["summary"]["report_markdown"]


@pytest.mark.asyncio
async def test_quiz_answer_completes_code_ownership_and_recomposes_the_mark(world, monkeypatch):
    sv = world
    rid = new_run(sv)
    await runner.run_assessment(sv, rid)
    quiz = sv.store.get_quiz("T9", "T9-S1", "STU-1")
    if quiz is None:
        pytest.skip("the throwaway repository has no function the quiz generator accepts")
    assert quiz["status"] == "open" and quiz["question"] and quiz["snippet"]
    before = {r["student_id"]: r for r in sv.store.latest_results("T9", "T9-S1")}["STU-1"]
    assert before["factors"]["code_ownership"]["status"] == "pending" and before["status"] == "provisional"

    async def fake_score(q):
        return {"factor": "code_ownership", "score": 0.9, "status": "completed", "interval": [0.8, 1.0], "warnings": [], "versions": {}, "features": {"comprehension_rating_1_to_5": 4.6}, "provisional": False,
                "removed": {}, "tasks": None, "model": "fake"}

    monkeypatch.setattr(quiz_flow, "score_answer", fake_score)
    res = await runner.answer_quiz(sv, quiz["id"], "STU-1", "It builds the total of the two numbers and returns it.", now=sv.clock["now"] + timedelta(hours=1))
    assert res["accepted"] and res["result"]["status"] in ("final", "pending_review")
    after = {r["student_id"]: r for r in sv.store.latest_results("T9", "T9-S1")}["STU-1"]
    assert after["factors"]["code_ownership"]["score"] == 0.9
    assert after["mark"] != before["mark"]
    assert "code_ownership" in after["justification"]["factors"]
    # a second answer is refused, and so is someone else's
    assert not (await runner.answer_quiz(sv, quiz["id"], "STU-1", "again", now=sv.clock["now"] + timedelta(hours=2)))["accepted"]
    assert not (await runner.answer_quiz(sv, quiz["id"], "STU-2", "mine", now=sv.clock["now"] + timedelta(hours=2)))["accepted"]


@pytest.mark.asyncio
async def test_unanswered_quiz_gets_a_second_window_then_counts_as_zero(world):
    sv = world
    rid = new_run(sv)
    await runner.run_assessment(sv, rid)
    quiz = sv.store.get_quiz("T9", "T9-S1", "STU-1")
    if quiz is None:
        pytest.skip("the throwaway repository has no function the quiz generator accepts")
    t0 = quiz["deadline_at"]
    assert (await runner.sweep_quizzes(sv, t0 - timedelta(hours=1))) == {"extended": 0, "expired": 0}
    assert (await runner.sweep_quizzes(sv, t0 + timedelta(hours=1))) == {"extended": 1, "expired": 0}
    assert sv.store.get_quiz("T9", "T9-S1", "STU-1")["status"] == "extended"
    assert (await runner.sweep_quizzes(sv, t0 + timedelta(hours=60)))["expired"] == 1
    r = {r["student_id"]: r for r in sv.store.latest_results("T9", "T9-S1")}["STU-1"]
    assert r["factors"]["code_ownership"]["score"] == 0.0 and r["factors"]["code_ownership"]["status"] == "completed"
    assert r["status"] in ("final", "pending_review")


@pytest.mark.asyncio
async def test_without_a_language_model_requirement_fulfillment_is_not_available_not_zero(world):
    sv = world
    sv.llm = None
    rid = new_run(sv)
    assert (await runner.run_assessment(sv, rid))["status"] == "succeeded"
    amy = {r["student_id"]: r for r in sv.store.latest_results("T9", "T9-S1")}["STU-1"]
    assert amy["factors"]["requirement_fulfillment"]["status"] == "not_available"
    assert "requirement_fulfillment" not in amy["justification"]["summary"].lower().split("not part of the mark")[0]
    assert amy["mark"] is not None
