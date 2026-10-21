"""The whole flow as one LangGraph workflow: fetch -> scan -> governance -> interpret -> trace -> risk -> guidance -> questions -> report."""

import inspect
import json

import pytest

from app.agents.security_assistant import assess
from app.agents.security_assistant import orchestrator as orch
from app.agents.security_assistant import questions as qs
from app.agents.security_assistant import risk as rk
from app.agents.security_assistant.graphs import assess_graph as ag
from app.agents.security_assistant.tests.test_assess import SAMPLES, SAVED, Forbidden, Mock, demo, go, run, stage  # noqa: F401

CHAIN = ["fetch", "scan", "governance", "interpret", "trace", "risk", "guidance", "questions", "report"]


@pytest.fixture
def nodes(monkeypatch):
    """Record the nodes the workflow visits, in order, and the merged final state of each run."""
    seen = {"nodes": [], "state": None}
    real = assess.build_assess_graph

    class Wrapped:
        def __init__(self, graph):
            self.graph = graph

        async def ainvoke(self, state, config=None):
            final = {k: (dict(v) if isinstance(v, dict) else v) for k, v in state.items()}
            async for chunk in self.graph.astream(state, config, stream_mode="updates"):
                for name, update in chunk.items():
                    seen["nodes"].append(name)
                    for key, value in update.items():
                        final[key] = {**final.get(key, {}), **value} if key in ("stages", "trails") else value
            seen["state"] = final
            return final

    monkeypatch.setattr(assess, "build_assess_graph", lambda ctx: Wrapped(real(ctx)))
    return seen


def test_the_workflow_has_the_nine_nodes_and_leaves_the_chain_only_to_the_report():
    graph = ag.diagram_graph().get_graph()
    assert set(graph.nodes) - {"__start__", "__end__"} == set(ag.NODES) == set(CHAIN)
    edges = {(e.source, e.target, e.conditional) for e in graph.edges}
    assert {("fetch", "scan", True), ("fetch", "report", True), ("scan", "governance", True), ("scan", "report", True)} <= edges
    assert {(a, b, False) for a, b in zip(CHAIN[2:-1], CHAIN[3:])} <= edges and ("report", "__end__", False) in edges
    assert ("__start__", "fetch", False) in edges


