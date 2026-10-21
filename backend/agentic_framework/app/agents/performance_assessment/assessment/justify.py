"""Why a student got this mark: a justification per factor and an overall summary, built only from the factor results and the factor cards (no language model, no invented facts).

    explain(student_id, results, fused, evidence, cards, audit, status) -> {"summary", "factors": {name: {...}}, "how_computed", "flags", "caveats"}

Every number in the text is read from a result; every caveat comes from the factor's card. A language model, if used at all, may only rephrase this structure (see ``polish``), and its text is
dropped if it contains a number that is not in the structure.
"""
import json
import re
from datetime import datetime, timezone

TITLES = {"effort": "Effort", "consistency": "Consistency", "requirement_fulfillment": "Requirement Fulfillment", "collaboration": "Collaboration", "task_complexity": "Task Complexity",
          "code_ownership": "Code Ownership", "behavioral_pattern": "Behavioral Pattern"}

PROMPT_VERSION = "narrate/2"
_BAD_CLAIMS = re.compile(r"\b(lazy|cheated|cheating|copied|unprofessional|should|must|need to|always|never)\b", re.I)
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")


def curate_evidence(results, evidence):
    """Return stable, non-model evidence groups for a justification/2 payload."""
    evidence = evidence or {}
    groups = []
    for name, result in results.items():
        if name not in TITLES or name == "behavioral_pattern":
            continue
        reasons = _reasons(name, result or {}, evidence)
        if not reasons:
            continue
        items = []
        for i, text in enumerate(reasons, 1):
            kind = "commit" if name in ("effort", "consistency") else (
                "criterion" if name == "requirement_fulfillment" and "criteria" in text else
                "task" if name in ("requirement_fulfillment", "task_complexity") else
                "review" if name == "collaboration" else "note")
            ref = {"type": "commits", "count": 0} if kind == "commit" else {}
            if name == "consistency":
                ref = {"type": "days", "count": (result.get("features") or {}).get("C_AWR", 0)}
            elif name == "effort":
                f = result.get("features") or {}
                ref = {"type": "commits", "count": f.get("E_CC", 0)} if i == 1 else {"type": "lines", "count": f.get("E_LOC_net", 0)}
                kind = "commit" if i == 1 else "file"
            elif name == "collaboration":
                ref = {"type": "pull_requests", "count": (result.get("features") or {}).get("Co_count_reviewed_prs", 0)}
            items.append({"id": f"ev_{name}_{i}", "kind": kind, "text": text, "ref": ref})
        groups.append({"factor": name, "items": items, "scored": result.get("status") == "completed"})
    return groups


