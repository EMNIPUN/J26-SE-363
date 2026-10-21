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
  GET    /performance/teams/{team}/students/{student}/trajectory   day-by-day snapshots of every sprint
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
import hmac
import json
from datetime import date, datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from shared.contracts import UserRole
from shared.performance import RunAlreadyActive
from shared.performance.topology import topology
from starlette.concurrency import run_in_threadpool

from sqlalchemy.orm import Session

from app.api.deps import Account, get_onboarded_account, require_account_role
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.core.config import settings
from app.database.session import get_db
from app.models import Group, MemberRole
from app.modules.performance import service
from app.modules.performance.scrum_simulator import ScrumSimulator
from app.services import avatars
from app.services import github_links as links
from app.services import team_rules as rules
from shared.performance.review_forms import validate_review_form

router = APIRouter(prefix="/performance", tags=["Performance assessment"])
public_router = APIRouter(prefix="/performance", tags=["Performance assessment"])
internal_router = APIRouter(prefix="/internal/scrum", tags=["Scrum simulator"])

_staff_role = require_account_role(UserRole.LECTURER, UserRole.ADMIN)
_student_role = require_account_role(UserRole.STUDENT)


def staff(account: Annotated[Account, Depends(_staff_role)], session: Annotated[Session, Depends(get_db)]) -> Account:
    """A lecturer or an administrator, with the database session the access rules below need."""
    account.session = session
    return account


def student_only(account: Annotated[Account, Depends(_student_role)], session: Annotated[Session, Depends(get_db)]) -> Account:
    account.session = session
    return account


Staff = Annotated[Account, Depends(staff)]
StudentAccount = Annotated[Account, Depends(student_only)]
SignedInAccount = Annotated[Account, Depends(get_onboarded_account)]


def get_store():
    return service.default_store()


def get_enqueue():
    return service.enqueue


Store = Annotated[Any, Depends(get_store)]
Enqueue = Annotated[Any, Depends(get_enqueue)]


def _scrum_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    expected = settings.AI_BACKEND_INTERNAL_TOKEN
    if not expected or not x_internal_token or not hmac.compare_digest(x_internal_token, expected):
        raise HTTPException(status_code=401, detail="Invalid internal token", headers={"WWW-Authenticate": "Bearer"})


async def db(fn, *args, **kwargs):
    """The store uses blocking connections: run each call off the event loop."""
    return await run_in_threadpool(fn, *args, **kwargs)


def uid(account: Account) -> str:
    return str(account.user.id)


def platform_group(session: Session, ref: str) -> Group | None:
    return rules.find_team(session, ref)


def is_team_lecturer(group: Group, account: Account) -> bool:
    """Who may see a team's assessment: administrators, and the lecturers who are members of the team. Nobody else, not even other lecturers."""
    if account.role is UserRole.ADMIN:
        return True
    m = rules.membership(group, account.user.id)
    return bool(m and m.role is MemberRole.LECTURER)


async def can_see_team(store, account: Account, team_ref: str) -> bool:
    group = platform_group(account.session, team_ref)
    if group is not None:
        return is_team_lecturer(group, account)
    return service.can_manage(await db(store.get_tracked_team, team_ref), uid(account), account.role)  # a team that is not a platform team: the lecturer who started it


async def own_team(store, account: Account, team_ref: str) -> dict:
    """The tracking record of a team the person may manage. A platform team that has not been assessed yet has none stored: it is described from the team itself."""
    group = platform_group(account.session, team_ref)
    team = await db(store.get_tracked_team, group.code if group else team_ref)
    if group is not None:
        if not is_team_lecturer(group, account):
            raise not_found("Team is not tracked")
        return team or {"team_ref": group.code, "repo_url": group.repo_url or "", "board_ref": group.code, "status": "active", "config": {"source": "platform"}, "created_by": None}
    if team is None or not service.can_manage(team, uid(account), account.role):
        raise not_found("Team is not tracked")  # the same answer for "not yours" and "does not exist"
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
    students: list[str] | None = None


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
    answers: dict[str, Any] = Field(default_factory=dict)


class QuizAnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)

# ---- tracking ------------------------------------------------------------------------------------------------------------------------

def tracking_out(team: dict, include_roster: bool = True) -> dict:
    cfg = dict(team.get("config") or {})
    if not include_roster:
        cfg.pop("roster", None)
    return {"team_ref": team["team_ref"], "repo_url": team["repo_url"], "board_ref": team.get("board_ref"), "status": team["status"], "config": cfg, "created_at": team.get("created_at"),
            "updated_at": team.get("updated_at")}


async def team_card(store, session: Session, group: Group | None, tracked: dict | None) -> dict:
    """One line of the lecturer's team list: the team, its repository, whether it can be assessed, and its latest run."""
    ref = group.code if group else tracked["team_ref"]
    runs = await db(store.list_runs, ref, None, 1)
    cfg = (tracked or {}).get("config") or {}
    card = {"team_ref": ref, "name": group.name if group else ref, "source": "platform" if group else "manual", "repo_url": (group.repo_url if group else tracked["repo_url"]) or None,
            "status": (tracked or {}).get("status", "active"), "sprints": cfg.get("sprints", []), "latest_run": runs[0] if runs else None,
            "student_count": len(rules.students(group)) if group else len(cfg.get("roster", []))}
    if group is not None:
        r = links.readiness(session, group)
        card["readiness"] = {"ready": r["ready"], "blockers": r["blockers"], "notes": len(r["notes"])}
    return card


@router.get("/teams")
async def list_teams(account: Staff, store: Store):
    cards, seen = [], set()
    groups = account.session.scalars(__import__("sqlalchemy").select(Group)).all() if account.role is UserRole.ADMIN else [
        g for g in account.session.scalars(__import__("sqlalchemy").select(Group).join(rules.GroupMember, rules.GroupMember.group_id == Group.id).where(rules.GroupMember.user_id == account.user.id))
        if is_team_lecturer(g, account)]
    for g in groups:
        seen.add(g.code.upper())
        cards.append(await team_card(store, account.session, g, await db(store.get_tracked_team, g.code)))
    for t in await db(store.list_tracked_teams, None):
        if t["team_ref"].upper() not in seen and service.can_manage(t, uid(account), account.role):
            cards.append(await team_card(store, account.session, None, t))
    return cards


@router.put("/teams/{team_ref}/tracking")
async def put_tracking(team_ref: str, body: TrackingIn, account: Staff, store: Store):
    if platform_group(account.session, team_ref) is not None:
        raise bad_request("platform_team", "This team is a platform team: its repository and members come from GitHub linking. Use the settings route for sprints")
    existing = await db(store.get_tracked_team, team_ref)
    if existing and not service.can_manage(existing, uid(account), account.role):
        raise not_found("Team is not tracked")
    config = {"roster": [s.model_dump() for s in body.roster], "sprints": [{"id": s.id, "start": s.start.isoformat(), "end": s.end.isoformat()} for s in body.sprints],
              "release_to_students": body.release_to_students, **({"last_sync": existing["config"]["last_sync"]} if existing and "last_sync" in (existing.get("config") or {}) else {})}
    team = await db(store.upsert_tracked_team, team_ref, body.repo_url, body.board_ref or team_ref, config, uid(account))
    return tracking_out(team)


