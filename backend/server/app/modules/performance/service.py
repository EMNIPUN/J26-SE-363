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
FACTORS = (
    ("effort", "Effort", "Effort", "#10b981", "How much real work was done?", True, 0.20),
    ("consistency", "Consistency", "Consistency", "#06b6d4", "Was the work spread consistently?", True, 0.15),
    ("requirement_fulfillment", "Requirement Fulfillment", "Requirements", "#f59e0b", "Were the requirements fulfilled?", True, 0.25),
    ("collaboration", "Collaboration", "Collaboration", "#ef4444", "How well did the student collaborate?", True, 0.15),
    ("task_complexity", "Task Complexity", "Complexity", "#3b82f6", "How difficult were the tasks?", True, 0.10),
    ("code_ownership", "Code Ownership", "Ownership", "#8b5cf6", "Does the student understand their code?", False, 0.15),
)
WEIGHTS = {factor[0]: factor[6] for factor in FACTORS}


def performance_meta() -> dict:
    """Stable server-owned vocabulary used by the versioned performance payloads."""
    return {
        "schema": "meta/1", "version": "2026-10-20.1",
        "factors": [
            {"id": i, "label": label, "short": short, "colour": colour, "question": question,
             "measures": "", "validation": "", "limits": "", "tracked_by_sprint": tracked,
             "why_not_tracked": None if tracked else "It is measured by questions at the end of a sprint, so one sprint is not comparable with the next.",
             "default_weight": weight}
            for i, label, short, colour, question, tracked, weight in FACTORS
        ],
        "bands": {"low_below": 0.34, "medium_below": 0.67},
        "status": {
            "result": {"final": {"label": "Final", "tone": "success"}, "provisional": {"label": "Provisional", "tone": "primary"},
                       "pending_review": {"label": "Needs your review", "tone": "warning"}, "under_review": {"label": "Being checked", "tone": "warning"}},
            "run": {s: {"label": s.replace("_", " ").title(), "tone": "neutral"} for s in ("queued", "running", "waiting_human", "succeeded", "failed", "cancelled")},
            "factor_state": {"scored": {"label": "Scored", "short": ""}, "unavailable": {"label": "Cannot be measured", "short": "n/a"},
                             "pending": {"label": "Waiting for the answer", "short": "pending"}, "failed": {"label": "Did not run", "short": "failed"}, "missing": {"label": "Not run", "short": "-"}},
            "trend": {"rising": "Rising", "falling": "Falling", "steady": "Steady", "none": "Not enough yet"},
            "quiz": {"open": "Waiting for the answer", "extended": "Second answer window", "answered": "Answered", "expired": "Not answered: counts as 0"},
            "review_kind": {"audit": "The agent wants a person to look at this", "identity_mapping": "Some commits could not be matched to a student", "mark_check": "Mark check", "data_question": "A question about the data"},
            "why_lead": {k: k.replace("_", " ").title() for k in ("strong", "weak", "flag", "out", "override", "range", "pattern", "provisional")},
        },
        "limits": {"override_reason_min": 10, "min_cohort_for_average": 5, "questions_per_student_default": 10, "quiz_window_hours": 48, "quiz_extra_hours": 48, "quiz_second_cap": 0.5},
        "weights": WEIGHTS,
    }
SIGNATURE_PREFIX = "sha256="


@lru_cache(maxsize=1)
def default_store():
    from shared.performance import PerformanceStore

    return PerformanceStore(max_size=10)


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


def factor_state(factor: dict | None) -> str:
    if not factor:
        return "missing"
    status = factor.get("status")
    if status == "completed" and factor.get("score") is not None:
        return "scored"
    if status in ("not_available", "unavailable"):
        return "unavailable"
    if status == "pending":
        return "pending"
    if status in ("failed", "error"):
        return "failed"
    return "missing"


def display_factors(result: dict) -> dict:
    out = {}
    for factor, *_ in FACTORS:
        raw = (result.get("factors") or {}).get(factor)
        out[factor] = {"status": raw.get("status") if raw else None, "state": factor_state(raw), "score": raw.get("score") if raw else None,
                       "interval": raw.get("interval") if raw else None, "provisional": bool(raw and raw.get("provisional"))}
    return out


def counted(results: list[dict]) -> list[dict]:
    """The sprint results that count towards the final mark: a sprint whose result is still under review does not until a person has looked at it."""
    return [r for r in results if not (r["status"] == "pending_review" and not r.get("override"))]


