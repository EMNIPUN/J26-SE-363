"""Findings viewer: table, report.md, findings.json, coverage and --skip. Uses a saved findings JSON (CodeQL style
findings included); no scanner and no network is started."""

import asyncio
import json
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from app.agents.security_assistant import scan as scan_module
from app.agents.security_assistant.report import (
    build_report, coverage, from_json, render_console, render_markdown, to_json, write_report,
)
from app.agents.security_assistant.schemas import Category, RunStatus
from app.agents.security_assistant.tools.tests.demo_repos import make_demo_repos
from app.agents.security_assistant.tools.tests.conftest import FIXTURES

SAVED = Path(__file__).parent / "saved" / "python_full.json"
REPO = FIXTURES / "vuln_py_repo"


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def load(skip=(), mutate=None):
    """The saved scan; `skip` removes those tools' runs and findings, as a scan with --skip would."""
    doc = json.loads(SAVED.read_text(encoding="utf-8"))
    doc["runs"] = [r for r in doc["runs"] if r["tool"] not in skip]
    doc["findings"] = [f for f in doc["findings"] if f["tool"] not in skip]
    doc["scan"]["skipped_tools"] = sorted(skip)
    if mutate:
        mutate(doc)
    return doc


def report_for(doc, repo=REPO):
    result, skipped = from_json(json.dumps(doc))
    return build_report(result, skipped=skipped, source="vuln_py_repo", repo=repo)


# ---- coverage ------------------------------------------------------------------------------------------------------
def test_full_scan_covers_every_category():
    cov = report_for(load()).coverage
    assert {c: v.level for c, v in cov.items()} == {c: "FULL" for c in Category}


def test_skipping_codeql_leaves_v2_and_v1_uncovered_and_v3_reduced():
    cov = report_for(load(skip=("codeql",))).coverage
    assert cov[Category.V2].level == "NONE" and "codeql (skipped)" in cov[Category.V2].note
    assert cov[Category.V1].level == "NONE" and "partial: config-scan" in cov[Category.V1].note
    assert cov[Category.V3].level == "REDUCED"
    assert cov[Category.V4].level == "FULL" and cov[Category.V5].level == "FULL"


def test_a_failed_tool_reduces_coverage_and_makes_the_scan_incomplete():
    def fail_trufflehog(doc):
        next(r for r in doc["runs"] if r["tool"] == "trufflehog").update(status="timed_out", reason="exceeded 300s")
        doc["findings"] = [f for f in doc["findings"] if f["tool"] != "trufflehog"]

    rep = report_for(load(mutate=fail_trufflehog))
    assert rep.coverage[Category.V4].level == "REDUCED" and not rep.complete
    text = render_console(rep)
    assert "RESULT: INCOMPLETE" in text and "trufflehog (timed_out)" in text and "do NOT mean the project is clean" in text


def test_not_applicable_tools_do_not_lower_coverage():
    rep = report_for(load())
    assert rep.coverage[Category.V5].tools["npm-audit"] == "not applicable" and rep.coverage[Category.V5].level == "FULL"


def test_category_with_nothing_to_scan():
    doc = load()
    for r in doc["runs"]:
        if r["tool"] in ("osv-scanner", "npm-audit", "pip-audit", "actionlint", "zizmor"):
            r["status"] = "not_applicable"
    assert report_for(doc).coverage[Category.V5].level == "NOTHING TO SCAN"


# ---- console -------------------------------------------------------------------------------------------------------------
def test_console_shows_tools_findings_and_result():
    text = render_console(report_for(load()))
    for expected in ("TOOLS", "COVERAGE", "FINDINGS: 12 total", "py/sql-injection", "app.py:22", "CWE-89",
                     "zizmor:unpinned-uses", ".github/workflows/ci.yml:6", "npm-audit", "not_applicable",
                     "RESULT: COMPLETE for the tools that ran"):
        assert expected in text, expected


def test_console_names_skipped_tools_and_the_categories_they_leave_uncovered():
    text = render_console(report_for(load(skip=("codeql",))))
    assert "SKIPPED" in text and "skipped with --skip" in text
    assert "SKIPPED with --skip: codeql." in text and "V2 NONE" in text and "V1 NONE" in text and "V3 REDUCED" in text