class SettingsIn(BaseModel):
    board_ref: str | None = None
    sprints: list[SprintWindow] = []
    release_to_students: bool = True


@router.put("/teams/{team_ref}/settings")
async def put_settings(team_ref: str, body: SettingsIn, account: Staff, store: Store):
    """Sprint dates, the Scrum board id and whether students see their own results. The repository and the roster of a platform team come from GitHub linking, never from here."""
    team = await own_team(store, account, team_ref)
    cfg = {**(team.get("config") or {}), "sprints": [{"id": x.id, "start": x.start.isoformat(), "end": x.end.isoformat()} for x in body.sprints], "release_to_students": body.release_to_students}
    group = platform_group(account.session, team_ref)
    saved = await db(store.upsert_tracked_team, group.code if group else team_ref, team["repo_url"] or "https://github.com/none/none", body.board_ref or team.get("board_ref") or team_ref, cfg, team.get("created_by") or uid(account))
    return tracking_out(saved)


@router.get("/teams/{team_ref}/readiness")
async def readiness(team_ref: str, account: Staff, store: Store):
    await own_team(store, account, team_ref)
    group = platform_group(account.session, team_ref)
    if group is None:
        return {"ready": True, "blockers": [], "notes": [], "members": [], "repo": None}
    return links.readiness(account.session, group)


@router.get("/teams/{team_ref}/tracking")
async def get_tracking(team_ref: str, account: Staff, store: Store):
    return tracking_out(await own_team(store, account, team_ref))


@router.get("/teams/{team_ref}/setup")
async def team_setup(team_ref: str, account: Staff, store: Store):
    team = await own_team(store, account, team_ref)
    group = platform_group(account.session, team_ref)
    readiness_data = links.readiness(account.session, group) if group else {"ready": True, "blockers": [], "notes": [], "members": [], "repo": None}
    sprints = _sprints(team)
    runs = await db(store.list_runs, team["team_ref"], None, 10)
    meta = service.performance_meta()
    return {
        "team_ref": team["team_ref"],
        "repo": team.get("repo_url") or readiness_data.get("repo"),
        "board_ref": team.get("board_ref") or team["team_ref"],
        "members": readiness_data.get("members", []),
        "sprints": sprints,
        "recent_runs": runs,
        "weights": meta.get("weights"),
        "ready": readiness_data.get("ready", True),
        "blockers": readiness_data.get("blockers", []),
    }


@router.get("/teams/{team_ref}/scrum")
async def get_scrum_board(team_ref: str, account: Staff, store: Store):
    """Return the fixture matched to the team's connected GitHub repository.

    An unmatched repository is deliberately a 404: the simulator must never
    silently serve a course/sample board to a real team.
    """
    team = await own_team(store, account, team_ref)
    simulator = ScrumSimulator()
    if simulator.match(team.get("repo_url") or "") is None:
        raise not_found("No Scrum fixture is configured for this repository")
    return {
        "team_ref": team_ref,
        "repo_url": team["repo_url"],
        "sprints": simulator.payload("list_sprints", team["repo_url"]),
        "roster": simulator.payload("get_team_roster", team["repo_url"]),
    }


@internal_router.get("/{team_ref}/{operation}", dependencies=[Depends(_scrum_internal_token)])
async def internal_scrum(
    team_ref: str,
    operation: str,
    repo_url: str = Query(..., min_length=8),
    sprint_id: str = Query(""),
    student_id: str = Query(""),
    task_id: str = Query(""),
):
    """Worker-only read path; repository matching happens inside the simulator."""
    simulator = ScrumSimulator()
    if simulator.match(repo_url) is None:
        raise HTTPException(status_code=404, detail="No Scrum fixture matches repository")
    return simulator.payload(operation, repo_url, sprint_id=sprint_id, student_id=student_id, task_id=task_id)


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

async def start_run(store, enqueue, team_ref: str, sprint_id: str, mode: str, requested_by: str, options: dict | None = None) -> dict:
    try:
        run = await db(store.create_run, team_ref, sprint_id, mode, requested_by)
    except RunAlreadyActive as e:
        raise conflict("run_active", f"A {mode} run for this sprint is already {e.run['status']}") from None
    payload = {"run_id": str(run["id"])}
    if options:
        payload["options"] = options
    job = await enqueue("performance.assess_team", payload, lock=team_ref)
    await db(store.update_run, str(run["id"]), job_id=job)
    return {"run_id": str(run["id"]), "job_id": job, "status": run["status"]}


def merge_roster(kept: list[dict], fresh: list[dict]) -> list[dict]:
    """The platform's verified details of each student, added to what the lecturer already mapped for them (extra e-mails, logins, names), so starting an assessment never undoes a mapping."""
    old = {r.get("student_id"): r for r in kept}
    out = []
    for r in fresh:
        before = old.get(r["student_id"], {})
        out.append({**r, **{key: list(dict.fromkeys([*r.get(key, []), *before.get(key, [])])) for key in ("emails", "logins", "names")}})
    return out


async def prepare_platform_team(store, session: Session, group: Group, sprint_id: str, account: Account) -> None:
    """Write what the agent is given from the team's verified GitHub facts: the repository, the installation, each student's own id with the verified login and commit addresses."""
    state = links.readiness(session, group)
    if not state["ready"]:
        raise conflict("not_ready", " ".join(state["blockers"]))
    existing = await db(store.get_tracked_team, group.code)
    cfg = dict((existing or {}).get("config") or {})
    sprints_in_cfg = {x["id"] for x in cfg.get("sprints", [])}
    if sprint_id not in sprints_in_cfg:
        repo = group.repo_url or (existing or {}).get("repo_url")
        if repo:
            try:
                sim = ScrumSimulator()
                if sim.match(repo):
                    sim_sprints = [
                        {"id": s["sprint_id"], "start": s["start_date"], "end": s["end_date"]}
                        for s in sim.payload("list_sprints", repo)
                    ]
                    cfg["sprints"] = sim_sprints
                    sprints_in_cfg = {x["id"] for x in sim_sprints}
            except Exception:
                pass
    if sprint_id not in sprints_in_cfg:
        raise bad_request("unknown_sprint", "Add this sprint (its dates) in the team's settings first")
    row = links.team_link(session, group)
    cfg.update({"roster": merge_roster(cfg.get("roster") or [], links.agent_roster(session, group)), "group_id": str(group.id), "installation_id": row.installation_id, "repo_full_name": row.repo_full_name, "source": "platform"})
    cfg.setdefault("release_to_students", True)
    await db(store.upsert_tracked_team, group.code, group.repo_url, (existing or {}).get("board_ref") or group.code, cfg, (existing or {}).get("created_by") or uid(account))


def sprints_with_data(team: dict) -> list[dict]:
    """The team's sprints that have anything to assess: all of them when the board cannot say, otherwise those with at least one task."""
    sprints = _sprints(team)
    try:
        simulator = ScrumSimulator()
        if team.get("repo_url") and simulator.match(team["repo_url"]):
            tasks = {s["sprint_id"]: s["task_count"] for s in simulator.payload("list_sprints", team["repo_url"])}
            return [s for s in sprints if tasks.get(s["id"], 1) > 0]  # a sprint the board does not know is kept: the run will say so
    except Exception:
        pass
    return sprints


