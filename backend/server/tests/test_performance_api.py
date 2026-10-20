"""The performance routes: tracking, runs, events, results, reviews, the student's view, the webhook. Storage is the in-memory stand-in and jobs are recorded, not queued."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from shared.performance.memory_store import MemoryStore

from app.api.v1.performance import get_enqueue, get_store
from app.main import app
from app.services.accounts import CONSENT_VERSION
from tests.test_teams_api import lecturer, student

REPO = "https://github.com/acme/project-x"
SPRINT = "T9-S1"
ROSTER = [{"student_id": "STU-1", "logins": ["gh-ann"], "emails": ["ann@x.org"]}, {"student_id": "STU-2", "logins": ["gh-ben"]}]


class Jobs:
    def __init__(self):
        self.sent = []

    async def __call__(self, task, payload, *, lock=None, queueing_lock=None):
        self.sent.append({"task": task, "payload": payload, "lock": lock, "queueing_lock": queueing_lock})
        return len(self.sent)


@pytest.fixture()
def perf(api):
    store, jobs = MemoryStore(), Jobs()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_enqueue] = lambda: jobs
    api.store, api.jobs = store, jobs
    return api


def track(api, team="T9", **extra):
    body = {"repo_url": REPO, "roster": ROSTER, "sprints": [{"id": SPRINT, "start": "2026-03-01", "end": "2026-03-14"}], **extra}
    r = api.request("PUT", f"/performance/teams/{team}/tracking", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def result(store, run_id, student, mark=70.0, status="final", team="T9", **kw):
    return store.save_assessment_result(run_id, team, SPRINT, student, mark=mark, status=status, mark_interval=[mark - 10, mark + 10],
                                        factors={"effort": {"score": 0.6, "status": "completed"}}, justification={"summary": "because", "factors": {}, "caveats": ["c"], "flags": []}, flags=[])


def test_lecturer_tracks_a_team_and_only_the_owner_sees_it(perf):
    lecturer(perf, "ada")
    out = track(perf)
    assert out["status"] == "active" and out["config"]["roster"][0]["student_id"] == "STU-1"
    assert perf.get("/performance/teams/T9/tracking").json()["repo_url"] == REPO
    listed = perf.get("/performance/teams").json()
    assert [t["team_ref"] for t in listed] == ["T9"] and listed[0]["source"] == "manual" and listed[0]["student_count"] == 2
    assert "roster" not in json.dumps(listed)  # the list carries no student details
    lecturer(perf, "bob")
    assert perf.get("/performance/teams/T9/tracking").status_code == 404
    assert perf.get("/performance/teams").json() == []
    assert perf.request("PUT", "/performance/teams/T9/tracking", json={"repo_url": "https://github.com/x/y"}).status_code == 404


def test_students_cannot_use_the_lecturer_routes(perf):
    lecturer(perf, "ada")
    track(perf)
    student(perf, "ann")
    for method, path in (("GET", "/performance/teams"), ("GET", "/performance/teams/T9/tracking"), ("GET", "/performance/graph"), ("POST", "/performance/teams/T9/sync")):
        assert perf.request(method, path).status_code == 403, path


def test_starting_a_run_queues_one_job_and_refuses_a_second(perf):
    lecturer(perf, "ada")
    track(perf)
    r = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT, "mode": "final"})
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    assert perf.jobs.sent[0]["task"] == "performance.assess_team" and perf.jobs.sent[0]["payload"] == {"run_id": run_id} and perf.jobs.sent[0]["lock"] == "T9"
    assert perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT, "mode": "final"}).status_code == 409
    assert perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT, "mode": "snapshot"}).status_code == 202  # another mode is a different run
    assert perf.get(f"/performance/runs/{run_id}").json()["status"] == "queued"
    assert [x["id"] for x in perf.get("/performance/teams/T9/runs").json()].count(run_id) == 1
    assert perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT, "mode": "weekly"}).status_code == 422
    # stopped tracking: no new runs
    assert perf.delete("/performance/teams/T9/tracking").status_code == 204
    assert perf.post("/performance/teams/T9/runs", {"sprint_id": "T9-S2", "mode": "final"}).status_code == 400


def test_cancel_marks_the_run_and_logs_it(perf):
    lecturer(perf, "ada")
    track(perf)
    run_id = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT}).json()["run_id"]
    assert perf.post(f"/performance/runs/{run_id}/cancel").json() == {"status": "cancelled"}
    assert perf.post(f"/performance/runs/{run_id}/cancel").status_code == 409
    assert perf.get(f"/performance/runs/{run_id}/events").json()[-1]["type"] == "run_end"


def test_events_can_be_polled_and_streamed(perf):
    lecturer(perf, "ada")
    track(perf)
    run_id = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT}).json()["run_id"]
    for i in range(3):
        perf.store.add_event(run_id, "log", f"m{i}", node_path="team/publish" if i else "student:STU-1/fusion")
    perf.store.update_run(run_id, status="succeeded")
    polled = perf.get(f"/performance/runs/{run_id}/events", params={"after": 1}).json()
    assert [e["seq"] for e in polled] == [2, 3]
    assert [e["message"] for e in perf.get(f"/performance/runs/{run_id}/events", params={"node": "student:STU-1"}).json()] == ["m0"]
    with perf.client.stream("GET", f"/api/v1/performance/runs/{run_id}/stream", headers={"Last-Event-ID": "1"}) as s:
        text = "".join(s.iter_text())
    assert "id: 2" in text and "id: 3" in text and "id: 1\n" not in text
    assert "event: end" in text and '"succeeded"' in text
    graph = perf.get("/performance/graph").json()
    assert {n["id"] for n in graph["nodes"]} >= {"collect_scrum", "factor_audit", "decide"} and graph["edges"]


def test_results_show_overrides_and_a_foreign_lecturer_sees_nothing(perf):
    lecturer(perf, "ada")
    track(perf)
    run_id = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT}).json()["run_id"]
    result(perf.store, run_id, "STU-1", 70.0)
    result(perf.store, run_id, "STU-2", 40.0, status="pending_review")
    rows = {r["student_id"]: r for r in perf.get(f"/performance/teams/T9/sprints/{SPRINT}/results").json()}
    assert rows["STU-1"]["effective_mark"] == 70.0 and rows["STU-2"]["status"] == "pending_review"
    perf.store.add_snapshot("T9", SPRINT, "STU-1", datetime(2026, 3, 5, tzinfo=timezone.utc), 0.3, mark=50.0)
    assert len(perf.get(f"/performance/teams/T9/sprints/{SPRINT}/students/STU-1/trajectory").json()) == 1
    lecturer(perf, "bob")
    assert perf.get(f"/performance/teams/T9/sprints/{SPRINT}/results").status_code == 404


def test_review_override_needs_a_reason_and_changes_what_is_shown(perf):
    lecturer(perf, "ada")
    track(perf)
    run_id = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT}).json()["run_id"]
    result(perf.store, run_id, "STU-2", 40.0, status="pending_review")
    rev = perf.store.create_review(run_id, "audit", "effort high but ownership low", student_id="STU-2")
    listed = perf.get("/performance/reviews").json()
    assert [r["id"] for r in listed] == [rev["id"]] and listed[0]["team_ref"] == "T9"
    bad = perf.post(f"/performance/reviews/{rev['id']}/decision", {"decision": "override", "mark": 65, "reason": "short"})
    assert bad.status_code == 400
    ok = perf.post(f"/performance/reviews/{rev['id']}/decision", {"decision": "override", "mark": 65, "reason": "Spoke with the team; the pair-programmed work is his."})
    assert ok.status_code == 200
    row = {r["student_id"]: r for r in perf.get(f"/performance/teams/T9/sprints/{SPRINT}/results").json()}["STU-2"]
    assert row["effective_mark"] == 65 and row["mark"] == 40.0  # the model's value is kept next to the override
    assert perf.post(f"/performance/reviews/{rev['id']}/decision", {"decision": "accept"}).status_code == 409
    assert perf.get("/performance/reviews").json() == []


def test_review_rerun_queues_a_new_run(perf):
    lecturer(perf, "ada")
    track(perf)
    run_id = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT}).json()["run_id"]
    perf.store.update_run(run_id, status="succeeded")
    rev = perf.store.create_review(run_id, "audit", "x", student_id="STU-1")
    out = perf.post(f"/performance/reviews/{rev['id']}/decision", {"decision": "rerun"}).json()
    assert out["run"]["run_id"] != run_id and perf.jobs.sent[-1]["task"] == "performance.assess_team"


def test_identity_map_resumes_a_waiting_run(perf):
    lecturer(perf, "ada")
    track(perf)
    run_id = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT}).json()["run_id"]
    assert perf.post(f"/performance/runs/{run_id}/identity-map", {"mapping": [{"student_id": "STU-2", "email": "b@x.org"}]}).status_code == 409
    perf.store.update_run(run_id, status="waiting_human")
    rev = perf.store.create_review(run_id, "identity_mapping", "unmapped")
    assert perf.post(f"/performance/reviews/{rev['id']}/decision", {"decision": "accept"}).status_code == 400
    assert perf.post(f"/performance/runs/{run_id}/identity-map", {}).status_code == 400
    assert perf.post(f"/performance/runs/{run_id}/identity-map", {"mapping": [{"student_id": "STU-2", "email": "b@x.org"}]}).status_code == 202
    sent = perf.jobs.sent[-1]
    assert sent["task"] == "performance.resume_run" and sent["payload"]["resume"] == {"mapping": [{"student_id": "STU-2", "email": "b@x.org"}]}
    assert perf.store.list_reviews("open", run_id) == []


def test_report_is_available_when_the_run_has_one(perf):
    lecturer(perf, "ada")
    track(perf)
    run_id = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT}).json()["run_id"]
    assert perf.get(f"/performance/runs/{run_id}/report").status_code == 404
    perf.store.update_run(run_id, summary={"report_markdown": "# Assessment report\n"})
    r = perf.get(f"/performance/runs/{run_id}/report")
    assert r.status_code == 200 and r.text.startswith("# Assessment report")
    assert "report_markdown" not in perf.get(f"/performance/runs/{run_id}").json()["summary"]


def me(perf, sub):
    """Sign in as an existing person and return their account id (the student id the agent uses)."""
    perf.sign_in(sub, email=f"{sub}@example.com", name=sub.title())
    return perf.get("/me").json()["id"]


def track_with_ids(perf, ann, ben, **extra):
    roster = [{"student_id": ann, "logins": ["gh-ann"]}, {"student_id": ben, "logins": ["gh-ben"]}]
    body = {"repo_url": REPO, "roster": roster, "sprints": [{"id": SPRINT, "start": "2026-03-01", "end": "2026-03-14"}], **extra}
    assert perf.request("PUT", "/performance/teams/T9/tracking", json=body).status_code == 200


def test_a_student_sees_only_their_own_released_result(perf):
    student(perf, "ann")
    student(perf, "ben")
    student(perf, "cy")
    lecturer(perf, "ada")
    ann, ben = me(perf, "ann"), me(perf, "ben")
    perf.sign_in("ada", email="ada@example.com", name="Ada")
    track_with_ids(perf, ann, ben)
    run_id = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT}).json()["run_id"]
    result(perf.store, run_id, ann, 72.0)
    result(perf.store, run_id, ben, 31.0, status="pending_review")
    me(perf, "ann")
    mine = perf.get("/performance/me/results").json()
    assert [r["student_id"] for r in mine] == [ann] and mine[0]["mark"] == 72.0 and mine[0]["justification"]["summary"] == "because"
    assert str(ben) not in json.dumps(mine)  # nothing about a teammate
    me(perf, "ben")  # under review: the mark is not shown yet
    mine = perf.get("/performance/me/results").json()
    assert mine[0]["status"] == "under_review" and "mark" not in mine[0]
    me(perf, "cy")
    assert perf.get("/performance/me/results").json() == []
    # the lecturer can hold results back
    perf.sign_in("ada", email="ada@example.com", name="Ada")
    track_with_ids(perf, ann, ben, release_to_students=False)
    me(perf, "ann")
    assert perf.get("/performance/me/results").json() == []


def test_a_typed_github_name_or_email_does_not_open_anyone_elses_results(perf):
    """Students type their GitHub username at registration. Matching on it would let a student read a classmate's results; results belong to the account id."""
    student(perf, "ann")
    lecturer(perf, "ada")
    ann = me(perf, "ann")
    perf.sign_in("ada", email="ada@example.com", name="Ada")
    track_with_ids(perf, ann, "someone-else-entirely")
    run_id = perf.post("/performance/teams/T9/runs", {"sprint_id": SPRINT}).json()["run_id"]
    result(perf.store, run_id, "someone-else-entirely", 55.0)
    perf.sign_in("mallory", email="ann@x.org", name="Mallory")  # the roster lists the e-mail ann@x.org and the login gh-ann for the other entry
    perf.post("/me/onboarding", {"account_type": "student", "display_name": "Mallory", "accept_terms": True, "consent_version": CONSENT_VERSION, "github_username": "gh-ben"})
    assert perf.get("/performance/me/results").json() == []
    assert perf.get("/performance/me/quizzes").json() == []


