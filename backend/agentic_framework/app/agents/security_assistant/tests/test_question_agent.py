"""Question Generation Component as a bounded agent loop, with the mock Tutor: follow-ups from a different angle, escalation, state."""

import asyncio
import json
import re
import sys

import pytest

from app.agents.security_assistant import guidance as guide
from app.agents.security_assistant import questions as q
from app.agents.security_assistant.agent_loop import Action, LoopConfig
from app.agents.security_assistant.governance import AuditLog
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.tests.test_questions import JAVA, JS, PY, group


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "app.py").write_text(PY, encoding="utf-8")
    (tmp_path / "server.js").write_text(JS, encoding="utf-8")
    (tmp_path / "OrderController.java").write_text(JAVA, encoding="utf-8")
    return tmp_path


def gen(repo, scores, threshold=0.7, retries=2, groups=None, **kw):
    doc = {"groups": groups or [group("G01", "app.py", 10, "sql-injection")]}
    cfg = kw.pop("config", LoopConfig(max_steps=200, max_retries=retries))
    return run(q.generate(doc, repo, q.MockTutor(scores=scores), threshold, PIIRedactor(), config=cfg, **kw))


def chosen(out):
    return [e["chosen"] for e in out["decision_trail"]]


# ---- the goal: closed by the score ---------------------------------------------------------------------------------------------------------------
def test_a_finding_closes_on_attempt_two_after_a_follow_up_from_a_different_angle(repo):
    out = gen(repo, {"keyG01": [0.4, 0.8]})
    item, = out["questions"]
    assert item["decision"] == "closed" and [a["score"] for a in item["attempts"]] == [0.4, 0.8]
    assert chosen(out) == ["ask_question:level 0", "ask_followup:level 1", "close_finding"]
    first, second = item["attempts"]
    assert (first["hint_level"], second["hint_level"]) == (0, 1) and first["text"] != second["text"]  # another angle, not a repeat
    assert [a["result"] for a in item["attempts"]] == ["open", "closed"] and item["question"]["attempt"] == 2
    assert item["question"]["id"].endswith("-a2") and item["tutor_result"]["score"] == 0.8
    assert out["summary"] == {"questions": 1, "closed": 1, "escalated": 0, "attempts": 2, "steps": 3}


def test_a_finding_that_closes_at_once_gets_no_follow_up(repo):
    out = gen(repo, {"keyG01": 0.7})
    assert chosen(out) == ["ask_question:level 0", "close_finding"] and out["questions"][0]["attempts"][0]["result"] == "closed"


# ---- the limit and the escalation ---------------------------------------------------------------------------------------------------------------------
def test_a_finding_that_never_reaches_the_threshold_is_escalated_to_the_lecturer_after_the_limit(repo):
    out = gen(repo, {"keyG01": 0.3})
    item, = out["questions"]
    assert chosen(out) == ["ask_question:level 0", "ask_followup:level 1", "ask_followup:level 2", "escalate_to_lecturer"]
    assert item["decision"] == "escalated" and len(item["attempts"]) == 3 and "limit of 2 follow-up(s) is reached" in item["escalation_reason"]
    assert out["summary"]["escalated"] == 1 and out["summary"]["closed"] == 0 and out["meta"]["max_followups"] == 2


@pytest.mark.parametrize("retries, attempts", [(0, 1), (1, 2), (3, 4)])
def test_the_limit_is_configurable(repo, retries, attempts):
    out = gen(repo, {"keyG01": 0.1}, retries=retries)
    assert len(out["questions"][0]["attempts"]) == attempts and out["questions"][0]["decision"] == "escalated"


def test_state_is_kept_per_finding_and_recorded(repo):
    out = gen(repo, {"keyG01": [0.2, 0.9], "keyG02": 0.1}, groups=[group("G01", "app.py", 10, "sql-injection"), group("G02", "app.py", 7, "ownership-check", "V1")])
    assert [i["state"] for i in out["questions"]] == [
        {"attempts_used": 2, "status": "closed", "scores": [0.2, 0.9]}, {"attempts_used": 3, "status": "escalated", "scores": [0.1, 0.1, 0.1]}]
    state = out["decision_trail"][1]["state"]  # what the policy saw before its second decision
    assert state == {"finding": "G01", "attempts": 1, "scores": [0.2], "threshold": 0.7, "steps_used": 1, "max_steps": 200}
    assert [e["subject"] for e in out["decision_trail"]] == ["G01"] * 3 + ["G02"] * 4


def test_the_mock_tutor_is_asked_once_per_attempt_and_its_answers_can_differ_per_attempt(repo):
    asked = []

    class Counting(q.MockTutor):
        async def ask(self, question):
            asked.append((question.attempt, question.hint_level))
            return await super().ask(question)

    doc = {"groups": [group("G01", "app.py", 10, "sql-injection")]}
    run(q.generate(doc, repo, Counting(scores={"keyG01": [0.1, 0.2, 0.9]}), 0.7, PIIRedactor()))
    assert asked == [(1, 0), (2, 1), (3, 2)]


def test_the_default_simulated_score_rises_with_the_hint_level():
    tutor = q.MockTutor()
    base = q.Question(id="x", finding_key="abc", group_id="G", category="V2", fix_pattern="", file_path=None, line=None, text="", code="", code_source="x")
    scores = [run(tutor.ask(q.Question(**{**base.__dict__, "attempt": n + 1, "hint_level": n}))).score for n in range(3)]
    assert scores[0] <= scores[1] <= scores[2] and scores[2] <= 0.95 and "MOCK" in tutor.label


