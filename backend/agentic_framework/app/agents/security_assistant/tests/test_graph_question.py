"""The Question Agent as a LangGraph graph: ask -> score -> follow_up -> score ... -> close | escalate."""

import pytest

from app.agents.security_assistant import questions as q
from app.agents.security_assistant.agent_loop import DecisionTrail, LoopConfig, RulePolicy
from app.agents.security_assistant.graphs import question_graph as qg
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.tests.test_question_agent import ClosesAnything, repo, run  # noqa: F401
from app.agents.security_assistant.tests.test_questions import group


def walk(repo, scores, threshold=0.7, retries=2, policy=None, steps=0, max_steps=200):
    """The nodes the graph visits for one finding, and the final state."""
    cfg = LoopConfig(max_steps, retries)
    trail = DecisionTrail("question agent")
    ctx = qg.QuestionContext(trail, policy or RulePolicy(), RulePolicy(), cfg, q.MockTutor(scores=scores), threshold, repo, PIIRedactor())
    graph = qg.build_question_graph(ctx)
    state = {"group": group("G01", "app.py", 10, "sql-injection"), "attempts": [], "status": "open", "escalation": None, "steps": steps}

    async def go():
        nodes, final = [], dict(state)
        async for chunk in graph.astream(state, {"recursion_limit": qg.recursion_limit(cfg)}, stream_mode="updates"):
            for name, update in chunk.items():
                nodes.append(name)
                final.update(update)
        return nodes, final

    nodes, final = run(go())
    return nodes, final, trail


def test_the_graph_has_the_five_nodes_and_conditional_edges_on_the_score_and_the_budget():
    graph = qg.diagram_graph().get_graph()
    assert set(graph.nodes) - {"__start__", "__end__"} == set(qg.NODES)
    edges = {(e.source, e.target, e.conditional) for e in graph.edges}
    assert {("ask", "score", True), ("ask", "escalate", True), ("score", "close", True), ("score", "follow_up", True), ("score", "escalate", True)} <= edges
    assert ("follow_up", "score", False) in edges and ("close", "__end__", False) in edges and ("escalate", "__end__", False) in edges


def test_a_score_at_or_above_the_threshold_closes_at_once(repo):
    nodes, final, _ = walk(repo, {"keyG01": 0.7})
    assert nodes == ["ask", "score", "close"] and final["status"] == "closed" and len(final["attempts"]) == 1


def test_a_low_score_goes_through_a_follow_up_and_closes_on_attempt_two(repo):
    nodes, final, trail = walk(repo, {"keyG01": [0.4, 0.8]})
    assert nodes == ["ask", "score", "follow_up", "score", "close"] and final["status"] == "closed"
    assert [a["hint_level"] for a in final["attempts"]] == [0, 1] and final["last_q"].attempt == 2 and final["steps"] == 3
    assert [e["chosen"] for e in trail.entries] == ["ask_question:level 0", "ask_followup:level 1", "close_finding"]


def test_the_attempt_budget_ends_in_escalation(repo):
    nodes, final, _ = walk(repo, {"keyG01": 0.3})
    assert nodes == ["ask", "score", "follow_up", "score", "follow_up", "score", "escalate"]
    assert final["status"] == "escalated" and len(final["attempts"]) == 3 and "limit of 2 follow-up(s) is reached" in final["escalation"]


def test_a_rogue_policy_cannot_close_a_finding_inside_the_graph(repo):
    nodes, final, trail = walk(repo, {"keyG01": 0.3}, policy=ClosesAnything())
    assert "close" not in nodes and final["status"] == "escalated"
    rejected = [e for e in trail.entries if e["rejected"]]
    assert rejected and all(e["rejected"]["proposed"] == "close_finding" for e in rejected) and all(e["policy"] == "closer -> rules" for e in rejected)
    assert all(e["chosen"] in e["options"] for e in trail.entries)  # what the graph acted on was always a valid option


def test_the_step_budget_routes_to_escalate_whatever_the_policy_would_choose(repo):
    nodes, final, trail = walk(repo, {"keyG01": 0.3}, max_steps=2)
    assert nodes == ["ask", "score", "follow_up", "score", "escalate"] and final["status"] == "escalated"
    assert "step budget spent (2 steps)" in final["escalation"] and trail.entries[-1]["policy"] == "budget"
    already = walk(repo, {"keyG01": 0.3}, steps=2, max_steps=2)  # the budget was spent by earlier findings: not even the first question
    assert already[0] == ["ask", "escalate"] and already[1]["attempts"] == [] and already[1].get("last_q") is None


def test_the_step_counter_is_shared_across_findings_through_the_state(repo):
    _nodes, final, _ = walk(repo, {"keyG01": [0.4, 0.8]}, steps=10)
    assert final["steps"] == 13


def test_generate_runs_this_graph_once_per_finding(repo, monkeypatch):
    calls = []
    real = qg.build_question_graph
    monkeypatch.setattr(q, "build_question_graph", lambda ctx: calls.append(ctx) or real(ctx))
    doc = {"groups": [group("G01", "app.py", 10, "sql-injection"), group("G02", "app.py", 7, "ownership-check", "V1")]}
    out = run(q.generate(doc, repo, q.MockTutor(scores={"keyG01": 0.9, "keyG02": 0.9}), 0.7, PIIRedactor()))
    assert len(calls) == 1 and out["summary"]["closed"] == 2  # one compiled graph, invoked for each finding
