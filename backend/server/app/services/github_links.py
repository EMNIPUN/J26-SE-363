"""Who is who on GitHub, and which repository a team works in.

Three facts are kept, all verified by GitHub rather than typed:
  * ``UserGithubAccount``   this person signed in to GitHub from the system, so they own that account;
  * ``TeamGithub``          the team leader installed the GitHub App on a repository and picked it for the team;
  * ``TeamGithubAccess``    what GitHub says each linked member may do on that repository (none, read, write, admin).
The assessment agent is started from these facts only (``agent_roster``); nobody types a roster.
"""
import uuid
from datetime import datetime, timezone

from shared.github_app import GitHubApp, GitHubAppConfig, GitHubAppError, noreply_emails
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import bad_request, conflict
from app.models import Group, GroupMember, MemberRole, TeamGithub, TeamGithubAccess, User, UserGithubAccount

WRITE = ("write", "admin")


def app_config() -> GitHubAppConfig:
    key = settings.GITHUB_APP_PRIVATE_KEY
    if not key and settings.GITHUB_APP_PRIVATE_KEY_PATH:
        from pathlib import Path

        p = Path(settings.GITHUB_APP_PRIVATE_KEY_PATH)
        key = p.read_text(encoding="utf-8") if p.is_file() else ""
    return GitHubAppConfig(app_id=settings.GITHUB_APP_ID, slug=settings.GITHUB_APP_SLUG, client_id=settings.GITHUB_APP_CLIENT_ID, client_secret=settings.GITHUB_APP_CLIENT_SECRET,
                           private_key=key.replace("\\n", "\n"), state_secret=settings.GITHUB_STATE_SECRET or settings.GITHUB_APP_CLIENT_SECRET)


def now() -> datetime:
    return datetime.now(timezone.utc)


def callback_url(path: str) -> str:
    return f"{settings.GITHUB_CALLBACK_BASE.rstrip('/')}/github/{path}"


def team_link(db: Session, group: Group) -> TeamGithub | None:
    return db.scalar(select(TeamGithub).where(TeamGithub.group_id == group.id))


def linked_accounts(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, UserGithubAccount]:
    if not user_ids:
        return {}
    return {a.user_id: a for a in db.scalars(select(UserGithubAccount).where(UserGithubAccount.user_id.in_(user_ids)))}


# ---- the team ------------------------------------------------------------------------------------------------------------------------

def link_installation(db: Session, group: Group, installation_id: int, by: User, app: GitHubApp) -> TeamGithub:
    """Remember the installation the leader made for this team. A different installation than before clears the chosen repository."""
    try:
        account = app.installation_account(installation_id)
    except GitHubAppError as e:
        raise bad_request("github_installation", str(e)) from None
    row = team_link(db, group)
    if row is None:
        row = TeamGithub(group_id=group.id, installation_id=installation_id)
        db.add(row)
    elif row.installation_id != installation_id:
        row.repo_full_name = row.repo_id = None
        db.query(TeamGithubAccess).filter(TeamGithubAccess.group_id == group.id).delete()
    row.installation_id, row.account_login, row.linked_by_id = installation_id, account.get("login"), by.id
    db.commit()
    return row


def available_repos(db: Session, group: Group, app: GitHubApp) -> list[dict]:
    row = team_link(db, group)
    if row is None:
        raise bad_request("github_not_installed", "Install the GitHub App on your repository first")
    try:
        return app.installation_repos(row.installation_id)
    except GitHubAppError as e:
        raise bad_request("github_installation", str(e)) from None


def choose_repo(db: Session, group: Group, full_name: str, by: User, app: GitHubApp) -> TeamGithub:
    """The repository the team works in. It must be one the leader gave the App access to."""
    repos = {r["full_name"].lower(): r for r in available_repos(db, group, app)}
    chosen = repos.get(full_name.strip().lower())
    if chosen is None:
        raise bad_request("github_repo_not_available", "The App is not installed on that repository")
    row = team_link(db, group)
    row.repo_full_name, row.repo_id, row.repo_private, row.linked_by_id = chosen["full_name"], chosen["id"], chosen["private"], by.id
    group.repo_url = f"https://github.com/{chosen['full_name']}"
    db.commit()
    refresh_access(db, group, app)
    return row


def unlink(db: Session, group: Group) -> None:
    db.query(TeamGithubAccess).filter(TeamGithubAccess.group_id == group.id).delete()
    db.query(TeamGithub).filter(TeamGithub.group_id == group.id).delete()
    group.repo_url = None
    db.commit()


