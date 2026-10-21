"""Java / Spring Boot: config scanning and OSV-Scanner behaviour for Maven and Gradle (no real scanners)."""

import asyncio
import shutil
import sys
from pathlib import Path

import pytest

from app.agents.security_assistant.schemas import Category, RunStatus
from app.agents.security_assistant.tools import dependencies
from app.agents.security_assistant.tools.base import (
    CommandResult, NotApplicable, ScanContext, ToolFailed,
)
from app.agents.security_assistant.tools.config_scan import ConfigScanTool, _seconds, flatten_config
from app.agents.security_assistant.tools.dependencies import OsvScannerTool, gradle_without_lockfile
from app.agents.security_assistant.tools.languages import detect_languages
from app.agents.security_assistant.tools.tests.conftest import FIXTURES

R = "security-assistant-cfg"
OSV_JSON = '{"results": []}'


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _scan_config(repo: Path, tmp_path):
    ctx = ScanContext(repo=repo, work_dir=tmp_path / "w", languages=detect_languages(repo))
    ctx.work_dir.mkdir()
    findings, rec = run(ConfigScanTool().run(ctx))
    assert rec.status is RunStatus.SUCCEEDED
    return findings


# ---- config scanner: Spring Boot ---------------------------------------------------------------------
def test_config_scan_spring_gradle_fixture(tmp_path):
    findings = _scan_config(FIXTURES / "vuln_java_gradle_repo", tmp_path)
    rules = {f.rule_id for f in findings}
    # application.yml (nested keys), password encoder, CSRF, permitAll
    assert {f"{R}-003", f"{R}-004", f"{R}-005", f"{R}-006", f"{R}-008", f"{R}-011", f"{R}-012"} <= rules
    permit_all = [f for f in findings if f.rule_id == f"{R}-008"]
    assert permit_all and permit_all[0].category is Category.V1
    # Spring Security is present here, so the "no Spring Security at all" rule must not fire
    assert f"{R}-013" not in rules


def test_config_scan_spring_maven_fixture_has_no_spring_security(tmp_path):
    findings = _scan_config(FIXTURES / "vuln_java_repo", tmp_path)
    no_security = [f for f in findings if f.rule_id == f"{R}-013"]
    assert no_security and no_security[0].category is Category.V1


def test_flatten_yaml_and_properties(tmp_path):
    flat = flatten_config(tmp_path / "application.yml",
                          "server:\n  servlet:\n    session:\n      timeout: 7d\nlist:\n  - a\n  - b\n")
    assert flat["server.servlet.session.timeout"] == "7d" and flat["list"] == "a,b"
    flat = flatten_config(tmp_path / "application.properties",
                          "# c\nserver.port=8080\nspring.security.user.password: secret\n")
    assert flat == {"server.port": "8080", "spring.security.user.password": "secret"}


@pytest.mark.parametrize("value,expected", [
    ("30m", 1800), ("2h", 7200), ("7d", 604800), ("1800", 1800),
    ("PT30M", 1800), ("P1D", 86400), ("-1", -1), ("soon", None),
])
def test_duration_parsing(value, expected):
    assert _seconds(value) == expected


def test_spring_password_placeholder_is_not_flagged(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "application.properties").write_text("spring.security.user.password=${ADMIN_PASSWORD}\n")
    (repo / "A.java").write_text("class A {}")
    assert not [f for f in _scan_config(repo, tmp_path) if f.rule_id == f"{R}-011"]


# ---- OSV-Scanner: Maven / Gradle behaviour ------------------------------------------------------------
def _osv_ctx(monkeypatch, tmp_path, repo, replies):
    """Replace run_command with canned replies [(exit_code, stdout, stderr), ...]."""
    calls = []

    async def fake(argv, **kw):
        calls.append(argv)
        code, out, err = replies[len(calls) - 1]
        if code not in kw.get("accept_codes", (0,)):
            raise ToolFailed(f"exit code {code}")
        return CommandResult(code, out, err)

    monkeypatch.setattr(dependencies, "run_command", fake)
    return calls, ScanContext(repo=repo, work_dir=tmp_path, languages={"java"})


def test_osv_registry_unreachable_falls_back_to_direct_only(monkeypatch, tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "pom.xml").write_text("<project/>")
    calls, ctx = _osv_ctx(monkeypatch, tmp_path, repo,
                          [(128, "", "Error during extraction: dns"), (0, OSV_JSON, "")])
    out = run(OsvScannerTool().scan(ctx, "osv-scanner"))
    assert "--no-resolve" in calls[1] and "--no-resolve" not in calls[0]
    assert "transitive dependencies NOT resolved" in out.note


def test_osv_other_error_is_a_failure_not_not_applicable(monkeypatch, tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _, ctx = _osv_ctx(monkeypatch, tmp_path, repo, [(128, "", "Error: something else broke")])
    with pytest.raises(ToolFailed):
        run(OsvScannerTool().scan(ctx, "osv-scanner"))


def test_osv_nothing_found_is_not_applicable(monkeypatch, tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _, ctx = _osv_ctx(monkeypatch, tmp_path, repo, [(128, "", "No package sources found")])
    with pytest.raises(NotApplicable):
        run(OsvScannerTool().scan(ctx, "osv-scanner"))


def test_gradle_without_lockfile_is_noted(monkeypatch, tmp_path):
    repo = tmp_path / "g"
    shutil.copytree(FIXTURES / "vuln_java_gradle_repo", repo)
    assert gradle_without_lockfile(repo) is False  # the fixture has a gradle.lockfile
    _, ctx = _osv_ctx(monkeypatch, tmp_path, repo, [(0, OSV_JSON, "")])
    assert run(OsvScannerTool().scan(ctx, "x")).note is None
    (repo / "gradle.lockfile").unlink()
    assert gradle_without_lockfile(repo) is True
    _, ctx = _osv_ctx(monkeypatch, tmp_path, repo, [(0, OSV_JSON, "")])
    assert "Gradle dependencies NOT scanned" in run(OsvScannerTool().scan(ctx, "x")).note
