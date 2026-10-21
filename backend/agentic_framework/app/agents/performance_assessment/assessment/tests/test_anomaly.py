"""Anomaly checks: fixed rules that flag passive data that may be gamed, and a model review whose unsupported numbers are dropped."""
import json

from app.agents.performance_assessment.assessment import anomaly


def commit(i, day, lines):
    return {"id": f"c{i}", "authored_at": f"2026-03-{day:02d}T10:00:00+00:00", "is_merge": False, "files": [{"path": "a.js", "added": lines, "deleted": 0, "line_stats": {"added": {"code": lines, "comment": 0, "blank": 0, "format_only": 0}}}]}


def evidence(commits, **kw):
    return {"sprint": {"id": "S", "start": "2026-03-01", "days": 14}, "commits": commits, "tasks": [], "reviews": [], "pull_requests": [], **kw}


def test_one_big_commit_and_one_day_are_flagged_for_effort():
    e = evidence([commit(1, 13, 900)] + [commit(i, 13, 5) for i in range(2, 8)])
    ids = {a["id"] for a in anomaly.rules("effort", {"features": {"E_LOC_net": 930}}, e)}
    assert {"one_big_commit", "one_day"} <= ids


def test_work_left_to_the_deadline_is_flagged_for_consistency():
    e = evidence([commit(i, 12 + i % 2, 30) for i in range(6)])
    assert "deadline_rush" in {a["id"] for a in anomaly.rules("consistency", {}, e)}


def test_a_repository_without_pull_requests_is_named_not_scored_as_zero():
    found = anomaly.rules("collaboration", {}, evidence([commit(1, 3, 10)]))
    assert found[0]["id"] == "no_pull_requests" and "not scored as 0" in found[0]["message"]


def test_done_tasks_without_commits_are_flagged_for_requirements():
    e = evidence([], tasks=[{"id": "t", "status": "Done", "commit_ids": []}])
    assert "done_without_commits" in {a["id"] for a in anomaly.rules("requirement_fulfillment", {"tasks": []}, e)}


class Llm:
    def __init__(self, rows):
        self.rows = rows

    def chat(self, messages, **kw):
        rows = self.rows

        class R:
            text = json.dumps({"anomalies": rows})
        return R()


def test_model_findings_with_numbers_not_in_the_facts_are_dropped():
    e = evidence([commit(i, 3, 10) for i in range(4)])
    r = {"status": "completed", "score": 0.5, "features": {"E_CC": 4}}
    rows = [{"severity": "warn", "message": "4 commits were made in one afternoon."}, {"severity": "warn", "message": "412 commits were made overnight."}]
    out = anomaly.review(Llm(rows), "effort", r, e, {"measures": "x"}, [], [])
    assert [a["message"] for a in out] == ["4 commits were made in one afternoon."]
    assert anomaly.review(None, "effort", r, e, {}, [], []) == []


def test_memory_digest_carries_marks_scores_and_flags():
    rows = [{"sprint_id": "S1", "mark": 46.2, "status": "final", "factors": {"effort": {"score": 0.48}}, "justification": {"anomalies": {"effort": [{"message": "one day"}]}}}]
    assert anomaly.memory_of(rows) == [{"sprint": "S1", "mark": 46.2, "status": "final", "scores": {"effort": 48}, "anomalies": ["one day"]}]