def overall(results: list[dict]) -> dict:
    """A student's final result over every sprint that has a result so far: the mean of the sprint marks and, for each factor, the mean of its scores in the sprints where it was scored.
    ``results`` are the student's lecturer views, oldest sprint first (see ``counted`` for which of them count)."""
    counted_results = counted(results)
    marks = [m for m in (effective_mark(r) for r in counted_results) if m is not None]
    factors = {}
    for factor, *_ in FACTORS:
        shown = [display_factors(r)[factor] for r in counted_results]
        scored = [f for f in shown if f["state"] == "scored"]
        if scored:
            lows = [f["interval"][0] for f in scored if f["interval"]]
            highs = [f["interval"][1] for f in scored if f["interval"]]
            factors[factor] = {"status": "completed", "state": "scored", "score": sum(f["score"] for f in scored) / len(scored), "interval": [sum(lows) / len(lows), sum(highs) / len(highs)] if lows and len(lows) == len(highs) else None,
                               "provisional": any(f["provisional"] for f in scored), "sprints": len(scored)}
        else:
            last = next((f for f in reversed(shown) if f["state"] != "missing"), {"status": None, "state": "missing", "score": None, "interval": None, "provisional": False})
            factors[factor] = {**last, "sprints": 0}
    intervals = [r["mark_interval"] for r in counted_results if r.get("mark_interval") and not r.get("override")]
    statuses = [r["status"] for r in results]
    status = "pending_review" if "pending_review" in statuses and counted_results != results else "provisional" if any(x != "final" for x in statuses) else "final"
    return {"mark": sum(marks) / len(marks) if marks else None, "mark_interval": [sum(i[0] for i in intervals) / len(intervals), sum(i[1] for i in intervals) / len(intervals)] if intervals and len(intervals) == len(marks) else None,
            "factors": factors, "status": status, "sprints": len(marks)}


def _iso_day(at) -> str:
    return (at.date() if hasattr(at, "date") else datetime.fromisoformat(str(at)).date()).isoformat()


def development(rows: list[dict], snapshots: list[dict], sprint_ids: list[str]) -> dict:
    """What the Development page shows, worked out from the day-by-day snapshots of one sprint and the final marks of every sprint.

    ``rows`` are the team overview rows (one per student: id, name, href, by_sprint); ``snapshots`` are the sprint's snapshots (student_id, as_of, mark).
    Returns the students' movement, the team's day-by-day chart (average, lowest to highest, and every student's mark), the headline numbers, the students worth a look,
    and the final mark of every student in every sprint (for the graph across sprints).
    """
    names = {r["student_id"]: " ".join(str(r.get("name") or r["student_id"]).split()) for r in rows}
    per_day: dict[str, dict[str, float]] = {}
    for p in sorted(snapshots, key=lambda p: p["as_of"]):
        if p.get("mark") is not None:
            per_day.setdefault(_iso_day(p["as_of"]), {})[p["student_id"]] = round(p["mark"], 1)  # the last snapshot of a day is the one that counts
    days = sorted(per_day)
    chart = [{"day": d, "average": round(sum(per_day[d].values()) / len(per_day[d]), 1), "low": min(per_day[d].values()), "high": max(per_day[d].values()), "marks": per_day[d]} for d in days]

    students, warnings, changes = [], [], []
    for r in rows:
        sid = r["student_id"]
        points = [(d, per_day[d][sid]) for d in days if sid in per_day[d]]
        marks = [m for _, m in points]
        first, latest = (marks[0], marks[-1]) if marks else (None, None)
        change = round(latest - first, 1) if len(marks) > 1 else 0
        trend = "none" if not marks else "rising" if len(marks) > 1 and change >= 5 else "falling" if len(marks) > 1 and change <= -5 else "steady"
        students.append({"student_id": sid, "name": names[sid], "picture": r.get("picture"), "spark": marks, "first": first, "latest": latest, "change": change, "trend": trend, "href": r.get("href")})
        if latest is not None and len(marks) > 1:
            changes.append((change, sid))
        if latest is not None and latest < 40:
            warnings.append({"student_id": sid, "kind": "below_40", "text": f"{names[sid]} is at {round(latest)} now, below 40."})
        if len(marks) > 1 and change <= -10:
            warnings.append({"student_id": sid, "kind": "falling", "text": f"{names[sid]} has fallen {abs(round(change))} points since the first snapshot ({round(first)} to {round(latest)})."})
        drops = [(a[1] - b[1], b[0]) for a, b in zip(points, points[1:]) if a[1] - b[1] >= 10]
        if drops:
            size, at = max(drops)
            warnings.append({"student_id": sid, "kind": "sudden_drop", "text": f"{names[sid]} dropped {round(size)} points in one day ({at})."})

    best = max(changes, default=None)
    improved = next((s for s in students if best and s["student_id"] == best[1]), None) if best and best[0] > 0 else None
    latest_marks = [s["latest"] for s in students if s["latest"] is not None]
    kpis = {"team_average": round(sum(latest_marks) / len(latest_marks)) if latest_marks else None,
            "team_change": round(chart[-1]["average"] - chart[0]["average"], 1) if len(chart) > 1 else None,
            "last_snapshot_at": max((p["as_of"].isoformat() if hasattr(p["as_of"], "isoformat") else str(p["as_of"]) for p in snapshots), default=None),
            "most_improved": {"student_id": improved["student_id"], "name": improved["name"], "first_name": improved["name"].split()[0], "change": round(improved["change"])} if improved else None,
            "below_40": sum(1 for m in latest_marks if m < 40)}

    final_marks = {r["student_id"]: {b["sprint"]: b.get("mark") for b in r.get("by_sprint") or []} for r in rows}
    team_by_sprint = []
    for sp in sprint_ids:
        vals = [m for per in final_marks.values() if (m := per.get(sp)) is not None]
        team_by_sprint.append(round(sum(vals) / len(vals), 1) if vals else None)
    sprint_series = {"sprints": sprint_ids, "team": team_by_sprint,
                     "students": [{"student_id": sid, "name": names[sid], "marks": [None if per.get(sp) is None else round(per[sp], 1) for sp in sprint_ids]} for sid, per in final_marks.items()]}
    return {"students": students, "chart": chart, "kpis": kpis, "warnings": warnings, "sprint_series": sprint_series}