async def queue_unevaluated_sprints(store, enqueue, team: dict, team_ref: str, first: str, requested_by: str, options: dict | None) -> list[dict]:
    """Queue a final run for every sprint other than ``first`` that has data but has not been evaluated, oldest first.

    A sprint being over (or marked completed on the board) says nothing about whether it was evaluated: the test is a finished run of ours for it. The runs go one after another (the team lock)."""
    queued = []
    for sprint in sprints_with_data(team):
        if sprint["id"] == first:
            continue
        runs = await db(store.list_runs, team_ref, sprint["id"], 50)
        if any(r["mode"] == "final" and r["status"] in ("succeeded", "queued", "running", "waiting_human") for r in runs):
            continue
        try:
            queued.append({**await start_run(store, enqueue, team_ref, sprint["id"], "final", requested_by, options=options), "sprint_id": sprint["id"]})
        except HTTPException:
            continue  # a run for it became active in the meantime
    return queued


async def earliest_unevaluated(store, team: dict, team_ref: str, asked: str) -> str:
    """Where a final assessment starts: the oldest sprint with data that has no finished or active final run, so the sprints are evaluated in the order they happened. When every sprint was evaluated, the one asked for."""
    for sprint in sprints_with_data(team):
        runs = await db(store.list_runs, team_ref, sprint["id"], 50)
        if not any(r["mode"] == "final" and r["status"] in ("succeeded", "queued", "running", "waiting_human") for r in runs):
            return sprint["id"]
    return asked


@router.post("/teams/{team_ref}/runs", status_code=202)
async def post_run(team_ref: str, body: RunIn, account: Staff, store: Store, enqueue: Enqueue):
    team = await own_team(store, account, team_ref)
    if team["status"] != "active":
        raise bad_request("tracking_stopped", "Tracking of this team is stopped")
    group = platform_group(account.session, team_ref)
    if group is not None:
        await prepare_platform_team(store, account.session, group, body.sprint_id, account)
        team_ref = group.code
    options = {"students": body.students} if body.students else None
    sprint_id = body.sprint_id
    if body.mode == "final":
        team = await db(store.get_tracked_team, team_ref) or team
        sprint_id = await earliest_unevaluated(store, team, team_ref, body.sprint_id)
    started = {**await start_run(store, enqueue, team_ref, sprint_id, body.mode, uid(account), options=options), "sprint_id": sprint_id}
    if body.mode == "final":
        started["also_queued"] = await queue_unevaluated_sprints(store, enqueue, team, team_ref, sprint_id, uid(account), options)
    return started



@router.delete("/teams/{team_ref}/evaluation")
async def clear_evaluation(team_ref: str, account: Staff, store: Store, sprint: str | None = None):
    """Delete all evaluation data (runs, results, quizzes, reviews, snapshots) for this team, optionally scoped to a sprint."""
    await own_team(store, account, team_ref)
    group = platform_group(account.session, team_ref)
    ref = group.code if group else team_ref
    return await db(store.clear_evaluation_data, ref, sprint)



@router.post("/runs/{run_id}/rerun", status_code=202)
async def rerun(run_id: str, account: Staff, store: Store, enqueue: Enqueue):
    """Evaluate again: a new run for the same team, sprint and kind. The earlier run and its results stay as they were."""
    run = await own_run(store, account, run_id)
    group = platform_group(account.session, run["team_ref"])
    if group is not None:
        await prepare_platform_team(store, account.session, group, run["sprint_id"], account)
    out = await start_run(store, enqueue, run["team_ref"], run["sprint_id"], run["mode"], uid(account))
    if run["mode"] == "final":
        team = await db(store.get_tracked_team, run["team_ref"])
        out["also_queued"] = await queue_unevaluated_sprints(store, enqueue, team, run["team_ref"], run["sprint_id"], uid(account), None) if team else []
    return {**out, "previous_run_id": run_id}


@router.get("/teams/{team_ref}/runs")
async def list_runs(team_ref: str, account: Staff, store: Store, sprint: str | None = None, limit: int = Query(30, ge=1, le=200)):
    await own_team(store, account, team_ref)
    group = platform_group(account.session, team_ref)
    rows = await db(store.list_runs, group.code if group else team_ref, sprint, limit)
    return [{**r, "summary": {k: v for k, v in (r.get("summary") or {}).items() if k != "report_markdown"}, "has_report": bool((r.get("summary") or {}).get("report_markdown"))} for r in rows]


@router.get("/meta")
async def performance_meta(account: SignedInAccount):
    return service.performance_meta()


def _sprints(team: dict) -> list[dict]:
    configured = (team.get("config") or {}).get("sprints", [])
    if not configured and team.get("repo_url"):
        try:
            simulator = ScrumSimulator()
            matched = simulator.match(team["repo_url"])
            if matched:
                sprints_raw = simulator.payload("list_sprints", team["repo_url"])
                configured = [
                    {"id": s["sprint_id"], "start": s["start_date"], "end": s["end_date"]}
                    for s in sprints_raw
                ]
        except Exception:
            pass
    latest = configured[-1]["id"] if configured else None
    return [{**s, "state": service.sprint_state(s.get("start"), s.get("end")),
             "is_latest": s.get("id") == latest} for s in configured]


async def _overview(store, account: Account, team_ref: str, sprint_id: str | None) -> dict:
    team = await own_team(store, account, team_ref)
    ref = team["team_ref"]
    sprints = _sprints(team)
    selected = sprint_id or (sprints[-1]["id"] if sprints else "")
    if sprints and selected not in {s["id"] for s in sprints}:
        raise bad_request("unknown_sprint", "Unknown sprint")
    # Every sprint that has results counts: a student's card shows where they stand over all of them so far, not one sprint at a time.
    per_sprint = {}
    for sp in sprints:
        for r in await db(store.latest_results, ref, sp["id"]):
            per_sprint.setdefault(r["student_id"], []).append(service.lecturer_view(r))
    group = platform_group(account.session, team_ref)
    people = {str(m.user_id): {"name": m.user.name, "picture": avatars.picture_of(m.user)} for m in group.members} if group else {}
    roster = {(s.get("student_id")): s for s in (team.get("config") or {}).get("roster", [])}
    rows = []
    for sid, results in per_sprint.items():
        total = service.overall(results)
        latest = next((r for r in results if r["sprint_id"] == selected), results[-1])
        rows.append({**latest, "mark": total["mark"], "mark_interval": total["mark_interval"], "override": None, "effective_mark": total["mark"], "status": total["status"],
                     "factors_overall": total["factors"], "sprints_done": total["sprints"], "latest_sprint": latest["sprint_id"],
                     "by_sprint": [{"sprint": r["sprint_id"], "mark": service.effective_mark(r), "status": r["status"]} for r in results],
                     "flags": [f for r in results for f in (r.get("flags") or [])]})
    rows.sort(key=lambda r: (r["mark"] is None, -(r["mark"] or 0), r["student_id"]))
    rank, previous = 0, None
    formatted = []
    for index, row in enumerate(rows, 1):
        mark = row["mark"]
        if mark != previous:
            rank = index
            previous = mark
        person = roster.get(row["student_id"], {})
        who = {"id": row["student_id"], "name": (people.get(row["student_id"]) or {}).get("name") or (person.get("names") or [row["student_id"]])[0], "picture": (people.get(row["student_id"]) or {}).get("picture")}
        formatted.append({**row, "name": who["name"], "picture": who["picture"], "student": who, "interval": row.get("mark_interval"), "overridden": False,
                          "flags": len(row["flags"]), "rank": rank, "factors": row["factors_overall"],
                          "href": f"/teams/{ref}/performance/students/{row['student_id']}?sprint={row['latest_sprint']}"})
    runs = await db(store.list_runs, ref, selected, 50)
    active = next((r for r in runs if r["status"] in ("queued", "running", "waiting_human")), None)
    latest_run = runs[0] if runs else None
    marks = [r["mark"] for r in rows if r["mark"] is not None]
    roster_list = (team.get("config") or {}).get("roster", [])
    if not roster_list and group:
        roster_list = links.agent_roster(account.session, group)
    return {"schema": "team_overview/1", "team": {"ref": ref, "name": ref, "repo": team.get("repo_url")},
            "sprints": sprints, "sprint": selected,
            "roster": roster_list,
            "run_state": {"ready": True, "blockers": [], "active_run": active, "latest_run": latest_run,
                         "can_snapshot": not active, "can_final": not active, "can_rerun": bool(latest_run and latest_run["status"] in service.FINAL_STATES),
                         "open_reviews": len(await db(store.list_reviews, "open", None))},
            "kpis": {"students": len(formatted), "average_mark": round(sum(marks) / len(marks)) if marks else None,
                     "lowest": min(marks) if marks else None, "highest": max(marks) if marks else None,
                     "need_review": sum(r["status"] == "pending_review" for r in rows), "flags": sum(len(r.get("flags") or []) for r in rows),
                     "waiting_for_answer": 0, "provisional": sum(r["status"] == "provisional" for r in rows)},
            "rows": formatted, "spread": [{k: row.get(k) for k in ("student_id", "name", "picture", "effective_mark")} for row in formatted]}


