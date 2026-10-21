"""Probe questions and the mock Tutor. The student's code is a small temporary project; no LLM, scanner or network."""

import asyncio
import json
import re
import sys

import pytest

from app.agents.security_assistant import guidance as guide
from app.agents.security_assistant import questions as q
from app.agents.security_assistant.pii import PIIRedactor

FAKE_KEY = "AKIA" + "QYLPMN5HHHFPZAM2"
PY = f'''import sqlite3
from flask import Flask, request
app = Flask(__name__)
AWS_KEY = "{FAKE_KEY}"

@app.route("/users/<user_id>/orders")
def orders(user_id):
    db = sqlite3.connect("shop.db")
    name = request.args.get("name")
    # contact: Maria Student <maria.student@students.example.org>
    return db.execute("SELECT * FROM orders WHERE user_id = " + user_id + " AND name = '" + name + "'")

def unrelated():
    return 1
'''
JS = '''const express = require('express');
const app = express();
app.get('/users/:id/orders', (req, res) => {
  const id = req.params.id;
  db.query("SELECT * FROM orders WHERE user_id = " + id, (e, rows) => res.json(rows));
});
'''
JAVA = '''public class OrderController {
    @GetMapping("/orders/{id}")
    public Order getOrder(@PathVariable Long id) {
        return repo.findById(id).orElseThrow();
    }
}
'''


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "app.py").write_text(PY, encoding="utf-8")
    (tmp_path / "server.js").write_text(JS, encoding="utf-8")
    (tmp_path / "OrderController.java").write_text(JAVA, encoding="utf-8")
    return tmp_path


def group(gid, file, line, fix, cat="V2", status="confirmed", package=None):
    rep = {"finding_key": f"key{gid}", "category": cat, "tool": "t", "rule_id": "r", "file_path": file, "line": line,
           "fix_pattern": fix, "severity_tool": "high", "cwe": None, "source": None, "sink": None,
           "function_or_endpoint": None, "message": ""}
    return {"group_id": gid, "kind": "single", "package": package, "representative": rep, "members": [rep],
            "result": {"status": status, "confidence": 0.9, "rationale": "r", "evidence_ids": ["E1"]}}


def build(g, repo):
    return q.build_question(g, repo, PIIRedactor())


# ---- built from the student's own code ----------------------------------------------------------------------------------------
def test_python_question_uses_the_enclosing_function_and_its_parameter(repo):
    qu = build(group("G01", "app.py", 10, "sql-injection"), repo)
    assert qu.code_source == "ast" and "`orders`" in qu.text and "`user_id`" in qu.text
    assert "def orders(user_id)" in qu.code and "def unrelated" not in qu.code  # only the one function
    assert ">>   10" in qu.code or ">> 10" in qu.code.replace("  ", " ")


def test_the_question_uses_only_names_from_the_students_code(repo):
    for g in (group("G01", "app.py", 10, "ownership-check", "V1"), group("G02", "app.py", 10, "sql-injection")):
        qu = build(g, repo)
        names = set(re.findall(r"`([^`]+)`", qu.text))
        assert names and all(re.search(rf"\b{re.escape(n)}\b", PY) for n in names), names


def test_javascript_and_java_use_the_enclosing_route_or_method(repo):
    js = build(group("G01", "server.js", 5, "sql-injection"), repo)
    assert js.code_source == "text-search" and "req.params.id" in js.code and "`/users/:id/orders`" in js.text
    java = build(group("G02", "OrderController.java", 4, "ownership-check", "V1"), repo)
    assert java.code_source == "text-search" and "`getOrder`" in java.text and "`id`" in java.text
    assert "findById" in java.code


def test_other_files_use_a_window_and_a_missing_file_uses_metadata_only(repo):
    (repo / "config.yml").write_text("a: 1\nb: 2\ndebug: true\nc: 3\n")
    w = build(group("G01", "config.yml", 3, "debug-and-actuator", "V3"), repo)
    assert w.code_source == "window" and "debug: true" in w.code
    m = build(group("G02", "gone.py", 3, "sql-injection"), repo)
    assert m.code_source == "metadata-only" and m.code == "" and "gone.py:3" in m.text
    assert build(group("G03", "../escape.py", 3, "xss"), repo).code_source == "metadata-only"


# ---- redaction --------------------------------------------------------------------------------------------------------------------
def test_secrets_and_personal_data_are_redacted_in_the_question_and_the_excerpt(repo):
    (repo / "full.py").write_text(PY.replace("def unrelated", "def x"), encoding="utf-8")
    qu = build(group("G01", "full.py", 4, "hardcoded-secret", "V4"), repo)
    shown = qu.text + qu.code
    assert FAKE_KEY not in shown and "maria.student" not in shown
    assert "`AWS_KEY`" in qu.text  # the name of the variable is fine, the value never appears
    big = build(group("G02", "app.py", 10, "sql-injection"), repo)
    assert "maria.student" not in big.code and "Maria" not in big.code


