"""The Question Agent as a LangGraph graph, run once per confirmed finding.

    START -> ask -> score -+-> close -> END
                           +-> follow_up -> score ...
                           +-> escalate -> END

ask         the first question (hint level 0): builds it from the student's own code and puts it to the Tutor.
score       records the Tutor's comprehension score against the threshold and decides what happens next. The options that are valid after
            this score are computed in code (`question_options`): closing only at or above the threshold, a follow-up only while the attempt
            budget lasts, escalation whenever the finding is not closed. The policy chooses among them through `agent_loop.select`, so a
            rogue choice (closing a finding that is below the threshold) is rejected and replaced by the rule policy.
conditional dispatches on the validated choice (close_finding / ask_followup / escalate_to_lecturer) and on the step budget: when the
edges       budget is spent the finding goes to escalate whatever the policy would have chosen.
follow_up   asks again from a different angle with the next hint level (it narrows what to look at and never states the fix).
close       the Tutor's score reached the threshold: the finding is closed.
escalate    the attempt limit or the step budget is reached: the finding goes to lecturer review, with the reason.

Every decision is a row of the decision trail and an audit line (agent_loop.DecisionTrail); the step counter is shared across the findings
of one run, so the step budget is global.
"""

from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.security_assistant.agent_loop import Action, DecisionTrail, DisallowedAction, LoopConfig, Policy, select

NODES = ("ask", "score", "follow_up", "close", "escalate")


class QuestionState(TypedDict, total=False):
    group: dict
    attempts: list[dict]
    status: str  # open | closed | escalated
    escalation: str | None
    steps: int  # decisions made so far in the whole run
    last_q: Any
    last_r: Any
    options: list[Action]
    chosen: Action
    entry: dict
    budget_spent: bool


@dataclass
class QuestionContext:
    """What the nodes need besides the state: the loop's rules and the collaborators. None of it is decided by a node."""

    trail: DecisionTrail
    policy: Policy
    rules: Policy
    cfg: LoopConfig
    tutor: Any
    threshold: float
    repo: Any
    pii: Any


def recursion_limit(cfg: LoopConfig) -> int:
    return 6 * (cfg.max_retries + 2) + 20


def build_question_graph(ctx: QuestionContext):
    from app.agents.security_assistant import questions as qs  # imported here: questions.py imports this module

    def budget_spent(state: QuestionState) -> bool:
        return state["steps"] >= ctx.cfg.max_steps

    async def ask(state: QuestionState) -> dict:
        if budget_spent(state):
            return {"budget_spent": True}
        options = qs.question_options(state["attempts"], ctx.threshold, ctx.cfg)
        summary = _summary(state)
        action, reason, rejected = select(ctx.policy, ctx.rules, summary, options)
        entry = ctx.trail.record(state["steps"] + 1, ctx.policy.name if rejected is None else f"{ctx.policy.name} -> rules", summary, options,
                                 action, reason, rejected, subject=state["group"]["group_id"])
        return await _ask(state, entry, hint_level=len(state["attempts"]), steps=state["steps"] + 1)

    def _summary(state: QuestionState) -> dict:
        return {"finding": state["group"]["group_id"], "attempts": len(state["attempts"]), "scores": [a["score"] for a in state["attempts"]],
                "threshold": ctx.threshold, "steps_used": state["steps"], "max_steps": ctx.cfg.max_steps}

    async def _ask(state: QuestionState, entry: dict, hint_level: int, steps: int) -> dict:
        attempts = list(state["attempts"])
        q = qs.build_question(state["group"], ctx.repo, ctx.pii, hint_level=hint_level, attempt=len(attempts) + 1)
        r = await ctx.tutor.ask(q)
        attempts.append({"attempt": q.attempt, "hint_level": hint_level, "question_id": q.id, "text": q.text, "score": r.score,
                         "result": qs.decide(r.score, ctx.threshold)})
        ctx.trail.outcome(entry, f"attempt {q.attempt}: score {r.score:.2f} -> {attempts[-1]['result']}")
        return {"attempts": attempts, "last_q": q, "last_r": r, "steps": steps}

    def score(state: QuestionState) -> dict:
        if budget_spent(state):
            return {"budget_spent": True}
        options = qs.question_options(state["attempts"], ctx.threshold, ctx.cfg)
        summary = _summary(state)
        action, reason, rejected = select(ctx.policy, ctx.rules, summary, options)
        entry = ctx.trail.record(state["steps"] + 1, ctx.policy.name if rejected is None else f"{ctx.policy.name} -> rules", summary, options,
                                 action, reason, rejected, subject=state["group"]["group_id"])
        return {"options": options, "chosen": action, "entry": entry, "steps": state["steps"] + 1, "escalation": reason}

    def route_after_ask(state: QuestionState) -> str:
        return "escalate" if state.get("budget_spent") else "score"

    def route_after_score(state: QuestionState) -> str:
        if state.get("budget_spent"):
            return "escalate"
        chosen = state["chosen"]
        if chosen.key not in {o.key for o in state["options"]}:  # cannot happen after select(); the edge does not trust that
            raise DisallowedAction(f"{chosen.key} is not one of the valid options")
        return {"close_finding": "close", "ask_followup": "follow_up", "escalate_to_lecturer": "escalate"}.get(chosen.name, "escalate")

    async def follow_up(state: QuestionState) -> dict:
        return await _ask(state, state["entry"], hint_level=len(state["attempts"]), steps=state["steps"])

    def close(state: QuestionState) -> dict:
        ctx.trail.outcome(state["entry"], f"closed after {len(state['attempts'])} attempt(s)")
        return {"status": "closed", "escalation": None}

    def escalate(state: QuestionState) -> dict:
        if state.get("budget_spent"):  # no decision was made: the budget forces it, and the trail says so
            reason = f"step budget spent ({ctx.cfg.max_steps} steps) before this finding was closed"
            entry = ctx.trail.record(state["steps"] + 1, "budget", {"attempts": len(state["attempts"])}, [], Action("escalate_to_lecturer"),
                                     reason, subject=state["group"]["group_id"])
            ctx.trail.outcome(entry, "escalated")
            return {"status": "escalated", "escalation": reason}
        ctx.trail.outcome(state["entry"], "escalated to lecturer review")
        return {"status": "escalated", "escalation": state["escalation"]}

    builder = StateGraph(QuestionState)
    for name, fn in (("ask", ask), ("score", score), ("follow_up", follow_up), ("close", close), ("escalate", escalate)):
        builder.add_node(name, fn)
    builder.add_edge(START, "ask")
    builder.add_conditional_edges("ask", route_after_ask, {"score": "score", "escalate": "escalate"})
    builder.add_conditional_edges("score", route_after_score, {"close": "close", "follow_up": "follow_up", "escalate": "escalate"})
    builder.add_edge("follow_up", "score")
    builder.add_edge("close", END)
    builder.add_edge("escalate", END)
    return builder.compile()


def diagram_graph():
    """A compiled graph with no collaborators behind it, for the diagram export only (the nodes are never run)."""
    return build_question_graph(QuestionContext(DecisionTrail("question agent"), None, None, LoopConfig(1, 0), None, 0.0, None, None))
