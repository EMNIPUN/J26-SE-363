"""The final mark is the average over every sprint, on the lecturer's report and on the student's own page; a single sprint can still be read alone."""
from tests.test_performance_api import perf, me, track_with_ids  # noqa: F401  (fixtures and helpers)
from tests.test_teams_api import lecturer, student

SPRINTS = [{"id": f"T9-S{n}", "start": f"2026-0{n}-01", "end": f"2026-0{n}-14"} for n in (1, 2, 3)]
ANN = {"T9-S1": 60.0, "T9-S2": 30.0, "T9-S3": 90.0}   # the last sprint (90) is not the final mark: the average is 60
BEN = {"T9-S1": 20.0, "T9-S2": 20.0, "T9-S3": 20.0}


def save_sprint(perf, sprint_id, marks, *, status="final"):
    """One finished run of a sprint, with one result for each student in ``marks`` ({student id: mark})."""
    run = perf.store.create_run("T9", sprint_id, "final")
    for student_id, mark in marks.items():
        perf.store.save_assessment_result(run["id"], "T9", sprint_id, student_id, mark=mark, status=status, mark_interval=[mark - 10, mark + 10],
                                          factors={"effort": {"score": mark / 100, "status": "completed"}},
                                          justification={"summary": f"about {sprint_id}", "caveats": [], "flags": [],
                                                          "factors": {"effort": {"reasons": [f"effort in {sprint_id}"], "explain": {"in_short": f"Effort in {sprint_id}"}}}}, flags=[])
    perf.store.update_run(run["id"], status="succeeded")


def set_up(perf, last_sprint_status="final"):
    student(perf, "ann")
    student(perf, "ben")
    lecturer(perf, "ada")
    ann, ben = me(perf, "ann"), me(perf, "ben")
    perf.sign_in("ada", email="ada@example.com", name="Ada")
    track_with_ids(perf, ann, ben, sprints=SPRINTS)
    for sprint in SPRINTS[:-1]:
        save_sprint(perf, sprint["id"], {ann: ANN[sprint["id"]], ben: BEN[sprint["id"]]})
    save_sprint(perf, "T9-S3", {ann: ANN["T9-S3"]}, status=last_sprint_status)              # Ann's last sprint may still be under review
    save_sprint(perf, "T9-S3", {ben: BEN["T9-S3"]})
    return ann, ben


def test_the_lecturer_report_opens_on_the_final_mark_and_a_sprint_can_be_read_alone(perf):
    ann, _ben = set_up(perf)
    final = perf.get(f"/performance/teams/T9/students/{ann}/report").json()
    assert final["scope"] == "overall" and final["sprints_counted"] == 3
    assert final["mark"] == final["effective_mark"] == final["hero"]["mark"] == 60.0     # not 90, the last sprint's
    assert abs(final["factors"]["effort"]["score"] - 0.6) < 1e-9 and final["factors"]["effort"]["sprints_scored"] == 3
    assert final["can_override"] is False and final["narrative_sprint"] == "T9-S3"
    assert "Final mark 60" in final["hero"]["summary"] and "T9-S1 60" in final["hero"]["summary"] and "T9-S3 90" in final["hero"]["summary"]
    # the team average of a factor is over the same final results: (0.6 + 0.2) / 2
    assert abs(final["team_average"]["effort"] - 0.4) < 1e-9
    assert next(a for a in final["radar"]["axes"] if a["id"] == "effort")["average"] == 40.0
    assert perf.get(f"/performance/teams/T9/students/{ann}/report", params={"sprint": "overall"}).json()["mark"] == 60.0
    # the factor cards are read one sprint at a time: each sprint has its own score and the agent's explanation for it; the final result has no explanation of its own
    cards = final["sprint_factors"]
    assert list(cards) == ["T9-S1", "T9-S2", "T9-S3"]
    assert [round(cards[sid]["factors"]["effort"]["score"], 2) for sid in cards] == [0.6, 0.3, 0.9]
    assert cards["T9-S2"]["factors"]["effort"]["explain"] == "Effort in T9-S2" and cards["T9-S2"]["factors"]["effort"]["reasons"] == ["effort in T9-S2"]
    assert final["factors"]["effort"]["explain"] is None and cards["T9-S3"]["mark"] == 90.0

    one = perf.get(f"/performance/teams/T9/students/{ann}/report", params={"sprint": "T9-S3"}).json()
    assert one["scope"] == "sprint" and one["mark"] == 90.0 and one["can_override"] is True
    assert abs(one["team_average"]["effort"] - 0.55) < 1e-9                                # (0.9 + 0.2) / 2: that sprint's cohort


def test_a_sprint_still_under_review_does_not_count_towards_the_final_mark(perf):
    ann, _ben = set_up(perf, last_sprint_status="pending_review")                          # her last sprint is not yet looked at by a person
    final = perf.get(f"/performance/teams/T9/students/{ann}/report").json()
    assert final["sprints_counted"] == 2 and final["mark"] == 45.0                         # (60 + 30) / 2


def test_the_team_results_and_the_student_page_agree_on_the_final_mark(perf):
    ann, _ben = set_up(perf)
    overview = perf.get("/performance/teams/T9/overview").json()
    row = next(r for r in overview["rows"] if r["student_id"] == ann)
    assert overview["scope"] == "overall" and row["effective_mark"] == 60.0 and overview["kpis"]["average_mark"] == 40  # (60 + 20) / 2

    me(perf, "ann")                                                                         # sign in as the student
    mine = perf.get("/performance/me/reports", params={"team": "T9"}).json()
    assert mine["overall"]["scope"] == "overall" and mine["overall"]["mark"] == 60.0 and mine["overall"]["sprints_counted"] == 3
    assert [r["sprint"]["id"] for r in mine["reports"]] == ["T9-S1", "T9-S2", "T9-S3"]      # the sprint by sprint reports are still there
    assert abs(mine["overall"]["factors"]["effort"]["score"] - 0.6) < 1e-9
    assert list(mine["overall"]["sprint_factors"]) == ["T9-S1", "T9-S2", "T9-S3"]
    assert mine["overall"]["sprint_factors"]["T9-S2"]["factors"]["effort"]["score"] == 0.3
