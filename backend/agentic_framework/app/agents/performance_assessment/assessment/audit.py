"""The agent checks its own factor results before they become a mark.

Step 1, deterministic findings (``findings``): range errors, failed factors, contradictions between factors, jumps against the student's history, plus the existing discrepancy rules.
Step 2, reasoning (``llm_decide``, optional): a language model reads the findings and the factor cards (what each factor measures, how it fails, which remedies are allowed) and decides, per finding,
accept / retry / escalate, with a reason. It can only choose among the actions the card allows and **never sets or edits a score**: a score comes from a factor package or it does not exist.
Step 3 (``decide``): what actually happens. ``retry`` re-runs the factor once (transient failures); ``escalate`` opens a review for the lecturer with the findings and the evidence summary; ``accept``
records the reason. Without a language model, critical findings escalate and warnings are accepted with the finding's text.
"""
import json
import re

from app.agents.performance_assessment.com_agent.policies import discrepancy_rules

SEVERITIES = ("info", "warn", "critical")
JUMP_POINTS = 35.0


def finding(code, factor, severity, message, remedy=None, **extra):
    return {"id": f"{factor}:{code}", "code": code, "factor": factor, "severity": severity, "message": message, "remedy": remedy, **extra}


def findings(results: dict, evidence: dict | None = None, previous_mark: float | None = None, mark: float | None = None) -> list[dict]:
    out = []
    score = lambda n: results[n]["score"] if n in results and results[n]["status"] == "completed" else None  # noqa: E731
    for n, r in results.items():
        if r["status"] == "completed" and not (0.0 <= r["score"] <= 1.0):
            out.append(finding("range", n, "critical", f"{n} gave a score outside 0-1 ({r['score']})", "retry"))
        if r["status"] == "fallback":
            out.append(finding("failed", n, "critical", f"{n} could not be computed: {'; '.join(r['warnings'])[:200]}", "retry"))
        if r["status"] == "not_available":
            out.append(finding("not_available", n, "info", f"{n} is not available: {'; '.join(r['warnings'])[:200]}", None))
        if r["status"] == "completed" and r.get("provisional"):
            out.append(finding("provisional", n, "info", f"{n} is provisional (sprint not over)", None))
        if n == "task_complexity" and r["status"] == "completed" and any("not shown to beat" in w for w in r["warnings"]):
            out.append(finding("baseline_only", n, "info", "Task Complexity is effectively the sprint's story-point total", None))
    e, c, rf, co = score("effort"), score("consistency"), score("requirement_fulfillment"), score("collaboration")
    ev_tasks = (evidence or {}).get("tasks", [])
    done_by_me = [t for t in ev_tasks if t.get("status") == "Done" and t.get("completed_by") in ((evidence or {}).get("student_id"), None, "")]
    commits = (evidence or {}).get("commits") or []
    if e == 0.0 and commits:
        out.append(finding("commits_not_counted", "effort", "warn", f"{len(commits)} commits in the sprint changed no counted source line (configuration, documents or generated files only), so Effort cannot see this work: "
                           "its score of 0 does not mean the student did nothing", None))
    elif e == 0.0 and (done_by_me or (evidence or {}).get("pull_requests")):
        out.append(finding("silent_but_visible", "effort", "warn", "no commits in the sprint, but the board or GitHub shows work (tasks done or pull requests): the commits may be under an unmapped e-mail", "identity_mapping"))
    if rf is not None and e is not None and rf >= 0.7 and e <= 0.1:
        out.append(finding("rf_without_effort", "requirement_fulfillment", "critical", f"acceptance criteria look met (RF {rf:.2f}) while almost no code is attributed to the student (Effort {e:.2f})", "escalate_to_human"))
    judged = [t for t in (results.get("requirement_fulfillment") or {}).get("tasks") or [] if t.get("status") == "judged"]
    if rf is not None and e is not None and e >= 0.6 and rf <= 0.1 and judged:
        out.append(finding("effort_without_rf", "requirement_fulfillment", "warn", f"a lot of code (Effort {e:.2f}) but almost no task criteria met (RF {rf:.2f}): commits may not be linked to tasks", "refetch_evidence"))
    ko = score("code_ownership")
    if e is not None and ko is not None:
        a = discrepancy_rules.check_ghostwriter_suspicion(e, ko)
        if a:
            out.append(finding("ghostwriter", "code_ownership", "critical", a.description, "escalate_to_human"))
    if e is not None and c is not None:
        a = discrepancy_rules.check_deadline_panic(c, e)
        if a:
            out.append(finding("deadline_panic", "consistency", "warn", a.description, None))
    if e is not None and co is not None:
        a = discrepancy_rules.check_free_rider(e, co)
        if a:
            out.append(finding("free_rider", "collaboration", "warn", a.description, None))
    if previous_mark is not None and mark is not None and abs(mark - previous_mark) > JUMP_POINTS:
        out.append(finding("history_jump", "fusion", "warn", f"the mark moved {mark - previous_mark:+.0f} points since the last result ({previous_mark:.0f} to {mark:.0f})", "escalate_to_human"))
    return out