# ---- the actions are validated in code -------------------------------------------------------------------------------------------------------------------
class ClosesAnything:
    name = "closer"

    def choose(self, state, options):
        return Action("close_finding"), "the model says it is fine"


def test_closing_is_not_a_valid_action_below_the_threshold_so_a_policy_cannot_close_a_finding(repo):
    out = gen(repo, {"keyG01": 0.3}, policy=ClosesAnything())
    item, = out["questions"]
    assert item["decision"] == "escalated" and "close_finding" not in chosen(out)
    rejected = [e for e in out["decision_trail"] if e["rejected"]]
    assert rejected and rejected[0]["rejected"]["proposed"] == "close_finding" and rejected[0]["policy"] == "closer -> rules"


def test_the_options_are_derived_from_the_state(repo):
    cfg = LoopConfig(200, 2)
    assert [a.key for a in q.question_options([], 0.7, cfg)] == ["ask_question:level 0"]
    low = [{"attempt": 1, "score": 0.2}]
    assert [a.name for a in q.question_options(low, 0.7, cfg)] == ["ask_followup", "escalate_to_lecturer"]
    assert [a.name for a in q.question_options(low * 3, 0.7, cfg)] == ["escalate_to_lecturer"]
    assert [a.name for a in q.question_options([{"attempt": 1, "score": 0.7}], 0.7, cfg)] == ["close_finding"]


def test_the_step_budget_sends_what_is_left_to_the_lecturer_with_the_reason(repo):
    out = gen(repo, {"keyG01": 0.1, "keyG02": 0.1}, config=LoopConfig(max_steps=2, max_retries=2),
              groups=[group("G01", "app.py", 10, "sql-injection"), group("G02", "app.py", 7, "ownership-check", "V1")])
    first, second = out["questions"]
    assert first["decision"] == "escalated" and len(first["attempts"]) == 2 and "step budget spent (2 steps)" in first["escalation_reason"]
    assert second["decision"] == "escalated" and second["attempts"] == [] and "step budget spent" in second["escalation_reason"]
    assert out["summary"]["steps"] == 2 and out["questions"][1]["tutor_result"]["answer_summary"].startswith("(not asked")


def test_only_confirmed_findings_get_a_loop(repo):
    out = gen(repo, {}, groups=[group("G01", "app.py", 10, "sql-injection", status="dismissed")])
    assert out["questions"] == [] and out["decision_trail"] == [] and out["summary"]["questions"] == 0


# ---- no follow-up states the fix -----------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("fix", sorted({g.id for g in guide.GUIDANCE}))
@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_no_template_at_any_hint_level_states_the_fix(fix, level):
    text = q.question_text(fix, level, "X", "X", "X", None, None)
    assert q.leaks_fix(text) is None, text


def test_every_hint_level_asks_something_different_and_uses_only_the_students_names(repo):
    texts = []
    for level in range(4):
        question = q.build_question(group("G01", "app.py", 10, "sql-injection"), repo, PIIRedactor(), hint_level=level, attempt=level + 1)
        texts.append(question.text)
        for name in set(re.findall(r"`([^`]+)`", question.text)):
            assert re.search(rf"\b{re.escape(name)}\b", PY), (level, name)
    assert len(set(texts)) == 4


def test_a_template_that_would_state_the_fix_is_refused_at_every_level(repo, monkeypatch):
    monkeypatch.setattr(q, "_followup", lambda *a, **k: "You should use parameterized queries instead.")
    with pytest.raises(ValueError, match="leaks the fix"):
        q.build_question(group("G01", "app.py", 10, "sql-injection"), repo, PIIRedactor(), hint_level=1, attempt=2)


# ---- audit log and report ---------------------------------------------------------------------------------------------------------------------------------------------
def test_every_decision_is_an_audit_line(repo, tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    out = gen(repo, {"keyG01": [0.4, 0.8]}, audit=audit)
    lines = [json.loads(x) for x in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(lines) == len(out["decision_trail"]) == 3 and {e["event"] for e in lines} == {"agent_decision"}
    assert [e["chosen"] for e in lines] == chosen(out) and all(e["component"] == "question agent" and e["outcome"] for e in lines)
    assert lines[1]["state"]["scores"] == [0.4] and lines[2]["outcome"] == "closed after 2 attempt(s)"


def test_the_command_writes_the_attempts_the_decision_trail_and_the_audit_lines(repo, tmp_path):
    p = tmp_path / "interpreted.json"
    p.write_text(json.dumps({"groups": [group("G01", "app.py", 10, "sql-injection"), group("G02", "app.py", 7, "ownership-check", "V1")]}), encoding="utf-8")
    assert run(q.main([str(p), str(repo)], tutor=q.MockTutor(scores={"keyG01": [0.4, 0.8], "keyG02": 0.2}))) == 0
    data = json.loads((tmp_path / "questions.json").read_text(encoding="utf-8"))
    assert [i["decision"] for i in data["questions"]] == ["closed", "escalated"] and data["summary"]["attempts"] == 5
    md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "**Attempt 2 (hint level 1)**" in md and "**Result: escalated**" in md and "escalated to lecturer review" in md
    assert "## Decision trail" in md and "### Question Generation" in md and "`escalate_to_lecturer`" in md and "MOCK TUTOR" in md
    assert any(json.loads(x)["component"] == "question agent" for x in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines())
    assert run(q.main([str(p), str(repo)], tutor=q.MockTutor(scores={"keyG01": 0.9, "keyG02": 0.9}))) == 0  # a second run replaces, not appends
    assert (tmp_path / "report.md").read_text(encoding="utf-8").count("## Probe questions") == 1
    assert (tmp_path / "report.md").read_text(encoding="utf-8").count("### Question Generation") == 1