def test_the_happy_path_visits_every_node_in_order_and_the_stages_live_in_the_state(demo, tmp_path, nodes):
    report = go(demo, tmp_path, client=Mock(), req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")
    assert nodes["nodes"] == CHAIN
    stages = nodes["state"]["stages"]
    assert list(stages) == CHAIN[:-1] and all(s["status"] == "completed" for s in stages.values())
    assert [s["stage"] for s in report["run"]["stages"]] == CHAIN[:-1] and report["run"]["stages"] == [stages[n] for n in CHAIN[:-1]]
    assert nodes["state"]["report"] is report and json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["run"]["complete"] == report["run"]["complete"]


def test_the_nested_graphs_run_inside_the_nodes(demo, tmp_path, monkeypatch):
    calls = {"orchestrator": 0, "questions": 0, "gate": 0}
    real_orch, real_gen = orch.Orchestrator.run, qs.generate
    real_pre = assess.gv.Governance.pre_send

    async def run_counted(self):
        calls["orchestrator"] += 1
        return await real_orch(self)

    async def generate_counted(*a, **k):
        calls["questions"] += 1
        return await real_gen(*a, **k)

    def pre_send_counted(self, *a, **k):
        calls["gate"] += 1
        return real_pre(self, *a, **k)

    monkeypatch.setattr(orch.Orchestrator, "run", run_counted)
    monkeypatch.setattr(qs, "generate", generate_counted)
    monkeypatch.setattr(assess.gv.Governance, "pre_send", pre_send_counted)
    # a reused scan runs the orchestrator in review mode, a fresh scan runs the tools: use the review path here
    report = go(demo, tmp_path, client=Mock())
    assert calls["orchestrator"] == 1 and calls["questions"] == 1 and calls["gate"] == report["governance"]["calls_checked"] > 0


def test_an_unusable_scan_goes_straight_to_the_report_which_is_incomplete_and_says_why(demo, tmp_path, nodes):
    report = go(demo, tmp_path / "o", reuse=tmp_path / "missing.json")
    assert nodes["nodes"] == ["fetch", "scan", "report"]
    assert stage(report, "scan")["status"] == "failed" and report["run"]["complete"] is False
    assert [s["detail"] for s in report["run"]["stages"][2:]] == ["needs scan", "needs governance", "needs interpret", "needs interpret", "needs scan", "needs interpret"]
    assert any(r.startswith("stage scan failed") for r in report["run"]["incomplete_reasons"])
    assert (tmp_path / "o" / "report.json").exists() and (tmp_path / "o" / "report.md").exists()  # the report is still written


def test_nothing_fetched_goes_straight_to_the_report(tmp_path, nodes):
    report = run(assess.run_pipeline(str(tmp_path / "missing"), out_dir=tmp_path / "o", allow_external_llm=True, client=Forbidden()))
    assert nodes["nodes"] == ["fetch", "report"] and stage(report, "fetch")["status"] == "failed" and report["run"]["complete"] is False
    assert all(stage(report, n)["status"] == "skipped" for n in CHAIN[1:-1])


def test_a_failed_stage_does_not_end_the_run_early_and_the_report_marks_it_incomplete(demo, tmp_path, nodes, monkeypatch):
    monkeypatch.setattr(rk, "rank", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("scoring broke")))
    report = go(demo, tmp_path, client=Mock())
    assert nodes["nodes"] == CHAIN  # the later stages still ran
    assert stage(report, "risk")["status"] == "failed" and stage(report, "guidance")["status"] == "completed"
    assert report["run"]["complete"] is False and any("stage risk failed: RuntimeError: scoring broke" in r for r in report["run"]["incomplete_reasons"])
    assert "INCOMPLETE RUN" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_a_partial_stage_is_carried_to_the_report_as_incomplete(demo, tmp_path, nodes):
    from app.agents.security_assistant.tests.test_assess import Mock as FailingMock
    report = go(demo, tmp_path, client=FailingMock(fail=True))
    assert nodes["nodes"][-1] == "report" and stage(report, "interpret")["status"] == "partial" and report["run"]["complete"] is False
    assert any(r.startswith("stage interpret partial") for r in report["run"]["incomplete_reasons"])


def test_a_skipped_llm_stage_is_visible_in_the_state_and_the_report(demo, tmp_path, nodes):
    report = go(demo, tmp_path, allow_external_llm=False, client=Forbidden())
    assert nodes["nodes"] == CHAIN and nodes["state"]["llm_refused"] is True
    assert nodes["state"]["stages"]["interpret"]["status"] == "skipped" and report["run"]["llm_refused"] is True and report["run"]["complete"] is False


def test_governance_that_rejects_the_scan_stops_the_chain_at_the_report(demo, tmp_path, nodes):
    from app.agents.security_assistant.tests.test_governance import findings_file, repo  # noqa: F401
    path = tmp_path / "evil.json"
    doc = json.loads(SAVED.read_text(encoding="utf-8"))
    doc["runs"][0]["tool"] = "evil-scanner"
    path.write_text(json.dumps(doc), encoding="utf-8")
    report = go(demo, tmp_path / "o", reuse=path)
    assert nodes["nodes"] == ["fetch", "scan", "report"] and "evil-scanner" in stage(report, "scan")["detail"] and report["run"]["complete"] is False


def test_run_pipeline_keeps_its_signature():
    params = list(inspect.signature(assess.run_pipeline).parameters)
    assert params == ["repo_url", "requirements_file", "sprint_tasks_file", "skip", "reuse_scan", "out_dir", "allow_external_llm", "client", "tutor",
                      "threshold", "ref", "tools", "max_findings", "delay", "retries", "governance_warn_only", "fetch_options", "agent_config",
                      "orchestrator_policy", "question_config", "question_policy", "say"]
    assert inspect.iscoroutinefunction(assess.run_pipeline)