def test_a_student_answers_their_own_quiz_once(perf):
    student(perf, "ann")
    student(perf, "ben")
    lecturer(perf, "ada")
    ann, ben = me(perf, "ann"), me(perf, "ben")
    perf.sign_in("ada", email="ada@example.com", name="Ada")
    track_with_ids(perf, ann, ben)
    perf.store.create_quiz("T9", SPRINT, ann, question="What does a2 do?", snippet="def a2(): ...", file_path="a.py", line_range=[1, 9], meta={"facts": {"secret": 1}},
                           deadline_at=datetime.now(timezone.utc) + timedelta(hours=48))
    quiz_id = next(iter(perf.store.quizzes.values()))["id"]
    me(perf, "ben")
    assert perf.get("/performance/me/quizzes").json() == []
    assert perf.post(f"/performance/me/quizzes/{quiz_id}/answer", {"answer": "mine"}).status_code == 404
    me(perf, "ann")
    shown = perf.get("/performance/me/quizzes").json()
    assert shown[0]["question"] == "What does a2 do?" and "meta" not in shown[0] and "answer" not in shown[0]  # the reference facts never leave the server
    r = perf.post(f"/performance/me/quizzes/{quiz_id}/answer", {"answer": "It adds two numbers and returns them."})
    assert r.status_code == 202 and r.json()["accepted"] and not r.json()["in_second_window"]
    assert perf.jobs.sent[-1]["task"] == "performance.refuse_student" and perf.jobs.sent[-1]["payload"]["student_id"] == ann
    assert perf.post(f"/performance/me/quizzes/{quiz_id}/answer", {"answer": "again"}).status_code == 409
    assert perf.post(f"/performance/me/quizzes/{quiz_id}/answer", {"answer": ""}).status_code == 422


def sign(secret, body):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_webhook_needs_a_valid_signature_and_queues_a_sync(perf, monkeypatch):
    lecturer(perf, "ada")
    track(perf)
    body = json.dumps({"repository": {"html_url": REPO + ".git"}}).encode()
    perf.sign_out()  # the webhook is called by GitHub, not by a signed-in person
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    assert perf.post("/performance/webhooks/github", content=body).status_code == 403
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "s3cret")
    send = lambda sig, event="push": perf.request("POST", "/performance/webhooks/github", content=body, headers={"X-Hub-Signature-256": sig, "X-GitHub-Event": event, "Content-Type": "application/json"})  # noqa: E731
    assert send("sha256=00").status_code == 403
    assert send("").status_code == 403
    assert send(sign("other", body)).status_code == 403
    assert perf.jobs.sent == []
    assert send(sign("s3cret", body), "ping").json() == {"queued": 0}
    r = send(sign("s3cret", body))
    assert r.status_code == 202 and r.json() == {"queued": 1}
    assert perf.jobs.sent[0] == {"task": "performance.sync_team", "payload": {"team_ref": "T9"}, "lock": None, "queueing_lock": "sync:T9"}
