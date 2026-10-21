"""Day by day: the mark as it stood at the end of each day of a sprint, worked out by the agent from the evidence it already holds.

For every day the evidence is cut to what existed then (commits, reviews and comments up to that day, with ``as_of`` set so the factor packages give a result "to date"), and the factors that can be
measured from the repository alone are run again: Effort, Consistency, Task Complexity and Collaboration. Requirement Fulfillment (a language model reads the code for every criterion) and Code Ownership
(the student's answers) are not repeated for every day; they join the mark in the final result. The fused mark of a day is therefore a mark "so far", from the factors that could be measured then,
and each point lists which factors it used. A score only ever comes from a factor package; this module cuts the evidence and calls them.
"""
from datetime import date, datetime, timedelta, timezone

from app.agents.performance_assessment.assessment import factors
from app.agents.performance_assessment.assessment.fusion import fuse

DAILY_FACTORS = ("effort", "consistency", "task_complexity", "collaboration")


def _day(text):
    if not text:
        return None
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(timezone.utc).date()
    except ValueError:
        try:
            return date.fromisoformat(str(text)[:10])
        except ValueError:
            return None


def days_of(start: date, end: date, last: date | None = None) -> list[date]:
    """The days from the start of the sprint to ``end`` (not included: the final result stands for that day), or to the day before ``last`` when the sprint is still running."""
    stop = min(end, last) if last else end
    return [start + timedelta(days=i) for i in range((stop - start).days)]


def evidence_on(evidence: dict, day: date) -> dict:
    """The evidence as it was at the end of ``day``."""
    def upto(rows, key):
        kept = []
        for r in rows or []:
            d = _day(r.get(key))
            if d is None or d <= day:
                kept.append(r)
        return kept

    commits = upto(evidence.get("commits"), "authored_at")
    seen = {c["id"] for c in commits}
    tasks = [{**t, "commit_ids": [c for c in t.get("commit_ids", []) if c in seen]} for t in evidence.get("tasks", [])]
    cut = {**evidence, "commits": commits, "tasks": tasks, "as_of": datetime.combine(day, datetime.max.time().replace(microsecond=0), tzinfo=timezone.utc).isoformat()}
    for key, field in (("reviews", "at"), ("comments", "at"), ("pull_requests", "created_at")):
        if key in evidence:
            cut[key] = upto(evidence[key], field)
    return cut


async def mark_on(evidence: dict, day: date) -> dict:
    """One day's point: the factors measurable then, and the mark fused from them."""
    cut = evidence_on(evidence, day)
    results = {}
    for name in DAILY_FACTORS:
        try:
            results[name] = await factors.run_factor(name, cut)
        except Exception as e:  # one factor failing on one day leaves a gap for that factor, not for the day
            results[name] = {"factor": name, "score": None, "status": "fallback", "interval": None, "warnings": [f"{type(e).__name__}: {str(e)[:120]}"], "versions": {}, "features": {}, "provisional": True,
                             "removed": {}, "tasks": None, "model": None}
    fused = fuse(results, None)
    compact = {k: {"score": r["score"], "status": r["status"], "interval": r["interval"], "provisional": True} for k, r in results.items()}
    return {"mark": fused["mark"], "interval": fused["mark_interval"], "factors": compact, "commits": len(cut["commits"]), "measured": sorted(k for k, r in results.items() if r["status"] == "completed")}


async def trajectory(evidence: dict, start: date, end: date, days_total: int, last: date | None = None) -> list[dict]:
    """Every day's point of one student: [{"as_of", "elapsed", "mark", "interval", "factors", "commits", "measured"}]."""
    out = []
    for day in days_of(start, end, last):
        point = await mark_on(evidence, day)
        out.append({"as_of": datetime.combine(day, datetime.max.time().replace(microsecond=0), tzinfo=timezone.utc), "elapsed": min(1.0, ((day - start).days + 1) / max(1, days_total)), **point})
    return out
