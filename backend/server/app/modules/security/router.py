"""Security Assistant results, read-only.

GET /api/v1/security-assistant/teams/{team}/runs                 the runs of a team (newest first)
GET /api/v1/security-assistant/teams/{team}/students             the students of a team (lecturers and admins)
GET /api/v1/security-assistant/teams/{team}/runs/{run}           provenance, stages, tool runs, coverage, counts

`{team}` is the team's id or code, with the same rule as everywhere else: members only, anyone else gets 404. Nothing here writes
to the database or to the result folders, and nothing starts a scan. The data comes from `reader.ResultsReader`.
"""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from shared.contracts import UserRole
from sqlalchemy.orm import Session

from app.api.deps import Account, get_onboarded_account, require_account_role
from app.core.config import settings
from app.core.errors import not_found
from app.database.session import get_db
from app.models.group import Group, MemberRole
from app.modules.security.reader import NotFound, ResultsReader, counts
from app.services import team_rules as rules
from app.services import teams

router = APIRouter(prefix="/security-assistant", tags=["Security Assistant"])

SAMPLE_DIR = Path(__file__).parent / "sample_results"

Onboarded = Annotated[Account, Depends(get_onboarded_account)]
StaffOnly = Annotated[Account, Depends(require_account_role(UserRole.LECTURER, UserRole.ADMIN))]
Db = Annotated[Session, Depends(get_db)]


def get_reader() -> ResultsReader:
    """The result folders, or the checked-in sample when SECURITY_ASSISTANT_DEMO_MODE is on (never switched on by itself)."""
    return ResultsReader(SAMPLE_DIR if settings.SECURITY_ASSISTANT_DEMO_MODE else settings.security_assistant_results_dir)


Reader = Annotated[ResultsReader, Depends(get_reader)]


def demo_data() -> bool:
    return bool(settings.SECURITY_ASSISTANT_DEMO_MODE)


def team_access(db: Session, team: str, account: Account) -> Group:
    """The team if this person belongs to it (or is an administrator); otherwise 404."""
    group, _ = teams.team_for(db, team, account.user, is_admin=account.role is UserRole.ADMIN)
    return group


def load_run(reader: ResultsReader, group: Group, run_id: str) -> dict:
    try:
        return reader.run(group.code, run_id)
    except NotFound:
        raise not_found("Run not found") from None


def viewer_email(group: Group, account: Account, student: str | None) -> str | None:
    """Whose contributor ids "mine" means: the signed-in person; a lecturer or administrator may name a student of this team."""
    if student is None or account.role is UserRole.STUDENT:
        return account.user.email
    try:
        wanted = uuid.UUID(student)
    except ValueError:
        raise not_found("Student not found") from None
    member = next((m for m in group.members if m.user_id == wanted and m.role is MemberRole.MEMBER), None)
    if member is None:
        raise not_found("Student not found")
    return member.user.email


def my_contributor_ids(reader: ResultsReader, group: Group, run_id: str, account: Account, student: str | None) -> list[str]:
    return reader.contributor_ids(group.code, run_id, viewer_email(group, account, student))


@router.get("/teams/{team}/runs", summary="The Security Assistant runs of a team")
def list_runs(team: str, account: Onboarded, db: Db, reader: Reader) -> dict:
    group = team_access(db, team, account)
    return {"demo_data": demo_data(), "team": group.code, "team_repo_url": group.repo_url, "runs": reader.summaries(group.code)}


@router.get("/teams/{team}/students", summary="The students of a team (lecturers and admins)")
def list_students(team: str, account: StaffOnly, db: Db) -> list[dict]:
    group = team_access(db, team, account)
    return [{"id": str(m.user_id), "display_name": m.user.name, "github_username": m.user.github_username} for m in rules.students(group)]


@router.get("/teams/{team}/runs/{run}", summary="One run: provenance, stages, tool runs, coverage and counts")
def read_run(team: str, run: str, account: Onboarded, db: Db, reader: Reader, student: Annotated[str | None, Query()] = None) -> dict:
    group = team_access(db, team, account)
    data = load_run(reader, group, run)
    rep, usage = data["report"], data["report"].get("llm_usage") or {}
    meta = rep["meta"]
    return {
        "run_id": run, "demo_data": demo_data(), "team": group.code, "team_repo_url": group.repo_url,
        "manifest": data["manifest"],
        "stages": rep["run"]["stages"],
        "run": {"complete": rep["run"]["complete"], "incomplete_reasons": rep["run"]["incomplete_reasons"], "llm_refused": rep["run"].get("llm_refused", False)},
        "scan": rep["scan"],
        "counts": counts(rep["findings"]),
        "llm": {"model": meta.get("llm_model"), "temperature": meta.get("temperature"), "seed": usage.get("seed"),
                "interpreter_prompt": meta.get("interpreter_prompt"), "trace_prompt": meta.get("trace_prompt"), "risk_version": meta.get("risk_version"),
                "threshold": meta.get("threshold"), "total_tokens": usage.get("total_tokens"), "tutor_is_mock": bool((rep.get("questions") or {}).get("meta", {}).get("tutor_is_mock", True))},
        "my_contributor_ids": my_contributor_ids(reader, group, run, account, student),
    }
