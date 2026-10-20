"""The assessment of a platform team: who may see it, what the agent is given, and that a student only ever sees their own result."""
import json

import pytest

from tests.test_github_api import as_user, connect, gh, install, make_team  # noqa: F401  (fixtures)
from tests.test_performance_api import SPRINT, perf, result  # noqa: F401  (fixtures)
from tests.test_teams_api import lecturer, student

CODE = "TEAM-ALPHA"
SPRINTS = [{"id": SPRINT, "start": "2026-03-01", "end": "2026-03-14"}]


def account_id(api, sub):
    as_user(api, sub)
    return api.get("/me").json()["id"]


@pytest.fixture()
def team(gh, perf):  # noqa: F811
    """Ada's team with Sam as leader; the repository is linked and Sam and Kim have connected GitHub (Lee has not)."""
    make_team(gh)
    install(gh)
    as_user(gh, "sam")
    gh.put(f"/teams/{CODE}/github/repo", {"full_name": "acme/app"})
    gh.sign_out()
    connect(gh, "sam", "good-ann")
    connect(gh, "kim", "good-bob")
    as_user(gh, "ada")
    assert gh.put(f"/performance/teams/{CODE}/settings", {"sprints": SPRINTS}).status_code == 200
    return gh


def test_a_team_that_is_not_linked_cannot_be_assessed_and_the_answer_says_why(gh, perf):  # noqa: F811
    make_team(gh)
    as_user(gh, "ada")
    gh.put(f"/performance/teams/{CODE}/settings", {"sprints": SPRINTS})
    r = gh.post(f"/performance/teams/{CODE}/runs", {"sprint_id": SPRINT})
    assert r.status_code == 409 and r.json()["code"] == "not_ready" and "GitHub App" in r.json()["detail"]
    assert gh.get(f"/performance/teams/{CODE}/readiness").json()["ready"] is False
    assert perf.jobs.sent == []


def test_the_agent_is_given_account_ids_verified_logins_and_github_addresses(team, perf):
    sam, kim, lee = (account_id(team, s) for s in ("sam", "kim", "lee"))
    as_user(team, "ada")
    r = team.post(f"/performance/teams/{CODE}/runs", {"sprint_id": SPRINT, "mode": "snapshot"})
    assert r.status_code == 202
    tracked = perf.store.get_tracked_team(CODE)
    assert tracked["repo_url"] == "https://github.com/acme/app" and tracked["config"]["installation_id"] == 7 and tracked["config"]["source"] == "platform"
    roster = {s["student_id"]: s for s in tracked["config"]["roster"]}
    assert set(roster) == {sam, kim, lee}  # our own ids, so a result belongs to the logged-in person
    assert roster[sam]["logins"] == ["ann-dev"] and "4242+ann-dev@users.noreply.github.com" in roster[sam]["emails"]
    assert roster[kim]["logins"] == ["bob"]
    assert roster[lee]["logins"] == [] and not any("noreply" in e for e in roster[lee]["emails"])  # Lee has not connected: nothing is guessed
    assert perf.jobs.sent[-1]["task"] == "performance.assess_team" and perf.jobs.sent[-1]["lock"] == CODE


def test_a_sprint_must_be_set_up_before_a_run(team):
    as_user(team, "ada")
    r = team.post(f"/performance/teams/{CODE}/runs", {"sprint_id": "no-such-sprint"})
    assert r.status_code == 400 and r.json()["code"] == "unknown_sprint"


def test_only_the_teams_lecturers_and_administrators_see_the_assessment(team, perf):
    as_user(team, "ada")
    run_id = team.post(f"/performance/teams/{CODE}/runs", {"sprint_id": SPRINT}).json()["run_id"]
    perf.store.add_event(run_id, "log", "hello", node_path="team/publish")
    assert [t["team_ref"] for t in team.get("/performance/teams").json()] == [CODE]
    lecturer(team, "bob")  # a lecturer of the university, but not of this team
    assert team.get("/performance/teams").json() == []
    for path in (f"/performance/runs/{run_id}", f"/performance/runs/{run_id}/events", f"/performance/runs/{run_id}/report", f"/performance/teams/{CODE}/readiness",
                 f"/performance/teams/{CODE}/sprints/{SPRINT}/results", f"/performance/teams/{CODE}/runs"):
        assert team.get(path).status_code == 404, path
    assert team.post(f"/performance/runs/{run_id}/rerun").status_code == 404
    assert team.post(f"/performance/teams/{CODE}/runs", {"sprint_id": SPRINT}).status_code == 404
    for sub in ("sam", "kim", "lee"):  # the students of the team, and a student of no team
        as_user(team, sub)
        for path in (f"/performance/runs/{run_id}", f"/performance/runs/{run_id}/events", "/performance/teams", "/performance/graph"):
            assert team.get(path).status_code == 403, (sub, path)
    student(team, "eve")
    assert team.get(f"/performance/runs/{run_id}/events").status_code == 403
    team.sign_in("root", admin=True, email="root@example.com")
    assert team.get(f"/performance/runs/{run_id}").status_code == 200 and team.get(f"/performance/teams/{CODE}/readiness").status_code == 200


