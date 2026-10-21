"""Day by day: the evidence is cut to each day and the measurable factors are run on the cut."""
import asyncio
from datetime import date

from app.agents.performance_assessment.assessment import daily


def commit(i, day):
    return {"id": f"c{i}", "authored_at": f"2026-03-{day:02d}T10:00:00+00:00", "is_merge": False, "subject": "x",
            "files": [{"path": "src/a.js", "status": "M", "added": 10, "deleted": 0, "line_stats": {"added": {"code": 10, "comment": 0, "blank": 0, "format_only": 0}, "deleted": {"code": 0, "comment": 0, "blank": 0, "format_only": 0}}}]}


EVIDENCE = {"schema": "evidence/1", "student_id": "S", "team_id": "T", "sprint": {"id": "T-S1", "start": "2026-03-01", "days": 14},
            "commits": [commit(1, 2), commit(2, 5), commit(3, 9)], "tasks": [{"id": "t", "title": "t", "story_points": 3, "subtask_count": 1, "status": "Done", "commit_ids": ["c1", "c3"]}],
            "reviews": [{"pr_id": "1", "reviewer": "S", "at": "2026-03-08T10:00:00+00:00"}]}


def test_the_evidence_is_cut_to_the_end_of_the_day():
    cut = daily.evidence_on(EVIDENCE, date(2026, 3, 5))
    assert [c["id"] for c in cut["commits"]] == ["c1", "c2"] and cut["reviews"] == [] and cut["tasks"][0]["commit_ids"] == ["c1"]
    assert cut["as_of"].startswith("2026-03-05T23:59:59")
    assert len(EVIDENCE["commits"]) == 3  # the original is untouched


def test_a_finished_sprint_gets_every_day_but_the_last_and_a_running_one_stops_before_today():
    assert len(daily.days_of(date(2026, 3, 1), date(2026, 3, 14))) == 13
    assert daily.days_of(date(2026, 3, 1), date(2026, 3, 14), date(2026, 3, 4)) == [date(2026, 3, 1), date(2026, 3, 2), date(2026, 3, 3)]


def test_each_day_has_a_mark_that_only_uses_what_existed_then():
    points = asyncio.run(daily.trajectory(EVIDENCE, date(2026, 3, 1), date(2026, 3, 14), 14))
    assert len(points) == 13 and points[0]["elapsed"] < points[-1]["elapsed"] < 1.0
    assert points[0]["commits"] == 0 and points[-1]["commits"] == 3
    marks = [p["mark"] for p in points if p["mark"] is not None]
    assert marks and all(0 <= m <= 100 for m in marks)
    assert all(set(p["factors"]) == set(daily.DAILY_FACTORS) for p in points)