def refresh_access(db: Session, group: Group, app: GitHubApp) -> list[TeamGithubAccess]:
    """Ask GitHub what each member who linked an account may do on the repository."""
    row = team_link(db, group)
    if row is None or not row.repo_full_name:
        return []
    students = [m.user_id for m in group.members if m.role is MemberRole.MEMBER]
    accounts = linked_accounts(db, students)
    existing = {a.user_id: a for a in db.scalars(select(TeamGithubAccess).where(TeamGithubAccess.group_id == group.id))}
    out = []
    for uid in students:
        acc = accounts.get(uid)
        if acc is None:
            if uid in existing:
                db.delete(existing[uid])
            continue
        try:
            perm = app.permission(row.installation_id, row.repo_full_name, acc.login)
        except GitHubAppError:
            continue  # keep the earlier answer; GitHub may be down for a moment
        rec = existing.get(uid) or TeamGithubAccess(group_id=group.id, user_id=uid)
        rec.permission, rec.checked_at = perm, now()
        db.add(rec)
        out.append(rec)
    db.commit()
    return out


# ---- a person ------------------------------------------------------------------------------------------------------------------------

def connect_user(db: Session, user: User, code: str, redirect_uri: str, app: GitHubApp) -> UserGithubAccount:
    try:
        token = app.exchange_code(code, redirect_uri)
        who = app.user(token)
    except GitHubAppError as e:
        raise bad_request("github_sign_in", str(e)) from None
    other = db.scalar(select(UserGithubAccount).where(UserGithubAccount.github_id == who["id"], UserGithubAccount.user_id != user.id))
    if other is not None:
        raise conflict("github_account_taken", "That GitHub account is already linked to another person")
    acc = db.scalar(select(UserGithubAccount).where(UserGithubAccount.user_id == user.id))
    if acc is None:
        acc = UserGithubAccount(user_id=user.id, github_id=who["id"], login=who["login"], verified_at=now())
        db.add(acc)
    acc.github_id, acc.login, acc.avatar_url, acc.verified_at = who["id"], who["login"], who.get("avatar_url"), now()
    db.commit()
    return acc


def disconnect_user(db: Session, user: User) -> None:
    db.query(TeamGithubAccess).filter(TeamGithubAccess.user_id == user.id).delete()
    db.query(UserGithubAccount).filter(UserGithubAccount.user_id == user.id).delete()
    db.commit()


# ---- what the agent is given ---------------------------------------------------------------------------------------------------------

def member_states(db: Session, group: Group) -> list[dict]:
    """Every student of the team with the state of their GitHub link: not_connected, no_access, read_only or ready."""
    students = [m for m in group.members if m.role is MemberRole.MEMBER]
    accounts = linked_accounts(db, [m.user_id for m in students])
    access = {a.user_id: a for a in db.scalars(select(TeamGithubAccess).where(TeamGithubAccess.group_id == group.id))}
    out = []
    for m in students:
        acc, perm = accounts.get(m.user_id), access.get(m.user_id)
        if acc is None:
            state = "not_connected"
        elif perm is None:
            state = "unchecked"
        elif perm.permission in WRITE:
            state = "ready"
        elif perm.permission == "read":
            state = "read_only"
        else:
            state = "no_access"
        out.append({"user_id": str(m.user_id), "name": m.user.name, "is_leader": group.leader_id == m.user_id, "login": acc.login if acc else None, "avatar_url": acc.avatar_url if acc else None,
                    "permission": perm.permission if perm else None, "checked_at": perm.checked_at if perm else None, "state": state})
    return out


def readiness(db: Session, group: Group) -> dict:
    """What stands in the way of an assessment: a list of blockers (cannot start) and notes (can start, results will be thinner)."""
    row = team_link(db, group)
    states = member_states(db, group)
    blockers, notes = [], []
    if row is None:
        blockers.append("The team leader has not installed the GitHub App.")
    elif not row.repo_full_name:
        blockers.append("The team leader has not chosen the repository.")
    if not states:
        blockers.append("The team has no student members yet.")
    ready = [s for s in states if s["state"] == "ready"]
    if states and not ready:
        blockers.append("No member has connected a GitHub account that can write to the repository.")
    for s in states:
        if s["state"] == "not_connected":
            notes.append(f"{s['name']} has not connected GitHub: their commits may not be matched to them.")
        elif s["state"] in ("no_access", "read_only"):
            notes.append(f"{s['name']}'s GitHub account cannot write to the repository.")
    return {"ready": not blockers, "blockers": blockers, "notes": notes, "members": states, "repo": row.repo_full_name if row else None}


def agent_roster(db: Session, group: Group) -> list[dict]:
    """The students of the team as the agent wants them: our own user id, the verified GitHub login, GitHub's no-reply commit addresses, the name. Only verified logins are used."""
    students = [m for m in group.members if m.role is MemberRole.MEMBER]
    accounts = linked_accounts(db, [m.user_id for m in students])
    roster = []
    for m in students:
        acc = accounts.get(m.user_id)
        emails = list(noreply_emails(acc.github_id, acc.login)) if acc else []
        if m.user.email:
            emails.append(m.user.email.lower())
        roster.append({"student_id": str(m.user_id), "logins": [acc.login] if acc else [], "emails": emails, "names": [m.user.name] if m.user.name else []})
    return roster
