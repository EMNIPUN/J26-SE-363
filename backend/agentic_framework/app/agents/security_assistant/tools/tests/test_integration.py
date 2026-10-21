"""Run the real scanners on the seeded repos. Skipped per tool when its binary is not installed
(use the image from Dockerfile.tools to run them all)."""

import shutil

import pytest

from app.agents.security_assistant.schemas import Category, RunStatus
from app.agents.security_assistant.tools.runner import run_all
from app.agents.security_assistant.tools.tests.conftest import FAKE_AWS_KEY, FAKE_AWS_SECRET
from app.agents.security_assistant.tools.tests.test_tools import run
from app.agents.security_assistant.tools.secret_scanners import GitleaksTool, TruffleHogTool
from app.agents.security_assistant.tools.dependencies import OsvScannerTool
from app.agents.security_assistant.tools.workflow_lint import ZizmorTool

pytestmark = pytest.mark.integration


def _scan(make_repo, tmp_path, tool, fixture, **kw):
    repo = make_repo(fixture, **kw)
    result = run(run_all(repo, tools=[tool], scan_dir=tmp_path / "scans"))
    assert result.runs[0].status is RunStatus.SUCCEEDED, result.runs[0].reason
    return result


@pytest.mark.skipif(not shutil.which("gitleaks"), reason="gitleaks not installed")
def test_gitleaks_finds_secret_removed_from_history(make_repo, tmp_path):
    result = _scan(make_repo, tmp_path, GitleaksTool(), "vuln_py_repo", with_secret=True)
    assert any(f.category is Category.V4 and f.file_path == "settings_old.py" for f in result.findings)
    raw = open(result.runs[0].raw_output_ref, encoding="utf-8").read()
    assert FAKE_AWS_KEY not in raw and FAKE_AWS_KEY not in result.model_dump_json()


@pytest.mark.skipif(not shutil.which("trufflehog"), reason="trufflehog not installed")
def test_trufflehog_finds_secret_and_masks_it(make_repo, tmp_path):
    result = _scan(make_repo, tmp_path, TruffleHogTool(), "vuln_py_repo", with_secret=True)
    assert result.findings
    raw = open(result.runs[0].raw_output_ref, encoding="utf-8").read()
    for secret in (FAKE_AWS_KEY, FAKE_AWS_SECRET):
        assert secret not in raw and secret not in result.model_dump_json()


@pytest.mark.skipif(not shutil.which("osv-scanner"), reason="osv-scanner not installed")
def test_osv_finds_vulnerable_dependency(make_repo, tmp_path):
    result = _scan(make_repo, tmp_path, OsvScannerTool(), "vuln_java_repo")
    assert any(f.category is Category.V5 and "log4j" in (f.sink or "") for f in result.findings)


@pytest.mark.skipif(not shutil.which("zizmor"), reason="zizmor not installed")
def test_zizmor_flags_pull_request_target(make_repo, tmp_path):
    result = _scan(make_repo, tmp_path, ZizmorTool(), "vuln_js_repo")
    rules = {f.rule_id for f in result.findings}
    assert {"zizmor:dangerous-triggers", "zizmor:excessive-permissions", "zizmor:unpinned-uses"} <= rules
    assert all(f.category is Category.V5 for f in result.findings)


# ---- CodeQL: custom V1 (missing ownership check) queries ----------------------------------------------
from app.agents.security_assistant.tools.codeql import CodeQLTool

SAFE_REPOS = {
    "python": ("app.py", '''from flask import Flask
from flask_login import current_user
import sqlite3
app = Flask(__name__)

@app.route("/orders/<order_id>")
def orders(order_id):
    db = sqlite3.connect("shop.db")
    db.execute("SELECT * FROM orders WHERE id = " + order_id + " AND owner = " + str(current_user.id))
'''),
    "java": ("src/main/java/demo/C.java", '''package demo;
import java.security.Principal;
import java.sql.Statement;
import org.springframework.web.bind.annotation.*;
@RestController
public class C {
    @GetMapping("/orders/{id}")
    public String orders(@PathVariable String id, Principal principal, Statement st) throws Exception {
        st.executeQuery("SELECT * FROM orders WHERE id = " + id + " AND owner = '" + principal.getName() + "'");
        return "ok";
    }
}
'''),
    "javascript": ("server.js", '''const express = require('express')
const app = express()
app.get('/orders/:id', authenticate, (req, res) => {
  db.query('SELECT * FROM orders WHERE id = ' + req.params.id)
})
app.get('/mine/:id', (req, res) => {
  db.query('SELECT * FROM orders WHERE id = ' + req.params.id + ' AND owner = ' + req.user.id)
})
'''),
}


def _codeql(repo, tmp_path):
    result = run(run_all(repo, tools=[CodeQLTool()], scan_dir=tmp_path / "scans"))
    assert result.runs[0].status is RunStatus.SUCCEEDED, result.runs[0].reason
    return result


@pytest.mark.skipif(not shutil.which("codeql"), reason="codeql not installed")
@pytest.mark.parametrize("fixture,rule", [
    ("vuln_py_repo", "security-assistant/py/missing-ownership-check"),
    ("vuln_java_repo", "security-assistant/java/missing-ownership-check"),
    ("vuln_java_gradle_repo", "security-assistant/java/missing-ownership-check"),
    ("vuln_js_repo", "security-assistant/js/missing-ownership-check"),
])
def test_codeql_reports_v1_on_seeded_repo(make_repo, tmp_path, fixture, rule):
    result = _codeql(make_repo(fixture), tmp_path)
    assert any(f.rule_id == rule and f.category is Category.V1 for f in result.findings)


@pytest.mark.skipif(not shutil.which("codeql"), reason="codeql not installed")
@pytest.mark.parametrize("lang", sorted(SAFE_REPOS))
def test_codeql_no_v1_when_handler_checks_the_user(tmp_path, lang):
    name, text = SAFE_REPOS[lang]
    repo = tmp_path / "safe"
    (repo / name).parent.mkdir(parents=True)
    (repo / name).write_text(text)
    result = _codeql(repo, tmp_path)
    assert not [f for f in result.findings if f.category is Category.V1], result.findings
