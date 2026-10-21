"""Names from the git history are learned as known names, so an unlabelled name in a comment is redacted everywhere."""

import asyncio
import json
import os
import subprocess
import sys

import pytest

from app.agents.security_assistant import assess, questions
from app.agents.security_assistant.interpreter.evidence import build_bundle
from app.agents.security_assistant.interpreter.prompts import build_prompt
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.report import build_report, render_markdown, to_json
from app.agents.security_assistant.schemas import Category, Finding, ScanResult

AUTHOR, COMMITTER = "Priya Natarajan", "Kasun Perera"
CODE = '''import hashlib


def login(password):
    # ask Priya about this before changing the hash, Natarajan wrote it
    # (Kasun Perera reviewed it in the lab)
    return hashlib.md5(password.encode()).hexdigest()
'''


def git(repo, *args, author=AUTHOR, committer=None):
    env = {**os.environ, "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": "a@b.org",
           "GIT_COMMITTER_NAME": committer or author, "GIT_COMMITTER_EMAIL": "a@b.org"}
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "student"
    r.mkdir()
    git(r, "init", "-q")
    (r / "app.py").write_text(CODE, encoding="utf-8")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "login", author=AUTHOR, committer=COMMITTER)
    (r / "notes.txt").write_text("x\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "bump", author="dependabot[bot]")
    (r / "more.txt").write_text("y\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "more", author="demo")
    return r


FINDING = Finding(category=Category.V3, rule_id="cfg-005", tool="config-scan", file_path="app.py", line=6, message="md5 password hash")


def test_author_and_committer_names_are_learned_but_generic_identities_are_not(repo):
    pii = PIIRedactor()
    assert pii.learn_git_names(repo) >= 2
    assert pii.redact_plain("thanks Priya") != "thanks Priya" and pii.redact_plain("Natarajan") != "Natarajan"
    assert "Kasun" not in pii.redact_plain("with Kasun Perera")
    for generic in ("demo", "dependabot"):
        assert pii.redact_plain(f"the {generic} account") == f"the {generic} account"  # not treated as a person
    assert PIIRedactor.from_env(repo).redact_plain("Priya") != "Priya"


def test_no_git_history_means_nothing_is_learned(tmp_path):
    (tmp_path / "app.py").write_text(CODE, encoding="utf-8")
    pii = PIIRedactor()
    assert pii.learn_git_names(tmp_path) == 0 and pii.learn_git_names(tmp_path / "missing") == 0
    assert "Priya" in pii.redact_code(CODE)  # the documented limitation: a name that is nowhere known stays


def test_an_unlabelled_name_in_a_comment_is_replaced_in_the_evidence_and_the_prompt(repo):
    pii = PIIRedactor.from_env(repo)
    bundle = build_bundle(FINDING, repo, pii=pii)
    system, user = build_prompt(FINDING, bundle, pii)
    for text in (user, "\n".join(i.content for i in bundle.items)):
        for name in ("Priya", "Natarajan", "Kasun", "Perera"):
            assert name not in text, name
    assert "<NAME_" in user and "hashlib.md5" in user  # the code itself is still there
    assert any(v in (AUTHOR, "Priya", "Natarajan") or "Priya" in v for v in pii.mapping.values())  # kept locally


def test_the_mapping_is_local_and_never_in_the_prompt(repo, tmp_path):
    pii = PIIRedactor.from_env(repo)
    _system, user = build_prompt(FINDING, build_bundle(FINDING, repo, pii=pii), pii)
    saved = pii.save_mapping(tmp_path / "pii_mapping.local.json")
    assert "Priya" in saved.read_text(encoding="utf-8") and "Priya" not in user


def test_report_snippets_and_probe_questions_use_the_learned_names(repo):
    md = render_markdown(build_report(ScanResult(run_id="r", repo_path=str(repo), findings=[FINDING]), repo=repo))
    assert "hashlib.md5" in md and "Priya" not in md and "Natarajan" not in md and "Kasun" not in md
    group = {"group_id": "G01", "package": None, "representative": {
        "finding_key": "k", "category": "V3", "file_path": "app.py", "line": 6, "fix_pattern": "weak-password-hash"}}
    q = questions.build_question(group, repo)
    assert "Priya" not in q.code and "Natarajan" not in q.code and "Kasun" not in q.code


class Spy:
    model = "spy"
    temperature = 0.0

    def __init__(self):
        self.prompts = []

    async def complete(self, system, user, schema=None, schema_name="verdict"):
        self.prompts.append(user)
        return json.dumps({"status": "confirmed", "rationale": "ok", "evidence_ids": ["E1"], "confidence": 0.8, "recommendation": ""})


def test_assess_never_sends_or_writes_a_git_author_name(repo, tmp_path):
    result = ScanResult(run_id="r", repo_path=str(repo), findings=[FINDING])
    saved = tmp_path / "findings.json"
    saved.write_text(to_json(build_report(result)), encoding="utf-8")
    spy = Spy()
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        report = loop.run_until_complete(assess.run_pipeline(
            str(repo), reuse_scan=saved, out_dir=tmp_path / "out", allow_external_llm=True, client=spy))
    finally:
        loop.close()
    assert spy.prompts and report["findings"]
    everything = "\n".join(spy.prompts)
    for path in (tmp_path / "out").iterdir():
        if not path.name.endswith(".local.json"):
            everything += path.read_text(encoding="utf-8")
    for name in ("Priya", "Natarajan", "Kasun", "Perera"):
        assert name not in everything, name
