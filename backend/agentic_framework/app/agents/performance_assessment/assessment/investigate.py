"""The auditor as an investigator: before it decides, it may look.

``audit.findings`` lists what looks wrong. ``investigate`` lets a language model gather facts about one student with a few read-only tools, then decide per finding (accept, retry, escalate) with a reason.

Tools (all read-only except the last):
    get_factor_card(factor)            what the factor measures, its limits, typical problems and allowed remedies
    inspect_evidence(what, limit)      counts and short lines from the student's evidence: "commits", "files", "tasks", "pull_requests"
    compare_with_history()             the student's earlier marks and factor scores in this sprint (snapshots) and the previous result
    mark_not_available(factor, reason) leave one factor out of the mark when the evidence shows it cannot be trusted for this student. It never sets or changes a score.

The model asks for one tool at a time as a JSON object ``{"tool": ..., "args": {...}}`` and ends with ``{"decisions": [...], "summary": "..."}`` (same form as audit.llm_decide). At most ``MAX_STEPS`` tool calls;
a step that is not valid costs a step. Tool results are short and carry no e-mail addresses, student answers or file contents, only counts, paths, and commit subjects cut to 80 characters.
The result is a plain dict; nothing here writes to the store: the pipeline logs every call, applies the overrides (the factor becomes "not_available" with the reason) and composes the mark again.
"""
import json
import re

MAX_STEPS = 5
FACTORS = ("effort", "consistency", "requirement_fulfillment", "collaboration", "task_complexity", "code_ownership")

SYSTEM = """You are the auditor of an automated student-contribution assessment. You receive findings about one student's factor results. Decide for each finding: "accept" (the result stands), "retry" (the factor failed; run it again once) or "escalate" (a person must look).
Before deciding you may call tools to check the facts. Reply with exactly one JSON object per turn.
To call a tool: {"tool": "<name>", "args": {...}}. Tools: get_factor_card(factor), inspect_evidence(what: commits|files|tasks|pull_requests, limit), compare_with_history(), mark_not_available(factor, reason).
To finish: {"decisions": [{"finding": "<id>", "action": "accept|retry|escalate", "reason": "<one or two sentences that cite what you found>"}], "summary": "<two sentences on whether these results can be trusted>"}.
Rules: you cannot set, change or estimate a score. Use mark_not_available only when the evidence shows that a factor cannot measure this student's work (for example the work is outside what the factor counts); give the reason. Do not propose a remedy that is not in the factor card's allowed_remedies.
Prefer to finish after one or two tool calls. Use only facts from the findings and the tool results."""


def _short(text, n=80):
    return re.sub(r"\s+", " ", str(text or ""))[:n]


def _tool_inspect(evidence, args):
    what, limit = args.get("what", "commits"), max(1, min(int(args.get("limit", 8) or 8), 15))
    if what == "commits":
        cs = [c for c in evidence.get("commits", []) if not c.get("is_merge")]
        return {"count": len(cs), "recent": [{"at": c["authored_at"][:16], "subject": _short(c.get("subject")), "files": len(c["files"]), "source_lines": sum(f["line_stats"]["added"].get("code", 0) for f in c["files"] if f.get("kind") in ("code", "test"))} for c in cs[-limit:]]}
    if what == "files":
        kinds, paths = {}, {}
        for c in evidence.get("commits", []):
            for f in c["files"]:
                kinds[f.get("kind", "?")] = kinds.get(f.get("kind", "?"), 0) + 1
                paths[f["path"]] = paths.get(f["path"], 0) + f.get("added", 0)
        top = sorted(paths.items(), key=lambda kv: -kv[1])[:limit]
        return {"file_changes_by_kind": kinds, "most_added_lines": [{"path": p, "added": n} for p, n in top]}
    if what == "tasks":
        return {"count": len(evidence.get("tasks", [])), "tasks": [{"id": t["id"], "status": t.get("status"), "points": t.get("story_points"), "completed_by": t.get("completed_by"), "linked_commits": len(t.get("commit_ids", []))} for t in evidence.get("tasks", [])[:limit]]}
    if what == "pull_requests":
        return {"opened": len(evidence.get("pull_requests", [])), "reviews_written": len(evidence.get("reviews", [])), "comments_written": len(evidence.get("comments", [])), "merged_for_others": evidence.get("merged_for_others", 0),
                "team_reviews_and_comments": (evidence.get("team") or {}).get("reviews_and_comments")}
    return {"error": "what must be one of commits, files, tasks, pull_requests"}


