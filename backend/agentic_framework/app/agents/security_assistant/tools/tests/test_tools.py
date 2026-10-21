import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.agents.security_assistant.schemas import Category, RunStatus, ScanResult
from app.agents.security_assistant.tools.base import (
    BaseTool, NotApplicable, ScanContext, ScanOutput, mask_secret, run_command,
)
from app.agents.security_assistant.tools.codeql import parse_sarif
from app.agents.security_assistant.tools.config_scan import ConfigScanTool
from app.agents.security_assistant.tools.dependencies import parse_npm_audit, parse_osv, parse_pip_audit
from app.agents.security_assistant.tools.languages import detect_languages
from app.agents.security_assistant.tools.runner import InvalidRepoPath, default_tools, run_all
from app.agents.security_assistant.tools.secret_scanners import parse_gitleaks, parse_trufflehog
from app.agents.security_assistant.tools.tests.conftest import FAKE_AWS_KEY, FIXTURES
from app.agents.security_assistant.tools.workflow_lint import parse_actionlint, parse_zizmor

REPO = Path("/repo")


def ctx_for(tmp_path, languages=("python",)):
    return ScanContext(repo=tmp_path, work_dir=tmp_path / "work", languages=set(languages))


def run(coro):
    # The repo's root conftest sets the Windows selector loop (needed by psycopg), which cannot
    # spawn subprocesses; use a Proactor loop there.
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---- languages -------------------------------------------------------------------------------
@pytest.mark.parametrize("fixture,expected", [
    ("vuln_py_repo", {"python"}),
    ("vuln_java_repo", {"java"}),
    ("vuln_js_repo", {"javascript", "typescript"}),
])
def test_detect_languages(fixture, expected):
    assert detect_languages(FIXTURES / fixture) >= expected


def test_detect_languages_mixed_repo(tmp_path):
    (tmp_path / "a.ts").write_text("x")
    (tmp_path / "pom.xml").write_text("<project/>")
    assert detect_languages(tmp_path) == {"typescript", "java"}


# ---- config scanner on the seeded repos ---------------------------------------------------------
def _config_rules(make_repo, name):
    repo = make_repo(name)
    ctx = ScanContext(repo=repo, work_dir=repo.parent / "w", languages=detect_languages(repo))
    ctx.work_dir.mkdir()
    findings, rec = run(ConfigScanTool().run(ctx))
    assert rec.status is RunStatus.SUCCEEDED
    assert all(f.category in (Category.V3, Category.V1) for f in findings)  # V1: Spring access-control config rules
    return {f.rule_id for f in findings}


def test_config_scan_python(make_repo):
    assert {"security-assistant-cfg-001", "security-assistant-cfg-003", "security-assistant-cfg-005", "security-assistant-cfg-007"} <= _config_rules(make_repo, "vuln_py_repo")


def test_config_scan_javascript(make_repo):
    assert {"security-assistant-cfg-001", "security-assistant-cfg-003", "security-assistant-cfg-007"} <= _config_rules(make_repo, "vuln_js_repo")


def test_config_scan_java(make_repo):
    expected = {"security-assistant-cfg-001", "security-assistant-cfg-003", "security-assistant-cfg-004", "security-assistant-cfg-005", "security-assistant-cfg-006", "security-assistant-cfg-007"}
    assert expected <= _config_rules(make_repo, "vuln_java_repo")


def test_config_scan_no_jwt_finding_when_expiry_set(tmp_path):
    (tmp_path / "a.py").write_text('import jwt\njwt.encode({"exp": 1, "u": 2}, "k")\n')
    (tmp_path / "work").mkdir()
    findings, _ = run(ConfigScanTool().run(ctx_for(tmp_path)))
    assert not [f for f in findings if f.rule_id == "security-assistant-cfg-001"]


# ---- parsers on recorded tool output ---------------------------------------------------------------
def test_parse_gitleaks_masks_and_maps():
    report = [{"RuleID": "aws-access-token", "File": "settings_old.py", "StartLine": 1,
               "Commit": "abc123", "Secret": "REDACTED", "Match": "REDACTED", "Description": "AWS key"}]
    [f] = parse_gitleaks(report, REPO)
    assert (f.category, f.cwe, f.rule_id, f.line, f.source) == (
        Category.V4, "CWE-798", "aws-access-token", 1, "commit:abc123")
    assert FAKE_AWS_KEY not in f.model_dump_json()


def test_parse_gitleaks_masks_unredacted_value():
    [f] = parse_gitleaks([{"RuleID": "r", "File": "a", "Secret": FAKE_AWS_KEY}], REPO)
    assert f.masked_snippet == mask_secret(FAKE_AWS_KEY)
    assert FAKE_AWS_KEY not in f.model_dump_json()


def test_parse_trufflehog_masks_secret():
    item = {"DetectorName": "AWS", "Raw": FAKE_AWS_KEY,
            "SourceMetadata": {"Data": {"Git": {"file": "a.py", "line": 3, "commit": "c1"}}}}
    [f] = parse_trufflehog([item], REPO)
    assert f.masked_snippet == mask_secret(FAKE_AWS_KEY) and f.line == 3
    assert FAKE_AWS_KEY not in f.model_dump_json()


