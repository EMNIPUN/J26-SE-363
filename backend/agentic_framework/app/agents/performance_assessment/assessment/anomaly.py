"""Anomalies: signs that a factor's input may not mean what it seems, looked for after every factor has run.

The evidence is passive (commits, board states, pull requests), so it can be gamed or simply be unrepresentative: work saved in one burst at the deadline, one huge commit, lines that are not real work, tasks
closed without code, a team that never reviews. Two checks run after each factor and neither can change a score; they only raise a flag the lecturer sees:

  rules(factor, result, evidence, memory)   fixed, explainable checks on the evidence and the factor's own features (always run, no model)
  review(llm, factor, ...)                  the language model reads what the factor measured, what it was given and what it returned, together with the same student's earlier sprints,
                                            and names anything that looks gamed or unrepresentative. Each finding must quote numbers that are in the facts it was given, or it is dropped.

A finding is ``{"id", "factor", "severity": "info" | "warn", "message", "source": "rule" | "agent"}``.
"""
import json
import re
from collections import Counter
from datetime import date, datetime, timezone

BURST_SHARE = 0.5          # this share of a student's commits (or lines) in one place is a burst
MICRO_LINES = 3
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")


def _day(text):
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00")).astimezone(timezone.utc).date()
    except (TypeError, ValueError):
        return None


def _added(commit):
    total = 0
    for f in commit.get("files", []):
        stats = (f.get("line_stats") or {}).get("added")
        total += stats.get("code", 0) if stats else (f.get("added") or 0)
    return total


def _f(id, factor, severity, message):
    return {"id": id, "factor": factor, "severity": severity, "message": message, "source": "rule"}


def _effort(r, e):
    out, commits = [], [c for c in e.get("commits", []) if not c.get("is_merge")]
    sizes = [_added(c) for c in commits]
    total = sum(sizes)
    if total and max(sizes) / total >= BURST_SHARE and len(commits) > 2:
        out.append(_f("one_big_commit", "effort", "warn", f"One commit holds {round(100 * max(sizes) / total)}% of the {total} counted lines ({len(commits)} commits), so the effort score rests mostly on a single save."))
    if commits and sum(1 for s in sizes if s <= MICRO_LINES) / len(commits) >= BURST_SHARE and len(commits) >= 6:
        out.append(_f("micro_commits", "effort", "warn", f"{sum(1 for s in sizes if s <= MICRO_LINES)} of {len(commits)} commits change {MICRO_LINES} counted lines or fewer; many tiny commits can raise a commit count without adding work."))
    rem = r.get("removed") or {}
    ignored, counted = sum(rem.get(k, 0) for k in ("comment", "blank", "format_only")), (r.get("features") or {}).get("E_LOC_net", 0)
    if ignored and ignored >= counted and ignored >= 100:
        out.append(_f("mostly_noise", "effort", "warn", f"{ignored} lines were comments, blanks or formatting against {counted} counted lines: much of what was typed is not work."))
    days = Counter(d for d in (_day(c.get("authored_at")) for c in commits) if d)
    if len(commits) >= 5 and days and max(days.values()) / len(commits) >= 0.7:
        day, n = days.most_common(1)[0]
        out.append(_f("one_day", "effort", "warn", f"{n} of {len(commits)} commits were made on {day.isoformat()}."))
    return out


def _consistency(r, e):
    out, sprint = [], e.get("sprint") or {}
    try:
        start, days = date.fromisoformat(str(sprint["start"])[:10]), int(sprint.get("days") or 14)
    except (KeyError, ValueError):
        return out
    active = sorted({(d - start).days + 1 for d in (_day(c.get("authored_at")) for c in e.get("commits", [])) if d and 0 <= (d - start).days < days})
    if active and len(active) >= 1 and min(active) > 0.7 * days:
        out.append(_f("deadline_rush", "consistency", "warn", f"All the work falls in the last {days - min(active) + 1} days of the {days}-day sprint (first active day {min(active)}): consistent with leaving it to the deadline."))
    elif active and len(active) <= 2 and len(e.get("commits", [])) >= 4:
        out.append(_f("few_days", "consistency", "warn", f"{len(e['commits'])} commits fall on only {len(active)} day{'s' if len(active) != 1 else ''} of {days}."))
    late = (r.get("features") or {}).get("C_DC")
    if isinstance(late, (int, float)) and late >= 0.6 and active:
        out.append(_f("late_churn", "consistency", "info", f"{round(late * 100)}% of the changes come in the last part of the sprint."))
    return out


