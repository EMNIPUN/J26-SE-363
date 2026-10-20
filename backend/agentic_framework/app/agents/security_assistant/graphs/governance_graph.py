"""The Governance Agent as a stateful LangGraph gate, invoked before every LLM call (and once for the repository scan).

    START -> check_input -+-> raise_scrutiny -+-> raise_scrutiny ...        (a threshold was reached)
                          |                   +-> escalate -> check_input    (the high level was reached)
                          |                   +-> check_input | END
                          +-> allow -+-> raise_scrutiny -> ... -> END
                          +-> block -+
                          +-> END                                           (event "repo": nothing to decide)

The score, the scrutiny level, the history and the counters are keys of the GRAPH STATE (GateState). The `Governance` object keeps that
state between invocations: each invocation starts from the state the last one ended with, so the gate remembers the run.

check_input      notes what the input contains (injection indicators raise the score), and if that crosses a threshold hands over to
                 raise_scrutiny first, so the level applies to this very call. Then it runs the first check and, at "elevated" or "high", the
                 second, stricter check, and derives the options that are valid for THIS input: with a failed check there is no allow option.
                 The policy chooses among them through `agent_loop.select` (a rogue choice is rejected and replaced by the rules).
raise_scrutiny   scrutiny only goes up; reaching a threshold is a decision with one valid option, recorded like every other.
escalate         at "high": the run is flagged for human review (a decision with one valid option, an audit line, a report banner).
allow / block    carry out the validated choice, count it, add its points to the score (a block +2, a warn-only pass +1), and go back through
                 raise_scrutiny if that crossed a threshold.

Nothing here edits a verdict or drops a finding: the gate only decides whether an outgoing prompt is sent. The checks themselves
(`_violations`, `_strict_violations`), the policy, the trail and the audit log are the Governance object's, which the nodes call.
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.security_assistant.agent_loop import Action, DisallowedAction, select

NODES = ("check_input", "raise_scrutiny", "escalate", "allow", "block")
PERSISTENT = ("level", "score", "history", "checked", "blocked", "allowed", "repo_indicator_count", "prompt_with_indicators", "second_checks",
              "second_check_blocks", "escalated", "escalation_reason", "step")


class GateState(TypedDict, total=False):
    # persistent: the gate's memory of the run
    level: str
    score: int
    history: list
    checked: int
    blocked: int
    allowed: int
    repo_indicator_count: int
    prompt_with_indicators: int
    second_checks: int
    second_check_blocks: int
    escalated: bool
    escalation_reason: str | None
    step: int
    elevated_at: int
    high_at: int
    # the event: "repo" (indicators found in the repository) or "call" (an outgoing prompt)
    event: str
    distinct: int
    kind: str
    finding_key: str
    category: str
    rule_id: str
    system: str
    user: str
    offered_ids: Any
    model: str | None
    prompt_version: str | None
    seed: int | None
    # transient: this pass through the gate
    noted: bool
    phase: str
    raise_needed: bool
    escalate_needed: bool
    indicators: dict
    digest: str
    first: list
    second: list
    options: list
    chosen: Action
    entry: dict
    block: dict | None


def summary_of(s: dict) -> dict:
    return {"level": s["level"], "score": s["score"], "elevated_at": s["elevated_at"], "high_at": s["high_at"], "calls_checked": s["checked"],
            "calls_blocked": s["blocked"], "repo_indicators": s["repo_indicator_count"], "prompts_with_indicators": s["prompt_with_indicators"],
            "second_checks": s["second_checks"]}


def build_gate_graph(gov: Any):
    """Compile the gate for one `Governance` object (see governance.py). The object is the core; the nodes only call it."""
    from app.agents.security_assistant import governance as gv

    def points(s: dict, kind: str, count: int = 1) -> dict:
        total = s["score"] + gv.POINTS[kind] * count
        return {"score": total, "history": [*s["history"], {"event": kind, "points": gv.POINTS[kind] * count, "score": total, "level": s["level"]}]}

    def next_level(s: dict):
        for target, at in (("elevated", s["elevated_at"]), ("high", s["high_at"])):
            if gv.LEVELS.index(s["level"]) < gv.LEVELS.index(target) and s["score"] >= at:
                return target, at
        return None

    def decide(s: dict, options: list[Action], subject: str):
        summary = summary_of(s)
        action, reason, rejected = select(gov.policy, gov._rules, summary, options)
        step = s["step"] + 1
        entry = gov.trail.record(step, gov.policy.name if rejected is None else f"{gov.policy.name} -> rules", summary, options, action, reason,
                                 rejected, subject=subject)
        return action, entry, step

    def violations_of(s: dict) -> list[tuple[str, str]]:
        first = s["first"]
        return first + [v for v in s["second"] if v[0] not in {c for c, _ in first}]

    def check_input(state: GateState) -> dict:
        s = dict(state)
        if not s.get("noted"):
            if s["event"] == "repo":
                n = s["distinct"]
                upd = {"noted": True, "phase": "pre", "repo_indicator_count": s["repo_indicator_count"] + n, **points(s, "repo_indicator", n)}
                upd["raise_needed"] = next_level({**s, **upd}) is not None  # repeated indicators in the repository raise the scrutiny of every call
                return upd
            indicators = gv.injection_indicators(gv._HARNESS.sub("", s["user"]))
            gov.prompt_indicators.update(indicators.keys())
            upd = {"noted": True, "phase": "pre", "indicators": indicators, "digest": gv.prompt_hash(s["system"], s["user"]),
                   "checked": s["checked"] + 1}
            if indicators:
                upd["prompt_with_indicators"] = s["prompt_with_indicators"] + 1
                upd.update(points({**s, **upd}, "prompt_indicator"))
            if next_level({**s, **upd}):  # raise first: the new level applies to this very call
                upd["raise_needed"] = True
                return upd
            s.update(upd)
        else:
            upd = {}
        # the checks and the decision for this call
        first = gov._violations(s["system"], s["user"])
        second_required = s["level"] != "normal"
        second: list = []
        second_checks = s["second_checks"]
        if second_required:
            second_checks += 1
            second = gov._strict_violations(s["system"], s["user"])
        s.update(first=first, second=second, second_checks=second_checks)
        violations = violations_of(s)
        if not violations:
            options = [Action("allow_after_second_check" if second_required else "allow_call",
                              why="no check failed" + (" (first check and second check)" if second_required else ""))]
        else:
            why = "; ".join(m for _c, m in violations)
            options = [Action("block_call", why=why)]
            if gov.warn_only:
                options.insert(0, Action("allow_call_warn_only", why=f"--governance-warn-only: recorded, not blocked. {why}"))
        action, entry, step = decide(s, options, s["finding_key"])
        decision = {"allow_call": "send", "allow_after_second_check": "send", "allow_call_warn_only": "send-warn-only", "block_call": "blocked"}[action.name]
        gov.audit.record("pre_send_check", call=s["kind"], finding_key=s["finding_key"], category=s["category"], rule_id=s["rule_id"],
                         prompt_sha256=s["digest"], prompt_chars=len(s["system"]) + len(s["user"]), evidence_ids_offered=sorted(s["offered_ids"]),
                         model=s["model"], prompt_version=s["prompt_version"], seed=s["seed"],
                         secret_check="fail" if any("secret" in c for c, _ in violations) else "pass",
                         personal_data_check="fail" if any("personal" in c for c, _ in violations) else "pass",
                         scrutiny=s["level"], second_check=("fail" if second else "pass") if second_required else "not required",
                         violations=[c for c, _ in violations], injection_indicators=s["indicators"], decision=decision)
        return {**upd, "first": first, "second": second, "second_checks": second_checks, "options": options, "chosen": action, "entry": entry,
                "step": step, "raise_needed": False}

    def after_check(s: GateState) -> str:
        if s.get("raise_needed"):
            return "raise_scrutiny"
        if s["event"] == "repo":
            return "end"
        chosen = s["chosen"]
        if chosen.key not in {o.key for o in s["options"]}:  # cannot happen after select(); the edge does not trust that
            raise DisallowedAction(f"{chosen.key} is not one of the valid options")
        return "block" if chosen.name == "block_call" else "allow"

    def raise_scrutiny(state: GateState) -> dict:
        s = dict(state)
        target, at = next_level(s)
        why = (f"score {s['score']} reached {at}: {s['repo_indicator_count']} indicator(s) in the repository, "
               f"{s['prompt_with_indicators']} prompt(s) with indicators, {s['blocked']} blocked call(s)")
        _action, entry, step = decide(s, [Action("raise_scrutiny", target, why)], s.get("finding_key") or "run")
        previous = s["level"]
        gov.audit.record("scrutiny_change", from_level=previous, to_level=target, score=s["score"], threshold=at)
        gov.trail.outcome(entry, f"{previous} -> {target}" + ("; every later call gets a second, stricter check" if target == "elevated"
                                                               else "; escalating to human review"))
        upd = {"level": target, "step": step, "history": [*s["history"], {"event": "scrutiny_raised", "from": previous, "to": target, "score": s["score"]}],
               "escalate_needed": target == "high" and not s["escalated"]}
        upd["raise_needed"] = next_level({**s, **upd}) is not None
        return upd

    def continue_after(s: GateState) -> str:
        return "check_input" if s["phase"] == "pre" and s["event"] == "call" else "end"

    def after_raise(s: GateState) -> str:
        if s.get("raise_needed"):
            return "raise_scrutiny"
        if s.get("escalate_needed"):
            return "escalate"
        return continue_after(s)

    def escalate(state: GateState) -> dict:
        s = dict(state)
        reason = f"score {s['score']}: repeated injection indicators or blocked calls in this run"
        _action, entry, step = decide(s, [Action("escalate_to_reviewer", None, reason)], s.get("finding_key") or "run")
        gov.audit.record("escalation", level="high", score=s["score"], reason=reason)
        gov.trail.outcome(entry, "the run is flagged: a person should review audit.jsonl before relying on it")
        return {"escalated": True, "escalation_reason": reason, "escalate_needed": False, "step": step}

    def allow(state: GateState) -> dict:
        s = dict(state)
        upd: dict = {"phase": "post"}
        if s["chosen"].name == "allow_call_warn_only":
            gov.trail.outcome(s["entry"], "sent although a check failed (warn-only)")
            upd.update(allowed=s["allowed"] + 1, **points(s, "violation_allowed"))
        else:
            gov.trail.outcome(s["entry"], "sent")
        upd["raise_needed"] = next_level({**s, **upd}) is not None
        return upd

    def block(state: GateState) -> dict:
        s = dict(state)
        by_second = bool(s["second"]) and not s["first"]
        gov.trail.outcome(s["entry"], "blocked; nothing was sent")
        upd = {"phase": "post", "blocked": s["blocked"] + 1, "second_check_blocks": s["second_check_blocks"] + int(by_second),
               **points(s, "second_check_blocked" if by_second else "blocked_call")}
        code, message = violations_of(s)[0]
        upd["block"] = {"code": code, "message": f"governance blocked the call before it was sent: {message}"}
        upd["raise_needed"] = next_level({**s, **upd}) is not None
        return upd

    def after_outcome(s: GateState) -> str:
        return "raise_scrutiny" if s.get("raise_needed") else "end"

    builder = StateGraph(GateState)
    for name, fn in (("check_input", check_input), ("raise_scrutiny", raise_scrutiny), ("escalate", escalate), ("allow", allow), ("block", block)):
        builder.add_node(name, fn)
    builder.add_edge(START, "check_input")
    builder.add_conditional_edges("check_input", after_check, {"raise_scrutiny": "raise_scrutiny", "allow": "allow", "block": "block", "end": END})
    builder.add_conditional_edges("raise_scrutiny", after_raise,
                                  {"raise_scrutiny": "raise_scrutiny", "escalate": "escalate", "check_input": "check_input", "end": END})
    builder.add_conditional_edges("escalate", continue_after, {"check_input": "check_input", "end": END})
    builder.add_conditional_edges("allow", after_outcome, {"raise_scrutiny": "raise_scrutiny", "end": END})
    builder.add_conditional_edges("block", after_outcome, {"raise_scrutiny": "raise_scrutiny", "end": END})
    return builder.compile()


def diagram_graph():
    """A compiled graph with no Governance behind it, for the diagram export only (the nodes are never run)."""
    return build_gate_graph(object())