@router.get("/teams/{team_ref}/overview")
async def team_overview(team_ref: str, account: Staff, store: Store, sprint: str | None = None):
    return await _overview(store, account, team_ref, sprint)


@router.get("/teams/{team_ref}/development")
async def team_development(team_ref: str, account: Staff, store: Store, sprint: str | None = None):
    overview = await _overview(store, account, team_ref, sprint)
    snapshots = await db(store.list_snapshots, team_ref, overview["sprint"])
    by_student = {}
    for point in snapshots:
        by_student.setdefault(point["student_id"], []).append(point)
    students = []
    for row in overview["rows"]:
        points = sorted(by_student.get(row["student_id"], []), key=lambda p: p["as_of"])
        marks = [p["mark"] for p in points if p.get("mark") is not None]
        students.append({"student_id": row["student_id"], "name": row["name"], "picture": row["picture"],
                         "spark": marks, "first": marks[0] if marks else None, "latest": marks[-1] if marks else None,
                         "change": marks[-1] - marks[0] if len(marks) > 1 else 0,
                         "trend": "rising" if len(marks) > 1 and marks[-1] - marks[0] >= 5 else "falling" if len(marks) > 1 and marks[-1] - marks[0] <= -5 else "steady" if marks else "none",
                         "href": row["href"]})
    return {"schema": "team_development/1", "sprint": overview["sprint"],
            "progress": {"share": 0, "snapshots": []}, "kpis": {"team_average": None, "team_change": None, "snapshots": len(snapshots), "last_snapshot_at": None, "most_improved": None, "below_40": sum((s["latest"] or 0) < 40 for s in students)},
            "students": students, "chart": [], "factor_series": {"options": [], "team": [], "by_student": {}}, "warnings": []}


@router.get("/teams/{team_ref}/runs/summary")
async def team_runs_contract(team_ref: str, account: Staff, store: Store, sprint: str | None = None, limit: int = Query(30, ge=1, le=200)):
    await own_team(store, account, team_ref)
    rows = await db(store.list_runs, team_ref, sprint, limit)
    ended = [r for r in rows if r["status"] in service.FINAL_STATES]
    durations = [(r.get("finished_at") - r.get("started_at")).total_seconds() for r in ended if r.get("finished_at") and r.get("started_at")]
    return {"schema": "team_runs/1", "analysis": {"total": len(rows), "snapshots": sum(r["mode"] == "snapshot" for r in rows),
                "finals": sum(r["mode"] == "final" for r in rows), "success_rate": round(sum(r["status"] == "succeeded" for r in ended) / len(ended) * 100) if ended else None,
                "failed": sum(r["status"] == "failed" for r in rows), "average_seconds": sum(durations) / len(durations) if durations else None,
                "fastest_seconds": min(durations) if durations else None, "slowest_seconds": max(durations) if durations else None,
                "latest": rows[0] if rows else None, "outcomes": {s: sum(r["status"] == s for r in rows) for s in (*service.FINAL_STATES, "running")}},
            "runs": rows, "next": None}


@router.get("/teams/{team_ref}/students/{student_id}/history")
async def student_history(team_ref: str, student_id: str, account: Staff, store: Store, sprint: str | None = None):
    team = await own_team(store, account, team_ref)
    configured = _sprints(team)
    selected = sprint or (configured[-1]["id"] if configured else "")
    marks, factor_values = [], {factor[0]: [] for factor in service.FACTORS}
    for sprint_row in configured:
        result = next((r for r in await db(store.latest_results, team_ref, sprint_row["id"]) if r["student_id"] == student_id), None)
        if result:
            hidden = result["status"] in ("pending_review", "under_review") and not result.get("override")
            marks.append({"sprint": sprint_row["id"], "mark": None if hidden else service.effective_mark(result),
                          "status": "under_review" if hidden else result["status"]})
            if hidden:
                continue
            for factor, *_ in service.FACTORS:
                raw = (result.get("factors") or {}).get(factor)
                if raw and raw.get("score") is not None:
                    factor_values[factor].append((sprint_row["id"], raw["score"] * 100, service.factor_state(raw)))
    all_sprint_ids = [s["id"] for s in configured]
    marks_by_sprint = {m["sprint"]: m for m in marks}
    # Align marks to every configured sprint (null entry for sprints without a result)
    aligned_marks = [marks_by_sprint.get(sid, {"sprint": sid, "mark": None, "status": "not_assessed"}) for sid in all_sprint_ids]
    rows = []
    for factor, label, *_ in service.FACTORS:
        factor_idx = [x[0] for x in service.FACTORS].index(factor)
        tracked = service.FACTORS[factor_idx][5]
        values_by_sprint = {sid: (score, state) for sid, score, state in factor_values[factor]}
        cells, previous = [], None
        for sid in all_sprint_ids:
            if sid in values_by_sprint:
                score, state = values_by_sprint[sid]
                delta = None if previous is None else round(score - previous, 1)
                cells.append({"sprint": sid, "state": state, "score": round(score, 1), "delta": delta, "kind": "scored"})
                previous = score
            else:
                cells.append({"sprint": sid, "state": None, "score": None, "delta": None, "kind": "missing"})
        rows.append({"id": factor, "factor": factor, "label": label, "tracked": tracked,
                     "why_not_tracked": None if tracked else "Measured by questions, not sprint-to-sprint.",
                     "why": None if tracked else "Measured by questions, not sprint-to-sprint.",
                     "cells": cells})
    enough = sum(1 for m in aligned_marks if m.get("mark") is not None) >= 2
    return {"schema": "student_history/1", "current": selected, "sprints": all_sprint_ids, "marks": aligned_marks, "rows": rows, "enough": enough}


