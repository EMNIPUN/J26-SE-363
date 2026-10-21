"""The Governance Agent as a stateful LangGraph gate: check_input -> raise_scrutiny -> allow | block -> escalate. The score and the level
live in the graph state, which the Governance object carries from one pass to the next."""

import pytest

from app.agents.security_assistant import governance as gv
from app.agents.security_assistant.agent_loop import Action
from app.agents.security_assistant.graphs import governance_graph as gg
from app.agents.security_assistant.governance import Governance, GovernanceBlock
from app.agents.security_assistant.tests.test_governance import INJECTION, SECRET
from app.agents.security_assistant.tests.test_governance_agent import AllowEverything, HOSTILE, ZWSP, send  # noqa: F401


def passes(gov, event):
    """Run one pass through the gate and return the nodes it visited, in order, and the final state (kept by the Governance object)."""
    nodes, final = [], dict(gov._start_state(event))
    for chunk in gov._gate.stream(gov._start_state(event), {"recursion_limit": 60}, stream_mode="updates"):
        for name, update in chunk.items():
            nodes.append(name)
            final.update(update)
    gov._store(final)
    return nodes, final


def call(user, key="k"):
    return {"event": "call", "kind": "interpret", "finding_key": key, "category": "V3", "rule_id": "r", "system": "SYSTEM", "model": None,
            "user": f'<evidence id="E1" kind="finding" label="x">\n{user}\n</evidence>', "offered_ids": ["E1"], "prompt_version": None, "seed": None}


def test_the_gate_has_the_five_nodes_with_conditional_edges_for_the_decision_and_for_scrutiny():
    graph = gg.diagram_graph().get_graph()
    assert set(graph.nodes) - {"__start__", "__end__"} == set(gg.NODES)
    edges = {(e.source, e.target, e.conditional) for e in graph.edges}
    assert {("check_input", "allow", True), ("check_input", "block", True), ("check_input", "raise_scrutiny", True), ("raise_scrutiny", "escalate", True),
            ("raise_scrutiny", "check_input", True), ("allow", "raise_scrutiny", True), ("block", "raise_scrutiny", True)} <= edges


def test_a_clean_call_goes_check_input_then_allow(tmp_path):
    nodes, final = passes(Governance(tmp_path), call("an ordinary line"))
    assert nodes == ["check_input", "allow"] and final["chosen"].name == "allow_call" and final["checked"] == 1 and not final["block"]


def test_a_failed_check_leaves_no_allow_option_and_goes_to_block(tmp_path):
    gov = Governance(tmp_path, secret_values={SECRET})
    nodes, final = passes(gov, call(f"key {SECRET}"))
    assert nodes == ["check_input", "block"] and [o.key for o in final["options"]] == ["block_call"]
    assert final["block"]["code"] == "secret_value_in_prompt" and (final["blocked"], final["score"]) == (1, 2)


def test_a_rogue_policy_is_rejected_inside_the_gate_and_the_rules_decide(tmp_path):
    gov = Governance(tmp_path, secret_values={SECRET}, policy=AllowEverything())
    nodes, final = passes(gov, call(f"key {SECRET}"))
    assert nodes == ["check_input", "block"] and final["chosen"].name == "block_call"
    assert gov.trail.entries[0]["rejected"]["proposed"] == "allow_call" and gov.trail.entries[0]["policy"] == "permissive -> rules"


def test_the_score_and_the_level_live_in_the_graph_state_and_are_carried_between_passes(tmp_path):
    gov = Governance(tmp_path)
    nodes, final = passes(gov, call(f"# {INJECTION}", "a"))
    assert nodes == ["check_input", "allow"] and (final["score"], final["level"]) == (1, "normal")
    assert gov.gstate["score"] == 1 and gov.score == 1  # the Governance attributes are the graph state's keys
    gov.gstate["score"] = 2  # the next pass starts from the state, not from anything else
    nodes, final = passes(gov, call(f"# {INJECTION}", "b"))
    assert nodes == ["check_input", "raise_scrutiny", "check_input", "allow"] and final["level"] == "elevated" and gov.level == "elevated"
    gov.level = "high"  # and writing the attribute writes the state
    assert gov.gstate["level"] == "high"


def test_a_raise_before_the_decision_gives_this_very_call_the_second_check(tmp_path):
    gov = Governance(tmp_path, secret_values={SECRET}, elevated_at=1)
    hidden = f"{INJECTION} key {SECRET[:8]}{ZWSP}{SECRET[8:]}"
    nodes, final = passes(gov, call(hidden))
    assert nodes == ["check_input", "raise_scrutiny", "check_input", "block"] and final["block"]["code"] == "second_check_secret"
    assert final["second_checks"] == 1 and final["second_check_blocks"] == 1


def test_the_third_block_raises_to_high_and_escalates(tmp_path):
    gov = Governance(tmp_path, secret_values={SECRET})
    assert passes(gov, call(SECRET, "1"))[0] == ["check_input", "block"]
    assert passes(gov, call(SECRET, "2"))[0] == ["check_input", "block", "raise_scrutiny"] and gov.level == "elevated"
    nodes, final = passes(gov, call(SECRET, "3"))
    assert nodes == ["check_input", "block", "raise_scrutiny", "escalate"] and final["level"] == "high" and final["escalated"] is True
    assert gov.escalated and "repeated injection indicators or blocked calls" in gov.escalation_reason


def test_a_big_jump_in_score_raises_through_both_levels_in_one_pass(tmp_path):
    gov = Governance(tmp_path)
    nodes, final = passes(gov, {"event": "repo", "distinct": 7})
    assert nodes == ["check_input", "raise_scrutiny", "raise_scrutiny", "escalate"] and final["level"] == "high" and final["repo_indicator_count"] == 7
    assert [e["chosen"] for e in gov.trail.entries] == ["raise_scrutiny:elevated", "raise_scrutiny:high", "escalate_to_reviewer"]


def test_one_repository_indicator_changes_nothing_but_the_score(tmp_path):
    gov = Governance(tmp_path)
    nodes, final = passes(gov, {"event": "repo", "distinct": 1})
    assert nodes == ["check_input"] and (final["score"], final["level"]) == (1, "normal")


def test_scan_repo_uses_the_gate_for_its_indicators(tmp_path, monkeypatch):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "README.md").write_text(HOSTILE, encoding="utf-8")
    gov = Governance(tmp_path / "out")
    seen = []
    real = gov._invoke
    monkeypatch.setattr(gov, "_invoke", lambda event: seen.append(event) or real(event))
    gov.scan_repo(repo)
    assert seen and seen[0]["event"] == "repo" and seen[0]["distinct"] >= 6 and gov.escalated


def test_pre_send_is_one_pass_through_the_gate_and_raises_on_block(tmp_path):
    gov = Governance(tmp_path, secret_values={SECRET})
    calls = []
    real = gov._gate.invoke
    gov._gate = type("G", (), {"invoke": lambda self, s, c=None: calls.append(s["event"]) or real(s, c)})()
    send(gov, "fine")
    with pytest.raises(GovernanceBlock):
        send(gov, f"key {SECRET}")
    assert calls == ["call", "call"]


def test_the_gate_state_has_no_place_for_a_verdict_or_a_finding():
    assert not {k for k in gg.GateState.__annotations__ if any(w in k for w in ("verdict", "finding_list", "findings", "status"))}