def test_a_student_sees_only_their_own_result_of_a_platform_team(team, perf):
    sam, kim = account_id(team, "sam"), account_id(team, "kim")
    as_user(team, "ada")
    run_id = team.post(f"/performance/teams/{CODE}/runs", {"sprint_id": SPRINT}).json()["run_id"]
    result(perf.store, run_id, sam, 81.0, team=CODE)
    result(perf.store, run_id, kim, 44.0, team=CODE)
    rows = team.get(f"/performance/teams/{CODE}/sprints/{SPRINT}/results").json()
    assert {r["student"]["name"] for r in rows} == {"Sam", "Kim"}  # the lecturer sees names, not ids
    as_user(team, "sam")
    mine = team.get("/performance/me/results").json()
    assert [r["student_id"] for r in mine] == [sam] and mine[0]["mark"] == 81.0
    assert kim not in json.dumps(mine) and 44.0 not in [r.get("mark") for r in mine]  # nothing of the teammate: not the id, not the mark
    as_user(team, "lee")
    assert team.get("/performance/me/results").json() == []
    student(team, "eve")
    assert team.get("/performance/me/results").json() == []


def test_a_member_who_leaves_the_team_loses_the_result(team, perf):
    sam, kim = account_id(team, "sam"), account_id(team, "kim")
    as_user(team, "ada")
    run_id = team.post(f"/performance/teams/{CODE}/runs", {"sprint_id": SPRINT}).json()["run_id"]
    result(perf.store, run_id, kim, 44.0, team=CODE)
    as_user(team, "kim")
    assert len(team.get("/performance/me/results").json()) == 1
    assert team.delete(f"/teams/{CODE}/members/{kim}").status_code in (200, 204)  # leaves
    assert team.get("/performance/me/results").json() == []
    assert sam


def test_evaluate_again_starts_a_new_run_only_when_none_is_active(team, perf):
    as_user(team, "ada")
    first = team.post(f"/performance/teams/{CODE}/runs", {"sprint_id": SPRINT}).json()["run_id"]
    assert team.post(f"/performance/runs/{first}/rerun").status_code == 409  # still queued
    perf.store.update_run(first, status="succeeded")
    again = team.post(f"/performance/runs/{first}/rerun")
    assert again.status_code == 202 and again.json()["previous_run_id"] == first and again.json()["run_id"] != first
    assert perf.store.get_run(first)["status"] == "succeeded"  # the earlier run is untouched
    assert perf.jobs.sent[-1]["task"] == "performance.assess_team"


def test_the_team_list_says_what_is_missing(gh, perf):  # noqa: F811
    make_team(gh)
    as_user(gh, "ada")
    card = gh.get("/performance/teams").json()[0]
    assert card["source"] == "platform" and card["student_count"] == 3 and card["readiness"]["ready"] is False and card["readiness"]["blockers"]


def test_the_lecturer_sets_a_mark_with_a_reason_and_can_take_it_away(team, perf):
    sam = account_id(team, "sam")
    as_user(team, "ada")
    run_id = team.post(f"/performance/teams/{CODE}/runs", {"sprint_id": SPRINT}).json()["run_id"]
    result(perf.store, run_id, sam, 40.0, team=CODE)
    url = f"/performance/teams/{CODE}/sprints/{SPRINT}/students/{sam}/override"
    assert team.put(url, {"mark": 65, "reason": "short"}).status_code == 400
    ok = team.put(url, {"mark": 65, "reason": "Spoke to the team: most of the integration work was his."})
    assert ok.status_code == 200 and ok.json()["override"]["by_name"] == "Ada"
    row = team.get(f"/performance/teams/{CODE}/sprints/{SPRINT}/results").json()[0]
    assert row["effective_mark"] == 65 and row["mark"] == 40.0  # the prediction stays beside the lecturer's mark
    as_user(team, "sam")
    assert team.get("/performance/me/results").json()[0]["mark"] == 65 and team.get("/performance/me/results").json()[0]["overridden"] is True
    as_user(team, "ada")
    assert team.put(url, {"mark": None}).json() == {"override": None}
    assert team.get(f"/performance/teams/{CODE}/sprints/{SPRINT}/results").json()[0]["effective_mark"] == 40.0
    lecturer(team, "bob")  # not a lecturer of this team
    assert team.put(url, {"mark": 10, "reason": "I should not be able to do this"}).status_code == 404
    as_user(team, "sam")
    assert team.put(url, {"mark": 100, "reason": "A student marking themselves, no."}).status_code == 403


def test_the_lecturer_reads_the_students_code_question_and_answer(team, perf):
    from datetime import datetime, timedelta, timezone

    sam = account_id(team, "sam")
    perf.store.create_quiz(CODE, SPRINT, sam, question="What does a2 do?", snippet="def a2(): ...", file_path="a.py", line_range=[1, 9], meta={"facts": {"reference": "secret"}},
                           deadline_at=datetime.now(timezone.utc) + timedelta(hours=48))
    as_user(team, "ada")
    url = f"/performance/teams/{CODE}/sprints/{SPRINT}/students/{sam}/quiz"
    q = team.get(url).json()
    assert q["question"] == "What does a2 do?" and q["status"] == "open" and q["answer"] is None
    assert "reference" not in json.dumps(q) and "secret" not in json.dumps(q)
    as_user(team, "sam")
    assert team.get(url).status_code == 403


def test_the_lecturer_sees_each_students_profile_picture(team, perf):
    sam = account_id(team, "sam")
    team.sign_in("sam", email="sam@example.com", name="Sam", picture="https://img.example/sam.png")
    team.get("/me")  # the picture from the sign-in provider is kept on the account
    as_user(team, "ada")
    run_id = team.post(f"/performance/teams/{CODE}/runs", {"sprint_id": SPRINT}).json()["run_id"]
    result(perf.store, run_id, sam, 81.0, team=CODE)
    rows = team.get(f"/performance/teams/{CODE}/sprints/{SPRINT}/results").json()
    assert [r["student"]["picture"] for r in rows] == ["https://img.example/sam.png"]