@router.get("/teams/{team_ref}/students/{student_id}/report")
async def student_report(team_ref: str, student_id: str, account: Staff, store: Store, sprint: str | None = None):
    team = await own_team(store, account, team_ref)
    configured = _sprints(team)
    selected = sprint or (configured[-1]["id"] if configured else "")

    results = await db(store.latest_results, team_ref, selected)
    current = next((r for r in results if r["student_id"] == student_id), None)
    if not current and not sprint:
        for sp in reversed(configured):
            sp_results = await db(store.latest_results, team_ref, sp["id"])
            sp_curr = next((r for r in sp_results if r["student_id"] == student_id), None)
            if sp_curr:
                selected = sp["id"]
                current = sp_curr
                results = sp_results
                break

    if not current:
        raise not_found("No assessment result found for this student")

    group = platform_group(account.session, team_ref)
    roster_list = (team.get("config") or {}).get("roster", [])
    if not roster_list and group:
        roster_list = links.agent_roster(account.session, group)
    roster = {s.get("student_id"): s for s in roster_list}
    person = roster.get(student_id, {})
    # The platform account gives the name and photo, as on the team page; the roster only has a name.
    member = next((m for m in group.members if str(m.user_id) == student_id), None) if group else None
    student_name = (member.user.name if member else None) or (person.get("names") or [student_id])[0]
    student_picture = avatars.picture_of(member.user) if member else None

    cohort_marks = [service.effective_mark(r) for r in results if service.effective_mark(r) is not None]
    average = round(sum(cohort_marks) / len(cohort_marks), 2) if cohort_marks else None
    hist = await _student_history(store, team_ref, student_id, selected)

    j = current.get("justification") or {}
    mark = service.effective_mark(current)
    flags = [{"message": f.get("message", f) if isinstance(f, dict) else str(f), "action": f.get("action"), "reason": f.get("reason")} for f in (current.get("flags") or [])]

    stored_factors = current.get("factors") or {}
    factor_results = await db(store.list_factor_results, current["run_id"], student_id)
    factor_meta_map = {fr["factor"]: fr for fr in factor_results}

    factors_out = {}
    for factor_tuple in service.FACTORS:
        fname = factor_tuple[0]
        fmeta = factor_meta_map.get(fname) or stored_factors.get(fname) or {}
        score = fmeta.get("score")
        factors_out[fname] = {
            "id": fname,
            "label": factor_tuple[1],
            "status": fmeta.get("status", "not_available"),
            "state": service.factor_state(fmeta),
            "score": score,
            "interval": fmeta.get("interval"),
            "provisional": bool(fmeta.get("provisional")),
            "warnings": fmeta.get("warnings") or [],
            "reasons": (j.get("factors") or {}).get(fname, {}).get("reasons") or [],
            "explain": (j.get("factors") or {}).get(fname, {}).get("explain", {}).get("in_short"),
            "anomalies": [a["message"] for a in ((j.get("anomalies") or {}).get(fname) or []) if a.get("message")],
            "measures": factor_tuple[4],
            "tracked": factor_tuple[5],
        }

    sprint_info = next((s for s in configured if s["id"] == selected), {"id": selected})

    return {
        "schema": "student_report/1",
        "student_id": student_id,
        "sprint_id": selected,
        "status": current.get("status"),
        "mark": mark,
        "mark_interval": None if current.get("override") else current.get("mark_interval"),
        "effective_mark": mark,
        "overridden": bool(current.get("override")),
        "override": current.get("override"),
        "student": {
            "id": student_id,
            "name": student_name,
            "picture": student_picture,
        },
        "profile": {
            "student_id": student_id,
            "name": student_name,
            "picture": student_picture,
            "team": {"ref": team_ref, "name": team.get("name") or team_ref},
            "sprint": sprint_info,
        },
        "hero": {
            "mark": mark,
            "summary": j.get("friendly_summary") or j.get("summary"),
            "override": (current.get("override") or {}).get("reason"),
            "contributions": (j.get("fused") or {}).get("contributions") or [],
        },
        "factors": factors_out,
        "flags": flags,
        "history": hist,
        "radar": {
            "axes": [
                {
                    "id": f[0],
                    "factor": f[1],
                    "short": f[1].replace("Requirement Fulfillment", "Requirements").replace("Task Complexity", "Complexity").replace("Code Ownership", "Ownership"),
                    "score": round(factors_out.get(f[0], {}).get("score") * 100) if (factors_out.get(f[0], {}).get("score") is not None and (factors_out.get(f[0], {}).get("state") == "scored" or factors_out.get(f[0], {}).get("status") == "completed")) else 0,
                    "average": round(average, 1) if average is not None else None,
                    "measured": factors_out.get(f[0], {}).get("score") is not None and (factors_out.get(f[0], {}).get("state") == "scored" or factors_out.get(f[0], {}).get("status") == "completed"),
                    "state": factors_out.get(f[0], {}).get("state") or factors_out.get(f[0], {}).get("status") or "not measured",
                }
                for f in service.FACTORS
            ]
        },
        "justification": j,
        "can_override": True,
        "all_sprints": configured,
        **service.report_sections(j, factors_out),
        "generated": j.get("generated") or {},
    }


@router.get("/teams/{team_ref}/method")
async def method(team_ref: str, account: Staff, store: Store):
    await own_team(store, account, team_ref)
    return {"schema": "method/1", "run_id": None, "formula": {"name": "weighted additive score", "description": "Available factor weights are renormalized."},
            "weights": service.WEIGHTS, "factors": [{"id": i, "label": label, "weight": service.WEIGHTS[i]} for i, label, *_ in service.FACTORS],
            "notice": "Missing or unavailable factors are excluded and the remaining weights are shared proportionally."}


@router.get("/graph")
async def get_graph(account: Staff):
    return topology()


@router.get("/runs/{run_id}")
async def get_run(run_id: str, account: Staff, store: Store):
    run = await own_run(store, account, run_id)
    return {**run, "summary": {k: v for k, v in (run.get("summary") or {}).items() if k != "report_markdown"}, "has_report": bool((run.get("summary") or {}).get("report_markdown"))}


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
async def get_events(run_id: str, account: Staff, store: Store, after: int = 0, node: str | None = None, limit: int = Query(500, ge=1, le=5000)):
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
    group = platform_group(account.session, team_ref)
    names = {str(m.user_id): {"name": m.user.name, "picture": avatars.picture_of(m.user)} for m in group.members} if group else {}
    rows = await db(store.latest_results, group.code if group else team_ref, sprint_id)
    return [{**service.lecturer_view(r), "student": names.get(r["student_id"], {"name": r["student_id"], "picture": None})} for r in rows]


class OverrideIn(BaseModel):
    mark: float | None = Field(default=None, ge=0, le=100)
    reason: str = Field(default="", max_length=1000)


