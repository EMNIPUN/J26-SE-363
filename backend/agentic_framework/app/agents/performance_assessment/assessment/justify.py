"""Why a student got this mark: a justification per factor and an overall summary, built only from the factor results and the factor cards (no language model, no invented facts).

    explain(student_id, results, fused, evidence, cards, audit, status) -> {"summary", "factors": {name: {...}}, "how_computed", "flags", "caveats"}

Every number in the text is read from a result; every caveat comes from the factor's card. A language model, if used at all, may only rephrase this structure (see ``polish``), and its text is
dropped if it contains a number that is not in the structure.
"""
import re

TITLES = {"effort": "Effort", "consistency": "Consistency", "requirement_fulfillment": "Requirement Fulfillment", "collaboration": "Collaboration", "task_complexity": "Task Complexity",
          "code_ownership": "Code Ownership", "behavioral_pattern": "Behavioral Pattern"}


def band(score):
    return None if score is None else ("low" if score < 0.34 else "medium" if score < 0.67 else "high")


def _f(features, key, default=None):
    v = features.get(key)
    return default if v is None else v


def _reasons(name, r, evidence):
    f, out = r.get("features") or {}, []
    if name == "effort":
        out.append(f"{_f(f, 'E_CC', 0)} counted commits, {_f(f, 'E_LOC_net', 0)} net lines of real code, {_f(f, 'E_FC', 0)} files changed, {_f(f, 'E_CT', 0)} tasks finished")
        rem = r.get("removed") or {}
        ignored = sum(rem.get(k, 0) for k in ("comment", "blank", "format_only"))
        if ignored:
            out.append(f"{ignored} comment, blank or formatting-only lines were not counted as work")
    elif name == "consistency":
        days = (evidence or {}).get("sprint", {}).get("days", 14)
        out.append(f"worked on about {round(_f(f, 'C_AWR', 0) * days)} of {days} days; first commit on day {_f(f, 'C_first_active_day', '–')} of the sprint")
        if f.get("C_no_activity"):
            out.append("no counted activity in the sprint")
    elif name == "requirement_fulfillment":
        for t in (r.get("tasks") or []):
            if t.get("status") == "judged":
                v = t.get("verdicts") or []
                out.append(f"task {t['task']}: {sum(1 for x in v if x == 'met')} of {len(v)} acceptance criteria met" + (f", {sum(1 for x in v if x == 'partly')} partly" if 'partly' in v else ""))
            elif t.get("status") in ("not_started", "not_ready"):
                out.append(f"task {t['task']}: not started, counted as 0" if t["status"] == "not_started" else f"task {t['task']}: not finished yet, not judged")
    elif name == "collaboration":
        out.append(f"{_f(f, 'Co_count_substantive_texts', 0)} substantive review or discussion comments, {_f(f, 'Co_count_reviewed_prs', 0)} pull requests reviewed, {_f(f, 'Co_count_trivial_texts', 0)} short or approval-only comments (not counted)")
    elif name == "task_complexity":
        out.append(f"{_f(f, 'TC_SP_total', 0)} story points assigned in the sprint over {_f(f, 'TC_SC', 0)} subtasks in the sampled task")
    elif name == "code_ownership":
        if r.get("status") == "completed":
            out.append(f"comprehension rating {_f(f, 'comprehension_rating_1_to_5', '–')} of 5 on the question about their own code")
    return out


def _factor_block(name, r, card, evidence):
    block = {"factor": name, "title": TITLES[name], "status": r["status"], "score": r.get("score"), "band": band(r.get("score")), "interval": r.get("interval"), "provisional": bool(r.get("provisional")),
             "reasons": _reasons(name, r, evidence), "warnings": r.get("warnings", []), "how_much_to_trust": (card or {}).get("validation", ""), "measures": (card or {}).get("measures", "")}
    if r["status"] == "not_available":
        block["reasons"] = [f"{TITLES[name]} could not be measured: " + ("; ".join(r.get("warnings", [])) or "not enough evidence") + ". It is left out of the mark and its weight is shared by the other factors."]
    elif r["status"] == "pending":
        block["reasons"] = [f"{TITLES[name]} is still pending: " + ("; ".join(r.get("warnings", [])) or "waiting for the student's answer") + ". The mark is provisional until it arrives."]
    elif r["status"] == "fallback":
        block["reasons"] = [f"{TITLES[name]} failed to run: " + "; ".join(r.get("warnings", []))[:200]]
    return block


