"""The Mermaid diagrams are generated from the compiled graphs and stay in sync; WORKFLOW.md matches the code."""

import shutil
from pathlib import Path

import pytest

from app.agents.security_assistant import governance as gv
from app.agents.security_assistant import orchestrator as orch
from app.agents.security_assistant import questions as qs
from app.agents.security_assistant.graphs import assess_graph, diagrams, governance_graph, orchestrator_graph, question_graph

NODES = {"workflow": assess_graph.NODES, "orchestrator": orchestrator_graph.NODES, "question": question_graph.NODES,
         "governance": governance_graph.NODES}


def test_the_export_writes_one_diagram_per_graph_and_refreshes_the_workflow_md(tmp_path):
    md = tmp_path / "WORKFLOW.md"
    md.write_text("# x\n\n" + diagrams.BEGIN + "\nold\n" + diagrams.END + "\n\nafter\n", encoding="utf-8")
    written = diagrams.export(tmp_path / "docs", md)
    assert {p.name for p in written} == {"workflow.mmd", "orchestrator.mmd", "question.mmd", "governance.mmd", "WORKFLOW.md"}
    text = md.read_text(encoding="utf-8")
    assert text.startswith("# x") and text.rstrip().endswith("after") and "old" not in text and "```mermaid\n---" in text and "graph TD;" in text
    assert text == diagrams.refreshed_workflow_md(text, diagrams.render_all()["workflow"])  # refreshing again changes nothing


@pytest.mark.parametrize("name", sorted(NODES))
def test_each_diagram_is_mermaid_and_names_every_node_of_its_graph(name):
    text = diagrams.render_all()[name]
    assert "graph TD;" in text and "__start__" in text and "__end__" in text
    for node in NODES[name]:
        assert f"\t{node}({node})" in text, node


def test_the_committed_diagrams_and_workflow_md_are_in_sync_with_the_code():
    """Regenerate with: python -m app.agents.security_assistant.graphs.diagrams"""
    assert diagrams.stale() == []


def test_the_check_command_notices_a_stale_diagram(tmp_path, capsys):
    docs, md = tmp_path / "docs", tmp_path / "WORKFLOW.md"
    shutil.copytree(diagrams.DOCS, docs)
    shutil.copy(diagrams.WORKFLOW_MD, md)
    assert diagrams.main(["--check", "--out", str(docs), "--workflow-md", str(md)]) == 0
    (docs / "question.mmd").write_text("graph TD;\n\told --> stale;\n", encoding="utf-8")
    md.write_text(md.read_text(encoding="utf-8").replace("scan(scan)", "scan(renamed)"), encoding="utf-8")
    assert diagrams.main(["--check", "--out", str(docs), "--workflow-md", str(md)]) == 1
    out = capsys.readouterr().out
    assert "out of date: question.mmd, WORKFLOW.md" in out
    assert diagrams.main(["--out", str(docs), "--workflow-md", str(md)]) == 0  # the command repairs it
    assert diagrams.stale(docs, md) == []


def test_workflow_md_lists_every_allowed_action_and_every_node_of_the_three_agents():
    text = (Path(diagrams.WORKFLOW_MD)).read_text(encoding="utf-8")
    for action in (*orch.ACTIONS, *qs.QUESTION_ACTIONS, *gv.GOVERNANCE_ACTIONS):
        assert f"`{action}`" in text, action
    for node in (*orchestrator_graph.NODES, *question_graph.NODES, *governance_graph.NODES, *assess_graph.NODES):
        assert node in text, node
    for heading in ("## The flow", "## The three agents", "## What is mocked or not built", "### Analysis Orchestrator", "### Question Agent", "### Governance"):
        assert heading in text
    for mocked in ("Mock", "LLM policy", "not built", "RQ1"):
        assert mocked in text


def test_the_actions_the_code_can_produce_are_all_in_the_documented_vocabulary():
    """The fixed vocabularies are the ones documented: nothing outside them is a valid option anywhere."""
    from app.agents.security_assistant.agent_loop import Action
    from app.agents.security_assistant.agent_loop import LoopConfig

    assert {a.name for a in qs.question_options([], 0.7, LoopConfig(5, 2))} <= set(qs.QUESTION_ACTIONS)
    low, high = [{"attempt": 1, "score": 0.1}], [{"attempt": 1, "score": 0.9}]
    for attempts in (low, low * 3, high):
        assert {a.name for a in qs.question_options(attempts, 0.7, LoopConfig(5, 2))} <= set(qs.QUESTION_ACTIONS)
    assert isinstance(Action("stop"), Action) and "stop" in orch.ACTIONS