@router.put("/teams/{team_ref}/sprints/{sprint_id}/students/{student_id}/override")
async def set_mark(team_ref: str, sprint_id: str, student_id: str, body: OverrideIn, account: Staff, store: Store):
    """The lecturer's own mark for a student, with the reason. The agent's prediction stays beside it; a mark of null takes the override away. The agent supports the decision and never replaces it."""
    await own_team(store, account, team_ref)
    group = platform_group(account.session, team_ref)
    ref = group.code if group else team_ref
    current = {r["student_id"]: r for r in await db(store.latest_results, ref, sprint_id)}.get(student_id)
    if current is None:
        raise not_found("There is no result for this student and sprint yet")
    if body.mark is None:
        await db(store.set_override, str(current["run_id"]), student_id, {"mark": None, "cleared_by": uid(account), "at": service.now().isoformat()})
        return {"override": None}
    if len(body.reason.strip()) < 10:
        raise bad_request("override_needs_a_reason", "Give the reason for the mark in at least 10 characters")
    ov = {"mark": body.mark, "reason": body.reason.strip(), "by": uid(account), "by_name": account.user.name, "at": service.now().isoformat()}
    await db(store.set_override, str(current["run_id"]), student_id, ov)
    return {"override": ov}


@router.get("/teams/{team_ref}/sprints/{sprint_id}/students/{student_id}/quiz")
async def student_quiz(team_ref: str, sprint_id: str, student_id: str, account: Staff, store: Store):
    """The code question this student was asked, their answer and how it was rated, for the lecturer. The reference answer used by the rater is not part of it."""
    await own_team(store, account, team_ref)
    group = platform_group(account.session, team_ref)
    q = await db(store.get_quiz, group.code if group else team_ref, sprint_id, student_id)
    if q is None:
        return None
    result = q.get("result") or {}
    return {"status": q["status"], "question": q["question"], "snippet": q["snippet"], "file_path": q.get("file_path"), "line_range": q.get("line_range"), "deadline_at": q["deadline_at"],
            "extended_until": q.get("extended_until"), "answer": q.get("answer"), "answered_at": q.get("answered_at"), "in_second_window": bool(q.get("in_extension")),
            "score": result.get("score"), "rating": (result.get("features") or {}).get("comprehension_rating_1_to_5"), "warnings": result.get("warnings", [])}


@router.get("/teams/{team_ref}/students/{student_id}/questions")
async def student_questions_by_query(team_ref: str, student_id: str, account: Staff, store: Store, sprint: str | None = None, include: Literal["summary", "list"] = "list"):
    """Shorthand for the questions endpoint: accepts sprint as a query param instead of path segment."""
    await own_team(store, account, team_ref)
    group = platform_group(account.session, team_ref)
    ref = group.code if group else team_ref
    # Use the latest configured sprint if none provided
    if not sprint:
        team = await db(store.get_tracked_team, team_ref)
        configured = _sprints(team or {})
        sprint = configured[-1]["id"] if configured else None
    if not sprint:
        raise not_found("No sprint specified or configured")
    rows = await db(store.list_quizzes, ref, sprint, student_id)
    answered = [q for q in rows if q["status"] == "answered"]
    ratings = [(q.get("result") or {}).get("features", {}).get("comprehension_rating_1_to_5") for q in answered]
    valid_ratings = [r for r in ratings if isinstance(r, (int, float))]
    summary = {
        "total": len(rows),
        "answered": len(answered),
        "average_comprehension": round(sum(valid_ratings) / len(valid_ratings), 2) if valid_ratings else None,
    }
    if include == "summary":
        return {"schema": "questions/1", "sprint": sprint, "student_id": student_id, "summary": summary}
    return {
        "schema": "questions/1",
        "sprint": sprint,
        "student_id": student_id,
        "summary": summary,
        "questions": [
            {
                "id": q.get("id"),
                "code": q.get("question", {}).get("code") or q.get("code"),
                "question": q.get("question", {}).get("question") or q.get("question_text"),
                "status": q.get("status"),
                "answer": (q.get("result") or {}).get("answer") if q.get("status") == "answered" else None,
                "comprehension": (q.get("result") or {}).get("features", {}).get("comprehension_rating_1_to_5"),
            }
            for q in rows
        ],
    }


@router.get("/teams/{team_ref}/sprints/{sprint_id}/students/{student_id}/questions")
async def student_questions(team_ref: str, sprint_id: str, student_id: str, account: Staff, store: Store, include: Literal["summary", "list"] = "list"):
    """E13: the lecturer-facing batch of code questions; scorer criteria remain server-side."""
    await own_team(store, account, team_ref)
    group = platform_group(account.session, team_ref)
    ref = group.code if group else team_ref
    rows = await db(store.list_quizzes, ref, sprint_id, student_id)
    answered = [q for q in rows if q["status"] == "answered"]
    ratings = [(q.get("result") or {}).get("features", {}).get("comprehension_rating_1_to_5") for q in answered]
    summary = {"total": len(rows), "answered": len(answered), "open": sum(q["status"] in ("open", "extended") for q in rows),
               "expired": sum(q["status"] == "expired" for q in rows), "average_rating": (sum(ratings) / len(ratings) if ratings else None),
               "answered_by_second_window": sum(bool(q.get("in_extension")) for q in answered)}
    out = {"schema": "student_questions/1", "student": {"id": student_id}, "sprint": sprint_id, "summary": summary}
    if include == "summary":
        return {k: out[k] for k in ("schema", "student", "sprint", "summary")}
    out["questions"] = [{"id": q["id"], "n": q.get("n", 1), "type": q.get("type") or (q.get("meta") or {}).get("question_type"),
                         "status": q["status"], "file_path": q.get("file_path"), "line_range": q.get("line_range"), "snippet": q["snippet"],
                         "question": q["question"], "answer": q.get("answer"), "answered_at": q.get("answered_at"),
                         "in_second_window": bool(q.get("in_extension")), "deadline_at": q["deadline_at"], "extended_until": q.get("extended_until"),
                         "rating": (q.get("result") or {}).get("features", {}).get("comprehension_rating_1_to_5"),
                         "feedback": (q.get("result") or {}).get("feedback"), "warnings": (q.get("result") or {}).get("warnings", [])} for q in rows]
    return out


@router.get("/teams/{team_ref}/students/{student_id}/trajectory")
async def trajectory_all(team_ref: str, student_id: str, account: Staff, store: Store):
    """The student's day-by-day marks over every sprint, oldest first; each point says which sprint it belongs to."""
    team = await own_team(store, account, team_ref)
    return await db(store.trajectory_all, team["team_ref"], student_id)


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
            teams[run["team_ref"]] = await can_see_team(store, account, run["team_ref"])
        if teams[run["team_ref"]]:
            out.append({**r, "summary": r.get("summary") or r.get("reason", ""), "title": r.get("title") or "The agent wants a person to look at this",
                        "form": r.get("form") or {}, "team_ref": run["team_ref"], "sprint_id": run["sprint_id"]})
    return out


def _condition_matches(condition: dict | None, answers: dict) -> bool:
    if not condition:
        return True
    value = answers.get(condition.get("field"))
    if "equals" in condition:
        return value == condition["equals"]
    return value in condition.get("in", [])