def test_console_row_limit():
    text = render_console(report_for(load()), max_rows=3)
    assert "... 9 more in report.md / findings.json" in text


# ---- report.md and findings.json ---------------------------------------------------------------------------------------
def test_markdown_groups_by_category_with_all_fields_and_snippets():
    md = render_markdown(report_for(load()))
    for header in ("## V1 Broken access control (1)", "## V2 Injection (1)", "## V3 Authentication failures (4)",
                   "## V4 Sensitive data exposure / hard-coded secrets (2)", "## V5 Vulnerable dependencies and insecure CI/CD (4)"):
        assert header in md
    assert "`py/sql-injection` - app.py:22" in md and "**CWE:** CWE-89" in md and "**Severity (from tool):** 8.8" in md
    assert "**Source -> sink:** app.py:21 -> app.py:22" in md and "in `orders`" in md
    assert '>   22 | ' in md and "db.execute(" in md  # snippet around the finding, finding line marked
    assert "| codeql | succeeded | 2 |" in md and "| npm-audit | not_applicable | 0 |" in md


def test_markdown_flags_uncovered_categories_when_tools_are_skipped():
    md = render_markdown(report_for(load(skip=("codeql",))))
    assert "> Coverage NONE:" in md and "| codeql | **skipped** |" in md
    assert "## V2 Injection (0)" in md and "No findings." in md


def test_a_secret_findings_line_is_never_shown_and_a_missing_file_is_fine():
    rep = report_for(load())
    v4 = [i for i, f in enumerate(rep.findings) if f.category is Category.V4]
    assert all(i not in rep.snippets for i in v4)  # settings_old.py is not in the fixture folder: no snippet, no crash
    # a V4 finding that does point at a real line must hide that line
    doc = load()
    doc["findings"].append({"category": "V4", "tool": "gitleaks", "rule_id": "generic-api-key", "file_path": "app.py", "line": 14,
                            "message": "Detected a Generic API Key"})
    snippet = report_for(doc).snippets[len(doc["findings"]) - 1]
    lines = snippet.split("\n")
    assert any(l.startswith(">") and "<line hidden: it holds the secret>" in l for l in lines)  # the finding line is hidden
    assert "jwt.encode" not in snippet
    assert "return token" in snippet  # the neighbouring lines are still shown


def test_secrets_are_masked_in_every_output(tmp_path):
    secret = "hunter2hunter2"
    aws = "AKIA" + "QYLPMN5HHHFPZAM2"

    def plant(doc):
        doc["findings"][2]["message"] = f'config has password = "{secret}"'
        doc["findings"][6]["masked_snippet"] = aws
        doc["findings"][6]["message"] = f"key {aws} found"

    rep = report_for(load(mutate=plant))
    json_path, md_path = write_report(rep, tmp_path / "out")
    everything = json_path.read_text(encoding="utf-8") + md_path.read_text(encoding="utf-8") + render_console(rep)
    assert secret not in everything and aws not in everything and "[REDACTED" in everything


def test_findings_json_round_trips_and_keeps_the_coverage(tmp_path):
    rep = report_for(load(skip=("codeql",)))
    json_path, _ = write_report(rep, tmp_path)
    doc = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(doc["findings"]) == 10 and doc["scan"]["skipped_tools"] == ["codeql"]
    assert doc["coverage"]["V2"]["level"] == "NONE" and doc["coverage"]["V4"]["level"] == "FULL"
    result, skipped = from_json(json_path.read_text(encoding="utf-8"))
    assert skipped == ["codeql"] and len(result.findings) == 10 and len(result.runs) == 8


def test_snippets_never_read_outside_the_scanned_folder(tmp_path):
    doc = load()
    doc["findings"][0]["file_path"] = "../../../../etc/hosts"
    assert 0 not in report_for(doc, repo=REPO).snippets


# ---- the command ------------------------------------------------------------------------------------------------------------
def test_parse_skip():
    assert scan_module.parse_skip(["codeql,zizmor", "gitleaks"]) == ["codeql", "gitleaks", "zizmor"]
    assert scan_module.parse_skip(None) == []
    with pytest.raises(ValueError, match="unknown tool"):
        scan_module.parse_skip(["codeqll"])


