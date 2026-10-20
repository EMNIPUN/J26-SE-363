"""Performance assessment: tracking, runs, live events, results, reviews and the student's own view.

Lecturer/administrator (a lecturer only for the teams they started tracking):
  GET    /performance/teams                                    their tracked teams
  PUT    /performance/teams/{team}/tracking                    start or change tracking (repository, board, roster, sprints)
  GET    /performance/teams/{team}/tracking                    tracking record
  DELETE /performance/teams/{team}/tracking                    stop tracking
  POST   /performance/teams/{team}/sync                        fetch the repository now (202)
  GET    /performance/teams/{team}/runs                        runs of the team
  POST   /performance/teams/{team}/runs                        start a run {sprint_id, mode: snapshot | final} (202)
  GET    /performance/teams/{team}/sprints/{sprint}/results    every student's latest result
  GET    /performance/teams/{team}/sprints/{sprint}/students/{student}/trajectory   day-by-day snapshots
  GET    /performance/runs/{run}                               status and current node
  POST   /performance/runs/{run}/cancel
  GET    /performance/graph                                    the graph to draw
  GET    /performance/runs/{run}/events?after=&node=           events (polling)
  GET    /performance/runs/{run}/stream                        the same as server-sent events (Last-Event-ID resumes)
  GET    /performance/runs/{run}/report                        lecturer report (markdown)
  POST   /performance/runs/{run}/identity-map                  map unmapped authors and continue a waiting run
  GET    /performance/reviews                                  open reviews of their teams
  POST   /performance/reviews/{id}/decision                    accept, override with a reason, or run again

Student (their own results only):
  GET    /performance/me/results
  GET    /performance/me/quizzes
  POST   /performance/me/quizzes/{id}/answer

Public, signed by GitHub: POST /performance/webhooks/github
"""

import asyncio
import json
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from shared.contracts import UserRole
from shared.performance import RunAlreadyActive
from shared.performance.topology import topology
from starlette.concurrency import run_in_threadpool

from app.api.deps import Account, require_account_role
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.modules.performance import service

router = APIRouter(prefix="/performance", tags=["Performance assessment"])
public_router = APIRouter(prefix="/performance", tags=["Performance assessment"])

staff = require_account_role(UserRole.LECTURER, UserRole.ADMIN)
student_only = require_account_role(UserRole.STUDENT)
Staff = Annotated[Account, Depends(staff)]
StudentAccount = Annotated[Account, Depends(student_only)]


def get_store():
    return service.default_store()


def get_enqueue():
    return service.enqueue


Store = Annotated[Any, Depends(get_store)]
Enqueue = Annotated[Any, Depends(get_enqueue)]


async def db(fn, *args, **kwargs):
    """The store uses blocking connections: run each call off the event loop."""
    return await run_in_threadpool(fn, *args, **kwargs)


def uid(account: Account) -> str:
    return str(account.user.id)


async def own_team(store, account: Account, team_ref: str) -> dict:
    team = await db(store.get_tracked_team, team_ref)
    if team is None or not service.can_manage(team, uid(account), account.role):
        raise not_found("Team is not tracked")  # same answer for "not yours" and "does not exist"
    return team


async def own_run(store, account: Account, run_id: str) -> dict:
    run = await db(store.get_run, run_id)
    if run is None:
        raise not_found("Run not found")
    await own_team(store, account, run["team_ref"])
    return run


# ---- schemas -------------------------------------------------------------------------------------------------------------------------

class RosterStudent(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    logins: list[str] = []
    emails: list[str] = []
    names: list[str] = []
    user_email: str | None = None


class SprintWindow(BaseModel):
    id: str
    start: date
    end: date


class TrackingIn(BaseModel):
    repo_url: str = Field(min_length=8, max_length=300)
    board_ref: str | None = None
    roster: list[RosterStudent] = []
    sprints: list[SprintWindow] = []
    release_to_students: bool = True


class RunIn(BaseModel):
    sprint_id: str = Field(min_length=1, max_length=100)
    mode: Literal["snapshot", "final"] = "final"


class MapEntry(BaseModel):
    student_id: str
    email: str | None = None
    login: str | None = None
    name: str | None = None


class IdentityMapIn(BaseModel):
    mapping: list[MapEntry] = []
    continue_without_mapping: bool = False


class DecisionIn(BaseModel):
    decision: Literal["accept", "override", "rerun"]
    reason: str = Field(default="", max_length=1000)
    mark: float | None = Field(default=None, ge=0, le=100)


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)


# ---- tracking ------------------------------------------------------------------------------------------------------------------------

