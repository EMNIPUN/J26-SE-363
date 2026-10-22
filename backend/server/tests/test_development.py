"""The Development page: the day-by-day chart, the headline numbers and the students worth a look are worked out from the snapshots."""
from datetime import datetime, timezone

from app.modules.performance import service
from tests.test_performance_api import perf, track  # noqa: F401  (fixtures and helpers)
from tests.test_teams_api import lecturer

SPRINT = "T9-S1"


def day(n):
    return datetime(2026, 3, n, 23, 59, 59, tzinfo=timezone.utc)


def rows(*ids):
    return [{"student_id": i, "name": f"Student  {i}", "href": f"/s/{i}", "by_sprint": [{"sprint": SPRINT, "mark": 50.0}, {"sprint": "T9-S2", "mark": 70.0 if i == "A" else None}]} for i in ids]


def snaps(student, marks):
    return [{"student_id": student, "as_of": day(n + 1), "mark": m} for n, m in enumerate(marks)]


def test_the_chart_the_headline_numbers_and_the_students_worth_a_look():
    rs = rows("A", "B", "C")
    shots = snaps("A", [20, 30, 60]) + snaps("B", [60, 55, 20]) + snaps("C", [50, 50, 52])
    v = service.development(rs, shots, [SPRINT, "T9-S2"])

    assert [c["day"] for c in v["chart"]] == ["2026-03-01", "2026-03-02", "2026-03-03"]
    assert v["chart"][0] == {"day": "2026-03-01", "average": 43.3, "low": 20, "high": 60, "marks": {"A": 20, "B": 60, "C": 50}}
    assert v["kpis"]["team_average"] == 44 and v["kpis"]["team_change"] == 0.7 and v["kpis"]["below_40"] == 1       # latest 60, 20, 52
    assert v["kpis"]["most_improved"]["name"] == "Student  A".replace("  ", " ") and v["kpis"]["most_improved"]["change"] == 40
    by = {s["student_id"]: s for s in v["students"]}
    assert by["A"]["trend"] == "rising" and by["B"]["trend"] == "falling" and by["C"]["trend"] == "steady" and by["A"]["spark"] == [20, 30, 60]
    kinds = {(w["student_id"], w["kind"]) for w in v["warnings"]}
    assert ("B", "below_40") in kinds and ("B", "falling") in kinds and ("B", "sudden_drop") in kinds and not any(s == "A" for s, _ in kinds)

    series = v["sprint_series"]                                                                                      # the final mark of everyone in every sprint
    assert series["sprints"] == [SPRINT, "T9-S2"] and series["team"] == [50.0, 70.0]
    assert next(s for s in series["students"] if s["student_id"] == "A")["marks"] == [50.0, 70.0]


def test_with_no_snapshots_nothing_is_invented():
    v = service.development(rows("A"), [], [SPRINT])
    assert v["chart"] == [] and v["warnings"] == [] and v["kpis"]["team_average"] is None and v["kpis"]["most_improved"] is None and v["kpis"]["team_change"] is None


def test_the_endpoint_serves_it(perf):
    lecturer(perf, "ada")
    track(perf)
    for n, (a, b) in enumerate([(20, 70), (35, 60), (60, 30)]):
        perf.store.add_snapshot("T9", SPRINT, "STU-1", day(n + 1), 0.1 * n, mark=a)
        perf.store.add_snapshot("T9", SPRINT, "STU-2", day(n + 1), 0.1 * n, mark=b)
    run = perf.store.create_run("T9", SPRINT, "final")
    for sid, mark in (("STU-1", 60.0), ("STU-2", 30.0)):
        perf.store.save_assessment_result(run["id"], "T9", SPRINT, sid, mark=mark, status="final", mark_interval=[mark - 10, mark + 10], factors={}, justification={}, flags=[])
    d = perf.get("/performance/teams/T9/development").json()
    assert d["kpis"]["snapshots"] == 6 and d["kpis"]["team_average"] == 45 and d["kpis"]["below_40"] == 1
    assert len(d["chart"]) == 3 and set(d["chart"][0]["marks"]) == {"STU-1", "STU-2"}
    assert d["sprint_series"]["team"] == [45.0] and d["warnings"]