def explain(student_id, results, fused, evidence, cards, audit, status):
    blocks = {n: _factor_block(n, r, cards.get(n), evidence) for n, r in results.items()}
    bp = fused.get("behavioral") or {}
    if bp:
        blocks["behavioral_pattern"] = {"factor": "behavioral_pattern", "title": TITLES["behavioral_pattern"], "status": bp.get("status", "completed"), "score": None, "persona": bp.get("persona"),
                                        "modifier": bp.get("modifier") if bp.get("applied") else 1.0, "applied": bp.get("applied", False), "reasons": [bp.get("rationale", "")] + ([f"adjustment {bp['modifier']:.2f} applied to the weighted score"] if bp.get("applied") and bp.get("modifier") != 1.0 else []),
                                        "warnings": bp.get("warnings", []), "how_much_to_trust": (cards.get("behavioral_pattern") or {}).get("validation", "")}
    mark = fused.get("mark")
    completed = [(n, r["score"]) for n, r in results.items() if r["status"] == "completed"]
    top = max(completed, key=lambda x: x[1]) if completed else None
    low = min(completed, key=lambda x: x[1]) if completed else None
    parts = []
    if mark is None:
        parts.append("No mark could be computed: no factor could be scored.")
    else:
        lo, hi = fused["mark_interval"]
        parts.append(f"{status.replace('_', ' ').capitalize()} mark {mark:.0f} out of 100 (plausible range {lo:.0f} to {hi:.0f}).")
        if top and low and top[0] != low[0]:
            parts.append(f"Strongest factor: {TITLES[top[0]]} ({top[1]:.2f}); weakest: {TITLES[low[0]]} ({low[1]:.2f}).")
    unavailable = [TITLES[n] for n, r in results.items() if r["status"] in ("not_available", "fallback")] + [TITLES[n] for n in fused.get("pending", []) if n not in results or results[n]["status"] == "pending"]
    if unavailable:
        parts.append("Not part of the mark: " + ", ".join(sorted(set(unavailable))) + ".")
    if bp.get("applied") and bp.get("modifier") != 1.0:
        parts.append(f"Pattern '{bp['persona']}' adjusted the weighted score by a factor of {bp['modifier']:.2f}.")
    weights = fused.get("effective_weights", {})
    how = "Mark = 100 x pattern adjustment x sum of (weight x factor score) over the factors that exist. Weights used: " + ", ".join(f"{TITLES[n]} {w:.2f}" for n, w in sorted(weights.items(), key=lambda kv: -kv[1])) + "." if weights else ""
    flags = [{"severity": a["severity"], "message": a["message"], "action": a.get("action"), "reason": a.get("reason")} for a in (audit or []) if a.get("severity") != "info"]
    caveats = ["All validation of these factors used ratings written by the assistant, not human graders. Treat the mark as a prediction to check, not a grade."]
    return {"student_id": student_id, "summary": " ".join(parts), "status": status, "factors": blocks, "how_computed": how, "flags": flags, "caveats": caveats}


def polish(llm, justification: dict) -> str | None:
    """Optional: a language model rewrites the summary in friendlier words. Its text is dropped if it contains a number that the structure does not contain."""
    if llm is None:
        return None
    allowed = set(re.findall(r"\d+(?:\.\d+)?", str(justification)))
    reply = llm.chat([{"role": "system", "content": "Rewrite the summary in two or three plain sentences for a student. Use only facts and numbers that appear in the input. Do not add advice that is not in the input."},
                      {"role": "user", "content": justification["summary"] + "\n" + "\n".join(r for b in justification["factors"].values() for r in b.get("reasons", []))[:3000]}],
                     max_tokens=300, temperature=0.0, tag="polish", json_mode=False)
    text = (getattr(reply, "text", "") or "").strip()
    if not getattr(reply, "ok", True) or not text or set(re.findall(r"\d+(?:\.\d+)?", text)) - allowed:
        return None
    return text
