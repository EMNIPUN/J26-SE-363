"""Rules of the performance module that do not depend on HTTP: who may see what, what a student is allowed to read, how a job is queued.

The assessment itself runs in the agent worker (backend/agentic_framework); this side creates run rows, queues jobs and reads results from the shared tables (shared.performance).
"""

import hashlib
import hmac
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Protocol

from procrastinate.exceptions import AlreadyEnqueued
from shared.contracts import UserRole
from shared.queue import app as procrastinate_app

FINAL_STATES = ("succeeded", "failed", "cancelled")
SIGNATURE_PREFIX = "sha256="


@lru_cache(maxsize=1)
def default_store():
    from shared.performance import PerformanceStore

    return PerformanceStore()


class Enqueuer(Protocol):
    async def __call__(self, task: str, payload: dict[str, Any], *, lock: str | None = None, queueing_lock: str | None = None) -> int: ...


async def enqueue(task: str, payload: dict[str, Any], *, lock: str | None = None, queueing_lock: str | None = None) -> int:
    """Put a job on the queue (the worker in backend/agentic_framework picks it up)."""
    options: dict[str, Any] = {"name": task, "queue": "performance"}
    if lock:
        options["lock"] = lock
    if queueing_lock:
        options["queueing_lock"] = queueing_lock
    try:
        return await procrastinate_app.configure_task(**options).defer_async(payload=payload)
    except AlreadyEnqueued:  # the same job is already waiting (for example two pushes in a row): nothing more to do
        return 0


def can_manage(team: dict | None, user_id: str, role: UserRole | None) -> bool:
    """A lecturer manages the teams they started tracking; an administrator manages all."""
    return bool(team) and (role == UserRole.ADMIN or team.get("created_by") == user_id)


def effective_mark(result: dict) -> float | None:
    """The mark a person sees: the lecturer's override when there is one, otherwise the agent's prediction."""
    ov = result.get("override")
    return ov["mark"] if ov and ov.get("mark") is not None else result.get("mark")


def lecturer_view(result: dict) -> dict:
    return {**result, "effective_mark": effective_mark(result)}


def student_view(result: dict) -> dict:
    """What the student may read about their own result. A result under review is hidden until the lecturer has looked at it."""
    hidden = result["status"] == "pending_review" and not result.get("override")
    base = {"student_id": result["student_id"], "sprint_id": result["sprint_id"], "status": "under_review" if hidden else result["status"], "updated_at": result.get("updated_at")}
    if hidden:
        return base
    j = result.get("justification") or {}
    return {**base, "mark": effective_mark(result), "mark_interval": None if result.get("override") else result.get("mark_interval"), "factors": result.get("factors"),
            "justification": {k: j.get(k) for k in ("summary", "friendly_summary", "factors", "how_computed", "caveats") if k in j}, "overridden": bool(result.get("override"))}


def find_student(store, github_login: str | None, email: str | None) -> list[dict]:
    """The roster entries (team and student id) that belong to a signed-in student, matched on their GitHub login or e-mail address."""
    login, mail = (github_login or "").strip().lower(), (email or "").strip().lower()
    found = []
    for team in store.list_tracked_teams(None):
        for s in (team.get("config") or {}).get("roster", []):
            logins = {x.strip().lower() for x in s.get("logins", [])}
            emails = {x.strip().lower() for x in s.get("emails", []) + ([s["user_email"]] if s.get("user_email") else [])}
            if (login and login in logins) or (mail and mail in emails):
                found.append({"team_ref": team["team_ref"], "student_id": s["student_id"], "release": (team.get("config") or {}).get("release_to_students", True)})
    return found


def repo_key(url: str) -> str:
    u = (url or "").strip().lower().rstrip("/")
    for prefix in ("https://", "http://"):
        if u.startswith(prefix):
            u = u[len(prefix):]
    return u[:-4] if u.endswith(".git") else u


def verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    if not secret or not header or not header.startswith(SIGNATURE_PREFIX):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len(SIGNATURE_PREFIX):])


def webhook_secret() -> str:
    return os.environ.get("GITHUB_WEBHOOK_SECRET", "")


def now() -> datetime:
    return datetime.now(timezone.utc)