def _validate_answers(review: dict, answers: dict) -> tuple[dict, dict]:
    """Validate submitted fields and return (answers, selected outcome)."""
    form = validate_review_form(review.get("form") or {}, review["kind"])
    if not isinstance(answers, dict):
        raise bad_request("invalid_answers", "Answers must be an object")
    fields = {f["id"]: f for f in form["fields"]}
    if set(answers) - set(fields):
        raise bad_request("unknown_answer", "The form does not contain that field")
    for field_id, field in fields.items():
        visible = _condition_matches(field.get("visible_if"), answers)
        required = field.get("required", False) or _condition_matches(field.get("required_if"), answers)
        if review["kind"] == "identity_mapping" and field.get("type") == "author_map" and answers.get("decision") == "continue":
            required = False  # continuing without mapping means no author is mapped
        if not visible:
            if field_id in answers:
                raise bad_request("hidden_answer", "That field is not available for this choice")
            continue
        if required and (field_id not in answers or answers[field_id] in ("", None, [])):
            raise bad_request("missing_answer", f"{field.get('label', field_id)} is required")
        if field_id not in answers:
            continue
        value = answers[field_id]
        typ = field["type"]
        if typ in ("choice", "multi_choice"):
            options = {o["value"] for o in field.get("options", [])}
            values = value if typ == "multi_choice" else [value]
            if not isinstance(values, list) or any(v not in options for v in values):
                raise bad_request("invalid_option", f"Invalid value for {field_id}")
            if typ == "multi_choice" and not field.get("min", 0) <= len(values) <= field.get("max", len(options)):
                raise bad_request("invalid_option", f"Invalid number of values for {field_id}")
        elif typ in ("number", "slider", "mark"):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise bad_request("invalid_number", f"{field_id} must be a number")
            low, high = field.get("min", 0), field.get("max", 100 if typ == "mark" else None)
            if value < low or (high is not None and value > high):
                raise bad_request("invalid_number", f"{field_id} is outside its range")
        elif typ in ("text", "textarea") and (not isinstance(value, str) or len(value) > field.get("max_length", 300)):
            raise bad_request("invalid_text", f"Invalid value for {field_id}")
        elif typ == "author_map":
            if not isinstance(value, list):
                raise bad_request("invalid_mapping", "Author mappings must be a list")
            allowed = {str(s["id"]) for s in field.get("students", [])}
            if any(not isinstance(item, dict) or item.get("student_id") not in allowed for item in value):
                raise bad_request("invalid_mapping", "Mapping contains an unknown student")
    selected = answers.get("decision", "submit")
    outcome = form["outcomes"].get(selected)
    if outcome is None:
        raise bad_request("invalid_decision", "Choose one of the available outcomes")
    return answers, outcome


def _mapping_entry(m: dict) -> dict:
    """An author-map answer ({author: "Name <email>", student_id}) as the agent reads it: the student with the author's e-mail and name."""
    author = str(m.get("author") or "")
    email = author.rsplit("<", 1)[-1].rstrip("> ").strip() if "<" in author else ""
    name = author.split("<")[0].strip()
    return {k: v for k, v in {"student_id": m["student_id"], "email": email or m.get("email"), "name": name or m.get("name"), "login": m.get("login")}.items() if v}


@router.post("/reviews/{review_id}/answer", status_code=202)
async def answer_review(review_id: str, body: AnswerIn, account: Staff, store: Store, enqueue: Enqueue):
    review = next((r for r in await db(store.list_reviews, None, None) if str(r["id"]) == review_id), None)
    if review is None:
        raise not_found("Review not found")
    run = await own_run(store, account, str(review["run_id"]))
    if review["status"] != "open":
        raise conflict("already_decided", "This review has already been decided")
    answers, outcome = _validate_answers(review, body.answers)
    effect = outcome["effect"]
    decision: dict[str, Any] = {"effect": effect}
    if effect == "override":
        mark = answers.get(outcome.get("mark_from", "mark"))
        reason = answers.get(outcome.get("reason_from", "reason"), "")
        if not isinstance(mark, (int, float)) or len(str(reason).strip()) < 10:
            raise bad_request("override_needs_mark_and_reason", "An override needs a mark and a reason of at least 10 characters")
        if not review.get("student_id"):
            raise bad_request("no_student", "This review is not about one student")
        await db(store.set_override, str(review["run_id"]), review["student_id"], {"mark": mark, "reason": str(reason).strip(), "by": uid(account), "at": service.now().isoformat()})
        decision.update({"mark": mark, "reason": str(reason).strip()})
    elif effect == "mapping":
        if review["kind"] != "identity_mapping":
            raise bad_request("invalid_effect", "Mapping is only valid for identity reviews")
        mapping = [_mapping_entry(m) for m in answers.get(outcome.get("mapping_from", "mapping"), []) if isinstance(m, dict) and m.get("student_id")]
        decision["mapping"] = mapping
    elif effect == "rerun":
        decision["options"] = {key: answers[key] for key in outcome.get("options_from", []) if key in answers}
    decided = await db(store.decide_review, review_id, decision, uid(account), answers)
    if decided is None:
        raise conflict("already_decided", "This review has already been decided")
    if effect == "mapping":
        job = await enqueue("performance.resume_run", {"run_id": str(review["run_id"]), "resume": {"mapping": decision["mapping"]}}, lock=run["team_ref"])
    elif effect == "rerun":
        new_run = await start_run(store, enqueue, run["team_ref"], run["sprint_id"], run["mode"], uid(account), decision.get("options"))
        job = new_run.get("job_id")
    else:
        job = await enqueue("performance.review_answered", {"review_id": review_id, "run_id": str(review["run_id"]), "answers": answers, "effect": effect}, lock=run["team_ref"])
    return {"accepted": True, "review": decided, "job_id": job}


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
    """The teams in which this signed-in student is assessed, with their own student id: the account id, never a typed name. A platform team counts only while the person is still a member."""
    me = str(account.user.id)
    out = []
    for team in store.list_tracked_teams(None):
        cfg = team.get("config") or {}
        if me not in {s["student_id"] for s in cfg.get("roster", [])}:
            continue
        if cfg.get("source") == "platform":
            group = platform_group(account.session, team["team_ref"])
            m = rules.membership(group, account.user.id) if group else None
            if m is None or m.role is not MemberRole.MEMBER:
                continue
        out.append({"team_ref": team["team_ref"], "student_id": me, "release": cfg.get("release_to_students", True)})
    return out


async def _mine_for_team(store, account: Account, team_ref: str) -> dict:
    """Resolve one student/team pair without ever turning non-membership into an empty 200."""
    ref = team_ref.strip()
    matches = [m for m in await db(_mine, store, account) if m["team_ref"].lower() == ref.lower()]
    if not matches:
        raise not_found("Team is not available")
    return matches[0]