def _fact_numbers(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {str(value), str(round(value)), f"{value:g}"}
    if isinstance(value, dict):
        out = set()
        for v in value.values():
            out |= _fact_numbers(v)
        return out
    if isinstance(value, (list, tuple)):
        out = set()
        for v in value:
            out |= _fact_numbers(v)
        return out
    if isinstance(value, str):
        return set(_NUMBER.findall(value))
    return set()


def _verify_text(text, facts, evidence=None, max_chars=None):
    """Detailed verifier used by narrate; it never mutates scores or facts."""
    if not isinstance(text, str) or not text.strip():
        return False, ["empty"]
    if max_chars and len(text) > max_chars:
        return False, ["length"]
    if "<" in text or ">" in text or "```" in text or re.search(r"(^|\n)\s*[-*]\s", text):
        return False, ["markup"]
    if _BAD_CLAIMS.search(text):
        return False, ["unsupported_claim"]
    forbidden = set(facts.get("forbidden_names", [])) if isinstance(facts, dict) else set()
    if any(name and name.lower() in text.lower() for name in forbidden):
        return False, ["name"]
    allowed = _fact_numbers(facts)
    for number in _NUMBER.findall(text):
        raw = number.rstrip("%")
        if raw not in allowed and not any(raw == str(round(float(x))) for x in allowed if re.fullmatch(r"\d+(?:\.\d+)?", x)):
            return False, [f"number:{number}"]
    evidence = evidence or []
    ids = {x["id"] for group in evidence for x in group.get("items", [])}
    paths = {str(x.get("text", "")) for group in evidence for x in group.get("items", [])}
    cited = re.findall(r"\bev_[A-Za-z0-9_]+\b", text)
    if any(x not in ids for x in cited):
        return False, ["evidence_id"]
    if any(q in text for q in ("highest", "lowest")):
        labels = [str(f.get("label", "")) for f in facts.get("contributions", [])] if isinstance(facts, dict) else []
        if not any(label.lower() in text.lower() for label in labels):
            return False, ["comparison"]
    return True, []


def verify_text(text, facts, evidence=None, max_chars=None):
    """Public boolean text contract; detailed failures remain available internally."""
    return _verify_text(text, facts, evidence, max_chars)[0]


def early_warning_notes(results, fused):
    """Stable snapshot notes; detection is code-owned, wording is deliberately plain."""
    low = [TITLES[n] for n, r in results.items() if r.get("score") is not None and r["score"] < 0.34]
    dropped = [TITLES[n] for n, r in results.items() if r.get("status") in ("not_available", "fallback")]
    return {
        "dropped": ("Not measured yet: " + ", ".join(sorted(dropped)) + ".") if dropped else "",
        "low": ("Low to date: " + ", ".join(sorted(low)) + ".") if low else "",
    }


def _fallback(slot, facts):
    f = facts or {}
    if slot.get("id") == "hero_summary":
        return f.get("summary", "").split(". ", 1)[0].rstrip(".") + "."
    if slot.get("id") == "brief":
        return ". ".join(f.get("summary", "").split(". ")[:2]).rstrip(".") + "."
    kind, x = slot.get("kind"), slot.get("facts", {})
    if kind == "strong":
        return f"{x.get('label')}: {x.get('points', 0):g} of {x.get('of', 0):g} points (score {x.get('score', 0):g})"
    if kind == "weak":
        return f"{x.get('label')}: score {x.get('score', 0):g}, {x.get('band', 'medium')}"
    if kind == "flag":
        n = x.get("count", 0)
        return f"{n} point{'s' if n != 1 else ''} need a person to look (see Points to check)"
    if kind == "out":
        return ", ".join(x.get("labels", [])) + ". Their weight goes to the other factors"
    if kind == "override":
        return f"Set to {x.get('mark')}; the agent predicted {x.get('predicted')}"
    if kind == "range":
        lo, hi = x.get("interval", [0, 0])
        return f"Likely {lo} to {hi}. {'Wide: some evidence is missing' if hi - lo >= 30 else 'Narrow: the evidence is steady'}"
    if kind == "pattern":
        return f"{x.get('persona')}. Counts only once the sprint is final"
    if kind == "trend":
        return "Earlier sprints: " + ", ".join(f"{m['sprint']} {round(m['mark'])}" for m in x.get("earlier", []))
    if kind == "provisional":
        return "Scores are to date; the mark can still move"
    return slot.get("fallback", "")


NARRATE_PROMPT = (
    "You explain one student's sprint assessment to their lecturer. You know what every factor measures, what it was given, what it returned and how the student did in earlier sprints; use that. "
    "Fill every slot using only FACTS, including the evidence lines in it. hero_summary: two sentences giving the mark and what drives it. brief: five or six plain sentences, a short paragraph in your own words: what the student did "
    "in the sprint (read it from the evidence lines), what stands out as strong or weak, how this sprint compares with the earlier ones when history is given, what the anomaly findings mean for how far to trust the mark, "
    "and what could not be measured and why. key.*, more.*: one plain sentence each. factor.*: three or four sentences: what the factor looks at, what the evidence showed for this student (with the numbers), why that puts the score "
    "where it is (its band and interval_percent, as likely between X and Y) and what its limits or the anomaly findings mean for how far to trust it. Respect each slot's max_chars. "
    "Use only numbers that appear in FACTS, never a name, never advice, and avoid the words should, must, always, never, lazy, highest and lowest. "
    "Reply with JSON {\"slots\": {\"<slot id>\": \"<text>\"}}."
)


def narrate(llm, facts, evidence=None, *, now=None):
    """Fill narrative slots once, verifying every model field and falling back safely."""
    slots = facts.get("slots", [])
    fallback = {s["id"]: _fallback(s, facts) for s in slots}
    generated = {"model": getattr(llm, "model", None) if llm else None, "prompt_version": PROMPT_VERSION,
                 "verified": True, "fallback_used": False, "fallback_fields": [],
                 "at": (now or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")}
    output = {}
    if llm is not None:
        # two requests, so each stays inside the model's per-minute budget: the overall text first, then one explanation per factor
        rest = {k: v for k, v in facts.items() if k != "slots"}
        for group in ([x for x in slots if not x["id"].startswith("factor.")], [x for x in slots if x["id"].startswith("factor.")]):
            if not group:
                continue
            try:
                reply = llm.chat([{"role": "system", "content": NARRATE_PROMPT},
                                  {"role": "user", "content": json.dumps({"facts": rest, "slots": group}, sort_keys=True, default=str)}],
                                 max_tokens=4000, temperature=0.0, tag="narrate", json_mode=True)
                parsed = json.loads(getattr(reply, "text", "") or "")
                output.update(parsed.get("slots", {}) if isinstance(parsed, dict) else {})
            except Exception:
                continue
    for slot in slots:
        sid = slot["id"]
        text = output.get(sid)
        ok, _ = _verify_text(text, facts, evidence, slot.get("max_chars"))
        if not ok:
            text = fallback[sid]
            generated["fallback_used"] = True
            generated["fallback_fields"].append(sid)
        output[sid] = text
    generated["verified"] = not generated["fallback_used"]
    return {"slots": output, "generated": generated}


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


def explain(student_id, results, fused, evidence, cards, audit, status, anomalies=None, memory=None):
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
    anomalies = anomalies or {}
    for f, found in anomalies.items():  # what the checks after each factor found: a warning is a point for the lecturer to look at; it changes no score
        for a in found:
            if a.get("severity") == "warn" and f in TITLES:
                flags.append({"severity": "warn", "message": a["message"], "action": "note", "reason": f"{TITLES[f]} check"})
    caveats = ["All validation of these factors used ratings written by the assistant, not human graders. Treat the mark as a prediction to check, not a grade."]
    summary = " ".join(parts)
    ev_groups = curate_evidence(results, evidence)
    scored = [(n, r) for n, r in results.items() if r.get("status") == "completed" and r.get("score") is not None]
    strongest = max(scored, key=lambda x: x[1]["score"]) if scored else None
    weakest = min(scored, key=lambda x: x[1]["score"]) if scored else None
    facts = {
        "student": "{{student}}", "mark": mark, "interval": fused.get("mark_interval"),
        "status": status, "provisional": status == "provisional", "summary": summary,
        "contributions": [{"factor": n, "label": TITLES[n], "score": round(r["score"] * 100), "points": round(weights.get(n, 0) * r["score"] * 100, 1),
                           "weight_pct": round(weights.get(n, 0) * 100)} for n, r in scored],
        "evidence": [item for group in ev_groups for item in group["items"]],
        "history": memory or [], "anomalies": {TITLES[f]: [a["message"] for a in found] for f, found in anomalies.items() if found and f in TITLES},
        "slots": []
    }
    if strongest:
        n, r = strongest
        facts["slots"].append({"id": "key.1", "kind": "strong", "max_chars": 120,
                               "facts": {"label": TITLES[n], "points": round(weights.get(n, 0) * r["score"] * 100), "of": round(mark or 0), "score": round(r["score"] * 100)}})
    if weakest:
        n, r = weakest
        facts["slots"].append({"id": "key.2", "kind": "weak", "max_chars": 120,
                               "facts": {"label": TITLES[n], "score": round(r["score"] * 100), "band": band(r["score"])}})
    if flags:
        facts["slots"].append({"id": "key.3", "kind": "flag", "max_chars": 120, "facts": {"count": len(flags)}})
    left_out = unavailable
    if left_out:
        facts["slots"].append({"id": "more.1", "kind": "out", "max_chars": 160, "facts": {"labels": left_out}})
    if mark is not None and fused.get("mark_interval"):
        facts["slots"].append({"id": "more.2", "kind": "range", "max_chars": 160, "facts": {"interval": fused["mark_interval"]}})
    if memory:
        facts["slots"].append({"id": "more.3", "kind": "trend", "max_chars": 200, "facts": {"earlier": [{"sprint": m["sprint"], "mark": m["mark"]} for m in memory]}})
    facts["slots"] += [{"id": "hero_summary", "max_chars": 360}, {"id": "brief", "max_chars": 1100}]
    for n, block in blocks.items():
        if n in TITLES and n != "behavioral_pattern":
            facts["slots"].append({"id": f"factor.{n}", "max_chars": 620, "facts": {"score": round((block.get("score") or 0) * 100), "band": block.get("band"), "weight_pct": round(weights.get(n, 0) * 100), "points": round(weights.get(n, 0) * (block.get("score") or 0) * 100, 1),
                                                                               "measures": block.get("measures"), "limits": (cards.get(n) or {}).get("limits", ""), "reasons": block.get("reasons"), "warnings": (block.get("warnings") or [])[:4],
                                                                               "interval_percent": [round(x * 100) for x in block["interval"]] if block.get("interval") else None, "status": block.get("status"), "anomalies": [a["message"] for a in anomalies.get(n, [])]},
                                   "fallback": (f"Scored {round((block.get('score') or 0) * 100)} out of 100, which is {block.get('band')}. It counts for {round(weights.get(n, 0) * 100)}% of the mark and added {round(weights.get(n, 0) * (block.get('score') or 0) * 100, 1)} points." if block.get("status") == "completed" else "It is left out of the mark, and its weight is shared among the other factors.")})
    return {"schema": "justification/2", "student_id": student_id, "summary": summary, "status": status, "factors": blocks,
            "how_computed": how, "flags": flags, "caveats": caveats, "evidence": ev_groups, "anomalies": anomalies, "memory": [m["sprint"] for m in (memory or [])],
            "_narration_facts": facts}


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
