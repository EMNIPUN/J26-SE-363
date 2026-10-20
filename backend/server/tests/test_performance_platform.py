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
    assert kim not in json.dumps(mine) and "44" not in json.dumps(mine)
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