def _collaboration(r, e):
    out = []
    reviews, prs = e.get("reviews") or [], e.get("pull_requests") or []
    if not prs and not reviews:
        out.append(_f("no_pull_requests", "collaboration", "warn", "The repository has no pull requests in this sprint, so there are no reviews to read: the team may be committing straight to the main branch. Collaboration is left out, not scored as 0."))
    own = [x for x in reviews if x.get("reviewer") and x.get("reviewer") == x.get("pr_author")]
    if own:
        out.append(_f("self_review", "collaboration", "warn", f"{len(own)} review{'s' if len(own) != 1 else ''} were written by the author of the pull request itself."))
    quick = [x for x in reviews if str(x.get("state", "")).upper() == "APPROVED" and len(str(x.get("body") or "").strip()) < 12]
    if len(reviews) >= 3 and len(quick) / len(reviews) >= 0.8:
        out.append(_f("rubber_stamp", "collaboration", "warn", f"{len(quick)} of {len(reviews)} reviews are approvals with no comment."))
    return out


def _task_complexity(r, e):
    out, tasks = [], e.get("tasks") or []
    points = sum(t.get("story_points") or 0 for t in tasks)
    code = sum(_added(c) for c in e.get("commits", []))
    if points >= 13 and code and code / points < 15:
        out.append(_f("points_without_code", "task_complexity", "warn", f"{points} story points are assigned but only {code} counted lines were written: the points may overstate the work."))
    if points and not code:
        out.append(_f("points_no_commits", "task_complexity", "warn", f"{points} story points are assigned and no counted code is attributed to the student."))
    if tasks and max((t.get("story_points") or 0) for t in tasks) >= 0.7 * max(points, 1) and len(tasks) > 1:
        out.append(_f("one_task_holds_points", "task_complexity", "info", "Most of the story points sit on one task."))
    return out


def _requirements(r, e):
    out, done = [], [t for t in e.get("tasks") or [] if str(t.get("status", "")).lower() in ("done", "closed", "completed")]
    judged = [t for t in (r.get("tasks") or []) if t.get("status") == "judged"]
    unlinked = [t for t in done if not t.get("commit_ids")]
    if done and len(unlinked) == len(done):
        out.append(_f("done_without_commits", "requirement_fulfillment", "warn", f"{len(done)} task{'s are' if len(done) != 1 else ' is'} marked Done on the board with no commit linked to them."))
    met = [(sum(1 for v in (t.get("verdicts") or []) if v == "met"), len(t.get("verdicts") or [])) for t in judged]
    if met and done and sum(m for m, _ in met) == 0:
        out.append(_f("done_but_not_met", "requirement_fulfillment", "warn", f"{len(done)} task{'s are' if len(done) != 1 else ' is'} marked Done but no acceptance criterion was found in the code."))
    return out


RULES = {"effort": _effort, "consistency": _consistency, "collaboration": _collaboration, "task_complexity": _task_complexity, "requirement_fulfillment": _requirements}


def rules(factor, result, evidence, memory=None):
    """The fixed checks for one factor. Returns a list of findings; never raises (a failed check is a gap, not a failed run)."""
    try:
        return RULES[factor](result or {}, evidence or {})
    except Exception:
        return []


def _numbers(value):
    if isinstance(value, bool):
        return set()
    if isinstance(value, (int, float)):
        return {str(value), f"{value:g}", str(round(value)), f"{value * 100:g}", str(round(value * 100))}
    if isinstance(value, dict):
        return set().union(*[_numbers(v) for v in value.values()]) if value else set()
    if isinstance(value, (list, tuple)):
        return set().union(*[_numbers(v) for v in value]) if value else set()
    if isinstance(value, str):
        return {n.rstrip("%") for n in _NUMBER.findall(value)}
    return set()