async def _student_history(store, team_ref: str, student_id: str, sprint: str | None = None) -> dict:
    team = await db(store.get_tracked_team, team_ref)
    configured = _sprints(team or {})
    selected = sprint or (configured[-1]["id"] if configured else "")
    marks, factor_values = [], {factor[0]: [] for factor in service.FACTORS}
    for sprint_row in configured:
        result = next((r for r in await db(store.latest_results, team_ref, sprint_row["id"]) if r["student_id"] == student_id), None)
        if result:
            marks.append({"sprint": sprint_row["id"], "mark": service.effective_mark(result), "status": result["status"]})
            for factor, *_ in service.FACTORS:
                raw = (result.get("factors") or {}).get(factor)
                if raw and raw.get("score") is not None:
                    factor_values[factor].append((sprint_row["id"], raw["score"] * 100, service.factor_state(raw)))
    all_sprint_ids = [s["id"] for s in configured]
    marks_by_sprint = {m["sprint"]: m for m in marks}
    # Align marks to every configured sprint (null entry for sprints without a result)
    aligned_marks = [marks_by_sprint.get(sid, {"sprint": sid, "mark": None, "status": "not_assessed"}) for sid in all_sprint_ids]
    rows = []
    for factor, label, *_ in service.FACTORS:
        factor_idx = [x[0] for x in service.FACTORS].index(factor)
        tracked = service.FACTORS[factor_idx][5]
        values_by_sprint = {sid: (score, state) for sid, score, state in factor_values[factor]}
        cells, previous = [], None
        for sid in all_sprint_ids:
            if sid in values_by_sprint:
                score, state = values_by_sprint[sid]
                delta = None if previous is None else round(score - previous, 1)
                cells.append({"sprint": sid, "state": state, "score": round(score, 1), "delta": delta, "kind": "scored"})
                previous = score
            else:
                cells.append({"sprint": sid, "state": None, "score": None, "delta": None, "kind": "missing"})
        rows.append({"id": factor, "factor": factor, "label": label, "tracked": tracked,
                     "why_not_tracked": None if tracked else "Measured by questions, not sprint-to-sprint.",
                     "why": None if tracked else "Measured by questions, not sprint-to-sprint.",
                     "cells": cells})
    enough = sum(1 for m in aligned_marks if m.get("mark") is not None) >= 2
    return {"schema": "student_history/1", "current": selected, "sprints": all_sprint_ids, "marks": aligned_marks, "rows": rows, "enough": enough}


def _student_report(result: dict, team: dict, sprint: dict, account: Account, cohort: list[dict], history: dict) -> dict:
    """Build the student-safe subset of the lecturer report.

    Do not spread stored result or justification objects here: audit, agent actions and
    arbitrary generated fields are deliberately not part of the student contract.
    """
    j = result.get("justification") or {}
    mark = service.effective_mark(result)
    average = None
    cohort_marks = [service.effective_mark(r) for r in cohort if service.effective_mark(r) is not None]
    if len(cohort_marks) >= service.performance_meta()["limits"]["min_cohort_for_average"]:
        average = round(sum(cohort_marks) / len(cohort_marks), 2)
    flags = [{"message": f.get("message", f) if isinstance(f, dict) else str(f)} for f in (result.get("flags") or [])]
    status = result.get("status")
    allowed_factor_fields = ("status", "score", "interval", "provisional", "band", "headline", "reasons", "warnings", "explain", "measures", "how_much_to_trust")
    factors = {
        factor: {key: raw[key] for key in allowed_factor_fields if key in raw}
        for factor, raw in (result.get("factors") or {}).items() if isinstance(raw, dict)
    }
    report = {
        "schema": "student_report/1",
        "student_id": result["student_id"], "sprint_id": result["sprint_id"], "status": status,
        "mark": mark, "mark_interval": None if result.get("override") else result.get("mark_interval"),
        "overridden": bool(result.get("override")),
        "generated": {"run_id": str(result.get("run_id")) if result.get("run_id") else None,
                      "mode": "snapshot", "finished_at": None},
        "profile": {"student_id": result["student_id"], "name": account.user.name, "picture": account.user.picture_url,
                    "team": {"ref": team.get("team_ref"), "name": team.get("team_ref")},
                    "sprint": {"id": sprint.get("id"), "start": sprint.get("start"), "end": sprint.get("end")}},
        "hero": {"mark": mark, "summary": j.get("friendly_summary") or j.get("summary"), "override": (result.get("override") or {}).get("reason")},
        "factors": factors,
        "flags": flags,
        "history": history,
        "radar": {"axes": [{"factor": factor[0], "score": ((result.get("factors") or {}).get(factor[0]) or {}).get("score"),
                            **({"team_average": average} if average is not None else {})} for factor in service.FACTORS]},
        "justification": {k: j[k] for k in ("summary", "friendly_summary", "headline", "key", "more", "brief", "factors", "pattern", "how_computed", "caveats") if k in j},
        "can_override": False,
    }
    report["generated"]["mode"] = "final" if status == "final" else "snapshot"
    return report


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


@router.get("/me/reports")
async def my_reports(account: StudentAccount, store: Store, team: str | None = None):
    matches = [m for m in await db(_mine, store, account) if team is None or m["team_ref"].lower() == team.strip().lower()]
    if team is not None and not matches:
        raise not_found("Team is not available")
    reports = []
    for m in matches:
        if not m["release"]:
            continue
        tracked = await db(store.get_tracked_team, m["team_ref"]) or {}
        configured = _sprints(tracked)
        for sprint in configured:
            current = next((r for r in await db(store.latest_results, m["team_ref"], sprint["id"]) if r["student_id"] == m["student_id"]), None)
            if current is None:
                continue
            hidden = current["status"] in ("pending_review", "under_review") and not current.get("override")
            if hidden:
                reports.append({"sprint": sprint, "status": "under_review", "report": None})
                continue
            history = await _student_history(store, m["team_ref"], m["student_id"], sprint["id"])
            reports.append({"sprint": sprint, "status": current["status"], "report": _student_report(
                current, tracked, sprint, account, await db(store.latest_results, m["team_ref"], sprint["id"]), history)})
    needs_connect = any(team is not None and m["team_ref"].lower() == team.strip().lower() and not (account.user.github_username or "") for m in matches)
    return {"schema": "my_reports/1", "github": {"needs_connect": needs_connect}, "reports": reports}


@router.get("/me/quizzes")
async def my_quizzes(account: StudentAccount, store: Store, team: str | None = None, status: str | None = None):
    if team is not None:
        await _mine_for_team(store, account, team)
    out = []
    for m in await db(_mine, store, account):
        if team is not None and m["team_ref"].lower() != team.strip().lower():
            continue
        for q in await db(store.list_student_quizzes, m["student_id"], status):
            if q["team_ref"] == m["team_ref"]:
                shown = {k: q.get(k) for k in ("id", "team_ref", "sprint_id", "n", "of", "type", "question", "snippet", "file_path", "line_range", "status", "deadline_at", "extended_until", "answered_at")}
                out.append(shown)
    # Keep the pre-Phase-6 response for callers that did not opt into the
    # versioned contract.  The new frontend always supplies team/status.
    return {"schema": "my_quizzes/1", "items": out} if team is not None or status is not None else out


@router.post("/me/quizzes/{quiz_id}/answer", status_code=202)
async def answer_quiz(quiz_id: str, body: QuizAnswerIn, account: StudentAccount, store: Store, enqueue: Enqueue):
    mine = {(m["team_ref"], m["student_id"]) for m in await db(_mine, store, account)}
    quizzes = [q for m in mine for q in await db(store.list_student_quizzes, m[1], None) if str(q["id"]) == quiz_id and q["team_ref"] == m[0]]
    if not quizzes:
        raise not_found("Quiz not found")
    q = quizzes[0]
    row = await db(store.submit_quiz_answer, quiz_id, body.answer.strip())
    if row is None:
        raise conflict("quiz_closed", "This question can no longer be answered")
    job = await enqueue("performance.refuse_student", {"team_ref": q["team_ref"], "sprint_id": q["sprint_id"], "student_id": q["student_id"]}, queueing_lock=f"quiz:{quiz_id}")
    return {"accepted": True, "in_second_window": bool(row.get("in_extension")), "message": "Answer sent. Thank you.", "job_id": job}


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
