"""The Analysis Orchestrator as a LangGraph graph: plan -> execute_action -> update_state -> plan ... -> stop."""

import asyncio

import pytest

from app.agents.security_assistant import orchestrator as orch
from app.agents.security_assistant.agent_loop import Action, LoopConfig
from app.agents.security_assistant.graphs import orchestrator_graph as og
from app.agents.security_assistant.tests.test_orchestrator import Fake, Rogue, StopAtOnce, repo, run, suite  # noqa: F401


def build(repo, tools, tmp_path, max_steps=20, max_retries=1, policy=None):
    return orch.Orchestrator(repo, tools, config=LoopConfig(max_steps, max_retries), scan_dir=tmp_path / "scans", policy=policy)


def visited(o):
    """The nodes the graph ran, in order, with what each one returned."""
    async def go():
        return [(name, update) async for chunk in og.build_orchestrator_graph(o).astream({}, {"recursion_limit": og.recursion_limit(o.cfg.max_steps)},
                                                                                         stream_mode="updates") for name, update in chunk.items()]
    return run(go())


def test_the_graph_has_the_four_nodes_and_a_conditional_edge_from_plan():
    graph = og.diagram_graph().get_graph()
    assert {n for n in graph.nodes} - {"__start__", "__end__"} == set(og.NODES)
    edges = {(e.source, e.target, e.conditional) for e in graph.edges}
    assert ("plan", "execute_action", True) in edges and ("plan", "stop", True) in edges
    assert ("execute_action", "update_state", False) in edges and ("update_state", "plan", False) in edges and ("stop", "__end__", False) in edges


def test_happy_path_runs_plan_execute_update_plan_stop(repo, tmp_path):
    o = build(repo, suite(), tmp_path)
    names = [n for n, _u in visited(o)]
    assert names == ["plan", "execute_action", "update_state", "plan", "stop"]
    assert o.goal_met() and o.step == 2 and [e["chosen"] for e in o.trail.entries] == ["run_tools:all", "stop"]


def test_the_plan_node_returns_the_valid_options_and_the_validated_choice(repo, tmp_path):
    o = build(repo, suite(), tmp_path)
    plan = visited(o)[0][1]
    assert [a.key for a in plan["options"]] == ["run_tools:all", "stop"] and plan["chosen"].key == "run_tools:all" and plan["rejected"] is None
    assert plan["summary"]["pass_done"] is False and plan["entry"]["component"] == "orchestrator"


def test_a_retry_goes_around_the_loop_again(repo, tmp_path):
    names = [n for n, _u in visited(build(repo, suite(gitleaks=["fail", "ok"]), tmp_path))]
    assert names == ["plan", "execute_action", "update_state"] * 2 + ["plan", "stop"]


def test_a_rogue_policy_is_rejected_inside_the_graph_and_the_rules_decide(repo, tmp_path):
    o = build(repo, suite(gitleaks=["fail", "ok"]), tmp_path, policy=Rogue())
    executed = []
    real = o.execute

    async def spy(action):
        executed.append(action.key)
        return await real(action)

    o.execute = spy
    updates = visited(o)
    plans = [u for n, u in updates if n == "plan"]
    assert all(p["rejected"] and p["rejected"]["proposed"] == "shell:rm -rf /" for p in plans)
    assert all(p["chosen"].key in {a.key for a in p["options"]} for p in plans)  # the rules chose, from the valid options
    assert executed == ["run_tools:all", "retry_tool:gitleaks"] and not any("shell" in k for k in executed)
    assert o.goal_met() and all(e["policy"] == "rogue -> rules" for e in o.trail.entries)


def test_a_policy_that_picks_another_valid_option_is_followed_by_the_graph(repo, tmp_path):
    o = build(repo, suite(), tmp_path, policy=StopAtOnce())
    assert [n for n, _u in visited(o)] == ["plan", "stop"] and not o.runs


def test_the_stop_node_reports_why_and_the_budget_ends_the_loop(repo, tmp_path):
    o = build(repo, suite(gitleaks=["fail"] * 9), tmp_path, max_steps=4, max_retries=5)
    updates = visited(o)
    assert updates[-1][0] == "stop" and updates[-1][1]["stop_reason"] == "budget spent: 4 steps" and updates[-1][1]["goal_met"] is False
    assert o.step == 4 and [n for n, _u in updates].count("execute_action") == 3


def test_a_large_budget_does_not_hit_the_graph_recursion_limit(repo, tmp_path):
    o = build(repo, suite(gitleaks=["fail"] * 60), tmp_path, max_steps=45, max_retries=40)
    updates = visited(o)
    assert updates[-1][0] == "stop" and o.step == 43 and len(updates) > 100  # 1 run + 40 retries + skip + stop, far past the default limit


def test_the_graph_is_what_run_uses(repo, tmp_path, monkeypatch):
    seen = []
    real = og.build_orchestrator_graph
    monkeypatch.setattr(orch, "build_orchestrator_graph", lambda o: seen.append(o) or real(o))
    out = run(orch.orchestrate(repo, suite(), config=LoopConfig(20, 1), scan_dir=tmp_path / "scans"))
    assert len(seen) == 1 and out.goal_met