def facts_for(factor, result, evidence, card, memory, found):
    """What the model is given about one factor: what it measures and where it is weak (the card), what it returned, the evidence summary, the earlier sprints and what the rules found."""
    e = evidence or {}
    commits = e.get("commits", [])
    return {"factor": factor, "measures": (card or {}).get("measures", ""), "limits": (card or {}).get("limits", ""),
            "result": {"score": result.get("score"), "status": result.get("status"), "interval": result.get("interval"), "warnings": (result.get("warnings") or [])[:5],
                       "features": {k: v for k, v in (result.get("features") or {}).items() if isinstance(v, (int, float))}},
            "evidence": {"sprint_days": (e.get("sprint") or {}).get("days"), "commits": len(commits), "tasks": len(e.get("tasks") or []), "pull_requests": len(e.get("pull_requests") or []), "reviews": len(e.get("reviews") or []),
                         "commit_days": sorted(Counter(str(_day(c.get("authored_at"))) for c in commits).items())[:20], "lines_per_commit": sorted(_added(c) for c in commits)[-12:]},
            "earlier_sprints": memory or [], "rule_findings": [x["message"] for x in found]}


def review(llm, factor, result, evidence, card, memory, found):
    """The model's own reading of one factor: anything that looks gamed, inflated or unrepresentative that the rules did not already say. Findings that quote a number not in the facts are dropped."""
    if llm is None or (result or {}).get("status") not in ("completed", "not_available"):
        return []
    facts = facts_for(factor, result, evidence, card, memory, found)
    try:
        reply = llm.chat([{"role": "system", "content": "You check one factor of a student's sprint assessment for signs that the passive data (commits, board states, pull requests) was gamed, inflated or does not represent the work. "
                                                         "You know what the factor measures, what it was given and what it returned, and how the same student did in earlier sprints. Name only what the FACTS show, in one plain sentence each, "
                                                         "quoting the numbers; do not repeat rule_findings; say nothing about the student's character. Reply with JSON {\"anomalies\": [{\"severity\": \"info\" or \"warn\", \"message\": \"...\"}]}, an empty list when nothing looks wrong."},
                           {"role": "user", "content": json.dumps(facts, sort_keys=True, default=str)}], max_tokens=1800, temperature=0.0, tag="anomaly", json_mode=True)
        rows = json.loads(getattr(reply, "text", "") or "{}").get("anomalies", [])
    except Exception:
        return []
    allowed, out = _numbers(facts), []
    for row in rows if isinstance(rows, list) else []:
        text = str(row.get("message", "")).strip() if isinstance(row, dict) else ""
        if not text or len(text) > 320 or "<" in text or any(n.rstrip("%") not in allowed for n in _NUMBER.findall(text)):
            continue
        said = [x["message"] for x in found] + [x["message"] for x in out]
        mine = set(_NUMBER.findall(text))
        words = set(re.findall(r"[a-z]{4,}", text.lower()))
        if any((mine and mine <= set(_NUMBER.findall(m))) or len(mine & set(_NUMBER.findall(m))) >= 2
               or (words and len(words & set(re.findall(r"[a-z]{4,}", m.lower()))) / len(words | set(re.findall(r"[a-z]{4,}", m.lower()))) >= 0.4) for m in said):
            continue  # already said by a rule (or by an earlier finding), in other words
        out.append({"id": f"agent_{factor}_{len(out) + 1}", "factor": factor, "severity": "warn" if row.get("severity") == "warn" else "info", "message": text, "source": "agent"})
    return out[:4]


def memory_of(history_rows):
    """The earlier sprints of one student as a short digest for the model: [{"sprint", "mark", "status", "scores", "anomalies"}]. ``history_rows`` are stored assessment results, oldest first."""
    out = []
    for r in history_rows:
        j = r.get("justification") or {}
        out.append({"sprint": r["sprint_id"], "mark": r.get("mark"), "status": r.get("status"),
                    "scores": {k: round(v["score"] * 100) for k, v in (r.get("factors") or {}).items() if isinstance(v, dict) and v.get("score") is not None},
                    "anomalies": [a.get("message") for lst in (j.get("anomalies") or {}).values() for a in lst][:6]})
    return out