def test_parse_osv():
    doc = {"results": [{"source": {"path": "/repo/pom.xml"}, "packages": [{
        "package": {"name": "log4j-core", "version": "2.14.1", "ecosystem": "Maven"},
        "vulnerabilities": [{"id": "GHSA-jfh8-c2jp-5v3q", "aliases": ["CVE-2021-44228"], "summary": "RCE",
                             "database_specific": {"severity": "CRITICAL", "cwe_ids": ["CWE-502"]}}]}]}]}
    [f] = parse_osv(doc, REPO)
    assert (f.category, f.cwe, f.severity_tool) == (Category.V5, "CWE-502", "CRITICAL")
    assert "log4j-core@2.14.1" in f.sink and "CVE-2021-44228" in f.message


def test_parse_npm_audit_ignores_transitive_names():
    doc = {"vulnerabilities": {
        "lodash": {"range": "<4.17.21", "via": [{"source": 1, "title": "Prototype Pollution",
                                                   "severity": "high", "cwe": ["CWE-1321"]}]},
        "express": {"via": ["lodash"]}}}
    [f] = parse_npm_audit(doc, "package-lock.json")
    assert (f.cwe, f.severity_tool, f.category) == ("CWE-1321", "high", Category.V5)


def test_parse_pip_audit():
    doc = {"dependencies": [
        {"name": "requests", "version": "2.19.0", "vulns": [
            {"id": "PYSEC-2018-28", "fix_versions": ["2.20.0"], "aliases": ["CVE-2018-18074"], "description": "leak"}]},
        {"name": "flask", "version": "1.0", "vulns": []}]}
    [f] = parse_pip_audit(doc, "requirements.txt")
    assert f.sink == "requests==2.19.0" and "2.20.0" in f.message


def test_parse_actionlint_and_zizmor():
    [a] = parse_actionlint([{"message": "bad", "filepath": ".github/workflows/ci.yml", "line": 7,
                             "kind": "expression"}], REPO)
    assert (a.rule_id, a.line) == ("actionlint:expression", 7)
    z = {"ident": "dangerous-triggers", "desc": "pull_request_target", "determinations": {"severity": "High"},
         "locations": [{"symbolic": {"key": {"Local": {"given_path": ".github/workflows/ci.yml"}}},
                        "concrete": {"location": {"start_point": {"row": 0, "column": 4}}}}]}
    [f] = parse_zizmor([z], REPO)
    assert (f.rule_id, f.line, f.severity_tool, f.file_path) == (
        "zizmor:dangerous-triggers", 1, "High", ".github/workflows/ci.yml")


def test_parse_sarif_maps_cwe_to_category_and_flow():
    def step(line):
        return {"location": {"physicalLocation": {"artifactLocation": {"uri": "app.py"},
                                                   "region": {"startLine": line}}}}

    doc = {"runs": [{"tool": {"driver": {"semanticVersion": "2.17.0", "rules": [
        {"id": "py/sql-injection", "properties": {"tags": ["external/cwe/cwe-089"], "security-severity": "8.8"}},
        {"id": "py/unrelated", "properties": {"tags": ["maintainability"]}}]}},
        "results": [
            {"ruleId": "py/sql-injection", "message": {"text": "bad"},
             "locations": [step(20)["location"]],
             "codeFlows": [{"threadFlows": [{"locations": [step(18), step(20)]}]}]},
            {"ruleId": "py/unrelated", "locations": [{}]}]}]}
    [f], version = parse_sarif(doc, REPO)
    assert (f.category, f.cwe, f.source, f.sink, f.severity_tool) == (
        Category.V2, "CWE-89", "app.py:18", "app.py:20", "8.8")
    assert version == "2.17.0"


# ---- failure handling ---------------------------------------------------------------------------
@dataclass
class FakeTool(BaseTool):
    name: str = "fake"
    binary: str | None = sys.executable
    mode: str = "ok"
    default_timeout_s: float = 0.5

    async def scan(self, ctx, exe):
        if self.mode == "timeout":
            await run_command([exe, "-c", "import time; time.sleep(30)"], cwd=ctx.work_dir, timeout=self.timeout_s)
        if self.mode == "exit":
            await run_command([exe, "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"],
                              cwd=ctx.work_dir, timeout=10)
        if self.mode == "garbage":
            res = await run_command([exe, "-c", "print('not json')"], cwd=ctx.work_dir, timeout=10)
            json.loads(res.stdout)
        if self.mode == "na":
            raise NotApplicable("no lockfile")
        return ScanOutput([], "raw", 0)


def _run_fake(tmp_path, **kw):
    (tmp_path / "work").mkdir(exist_ok=True)
    return run(FakeTool(**kw).run(ctx_for(tmp_path)))