def tracking_out(team: dict, include_roster: bool = True) -> dict:
    cfg = dict(team.get("config") or {})
    if not include_roster:
        cfg.pop("roster", None)
    return {"team_ref": team["team_ref"], "repo_url": team["repo_url"], "board_ref": team.get("board_ref"), "status": team["status"], "config": cfg, "created_at": team.get("created_at"),
            "updated_at": team.get("updated_at")}


@router.get("/teams")
async def list_teams(account: Staff, store: Store):
    teams = await db(store.list_tracked_teams, None)
    return [tracking_out(t, include_roster=False) for t in teams if service.can_manage(t, uid(account), account.role)]


@router.put("/teams/{team_ref}/tracking")
async def put_tracking(team_ref: str, body: TrackingIn, account: Staff, store: Store):
    existing = await db(store.get_tracked_team, team_ref)
    if existing and not service.can_manage(existing, uid(account), account.role):
        raise not_found("Team is not tracked")
    config = {"roster": [s.model_dump() for s in body.roster], "sprints": [{"id": s.id, "start": s.start.isoformat(), "end": s.end.isoformat()} for s in body.sprints],
              "release_to_students": body.release_to_students, **({"last_sync": existing["config"]["last_sync"]} if existing and "last_sync" in (existing.get("config") or {}) else {})}
    team = await db(store.upsert_tracked_team, team_ref, body.repo_url, body.board_ref or team_ref, config, uid(account))
    return tracking_out(team)


@router.get("/teams/{team_ref}/tracking")
async def get_tracking(team_ref: str, account: Staff, store: Store):
    return tracking_out(await own_team(store, account, team_ref))


@router.delete("/teams/{team_ref}/tracking", status_code=204)
async def stop_tracking(team_ref: str, account: Staff, store: Store):
    await own_team(store, account, team_ref)
    await db(store.set_tracking_status, team_ref, "stopped")


@router.post("/teams/{team_ref}/sync", status_code=202)
async def sync_now(team_ref: str, account: Staff, store: Store, enqueue: Enqueue):
    await own_team(store, account, team_ref)
    job = await enqueue("performance.sync_team", {"team_ref": team_ref}, queueing_lock=f"sync:{team_ref}")
    return {"job_id": job}


# ---- runs ----------------------------------------------------------------------------------------------------------------------------

async def start_run(store, enqueue, team_ref: str, sprint_id: str, mode: str, requested_by: str) -> dict:
    try:
        run = await db(store.create_run, team_ref, sprint_id, mode, requested_by)
    except RunAlreadyActive as e:
        raise conflict("run_active", f"A {mode} run for this sprint is already {e.run['status']}") from None
    job = await enqueue("performance.assess_team", {"run_id": str(run["id"])}, lock=team_ref)
    await db(store.update_run, str(run["id"]), job_id=job)
    return {"run_id": str(run["id"]), "job_id": job, "status": run["status"]}


@router.post("/teams/{team_ref}/runs", status_code=202)
async def post_run(team_ref: str, body: RunIn, account: Staff, store: Store, enqueue: Enqueue):
    team = await own_team(store, account, team_ref)
    if team["status"] != "active":
        raise bad_request("tracking_stopped", "Tracking of this team is stopped")
    return await start_run(store, enqueue, team_ref, body.sprint_id, body.mode, uid(account))


@router.get("/teams/{team_ref}/runs")
async def list_runs(team_ref: str, account: Staff, store: Store, sprint: str | None = None, limit: int = Query(30, ge=1, le=200)):
    await own_team(store, account, team_ref)
    return await db(store.list_runs, team_ref, sprint, limit)


@router.get("/graph")
async def get_graph(account: Staff):
    return topology()


@router.get("/runs/{run_id}")
async def get_run(run_id: str, account: Staff, store: Store):
    run = await own_run(store, account, run_id)
    return {**run, "summary": {k: v for k, v in (run.get("summary") or {}).items() if k != "report_markdown"}}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, account: Staff, store: Store):
    run = await own_run(store, account, run_id)
    if run["status"] not in ("queued", "running", "waiting_human"):
        raise conflict("run_finished", "The run has already finished")
    if run.get("job_id"):
        try:  # stop the job if the worker has not started it yet or can be told to stop
            from shared.queue import app as procrastinate_app

            await procrastinate_app.job_manager.cancel_job_by_id_async(run["job_id"], abort=True)
        except Exception:
            pass
    await db(store.update_run, run_id, status="cancelled")
    await db(store.add_event, run_id, "run_end", "cancelled by the lecturer", level="warn")
    return {"status": "cancelled"}


def _event(e: dict) -> dict:
    return {**e, "ts": e["ts"].isoformat() if hasattr(e.get("ts"), "isoformat") else e.get("ts")}


