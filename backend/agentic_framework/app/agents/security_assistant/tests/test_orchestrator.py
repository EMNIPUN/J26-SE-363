"""Analysis Orchestrator Agent: a bounded loop with a fixed, validated action list. The tools are scripted fakes; nothing real runs."""

import asyncio
import json
import sys
from dataclasses import dataclass, field

import pytest

from app.agents.security_assistant import assess
from app.agents.security_assistant import orchestrator as orch
from app.agents.security_assistant.agent_loop import Action, LoopConfig
from app.agents.security_assistant.governance import AuditLog
from app.agents.security_assistant.orchestrator import orchestrate, review
from app.agents.security_assistant.report import build_report, to_json
from app.agents.security_assistant.schemas import Category, Finding, RunStatus, ScanResult, ToolRun
from app.agents.security_assistant.tools.base import BaseTool, ScanOutput, ToolFailed, ToolTimeout
from app.agents.security_assistant.tools.tests.conftest import FIXTURES

JS = frozenset({"javascript", "typescript"})
SPEC = {"config-scan": None, "gitleaks": None, "trufflehog": None, "osv-scanner": None, "npm-audit": JS, "pip-audit": frozenset({"python"}),
        "actionlint": None, "zizmor": None, "codeql": frozenset({"python", "java", "javascript", "typescript"})}


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@dataclass
class Fake(BaseTool):
    """A tool that does what its script says on each call: 'ok', 'fail', 'timeout' or a function of the context."""

    name: str = "fake"
    binary: str | None = None
    languages: frozenset | None = None
    script: list = field(default_factory=list)
    calls: list = field(default_factory=list)

    async def scan(self, ctx, exe):
        self.calls.append(ctx)
        step = self.script.pop(0) if self.script else "ok"
        if callable(step):
            step = step(ctx)
        if step == "fail":
            raise ToolFailed("boom")
        if step == "timeout":
            raise ToolTimeout("too slow")
        return ScanOutput([Finding(category=Category.V3, rule_id=f"{self.name}-rule", file_path="a.py", line=1, message="m")], "")


def suite(**scripts):
    return [Fake(name=n, languages=lang, script=list(scripts.get(n.replace("-", "_"), []))) for n, lang in SPEC.items()]


def tool(tools, name):
    return next(t for t in tools if t.name == name)


def put(root, files):
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")
    return root


@pytest.fixture
def repo(tmp_path):
    return put(tmp_path / "repo", {"app.py": "x = 1\n", "A.java": "class A {}\n", "requirements.txt": "flask==1.0\n"})


def go(repo, tools, tmp_path, max_steps=20, max_retries=1, **kw):
    return run(orchestrate(repo, tools, config=LoopConfig(max_steps, max_retries), scan_dir=tmp_path / "scans", **kw))


def chosen(outcome):
    return [e["chosen"] for e in outcome.trail]


# ---- retry ---------------------------------------------------------------------------------------------------------------------------------
def test_a_failed_tool_is_retried_once_and_the_goal_is_then_met(repo, tmp_path):
    tools = suite(gitleaks=["fail", "ok"])
    out = go(repo, tools, tmp_path)
    assert chosen(out) == ["run_tools:all", "retry_tool:gitleaks", "stop"]
    assert len(tool(tools, "gitleaks").calls) == 2
    run_ = next(r for r in out.result.runs if r.tool == "gitleaks")
    assert run_.status is RunStatus.SUCCEEDED and out.result.complete and out.goal_met
    assert out.stop_reason.startswith("goal met") and out.trail[1]["outcome"] == "gitleaks: failed -> succeeded"
    assert any(f.tool == "gitleaks" for f in out.result.findings)