def test_command_renders_a_saved_findings_json(tmp_path, capsys):
    out = tmp_path / "rendered"
    code = run(scan_module.main(["--from-json", str(SAVED), str(REPO), "--out", str(out)]))
    printed = capsys.readouterr().out
    assert code == 0 and "FINDINGS: 12 total" in printed and f"Wrote {out / 'findings.json'}" in printed
    assert (out / "report.md").read_text(encoding="utf-8").count("### V") == 12


def test_command_exit_code_is_2_when_a_tool_failed(tmp_path):
    doc = load(mutate=lambda d: next(r for r in d["runs"] if r["tool"] == "gitleaks").update(status="unavailable", reason="binary_not_found"))
    saved = tmp_path / "failed.json"
    saved.write_text(json.dumps(doc), encoding="utf-8")
    assert run(scan_module.main(["--from-json", str(saved), "--out", str(tmp_path / "o")])) == 2


def test_scan_a_local_folder_with_everything_but_config_scan_skipped(tmp_path):
    others = [n for n in scan_module.tool_names() if n != "config-scan"]
    text, code = run(scan_module.scan(str(REPO), skip=others, out_dir=tmp_path / "o"))
    assert code == 0
    assert "SKIPPED with --skip:" in text and "codeql" in text and "V2 NONE" in text
    assert "security-assistant-cfg-005" in text and "app.py:13" in text
    md = (tmp_path / "o" / "report.md").read_text(encoding="utf-8")
    assert "hashlib.md5" in md  # snippet from the scanned folder
    assert (tmp_path / "o" / "findings.json").exists()


def test_scan_a_url_uses_fetch_repo_and_reads_snippets_before_it_is_deleted(tmp_path, monkeypatch):
    seen = {}

    @asynccontextmanager
    async def fake_fetch(url, sha=None, **kw):
        work = tmp_path / "clone"
        shutil.copytree(REPO, work)
        seen.update(url=url, sha=sha)
        try:
            yield work
        finally:
            shutil.rmtree(work)  # like the real fetch_repo: gone when the block ends

    monkeypatch.setattr(scan_module, "fetch_repo", fake_fetch)
    others = [n for n in scan_module.tool_names() if n != "config-scan"]
    text, code = run(scan_module.scan("https://github.com/o/r", skip=others, ref="a" * 40, out_dir=tmp_path / "o"))
    assert code == 0 and seen == {"url": "https://github.com/o/r", "sha": "a" * 40}
    assert "hashlib.md5" in (tmp_path / "o" / "report.md").read_text(encoding="utf-8")
    assert not (tmp_path / "clone").exists()


def test_scan_rejects_a_non_github_url_and_a_missing_folder(tmp_path):
    text, code = run(scan_module.scan("https://gitlab.com/o/r", skip=[], out_dir=tmp_path / "o"))
    assert code == 3 and "cannot scan" in text and not (tmp_path / "o").exists()
    text, code = run(scan_module.scan(str(tmp_path / "missing"), skip=[], out_dir=tmp_path / "o"))
    assert code == 3 and "not a directory" in text


def test_unknown_skip_name_is_a_usage_error(capsys):
    assert run(scan_module.main([str(REPO), "--skip", "nope"])) == 3
    assert "unknown tool" in capsys.readouterr().err


# ---- demo copies of the fixtures --------------------------------------------------------------------------------------------
def test_demo_repos_hide_a_deleted_secret_in_the_git_history(tmp_path):
    import subprocess
    repos = make_demo_repos(tmp_path)
    assert {r.name for r in repos} == {"vuln_py_repo", "vuln_js_repo", "vuln_java_repo", "vuln_java_gradle_repo"}
    for repo in repos:
        assert not (repo / "settings_old.py").exists()
        log = subprocess.run(["git", "log", "--all", "--oneline", "--", "settings_old.py"], cwd=repo,
                             capture_output=True, text=True, check=True).stdout.strip().splitlines()
        assert len(log) == 2  # added, then removed