@router.get("/runs/{run_id}/events")
async def get_events(run_id: str, account: Staff, store: Store, after: int = 0, node: str | None = None, limit: int = Query(500, ge=1, le=2000)):
    await own_run(store, account, run_id)
    return [_event(e) for e in await db(store.list_events, run_id, after, limit, node)]


@router.get("/runs/{run_id}/stream")
async def stream_events(run_id: str, request: Request, account: Staff, store: Store, after: int = 0, last_event_id: Annotated[str | None, Header()] = None):
    await own_run(store, account, run_id)
    seq = int(last_event_id) if last_event_id and last_event_id.isdigit() else after

    async def gen():
        nonlocal seq
        idle = 0
        while True:
            rows = await db(store.list_events, run_id, seq, 200, None)
            for e in rows:
                seq = e["seq"]
                yield f"id: {seq}\nevent: {e['type']}\ndata: {json.dumps(_event(e), default=str)}\n\n"
            run = await db(store.get_run, run_id)
            if not rows and run and run["status"] in service.FINAL_STATES:
                yield f"event: end\ndata: {json.dumps({'status': run['status']})}\n\n"
                return
            if await request.is_disconnected():
                return
            idle = 0 if rows else idle + 1
            if idle % 15 == 14:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0 if rows else 1)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/runs/{run_id}/report", response_class=PlainTextResponse)
async def get_report(run_id: str, account: Staff, store: Store):
    run = await own_run(store, account, run_id)
    text = (run.get("summary") or {}).get("report_markdown")
    if not text:
        raise not_found("The report is written when the run finishes")
    return PlainTextResponse(text, media_type="text/markdown")


@router.post("/runs/{run_id}/identity-map", status_code=202)
async def identity_map(run_id: str, body: IdentityMapIn, account: Staff, store: Store, enqueue: Enqueue):
    run = await own_run(store, account, run_id)
    if run["status"] != "waiting_human":
        raise conflict("not_waiting", "The run is not waiting for an identity mapping")
    if not body.mapping and not body.continue_without_mapping:
        raise bad_request("empty_mapping", "Give at least one mapping, or choose to continue without")
    reviews = [r for r in await db(store.list_reviews, "open", run_id) if r["kind"] == "identity_mapping"]
    for r in reviews:
        await db(store.decide_review, str(r["id"]), {"mapping": [m.model_dump(exclude_none=True) for m in body.mapping], "continue_without": body.continue_without_mapping}, uid(account))
    job = await enqueue("performance.resume_run", {"run_id": run_id, "resume": {"mapping": [m.model_dump(exclude_none=True) for m in body.mapping]}}, lock=run["team_ref"])
    return {"job_id": job}


# ---- results -------------------------------------------------------------------------------------------------------------------------

@router.get("/teams/{team_ref}/sprints/{sprint_id}/results")
async def team_results(team_ref: str, sprint_id: str, account: Staff, store: Store):
    await own_team(store, account, team_ref)
    return [service.lecturer_view(r) for r in await db(store.latest_results, team_ref, sprint_id)]


@router.get("/teams/{team_ref}/sprints/{sprint_id}/students/{student_id}/trajectory")
async def trajectory(team_ref: str, sprint_id: str, student_id: str, account: Staff, store: Store):
    await own_team(store, account, team_ref)
    return await db(store.trajectory, team_ref, sprint_id, student_id)


# ---- reviews -------------------------------------------------------------------------------------------------------------------------

@router.get("/reviews")
async def list_reviews(account: Staff, store: Store, status: Literal["open", "decided"] = "open"):
    out, teams = [], {}
    for r in await db(store.list_reviews, status, None):
        run = await db(store.get_run, str(r["run_id"]))
        if run is None:
            continue
        if run["team_ref"] not in teams:
            teams[run["team_ref"]] = service.can_manage(await db(store.get_tracked_team, run["team_ref"]), uid(account), account.role)
        if teams[run["team_ref"]]:
            out.append({**r, "team_ref": run["team_ref"], "sprint_id": run["sprint_id"]})
    return out


