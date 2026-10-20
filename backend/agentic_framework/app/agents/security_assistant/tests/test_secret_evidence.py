"""Evidence for V4 findings: masked value, kind and length, current files or history, introducing commit (PII redacted).
Fast tests on tiny local git repositories; no scanner and no LLM."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from app.agents.security_assistant import interpret as flow
from app.agents.security_assistant.interpreter import evidence as evidence_module
from app.agents.security_assistant.interpreter.evidence import build_bundle
from app.agents.security_assistant.interpreter.llm import TEMPERATURE, GroqClient
from app.agents.security_assistant.interpreter.prompts import build_prompt
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.schemas import Category, Finding

AWS_KEY = "AKIA" + "QYLPMN5HHHFPZAM2"
AWS_SECRET = "Zk9xQ2v7Lm4Rt8Yp1Nc6Wd3Hs5Jb0Ga2Ue" + "+Ff7Xi"
EMAIL, STUDENT = "kasun.perera@students.example.edu", "IT21234567"


class Src:
    """A repository folder plus the sha of the commit that introduced the secret."""

    def __init__(self, path, sha):
        self.path, self.sha = path, sha

    def __fspath__(self):
        return str(self.path)

    __str__ = __fspath__


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=demo", "-c", "user.email=demo@example.com", *args], cwd=repo,
                          check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """settings_old.py with a key pair is added in one commit and deleted in the next: it exists only in the history."""
    git(tmp_path, "init", "-q")
    (tmp_path / "app.py").write_text("print('hello')\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "first commit")
    (tmp_path / "settings_old.py").write_text(f'AWS_ACCESS_KEY_ID = "{AWS_KEY}"\nAWS_SECRET_ACCESS_KEY = "{AWS_SECRET}"\n')
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", f"add old settings, asked {EMAIL} ({STUDENT}) to check")
    sha = git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "settings_old.py").unlink()
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "remove old settings")
    return Src(tmp_path, sha)


def secret_finding(repo, **kw):
    base = dict(category=Category.V4, tool="gitleaks", rule_id="aws-access-token", cwe="CWE-798",
                file_path="settings_old.py", line=1, source=f"commit:{repo.sha}", masked_snippet="REDACTED",
                message="Identified a pattern that may indicate AWS credentials")
    return Finding(**{**base, **kw})


def details(bundle):
    return next(i for i in bundle.items if i.label.startswith("details about the secret"))


def everything_sent(f, bundle, pii):
    system, user = build_prompt(f, bundle, pii)
    return system + user + json.dumps([i.model_dump() for i in bundle.items])


# ---- a secret that exists only in the history ----------------------------------------------------------------------------
def test_history_only_secret_has_kind_length_location_and_commit(repo):
    f, pii = secret_finding(repo), PIIRedactor()
    item = details(build_bundle(f, repo, pii=pii))
    c = item.content
    assert "masked value (from the scanner; the real value is never shown): REDACTED" in c
    assert "kind: aws_access_key; length: 20 characters; looks like a placeholder: no" in c
    assert "where: only in the git history; the file is not in the current files" in c
    assert f"introducing commit {repo.sha[:12]}: dated 20" in c  # an ISO date
    assert "the line as it was in that commit (secret masked):" in c
    assert '>    1 | AWS_ACCESS_KEY_ID = "[REDACTED secret kind=aws_access_key len=20 placeholder_like=no]"' in c


def test_the_second_line_is_measured_too(repo):
    c = details(build_bundle(secret_finding(repo, rule_id="generic-api-key", line=2), repo, pii=PIIRedactor())).content
    assert "kind: credential; length: 40 characters; looks like a placeholder: no" in c


def test_the_real_value_never_appears_anywhere(repo):
    f, pii = secret_finding(repo), PIIRedactor()
    bundle = build_bundle(f, repo, pii=pii)
    sent = everything_sent(f, bundle, pii)
    assert AWS_KEY not in sent and AWS_SECRET not in sent and AWS_KEY[:10] not in sent


def test_the_commit_message_is_pii_redacted(repo):
    f, pii = secret_finding(repo), PIIRedactor()
    bundle = build_bundle(f, repo, pii=pii)
    c = details(bundle).content
    assert 'message: "add old settings, asked <EMAIL_1> (<STUDENT_ID_1>) to check"' in c
    sent = everything_sent(f, bundle, pii)
    assert EMAIL not in sent and STUDENT not in sent
    assert pii.mapping["<EMAIL_1>"] == EMAIL  # the mapping stays local


def test_trufflehog_masked_value_is_passed_through(repo):
    c = details(build_bundle(secret_finding(repo, tool="trufflehog", rule_id="AWS", masked_snippet="AK****M2"), repo,
                             pii=PIIRedactor())).content
    assert "(from the scanner; the real value is never shown): AK****M2" in c


def test_the_details_come_after_the_snippet_with_a_valid_id_and_in_the_prompt(repo):
    f, pii = secret_finding(repo), PIIRedactor()
    bundle = build_bundle(f, repo, pii=pii)
    assert [i.id for i in bundle.items] == ["E1", "E2"] and bundle.items[1].kind == "context"
    _s, user = build_prompt(f, bundle, pii)
    assert '<evidence id="E2" kind="context" label="details about the secret (its value is never shown)">' in user


# ---- a secret in the current files ------------------------------------------------------------------------------------------
def test_secret_in_a_current_file(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "config.py").write_text(f'DEBUG = False\nAPI_KEY = "{AWS_KEY}"\n')
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "add config")
    src = Src(tmp_path, git(tmp_path, "rev-parse", "HEAD"))
    f = secret_finding(src, file_path="config.py", line=2)
    c = details(build_bundle(f, tmp_path, pii=PIIRedactor())).content
    assert "where: in the current files (config.py:2)" in c and "kind: aws_access_key; length: 20" in c
    assert "the line as it was in that commit" not in c  # the code snippet (E2) already shows the current file
    assert 'message: "add config"' in c


def test_a_test_value_is_marked_as_placeholder_like(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text('API_KEY = "test_key_0000000000000000"\n')
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "tests")
    src = Src(tmp_path, git(tmp_path, "rev-parse", "HEAD"))
    f = secret_finding(src, tool="gitleaks", rule_id="generic-api-key", file_path="tests/t.py", line=1)
    c = details(build_bundle(f, tmp_path, pii=PIIRedactor())).content
    assert "looks like a placeholder: yes" in c and "in the current files (tests/t.py:1)" in c


def test_a_file_that_no_longer_holds_the_secret(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "config.py").write_text(f'API_KEY = "{AWS_KEY}"\n')
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "add")
    src = Src(tmp_path, git(tmp_path, "rev-parse", "HEAD"))
    (tmp_path / "config.py").write_text('API_KEY = os.environ["API_KEY"]\n')
    git(tmp_path, "commit", "-q", "-am", "use the environment")
    c = details(build_bundle(secret_finding(src, file_path="config.py", line=1), tmp_path, pii=PIIRedactor())).content
    assert "the file exists, but line 1 no longer holds the secret" in c and "kind: aws_access_key; length: 20" in c


# ---- when information is missing ----------------------------------------------------------------------------------------------
def test_without_git_history_it_says_unknown_instead_of_guessing(repo, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    c = details(build_bundle(secret_finding(repo), plain, pii=PIIRedactor())).content
    assert "kind and length: unknown" in c and "where: unknown" in c and "introducing commit" not in c


@pytest.mark.parametrize("source", ["commit:zz; rm -rf /", "commit:--help", None, "file:x"])
def test_an_odd_commit_reference_never_reaches_git(repo, monkeypatch, source):
    calls = []
    monkeypatch.setattr(evidence_module, "_git_read", lambda *a, **k: calls.append(a) or None)
    build_bundle(secret_finding(repo, source=source), repo, pii=PIIRedactor())
    assert calls == []


def test_a_path_outside_the_repository_is_never_read(repo, monkeypatch):
    calls = []
    monkeypatch.setattr(evidence_module, "_git_read", lambda *a, **k: calls.append(a) or None)
    build_bundle(secret_finding(repo, file_path="../zz_unique_marker.py"), repo, pii=PIIRedactor())
    assert not any("zz_unique_marker" in " ".join(map(str, c)) for c in calls)  # the commit metadata may be read, the path never


def test_other_categories_get_no_secret_details(repo):
    f = secret_finding(repo, category=Category.V3, rule_id="security-assistant-cfg-005")
    assert not any(i.label.startswith("details about the secret") for i in build_bundle(f, repo, pii=PIIRedactor()).items)


# ---- dry run -----------------------------------------------------------------------------------------------------------------------
def test_dry_run_shows_the_secret_details_redacted(repo, tmp_path, capsys):
    doc = {"scan": {"source": "demo", "languages": ["python"], "skipped_tools": []}, "coverage": {}, "runs": [
        {"tool": "gitleaks", "status": "succeeded", "started_at": "2026-10-20T09:00:00Z", "findings_count": 1}],
        "findings": [secret_finding(repo).model_dump(mode="json")]}
    saved = tmp_path / "findings.json"
    saved.write_text(json.dumps(doc), encoding="utf-8")
    assert run(flow.main([str(saved), str(repo), "--dry-run"])) == 0
    out = capsys.readouterr().out
    assert "details about the secret (its value is never shown)" in out and "kind: aws_access_key; length: 20" in out
    assert "only in the git history" in out and 'message: "add old settings, asked <EMAIL_1> (<STUDENT_ID_1>) to check"' in out
    for secret in (AWS_KEY, AWS_SECRET, EMAIL, STUDENT):
        assert secret not in out


# ---- temperature ----------------------------------------------------------------------------------------------------------------------
def test_temperature_is_the_lowest_groq_accepts_and_is_sent_and_recorded():
    seen = {}

    def handler(request):
        seen.update(body=json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {}})

    client = GroqClient("gsk_x", "some-model", transport=httpx.MockTransport(handler), retries=0)
    run(client.complete("s", "u"))
    assert TEMPERATURE == 0.0 and seen["body"]["temperature"] == 0.0
    assert client.temperature == 0.0 and client.last_call.temperature == 0.0


def test_interpreted_json_records_model_prompt_version_and_temperature(repo, tmp_path):
    answer = json.dumps({"status": "uncertain", "rationale": "r", "evidence_ids": ["E1"], "confidence": 0.3, "recommendation": ""})
    client = GroqClient("gsk_x", "some-model", retries=0, transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"choices": [{"message": {"content": answer}, "finish_reason": "stop"}], "usage": {}})))
    doc = {"scan": {"source": "demo", "languages": ["python"], "skipped_tools": []}, "coverage": {}, "runs": [
        {"tool": "gitleaks", "status": "succeeded", "started_at": "2026-10-20T09:00:00Z", "findings_count": 1}],
        "findings": [secret_finding(repo).model_dump(mode="json")]}
    saved = tmp_path / "findings.json"
    saved.write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "out"
    assert run(flow.main([str(saved), str(repo), "--allow-external-llm", "--out", str(out)], client=client)) == 0
    meta = json.loads((out / "interpreted.json").read_text(encoding="utf-8"))["meta"]
    assert (meta["model"], meta["prompt_version"], meta["temperature"]) == ("some-model", "interpreter-v4", 0.0)
    assert AWS_KEY not in (out / "interpreted.json").read_text(encoding="utf-8")