def band(score: float | None) -> str | None:
    if score is None:
        return None
    return "low" if score < .34 else "medium" if score < .67 else "high"


EVIDENCE_KIND = {"commit": "commit", "task": "task", "criterion": "task", "review": "review", "file": "code", "code": "code"}


def report_sections(justification: dict, factors: dict) -> dict:
    """The parts of the student report that the agent wrote or that are read straight from what it stored: the brief with its evidence, the reasons for the mark, the points each factor adds,
    the working pattern and what the agent checked. ``factors`` is the report's factor map ({id: {label, state, score, ...}})."""
    j = justification or {}
    titles = {f[0]: f[1] for f in FACTORS}
    groups = []
    for g in j.get("evidence") or []:
        lines = [{"kind": EVIDENCE_KIND.get(i.get("kind"), "note"), "text": i["text"]} for i in g.get("items", []) if i.get("text")]
        if lines:
            groups.append({"id": g["factor"], "label": titles.get(g["factor"], g["factor"]), "scored": bool(g.get("scored")), "lines": lines})
    scored = {k: v for k, v in factors.items() if v.get("score") is not None and v.get("status") == "completed"}
    share = sum(WEIGHTS.get(k, 0) for k in scored) or 1
    contributions = [{"id": k, "label": v["label"], "score": v["score"], "weight": round(WEIGHTS.get(k, 0) / share, 4), "points": round(WEIGHTS.get(k, 0) / share * v["score"] * 100, 1)}
                     for k, v in scored.items()]
    behavioral = (j.get("factors") or {}).get("behavioral_pattern") or {}
    pattern = {"persona": behavioral.get("persona"), "applied": bool(behavioral.get("applied")), "modifier": behavioral.get("modifier") or 1.0, "reasons": [r for r in behavioral.get("reasons") or [] if r]}
    return {
        "brief": {"text": (j.get("brief") or {}).get("text") or j.get("friendly_summary") or j.get("summary") or "", "evidence": groups, "generated": j.get("generated") or {}},
        "why": {"headline": j.get("headline") or j.get("friendly_summary") or j.get("summary"), "key": j.get("key") or [], "more": j.get("more") or [], "summary": j.get("summary")},
        "contributions": contributions, "pattern": pattern, "audit": j.get("audit") or {},
    }


# What the Scrum board calls a sprint's state, in the words of the three states the pages use.
BOARD_SPRINT_STATE = {"completed": "finished", "complete": "finished", "done": "finished", "closed": "finished", "finished": "finished",
                      "active": "current", "in_progress": "current", "in progress": "current", "current": "current",
                      "planned": "upcoming", "upcoming": "upcoming", "not_started": "upcoming", "future": "upcoming"}


def sprint_state(start: str, end: str, today=None, board_status: str | None = None) -> str:
    """finished, current or upcoming. The Scrum board's own status wins when it gives one (the agent reads the same status); otherwise the dates decide."""
    reported = BOARD_SPRINT_STATE.get(str(board_status or "").strip().lower())
    if reported:
        return reported
    today = today or datetime.now(timezone.utc).date()
    try:
        begin, finish = datetime.fromisoformat(start).date(), datetime.fromisoformat(end).date()
    except (TypeError, ValueError):
        return "upcoming"
    return "upcoming" if today < begin else "finished" if today > finish else "current"


def sprint_progress(sprint: dict, snapshot_times: list, today=None) -> dict:
    """Where a sprint stands, for the Development page: its state, the day it is on, how far through it is (0 to 1), and where each snapshot falls along it."""
    state = sprint.get("state") or "upcoming"
    try:
        begin, finish = datetime.fromisoformat(str(sprint["start"])).date(), datetime.fromisoformat(str(sprint["end"])).date()
    except (KeyError, TypeError, ValueError):
        return {"state": state, "day": 0, "days": 0, "share": 1.0 if state == "finished" else 0.0, "snapshots": []}
    days = max(1, (finish - begin).days + 1)
    today = today or datetime.now(timezone.utc).date()
    day = days if state == "finished" else 0 if state == "upcoming" else min(max((today - begin).days + 1, 1), days)
    positions = []
    for at in snapshot_times:
        try:
            moment = at.date() if hasattr(at, "date") else datetime.fromisoformat(str(at)).date()
        except (TypeError, ValueError):
            continue
        positions.append(round(min(max((moment - begin).days / days, 0.0), 1.0), 4))
    return {"state": state, "day": day, "days": days, "share": round(day / days, 4), "snapshots": sorted(set(positions))}


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
