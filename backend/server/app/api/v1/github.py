"""Linking GitHub: the team's repository (by the leader) and each member's GitHub account (by the member).

GET    /api/v1/github/config                    is the GitHub App set up, and where it is installed from
POST   /api/v1/teams/{team}/github/install      step 1 (leader or lecturer): the address to install the App on a repository
GET    /api/v1/github/installed                 GitHub sends the browser back here after the install (signed state, no token)
GET    /api/v1/teams/{team}/github/repos        step 2: the repositories the App can see
PUT    /api/v1/teams/{team}/github/repo         step 2: the repository the team works in
DELETE /api/v1/teams/{team}/github              take the link away
GET    /api/v1/teams/{team}/github              the repository and each member's GitHub state (members see only their own row)
GET    /api/v1/teams/{team}/gate                may this person enter the team? Checked live against GitHub on every call
POST   /api/v1/teams/{team}/github/refresh      ask GitHub again who may write to the repository
POST   /api/v1/me/github/connect                the address where a person signs in to GitHub
GET    /api/v1/github/callback                  GitHub sends the browser back here after that sign-in (signed state, no token)
GET    /api/v1/me/github                        my linked account
DELETE /api/v1/me/github                        unlink my account

Only GitHub's answers are stored, never a GitHub token. The leader chooses the repository; a member proves the account by signing in to GitHub.
"""
import uuid
from urllib.parse import quote
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from shared.contracts import UserRole
from shared.github_app import GitHubApp, GitHubAppError, read_state, sign_state
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Account, get_onboarded_account
from app.core.config import settings
from app.core.errors import ApiError, bad_request, forbidden
from app.database.session import get_db
from app.models import Group, GroupMember, MemberRole, TeamGithub, User, UserGithubAccount
from app.services import github_links as links
from app.services import team_rules as rules
from app.services import teams

router = APIRouter(tags=["GitHub"])
public_router = APIRouter(tags=["GitHub"])

Onboarded = Annotated[Account, Depends(get_onboarded_account)]
Db = Annotated[Session, Depends(get_db)]
_app: GitHubApp | None = None


def get_github_app() -> GitHubApp:
    global _app
    if _app is None:
        _app = GitHubApp(links.app_config())
    return _app


App = Annotated[GitHubApp, Depends(get_github_app)]


def _require_configured(app: GitHubApp) -> None:
    if not app.config.configured:
        raise bad_request("github_not_configured", "Linking GitHub is not set up on this server yet")


def _team(db: Session, ref: str, account: Account) -> tuple[Group, GroupMember | None]:
    return teams.team_for(db, ref, account.user, is_admin=account.role is UserRole.ADMIN)


def _can_link(group: Group, member: GroupMember | None, account: Account) -> bool:
    """The team leader and the team's lecturers (and administrators) may link the repository."""
    return account.role is UserRole.ADMIN or group.leader_id == account.user.id or bool(member and member.role is MemberRole.LECTURER)


def _must_link(group: Group, member: GroupMember | None, account: Account) -> None:
    if not _can_link(group, member, account):
        raise forbidden("leader_only", "Only the team leader or a lecturer can link the repository")