@router.post("/reviews/{review_id}/decision")
async def decide_review(review_id: str, body: DecisionIn, account: Staff, store: Store, enqueue: Enqueue):
    review = next((r for r in await db(store.list_reviews, None, None) if str(r["id"]) == review_id), None)
    if review is None:
        raise not_found("Review not found")
    run = await own_run(store, account, str(review["run_id"]))
    if review["status"] != "open":
        raise conflict("already_decided", "This review has already been decided")
    if review["kind"] == "identity_mapping":
        raise bad_request("use_identity_map", "Identity mapping is answered with POST /runs/{run}/identity-map")
    if body.decision == "override":
        if body.mark is None or len(body.reason.strip()) < 10:
            raise bad_request("override_needs_mark_and_reason", "An override needs a mark and a reason of at least 10 characters")
        if not review.get("student_id"):
            raise bad_request("no_student", "This review is not about one student")
        await db(store.set_override, str(review["run_id"]), review["student_id"], {"mark": body.mark, "reason": body.reason.strip(), "by": uid(account), "at": service.now().isoformat()})
    decided = await db(store.decide_review, review_id, {"decision": body.decision, "reason": body.reason, "mark": body.mark}, uid(account))
    out: dict[str, Any] = {"review": decided}
    if body.decision == "rerun":
        out["run"] = await start_run(store, enqueue, run["team_ref"], run["sprint_id"], run["mode"], uid(account))
    return out


# ---- the student's own view ----------------------------------------------------------------------------------------------------------

def _mine(store, account: Account) -> list[dict]:
    return service.find_student(store, account.user.github_username, account.user.email)


@router.get("/me/results")
async def my_results(account: StudentAccount, store: Store):
    out = []
    for m in await db(_mine, store, account):
        if not m["release"]:
            continue
        team = await db(store.get_tracked_team, m["team_ref"])
        for sprint in (team.get("config") or {}).get("sprints", []):
            for r in await db(store.latest_results, m["team_ref"], sprint["id"]):
                if r["student_id"] == m["student_id"]:
                    out.append({"team_ref": m["team_ref"], **service.student_view(r)})
    return out


@router.get("/me/quizzes")
async def my_quizzes(account: StudentAccount, store: Store, status: str | None = None):
    out = []
    for m in await db(_mine, store, account):
        for q in await db(store.list_student_quizzes, m["student_id"], status):
            if q["team_ref"] == m["team_ref"]:
                shown = {k: q[k] for k in ("id", "team_ref", "sprint_id", "question", "snippet", "file_path", "line_range", "status", "deadline_at", "extended_until", "answered_at")}
                out.append(shown)
    return out


@router.post("/me/quizzes/{quiz_id}/answer", status_code=202)
async def answer_quiz(quiz_id: str, body: AnswerIn, account: StudentAccount, store: Store, enqueue: Enqueue):
    mine = {(m["team_ref"], m["student_id"]) for m in await db(_mine, store, account)}
    quizzes = [q for m in mine for q in await db(store.list_student_quizzes, m[1], None) if str(q["id"]) == quiz_id and q["team_ref"] == m[0]]
    if not quizzes:
        raise not_found("Quiz not found")
    q = quizzes[0]
    row = await db(store.submit_quiz_answer, quiz_id, body.answer.strip())
    if row is None:
        raise conflict("quiz_closed", "This question can no longer be answered")
    job = await enqueue("performance.refuse_student", {"team_ref": q["team_ref"], "sprint_id": q["sprint_id"], "student_id": q["student_id"]}, queueing_lock=f"quiz:{quiz_id}")
    return {"accepted": True, "in_second_window": bool(row.get("in_extension")), "job_id": job}


# ---- GitHub webhook ------------------------------------------------------------------------------------------------------------------

WEBHOOK_EVENTS = {"push", "pull_request", "pull_request_review", "pull_request_review_comment", "issue_comment"}


@public_router.post("/webhooks/github", status_code=202)
async def github_webhook(request: Request, store: Store, enqueue: Enqueue, x_hub_signature_256: Annotated[str | None, Header()] = None, x_github_event: Annotated[str | None, Header()] = None):
    """GitHub calls this, not a signed-in person: the request is accepted only with a valid HMAC signature of the body."""
    secret = service.webhook_secret()
    if not secret:
        raise forbidden("webhook_disabled", "Webhooks are not configured")
    body = await request.body()
    if not service.verify_signature(secret, body, x_hub_signature_256):
        raise forbidden("bad_signature", "Signature does not match")
    if x_github_event not in WEBHOOK_EVENTS:
        return {"queued": 0}
    try:
        repo = json.loads(body).get("repository", {})
    except ValueError:
        raise bad_request("bad_body", "Not JSON") from None
    key = service.repo_key(repo.get("html_url") or repo.get("clone_url") or "")
    n = 0
    for team in await db(store.list_tracked_teams, "active"):
        if key and service.repo_key(team["repo_url"]) == key:
            await enqueue("performance.sync_team", {"team_ref": team["team_ref"]}, queueing_lock=f"sync:{team['team_ref']}")
            n += 1
    return {"queued": n}