@pytest.mark.parametrize("kw,status,reason_part", [
    ({"mode": "ok"}, RunStatus.SUCCEEDED, None),
    ({"binary": "definitely-not-installed-xyz"}, RunStatus.UNAVAILABLE, "binary_not_found"),
    ({"mode": "timeout"}, RunStatus.TIMED_OUT, "exceeded"),
    ({"mode": "exit"}, RunStatus.FAILED, "exit code 3"),
    ({"mode": "garbage"}, RunStatus.FAILED, "JSONDecodeError"),
    ({"mode": "na"}, RunStatus.NOT_APPLICABLE, "no lockfile"),
])
def test_run_records_outcome(tmp_path, kw, status, reason_part):
    findings, rec = _run_fake(tmp_path, **kw)
    assert rec.status is status
    assert findings == []
    if reason_part:
        assert reason_part in rec.reason


def test_unsupported_language_is_not_applicable(tmp_path):
    (tmp_path / "work").mkdir()
    _, rec = run(FakeTool(languages=frozenset({"java"})).run(ctx_for(tmp_path, ("python",))))
    assert rec.status is RunStatus.NOT_APPLICABLE


@pytest.mark.parametrize("tool", default_tools(), ids=lambda t: t.name)
def test_every_real_adapter_reports_unavailable_when_binary_missing(tool, tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    (tmp_path / "work").mkdir()
    findings, rec = run(tool.run(ctx_for(tmp_path, ("python", "java", "javascript", "typescript"))))
    if tool.binary:
        assert rec.status is RunStatus.UNAVAILABLE and rec.reason == "binary_not_found"
    assert findings == []


def test_failed_tool_makes_scan_incomplete_not_clean(tmp_path):
    (tmp_path / "work").mkdir()
    ctx = ctx_for(tmp_path)
    runs = [run(FakeTool(name="ok").run(ctx))[1], run(FakeTool(name="bad", mode="timeout").run(ctx))[1]]
    result = ScanResult(run_id="x", repo_path=str(tmp_path), runs=runs)
    assert result.findings == [] and result.complete is False


def test_run_all_rejects_bad_paths(tmp_path):
    with pytest.raises(InvalidRepoPath):
        run(run_all(tmp_path / "nope"))
    with pytest.raises(InvalidRepoPath):
        run(run_all(tmp_path, scan_dir=tmp_path / "out"))


def test_run_all_with_config_scan_only(make_repo, tmp_path):
    repo = make_repo("vuln_py_repo")
    result = run(run_all(repo, tools=[ConfigScanTool()], scan_dir=tmp_path / "scans"))
    assert result.complete and result.findings
    assert Path(result.runs[0].raw_output_ref).exists()
    assert result.runs[0].tool_version == "builtin"


def test_weak_hashing_cwe_maps_to_v3_not_v4():
    doc = {"runs": [{"tool": {"driver": {"rules": [
        {"id": "py/weak-sensitive-data-hashing", "properties": {"tags": ["external/cwe/cwe-327"]}}]}},
        "results": [{"ruleId": "py/weak-sensitive-data-hashing", "locations": [{}]}]}]}
    [f], _ = parse_sarif(doc, REPO)
    assert f.category is Category.V3


def test_custom_query_tag_sets_category_v1():
    doc = {"runs": [{"tool": {"driver": {"rules": [
        {"id": "security-assistant/py/missing-ownership-check",
         "properties": {"tags": ["security", "external/cwe/cwe-639", "external/security-assistant/V1"]}}]}},
        "results": [{"ruleId": "security-assistant/py/missing-ownership-check", "locations": [{}]}]}]}
    [f], _ = parse_sarif(doc, REPO)
    assert (f.category, f.cwe) == (Category.V1, "CWE-639")


@dataclass
class _Probe(BaseTool):
    """Records how many probes are running at the same time."""
    binary: str | None = None
    state: dict | None = None

    async def scan(self, ctx, exe):
        self.state["now"] += 1
        self.state["peak"] = max(self.state["peak"], self.state["now"])
        await asyncio.sleep(0.05)
        self.state["now"] -= 1
        return ScanOutput([], "x", 0)


@pytest.mark.parametrize("limit,expected_peak", [(1, 1), (3, 3)])
def test_run_all_respects_max_parallel(tmp_path, limit, expected_peak):
    repo = tmp_path / "r"
    repo.mkdir()
    state = {"now": 0, "peak": 0}
    tools = [_Probe(name=f"p{i}", state=state) for i in range(3)]
    result = run(run_all(repo, tools=tools, scan_dir=tmp_path / "s", max_parallel=limit))
    assert state["peak"] == expected_peak
    assert [r.tool for r in result.runs] == ["p0", "p1", "p2"]


def test_run_all_is_sequential_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("SECURITY_ASSISTANT_MAX_PARALLEL", raising=False)
    repo = tmp_path / "r"
    repo.mkdir()
    state = {"now": 0, "peak": 0}
    run(run_all(repo, tools=[_Probe(name=f"p{i}", state=state) for i in range(3)], scan_dir=tmp_path / "s"))
    assert state["peak"] == 1