class RepoIn(BaseModel):
    full_name: str = Field(min_length=3, max_length=255, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class UrlOut(BaseModel):
    url: str


# ---- configuration ------------------------------------------------------------------------------------------------------------------

@router.get("/github/config")
def github_config(account: Onboarded, app: App):
    return {"configured": app.config.configured, "app_slug": app.config.slug or None}


# ---- the team ----------------------------------------------------------------------------------------------------------------------

@router.post("/teams/{team}/github/install", response_model=UrlOut)
def start_install(team: str, account: Onboarded, db: Db, app: App,
                  back: Annotated[str, Query(max_length=200, pattern=r"^(/[A-Za-z0-9/_\-.?=&]*)?$")] = "", popup: bool = False) -> UrlOut:
    group, member = _team(db, team, account)
    _must_link(group, member, account)
    _require_configured(app)
    state = sign_state(app.config.state_secret, {"purpose": "install", "user": str(account.user.id), "team": str(group.id), "back": back, "popup": popup})
    return UrlOut(url=f"{app.install_url}?state={state}")


def _finish_install(db: Db, app: App, installation_id: int, state: str) -> RedirectResponse:
    """The leader installed the App. The signed state says who started it and for which team."""
    base, popup = settings.APP_BASE_URL.rstrip("/"), False
    try:
        data = read_state(app.config.state_secret, state)
        popup = bool(data.get("popup"))
        if data.get("purpose") != "install":
            raise GitHubAppError("wrong kind of link")
        group = db.get(Group, uuid.UUID(data["team"]))
        user = db.get(User, uuid.UUID(data["user"]))
        if group is None or user is None:
            raise GitHubAppError("unknown team or person")
        member = rules.membership(group, user.id)
        account_like = type("A", (), {"user": user, "role": UserRole.LECTURER if member and member.role is MemberRole.LECTURER else UserRole.STUDENT})()
        if not _can_link(group, member, account_like):
            raise GitHubAppError("that person may not link this team")
        links.link_installation(db, group, installation_id, user, app)
    except (GitHubAppError, ValueError):
        return RedirectResponse(f"{base}/github/popup-done?github=error" if popup else f"{base}/?github=error")
    if popup:  # the small window only reports back to the page that opened it
        return RedirectResponse(f"{base}/github/popup-done?github=installed")
    # Back to the team's access page, which checks the person again before the dashboard opens (and then goes on to where they came from).
    nxt = f"&next={quote(data.get('back') or '', safe='/')}" if data.get("back") else ""
    return RedirectResponse(f"{base}/teams/{group.code}/access?github=installed{nxt}")


@public_router.get("/github/installed", include_in_schema=True)
def finish_install(db: Db, app: App, installation_id: int = Query(...), state: str = Query(...), setup_action: str | None = None):
    """GitHub sends the browser here after the leader installed the App (the Setup URL)."""
    return _finish_install(db, app, installation_id, state)


@router.get("/teams/{team}/github/repos")
def list_repos(team: str, account: Onboarded, db: Db, app: App):
    group, member = _team(db, team, account)
    _must_link(group, member, account)
    _require_configured(app)
    return links.available_repos(db, group, app)


@router.put("/teams/{team}/github/repo")
def choose_repo(team: str, body: RepoIn, account: Onboarded, db: Db, app: App):
    group, member = _team(db, team, account)
    _must_link(group, member, account)
    _require_configured(app)
    links.choose_repo(db, group, body.full_name, account.user, app)
    return links.readiness(db, group)


@router.delete("/teams/{team}/github", status_code=204)
def unlink_team(team: str, account: Onboarded, db: Db) -> None:
    group, member = _team(db, team, account)
    _must_link(group, member, account)
    links.unlink(db, group)


@router.get("/teams/{team}/github")
def team_github(team: str, account: Onboarded, db: Db):
    group, member = _team(db, team, account)
    state = links.readiness(db, group)
    if not _can_link(group, member, account):  # a plain member sees the repository and their own row, nobody else's
        state["members"] = [m for m in state["members"] if m["user_id"] == str(account.user.id)]
        state["notes"] = []
    state["can_link"] = _can_link(group, member, account)
    return state


@router.get("/teams/{team}/gate")
def team_gate(team: str, account: Onboarded, db: Db, app: App):
    """The check in front of the team's dashboard, made again on every page load: may this person enter, and if not, what must they do. Answered live from GitHub."""
    group, member = _team(db, team, account)
    staff = account.role is UserRole.ADMIN or bool(member and member.role is MemberRole.LECTURER)
    return {**links.gate(db, group, account.user, staff, app), "team": group.code, "team_name": group.name, "configured": app.config.configured}


@router.post("/teams/{team}/github/refresh")
def refresh(team: str, account: Onboarded, db: Db, app: App):
    group, member = _team(db, team, account)
    _must_link(group, member, account)
    _require_configured(app)
    links.refresh_access(db, group, app)
    return links.readiness(db, group)


# ---- the person --------------------------------------------------------------------------------------------------------------------

@router.post("/me/github/connect", response_model=UrlOut)
def start_connect(account: Onboarded, db: Db, app: App, team: Annotated[str, Query(max_length=64)],
                  back: Annotated[str, Query(max_length=200, pattern=r"^/[A-Za-z0-9/_\-.?=&]*$")] = "/", choose_account: bool = False) -> UrlOut:
    """A member signs in to GitHub for a team. The team leader has to link the repository first, so the member knows which repository they are joining."""
    group, _ = _team(db, team, account)
    row = links.team_link(db, group)
    if row is None or not row.repo_full_name:
        raise bad_request("leader_must_link_first", "The team leader has to link the repository before members connect their GitHub accounts")
    _require_configured(app)
    state = sign_state(app.config.state_secret, {"purpose": "connect", "user": str(account.user.id), "back": back})
    return UrlOut(url=app.authorize_url(state, links.callback_url("callback"), choose_account))


@public_router.get("/github/callback")
def finish_connect(db: Db, app: App, code: str | None = None, state: str | None = None, error: str | None = None, installation_id: int | None = None):
    """GitHub sends the browser here after the person signed in to GitHub. While "request user authorization during installation" is on, GitHub also sends an
    installation here (with the install state) instead of to the Setup URL; that is accepted too, and the code it carries is not needed."""
    base = settings.APP_BASE_URL.rstrip("/")
    if installation_id is not None and state:
        return _finish_install(db, app, installation_id, state)
    if error or not code or not state:
        return RedirectResponse(f"{base}/?github=error")
    back = "/"
    try:
        data = read_state(app.config.state_secret, state)
        if data.get("purpose") != "connect":
            raise GitHubAppError("wrong kind of link")
        back = data.get("back") or "/"
        user = db.get(User, uuid.UUID(data["user"]))
        if user is None:
            raise GitHubAppError("unknown person")
        links.connect_user(db, user, code, links.callback_url("callback"), app)
        for g in db.scalars(select(Group).join(GroupMember, GroupMember.group_id == Group.id).where(GroupMember.user_id == user.id)):
            row = links.team_link(db, g)
            if row and row.repo_full_name:
                links.refresh_access(db, g, app)
    except ApiError as e:  # for example: that GitHub account belongs to someone else. The page explains it.
        return RedirectResponse(f"{base}{back}{'&' if '?' in back else '?'}github=error&reason={e.code}")
    except (GitHubAppError, ValueError):
        return RedirectResponse(f"{base}/?github=error")
    return RedirectResponse(f"{base}{back}{'&' if '?' in back else '?'}github=connected")


@router.get("/me/github")
def my_github(account: Onboarded, db: Db):
    acc = db.scalar(select(UserGithubAccount).where(UserGithubAccount.user_id == account.user.id))
    return {"connected": acc is not None, "login": acc.login if acc else None, "avatar_url": acc.avatar_url if acc else None, "verified_at": acc.verified_at if acc else None,
            "typed_username": account.user.github_username}


@router.delete("/me/github", status_code=204)
def disconnect(account: Onboarded, db: Db) -> None:
    links.disconnect_user(db, account.user)