def run(llm, found, cards, results, evidence, history=None):
    """Investigate one student's findings. Returns {"decisions": {finding id: {"action", "reason"}}, "summary", "model", "trace": [...], "overrides": {factor: reason}, "thinking": the model's reasoning text, empty when it gave none} or None when there is nothing to decide, no model, or no usable answer."""
    actionable = [f for f in found if f["severity"] != "info"]
    if not actionable or llm is None:
        return None
    involved = sorted({f["factor"] for f in actionable if f["factor"] in cards})
    brief = {"findings": actionable, "results": {k: {"score": r["score"], "status": r["status"], "warnings": r["warnings"][:3]} for k, r in results.items()},
             "cards": {n: {k: cards[n].get(k) for k in ("title", "measures", "limits", "typical_problems", "allowed_remedies")} for n in involved}}
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(brief, ensure_ascii=False)[:14000]}]
    ids = {f["id"] for f in actionable}
    trace, overrides, thoughts = [], {}, []
    for step in range(MAX_STEPS + 1):
        reply = llm.chat(messages, max_tokens=900, temperature=0.0, tag="audit" if step == 0 else f"audit:step{step}", json_mode=True)
        if not getattr(reply, "ok", True):
            return None
        if str(getattr(reply, "reasoning", "") or "").strip():
            thoughts.append(str(reply.reasoning).strip())  # the model's own reasoning, for the live trace
        m = re.search(r"\{.*\}", reply.text or "", re.S)
        try:
            data = json.loads(m.group(0)) if m else None
        except ValueError:
            data = None
        if not isinstance(data, dict):
            messages += [{"role": "assistant", "content": (reply.text or "")[:400]}, {"role": "user", "content": "Reply with one JSON object: a tool call or the final decisions."}]
            trace.append({"tool": "(invalid reply)", "args": {}, "result": "not JSON"})
            continue
        if isinstance(data.get("decisions"), list):
            decisions = {}
            for d in data["decisions"]:
                if isinstance(d, dict) and d.get("finding") in ids and d.get("action") in ("accept", "retry", "escalate"):
                    decisions[d["finding"]] = {"action": d["action"], "reason": str(d.get("reason", ""))[:400]}
            return {"decisions": decisions, "summary": str(data.get("summary", ""))[:500], "model": getattr(llm, "model", ""), "trace": trace, "overrides": overrides, "thinking": "\n\n".join(thoughts)[:4000]}
        tool, args = data.get("tool"), data.get("args") if isinstance(data.get("args"), dict) else {}
        if step >= MAX_STEPS:
            messages += [{"role": "assistant", "content": json.dumps(data)[:300]}, {"role": "user", "content": "No more tool calls. Give the final decisions now."}]
            continue
        try:
            if tool == "get_factor_card":
                card = cards.get(args.get("factor"))
                out = {k: card.get(k) for k in ("title", "measures", "limits", "typical_problems", "allowed_remedies")} if card else {"error": f"unknown factor; one of {sorted(cards)}"}
            elif tool == "inspect_evidence":
                out = _tool_inspect(evidence or {}, args)
            elif tool == "compare_with_history":
                out = history or {"note": "no earlier result for this student in this sprint"}
            elif tool == "mark_not_available":
                f, why = args.get("factor"), _short(args.get("reason"), 240)
                if f not in FACTORS or f not in results or results[f]["status"] != "completed":
                    out = {"error": "only a factor that has a score can be marked not available"}
                elif len(why) < 15:
                    out = {"error": "give a reason of at least a sentence"}
                else:
                    overrides[f] = why
                    out = {"ok": f"{f} will be left out of the mark; its weight is shared by the other factors"}
            else:
                out = {"error": f"unknown tool {tool!r}"}
        except Exception as e:  # a bad argument is the model's mistake, not a failure of the run
            out = {"error": f"{type(e).__name__}: {str(e)[:100]}"}
        trace.append({"tool": tool, "args": args, "result": _short(json.dumps(out, default=str), 300)})
        messages += [{"role": "assistant", "content": json.dumps(data)[:300]}, {"role": "user", "content": "Tool result: " + json.dumps(out, default=str)[:3500]}]
    return None


def apply_overrides(results, overrides):
    """The factors the investigator left out, as results: status not_available, no score, the reason as a warning. Nothing else about the result changes."""
    out = {}
    for f, why in overrides.items():
        r = results[f]
        out[f] = {**r, "score": None, "status": "not_available", "interval": None, "warnings": [*r["warnings"], f"left out by the auditor: {why}"]}
    return out