def test_a_tool_that_keeps_failing_is_retried_only_once_then_acknowledged_and_the_report_stays_incomplete(repo, tmp_path):
    tools = suite(gitleaks=["fail", "fail", "ok"])
    out = go(repo, tools, tmp_path)
    assert len(tool(tools, "gitleaks").calls) == 2  # the third script step is never reached
    assert chosen(out) == ["run_tools:all", "retry_tool:gitleaks", "skip_with_reason:gitleaks", "stop"]
    assert out.result.complete is False and out.goal_met is False and "V4 REDUCED" in out.stop_reason
    assert out.acknowledged and "gitleaks" in out.acknowledged


def test_the_number_of_retries_is_configurable_and_a_timeout_is_retried_like_a_failure(repo, tmp_path):
    tools = suite(gitleaks=["timeout", "fail", "ok"])
    out = go(repo, tools, tmp_path, max_retries=2)
    assert len(tool(tools, "gitleaks").calls) == 3 and out.goal_met
    assert chosen(out).count("retry_tool:gitleaks") == 2
    assert go(repo, suite(gitleaks=["fail"]), tmp_path, max_retries=0).trail[1]["chosen"] == "skip_with_reason:gitleaks"


def test_a_missing_binary_is_never_retried(repo, tmp_path):
    tools = suite()
    tool(tools, "trufflehog").binary = "no-such-binary-xyz-123"
    out = go(repo, tools, tmp_path)
    assert chosen(out) == ["run_tools:all", "skip_with_reason:trufflehog", "stop"] and not tool(tools, "trufflehog").calls
    assert next(r for r in out.result.runs if r.tool == "trufflehog").status is RunStatus.UNAVAILABLE


# ---- fallbacks -----------------------------------------------------------------------------------------------------------------------------
def codeql_fails_on_two_languages(ctx):
    return "fail" if len({"python", "java"} & ctx.languages) > 1 else "ok"


def test_codeql_falls_back_to_one_run_per_language(repo, tmp_path):
    tools = suite(codeql=[codeql_fails_on_two_languages] * 6)
    out = go(repo, tools, tmp_path)
    assert chosen(out) == ["run_tools:all", "retry_tool:codeql", "codeql_per_language:python", "codeql_per_language:java-kotlin", "stop"]
    codeql_run = next(r for r in out.result.runs if r.tool == "codeql")
    assert codeql_run.status is RunStatus.SUCCEEDED and out.goal_met and out.result.complete
    assert [sorted(c.languages & {"python", "java"}) for c in tool(tools, "codeql").calls] == [["java", "python"], ["java", "python"], ["python"], ["java"]]
    assert sum(f.tool == "codeql" for f in out.result.findings) == 2  # one finding per language run


def test_when_one_language_keeps_failing_the_findings_of_the_other_are_kept_and_the_tool_stays_failed(repo, tmp_path):
    tools = suite(codeql=[lambda ctx: "fail" if "java" in ctx.languages else "ok"] * 6)
    out = go(repo, tools, tmp_path)
    codeql_run = next(r for r in out.result.runs if r.tool == "codeql")
    assert codeql_run.status is RunStatus.FAILED and "python succeeded" in codeql_run.reason and "java-kotlin failed" in codeql_run.reason
    assert sum(f.tool == "codeql" for f in out.result.findings) == 1 and out.result.complete is False
    assert "skip_with_reason:codeql" in chosen(out) and not out.goal_met


def test_one_language_is_not_split_further(tmp_path):
    repo = put(tmp_path / "r", {"app.py": "x = 1\n", "requirements.txt": "flask==1.0\n"})
    out = go(repo, suite(codeql=["fail", "fail"]), tmp_path)
    assert not any(c.startswith("codeql_per_language") for c in chosen(out)) and "skip_with_reason:codeql" in chosen(out)


