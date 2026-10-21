"""The Analysis Orchestrator Agent as a LangGraph graph.

    START -> plan -+-> execute_action -> update_state -> plan ...
                   +-> stop -> END

plan            asks the orchestrator for the options that are valid in its current state (`Orchestrator.options`, the valid-options
                function), then lets the policy choose through `agent_loop.select`: a choice outside the options is rejected and replaced by
                the rule policy, and the decision is recorded in the trail. The policy is swappable; the rule policy is the default.
conditional     dispatches on the validated choice: `stop` goes to the stop node, every other action to execute_action. The edge checks once
edge            more that the choice is one of the options and refuses to continue if it is not.
execute_action  runs the chosen action (`Orchestrator.execute`); an exception is recorded as the outcome, never silent.
update_state    counts the step, writes the outcome to the trail and the audit log, and refreshes the state summary.
stop            ends the loop and records why: goal met, nothing left to try, or budget spent.

The orchestrator object holds the tool state (runs, retries, coverage, gaps); the graph state holds the loop's own data (options, chosen
action, outcome, step). The step budget is enforced by `Orchestrator.options`, which offers only `stop` at the last allowed step.
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.security_assistant.agent_loop import Action, DisallowedAction, select

NODES = ("plan", "execute_action", "update_state", "stop")


class OrchestratorState(TypedDict, total=False):
    options: list[Action]
    summary: dict
    chosen: Action
    reason: str
    rejected: dict | None
    entry: dict
    outcome: str
    step: int
    stop_reason: str
    goal_met: bool
    done: bool


def recursion_limit(max_steps: int) -> int:
    """Three node visits per step plus the stop, with room to spare."""
    return 3 * max_steps + 20


def build_orchestrator_graph(orch: Any):
    """Compile the graph for one `Orchestrator` (see orchestrator.py). The orchestrator is the core; the nodes only call it."""

    def plan(state: OrchestratorState) -> dict:
        options = orch.options()
        summary = orch.state_summary()
        action, reason, rejected = select(orch.policy, orch.rules, summary, options)
        entry = orch.trail.record(orch.step + 1, orch.policy.name if rejected is None else f"{orch.policy.name} -> rules", summary, options,
                                  action, reason, rejected, subject=action.target)
        return {"options": options, "summary": summary, "chosen": action, "reason": reason, "rejected": rejected, "entry": entry}

    def route(state: OrchestratorState) -> str:
        chosen, options = state["chosen"], state["options"]
        if chosen.key not in {o.key for o in options}:  # cannot happen after select(); the edge does not trust that
            raise DisallowedAction(f"{chosen.key} is not one of the valid options")
        return "stop" if chosen.name == "stop" else "execute_action"

    async def execute_action(state: OrchestratorState) -> dict:
        action = state["chosen"]
        try:
            outcome = await orch.execute(action)
        except Exception as exc:  # an action that raises is recorded, never silent, and counts as a step
            outcome = f"action failed: {type(exc).__name__}: {str(exc)[:120]}"
            if action.name == "run_tools":
                orch.passed = True  # do not run the first pass again and again; the budget would end it, but say so once
        return {"outcome": outcome}

    def update_state(state: OrchestratorState) -> dict:
        orch.step += 1
        orch.trail.outcome(state["entry"], state["outcome"])
        return {"step": orch.step, "summary": orch.state_summary()}

    def stop(state: OrchestratorState) -> dict:
        orch.step += 1
        orch.trail.outcome(state["entry"], f"stopped after {orch.step} step(s); coverage {orch._levels()}")
        return {"step": orch.step, "stop_reason": state["reason"], "goal_met": orch.goal_met(), "done": True}

    builder = StateGraph(OrchestratorState)
    builder.add_node("plan", plan)
    builder.add_node("execute_action", execute_action)
    builder.add_node("update_state", update_state)
    builder.add_node("stop", stop)
    builder.add_edge(START, "plan")
    builder.add_conditional_edges("plan", route, {"execute_action": "execute_action", "stop": "stop"})
    builder.add_edge("execute_action", "update_state")
    builder.add_edge("update_state", "plan")
    builder.add_edge("stop", END)
    return builder.compile()


def diagram_graph():
    """A compiled graph with no orchestrator behind it, for the diagram export only (the nodes are never run)."""
    return build_orchestrator_graph(object())