# ---- reasoning ----------------------------------------------------------------------------------------------------------------------------

SYSTEM = """You are the auditor of an automated student-contribution assessment. You receive findings about one student's factor results and, for each factor involved, its card (what it measures, limits, typical problems, allowed remedies).
For each finding decide ONE action: "accept" (the result stands; say why it is not a problem), "retry" (the factor failed or gave an invalid value; run it again once) or "escalate" (a human must look; say what to check).
Rules: you cannot change, set or estimate a score. Use only the facts given. Prefer "escalate" over guessing when evidence of work is contradictory. A remedy not listed in the card's allowed_remedies must not be proposed.
Reply with one JSON object: {"decisions": [{"finding": "<id>", "action": "accept" | "retry" | "escalate", "reason": "<one or two sentences>"}], "summary": "<two sentences on whether these results can be trusted>"}."""


def _compact_card(card):
    return {k: card.get(k) for k in ("title", "measures", "limits", "typical_problems", "allowed_remedies")}


def llm_decide(llm, found: list[dict], cards: dict, summary: dict) -> dict | None:
    """Ask the language model for a decision per finding. Returns None when there is nothing to decide, no model, or the reply is unusable."""
    actionable = [f for f in found if f["severity"] != "info"]
    if not actionable or llm is None:
        return None
    involved = sorted({f["factor"] for f in actionable if f["factor"] in cards})
    user = json.dumps({"findings": actionable, "cards": {n: _compact_card(cards[n]) for n in involved}, "results": summary}, ensure_ascii=False)[:14000]
    reply = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], max_tokens=900, temperature=0.0, tag="audit", json_mode=True)
    if not getattr(reply, "ok", True):
        return None
    m = re.search(r"\{.*\}", reply.text or "", re.S)
    try:
        data = json.loads(m.group(0)) if m else None
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("decisions"), list):
        return None
    ids = {f["id"] for f in actionable}
    decisions = {}
    for d in data["decisions"]:
        if isinstance(d, dict) and d.get("finding") in ids and d.get("action") in ("accept", "retry", "escalate"):
            decisions[d["finding"]] = {"action": d["action"], "reason": str(d.get("reason", ""))[:400]}
    return {"decisions": decisions, "summary": str(data.get("summary", ""))[:500], "model": getattr(llm, "model", "")}


def decide(found: list[dict], reasoning: dict | None) -> list[dict]:
    """The action for each non-info finding: the model's choice when it gave one (a critical finding is never silently accepted without a reason), otherwise the default."""
    out = []
    for f in found:
        if f["severity"] == "info":
            continue
        d = (reasoning or {}).get("decisions", {}).get(f["id"])
        if d and d["action"] == "accept" and f["severity"] == "critical" and len(d["reason"]) < 20:
            d = {"action": "escalate", "reason": "a critical finding was accepted without a reason; sent to the lecturer"}
        if d is None:
            if f["remedy"] == "retry":
                act, why = "retry", "the factor failed or gave an invalid value; run it once more"
            elif f["severity"] == "critical" or f["remedy"] in ("identity_mapping", "refetch_evidence", "escalate_to_human"):
                act, why = "escalate", "needs a human look (default rule, no reasoning model)"
            else:
                act, why = "accept", "warning noted (default rule, no reasoning model)"
            d = {"action": act, "reason": why}
        if d["action"] == "retry" and f["remedy"] != "retry":
            d = {"action": "escalate", "reason": f"{d['reason']} (running the factor again cannot fix this, so a person should look)"}
        out.append({**f, **d})
    return out