def test_when_a_lockfile_is_missing_the_audit_tool_is_not_run_and_the_decision_says_osv_only(tmp_path):
    repo = put(tmp_path / "r", {"package.json": json.dumps({"dependencies": {"express": "4"}}), "server.js": "1\n"})
    tools = suite()
    out = go(repo, tools, tmp_path)
    first = out.trail[0]
    assert "npm-audit (no package-lock.json: OSV-Scanner only" in first["reason"] and not tool(tools, "npm-audit").calls
    npm = next(r for r in out.result.runs if r.tool == "npm-audit")
    assert npm.status is RunStatus.NOT_APPLICABLE and "OSV-Scanner only" in npm.reason
    # the missing lockfile is also a coverage gap: it is recorded, with the reason no tool can scan declared npm versions
    assert "record_gap" in chosen(out)[1] and "no tool reads package.json without a lockfile" in out.trail[1]["reason"]
    assert not any(c.startswith("scan_declared") for c in chosen(out))


def test_the_js_demo_gap_express_missing_from_the_lockfile_is_recorded_and_the_loop_stops_with_the_reason(tmp_path):
    out = go(FIXTURES / "vuln_js_repo", suite(), tmp_path)
    gap = "package.json declares 1 dependency that package-lock.json does not list, so no scanner checked it: express"
    assert out.result.coverage_gaps == [gap] and out.recorded_gaps == [gap]
    assert [c.split(":")[0] for c in chosen(out)] == ["run_tools", "record_gap", "stop"]
    decision = out.trail[1]
    assert "no tool reads package.json without a lockfile" in decision["reason"] and "npm would have to install packages" in decision["reason"]
    assert not any(o.startswith("scan_declared") for o in decision["options"])  # no tool supports it, so it was never offered
    assert out.stop_reason.startswith("coverage acceptable; 1 dependency gap(s) recorded and left open") and "npm" in out.stop_reason
    assert out.goal_met is False and out.result.complete is True  # every tool finished; the report is still not clean of gaps


def test_declared_versions_are_scanned_when_a_tool_supports_it_after_the_full_osv_run_failed(tmp_path):
    repo = put(tmp_path / "r", {"app.py": "x\n", "backend/requirements.txt": "flask>=1\n", "backend/b.py": "y\n"})
    root = repo.resolve()
    tools = suite(**{"osv_scanner": [lambda ctx: "fail" if ctx.repo == root else "ok"] * 4})
    out = go(repo, tools, tmp_path)
    names = chosen(out)
    assert names[:4] == ["run_tools:all", "retry_tool:osv-scanner", "scan_declared:backend", "record_gap:" + out.result.coverage_gaps[0][:120]]
    osv = tool(tools, "osv-scanner")
    assert osv.calls[-1].repo == repo.resolve() / "backend" and len(osv.calls) == 3
    assert any(f.tool == "osv-scanner" and f.file_path == "backend/a.py" for f in out.result.findings)  # paths are relative to the repo
    run_ = next(r for r in out.result.runs if r.tool == "osv-scanner")
    assert "scanned separately: succeeded" in run_.reason and run_.status is RunStatus.FAILED  # honest: the full run still failed


# ---- the budget ------------------------------------------------------------------------------------------------------------------------------
def test_the_loop_stops_at_the_step_budget_and_says_so(repo, tmp_path):
    tools = suite(gitleaks=["fail"] * 10)
    out = go(repo, tools, tmp_path, max_steps=4, max_retries=5)
    assert out.steps == 4 and chosen(out) == ["run_tools:all", "retry_tool:gitleaks", "retry_tool:gitleaks", "stop"]
    assert out.stop_reason == "budget spent: 4 steps" and len(tool(tools, "gitleaks").calls) == 3 and not out.goal_met
    assert out.trail[-1]["options"] == ["stop"]  # at the end of the budget the only valid action is stop


def test_the_budget_has_a_floor_so_a_first_pass_can_happen(repo, tmp_path):
    out = go(repo, suite(), tmp_path, max_steps=1)
    assert out.steps == 2 and chosen(out)[0] == "run_tools:all"