# ---- no fix leaked ------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("fix", sorted({g.id for g in guide.GUIDANCE}))
def test_no_question_template_states_the_fix(fix, repo):
    qu = build(group("G01", "app.py", 10, fix), repo)
    assert q.leaks_fix(qu.text) is None, qu.text


def test_the_guard_catches_wording_that_gives_the_answer():
    for bad in ("You should use parameterized queries.", "Replace it with bcrypt", "move the key to an environment variable",
                "upgrade to 2.31.0", "add an ownership check"):
        assert q.leaks_fix(bad), bad
    assert q.leaks_fix("What does the database receive if the value contains a quote?") is None


# ---- the mock Tutor and the threshold ------------------------------------------------------------------------------------
def test_the_mock_tutor_is_labelled_everywhere(repo, tmp_path):
    doc = {"groups": [group("G01", "app.py", 10, "sql-injection")]}
    out = run(q.generate(doc, repo, q.MockTutor(), 0.7, PIIRedactor()))
    r = out["questions"][0]["tutor_result"]
    assert r["mock"] is True and "MOCK" in r["label"] and out["meta"]["tutor_is_mock"] and "MOCK" in out["meta"]["tutor_label"]
    md = q.render_section(out)
    assert "MOCK TUTOR" in md and "simulated by the mock Tutor" in md
    assert q.MockTutor.mock is True


def test_below_threshold_is_followed_up_then_escalated_and_at_or_above_closes(repo):
    doc = {"groups": [group("G01", "app.py", 10, "sql-injection"), group("G02", "app.py", 7, "ownership-check", "V1"),
                      group("G03", "app.py", 10, "sql-injection", status="dismissed")]}
    tutor = q.MockTutor(scores={"keyG01": 0.69, "keyG02": 0.70})
    out = run(q.generate(doc, repo, tutor, 0.7, PIIRedactor()))
    assert [(i["question"]["group_id"], i["decision"]) for i in out["questions"]] == [("G01", "escalated"), ("G02", "closed")]
    assert out["summary"]["questions"] == 2 and out["summary"]["closed"] == 1 and out["summary"]["escalated"] == 1  # none for the dismissed one
    assert [len(i["attempts"]) for i in out["questions"]] == [3, 1]  # G01: the question and two follow-ups; G02 closed at once
    for i in out["questions"]:  # score, threshold and decision are logged for every attempt
        assert {"score", "mock", "label"} <= set(i["tutor_result"]) and i["threshold"] == 0.7
    assert q.decide(0.7, 0.7) == "closed" and q.decide(0.6999, 0.7) == "open"


def test_the_threshold_is_configurable(repo, monkeypatch):
    assert q.threshold_from_env() == 0.7
    monkeypatch.setenv("SECURITY_ASSISTANT_COMPREHENSION_THRESHOLD", "0.9")
    assert q.threshold_from_env() == 0.9
    monkeypatch.setenv("SECURITY_ASSISTANT_COMPREHENSION_THRESHOLD", "7")
    assert q.threshold_from_env() == 0.7


def test_mock_scores_are_deterministic_and_in_range(repo):
    t = q.MockTutor()
    first = run(t.ask(build(group("G01", "app.py", 10, "sql-injection"), repo)))
    again = run(t.ask(build(group("G01", "app.py", 10, "sql-injection"), repo)))
    assert first.score == again.score and 0.3 <= first.score <= 0.95


# ---- the command -----------------------------------------------------------------------------------------------------------------
def test_the_command_writes_questions_json_and_a_report_section(repo, tmp_path, capsys):
    p = tmp_path / "interpreted.json"
    p.write_text(json.dumps({"groups": [group("G01", "app.py", 10, "sql-injection")]}), encoding="utf-8")
    (tmp_path / "report.md").write_text("# scan\n", encoding="utf-8")
    assert run(q.main([str(p), str(repo), "--threshold", "0.5"], tutor=q.MockTutor(default=0.5))) == 0
    data = json.loads((tmp_path / "questions.json").read_text(encoding="utf-8"))
    assert data["questions"][0]["decision"] == "closed" and data["meta"]["threshold"] == 0.5
    md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "## Probe questions" in md and "MOCK TUTOR" in md and md.startswith("# scan")
    assert run(q.main([str(p), str(repo)], tutor=q.MockTutor())) == 0
    assert (tmp_path / "report.md").read_text(encoding="utf-8").count("## Probe questions") == 1
    assert run(q.main([str(tmp_path / "nope.json"), str(repo)])) == 3