def test_budgets_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("SECURITY_ASSISTANT_ORCHESTRATOR_MAX_STEPS", "7")
    monkeypatch.setenv("SECURITY_ASSISTANT_AGENT_MAX_RETRIES", "3")
    cfg = LoopConfig.from_env("ORCHESTRATOR", max_steps=20, max_retries=1)
    assert (cfg.max_steps, cfg.max_retries) == (7, 3)
    monkeypatch.setenv("SECURITY_ASSISTANT_ORCHESTRATOR_MAX_RETRIES", "0")
    assert LoopConfig.from_env("ORCHESTRATOR", 20, 1).max_retries == 0


# ---- the policy is swappable but cannot leave the action list ---------------------------------------------------------------------------------
class Rogue:
    name = "rogue"

    def choose(self, state, options):
        return Action("shell", "rm -rf /"), "run anything"


class Broken:
    name = "broken"

    def choose(self, state, options):
        raise RuntimeError("model unreachable")


class StopAtOnce:
    name = "stop-at-once"

    def choose(self, state, options):
        return next(o for o in options if o.name == "stop"), "an LLM may decide to stop"


class RetryEverythingFirst:
    name = "eager"

    def choose(self, state, options):  # picks a valid action that is not the first one
        retry = [o for o in options if o.name == "retry_tool"]
        return (retry or options)[-1 if not retry else 0], "prefers retries"


def test_an_action_outside_the_valid_options_is_rejected_recorded_and_replaced_by_the_rules(repo, tmp_path):
    out = go(repo, suite(), tmp_path, policy=Rogue())
    first = out.trail[0]
    assert first["chosen"] == "run_tools:all" and first["rejected"] == {"policy": "rogue", "proposed": "shell:rm -rf /", "problem": "not one of the valid options"}
    assert first["policy"] == "rogue -> rules" and out.goal_met  # the loop still did its work with the rules
    assert not any("shell" in o for e in out.trail for o in e["options"])


def test_a_policy_that_fails_does_not_stop_or_free_the_loop(repo, tmp_path):
    out = go(repo, suite(gitleaks=["fail", "ok"]), tmp_path, policy=Broken())
    assert all(e["rejected"]["error"] == "RuntimeError" for e in out.trail) and out.goal_met


def test_a_policy_may_pick_any_valid_option_for_example_to_stop_early(repo, tmp_path):
    tools = suite()
    out = go(repo, tools, tmp_path, policy=StopAtOnce())
    assert chosen(out) == ["stop"] and out.result.runs == [] and not any(t.calls for t in tools)
    out = go(repo, suite(gitleaks=["fail", "ok"]), tmp_path, policy=RetryEverythingFirst())
    assert out.trail[0]["chosen"] == "stop" or out.trail[0]["chosen"] == "run_tools:all"


def test_every_action_name_is_in_the_fixed_vocabulary(repo, tmp_path):
    out = go(repo, suite(gitleaks=["fail", "fail"], codeql=[codeql_fails_on_two_languages] * 4), tmp_path)
    assert {c.split(":")[0] for e in out.trail for c in e["options"] + [e["chosen"]]} <= set(orch.ACTIONS)


# ---- the decision trail ------------------------------------------------------------------------------------------------------------------------
def test_every_decision_is_a_line_in_the_audit_log(repo, tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    out = go(repo, suite(gitleaks=["fail", "ok"]), tmp_path, audit=audit)
    lines = [json.loads(x) for x in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(lines) == out.steps == len(out.trail) and {e["event"] for e in lines} == {"agent_decision"}
    assert [e["chosen"] for e in lines] == chosen(out) and all(e["component"] == "orchestrator" and e["reason"] and e["outcome"] for e in lines)
    assert [e["seq"] for e in lines] == list(range(len(lines))) and lines[1]["state"]["statuses"]["gitleaks"] == "failed"
    assert lines[1]["state"]["retries_used"] == {} and lines[2]["state"]["retries_used"] == {"gitleaks": 1}


def test_the_state_the_policy_sees_is_small_and_shows_coverage_retries_and_steps(repo, tmp_path):
    seen = []

    class Spy:
        name = "spy"

        def choose(self, state, options):
            seen.append((state, [o.key for o in options]))
            return options[0], options[0].why

    go(repo, suite(gitleaks=["fail", "ok"]), tmp_path, policy=Spy())
    state, options = seen[1]
    assert set(state) == {"pass_done", "statuses", "retries_used", "coverage", "open_gaps", "recorded_gaps", "steps_used", "max_steps"}
    assert state["coverage"]["V4"] == "REDUCED" and options[0] == "retry_tool:gitleaks" and state["steps_used"] == 1
    json.dumps(state)  # a summary an LLM policy could be given as it is


# ---- review mode and the pipeline ------------------------------------------------------------------------------------------------------------------
def test_review_mode_decides_about_a_reused_scan_without_running_anything():
    runs = [ToolRun(tool=t, status=RunStatus.SUCCEEDED, started_at="2026-10-20T00:00:00Z") for t in SPEC if t != "gitleaks"]
    runs.append(ToolRun(tool="gitleaks", status=RunStatus.FAILED, reason="boom", started_at="2026-10-20T00:00:00Z"))
    gap = "package.json declares 1 dependency that package-lock.json does not list, so no scanner checked it: express"
    scan = ScanResult(run_id="r", repo_path="x", languages=["javascript"], runs=runs, coverage_gaps=[gap],
                      findings=[Finding(category=Category.V4, rule_id="k", tool="gitleaks", file_path="a.py", line=1)])
    out = run(review(scan, config=LoopConfig(10, 1)))
    assert set(chosen(out)) == {f"record_gap:{gap[:120]}", "skip_with_reason:gitleaks", "stop"} and "retry_tool:gitleaks" not in chosen(out)
    assert out.result.findings == scan.findings and out.recorded_gaps == [gap] and "V4 REDUCED" in out.stop_reason


def reused_js_findings(tmp_path):
    runs = [ToolRun(tool=t, status=RunStatus.SUCCEEDED, started_at="2026-10-20T00:00:00Z") for t in SPEC]
    path = tmp_path / "findings.json"
    path.write_text(to_json(build_report(ScanResult(run_id="r", repo_path="x", languages=["javascript"], runs=runs))), encoding="utf-8")
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["scan"].pop("coverage_gaps")
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_the_decision_trail_is_in_the_report_the_json_and_the_audit_log(tmp_path):
    out = tmp_path / "out"
    report = run(assess.run_pipeline(str(FIXTURES / "vuln_js_repo"), reuse_scan=reused_js_findings(tmp_path), out_dir=out))
    trail = report["decision_trail"]["Analysis Orchestrator"]
    assert [e["chosen"].split(":")[0] for e in trail] == ["record_gap", "stop"] and "express" in trail[0]["reason"] + trail[0]["chosen"]
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "## Decision trail" in md and "### Analysis Orchestrator" in md and "`record_gap:" in md and "no tool reads package.json without a lockfile" in md
    assert "agent loop" in next(s for s in report["run"]["stages"] if s["stage"] == "scan")["detail"]
    events = [json.loads(x) for x in (out / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [e["chosen"].split(":")[0] for e in events if e["event"] == "agent_decision" and e["component"] == "orchestrator"] == ["record_gap", "stop"]
    assert any(r.startswith("dependency coverage gap:") for r in report["run"]["incomplete_reasons"])


def test_the_scan_command_writes_the_trail_too(tmp_path):
    from app.agents.security_assistant import scan as scan_module

    others = [n for n in scan_module.tool_names() if n != "config-scan"]
    text, _code = run(scan_module.scan(str(FIXTURES / "vuln_py_repo"), skip=others, out_dir=tmp_path / "o"))
    md = (tmp_path / "o" / "report.md").read_text(encoding="utf-8")
    assert "## Decision trail" in md and "`run_tools:all`" in md
    assert any(json.loads(x)["event"] == "agent_decision" for x in (tmp_path / "o" / "audit.jsonl").read_text(encoding="utf-8").splitlines())
