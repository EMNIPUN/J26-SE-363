"""PII redactor: personal data never reaches the prompt. Fast tests, mocked LLM, saved findings JSON, no scanner."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from app.agents.security_assistant import interpret as flow
from app.agents.security_assistant.interpreter.evidence import build_bundle
from app.agents.security_assistant.interpreter.interpreter import SemanticInterpreter
from app.agents.security_assistant.interpreter.models import EvidenceItem, finding_key
from app.agents.security_assistant.interpreter.prompts import build_prompt
from app.agents.security_assistant.pii import PIIRedactor, _protected_spans
from app.agents.security_assistant.schemas import Category, Finding

PERSON = "Kasun Perera"
EMAIL = "kasun.perera@students.example.edu"
PHONE_PLUS, PHONE_LOCAL = "+94 77 123 4567", "0771234567"
STUDENT = "IT21234567"
JANE, JANE_MAIL, OTHER_ID, OTHER_PHONE = "Jane Roe", "jane.roe@students.example.edu", "IT20250042", "+94 71 555 0199"
SECRET = "hunter2hunter2"

APP_PY = f'''# Author: {PERSON}
# Contact: {EMAIL}, phone {PHONE_PLUS}, student {STUDENT}
import hashlib


def login(author_name, email_address):
    """Written by {PERSON} ({STUDENT})."""
    support = "mail {EMAIL} or call {PHONE_LOCAL}"
    DB_PASSWORD = "{SECRET}"
    pw = hashlib.md5(author_name.encode()).hexdigest()  # weak hash, ask Kasun
    return pw
'''
PATH = "submissions/kasun_perera/app.py"
COMMIT_MESSAGE = f"Fix login\n\nCo-authored-by: {JANE} <{JANE_MAIL}>\nreviewed for {OTHER_ID}, call {OTHER_PHONE}"
ORIGINALS = [PERSON, EMAIL, PHONE_PLUS, PHONE_LOCAL, STUDENT, JANE, JANE_MAIL, OTHER_ID, OTHER_PHONE, "kasun_perera", SECRET]


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "submissions" / "kasun_perera").mkdir(parents=True)
    (tmp_path / PATH).write_text(APP_PY, encoding="utf-8")
    return tmp_path


def finding(**kw):
    base = dict(category=Category.V3, tool="config-scan", rule_id="security-assistant-cfg-005", cwe="CWE-916",
                file_path=PATH, line=10, message="Weak or unsalted password hashing")
    return Finding(**{**base, **kw})


def commit_item():
    return EvidenceItem(id="E9", kind="context", label="commit that introduced the line", content=COMMIT_MESSAGE)


def code_outside_comments_and_strings(text: str) -> str:
    """The text with every comment and string removed: what is left must not change."""
    out, last = [], 0
    for a, b in _protected_spans(text):
        out.append(text[last:a])
        last = b
    out.append(text[last:])
    return "".join(out)


# ---- the redactor itself ----------------------------------------------------------------------------------------------
def test_placeholders_are_stable_and_distinct():
    pii = PIIRedactor()
    out = pii.redact_plain(f"a {EMAIL} b {JANE_MAIL} c {EMAIL} d {STUDENT} e {OTHER_ID}")
    assert out == "a <EMAIL_1> b <EMAIL_2> c <EMAIL_1> d <STUDENT_ID_1> e <STUDENT_ID_2>"
    assert pii.mapping == {"<EMAIL_1>": EMAIL, "<EMAIL_2>": JANE_MAIL, "<STUDENT_ID_1>": STUDENT, "<STUDENT_ID_2>": OTHER_ID}


@pytest.mark.parametrize("text", [PHONE_PLUS, "077-123-4567", PHONE_LOCAL, "(011) 234 5678", "+94771234567", "011.234.5678"])
def test_phone_numbers_are_redacted(text):
    assert PIIRedactor().redact_plain(f"call {text} now") == "call <PHONE_1> now"


@pytest.mark.parametrize("text", ["version 1.2.3", "ip 192.168.100.200", "date 2024-01-15", "port 8080", "order 12345678",
                                  "hex 0xDEADBEEF", "item_0771234567"])
def test_numbers_that_are_not_phones_stay(text):
    assert PIIRedactor().redact_plain(text) == text


def test_student_id_pattern_is_configurable():
    pii = PIIRedactor(student_id_pattern=r"\bSE\d{6}\b")
    assert pii.redact_plain(f"SE123456 and {STUDENT}") == f"<STUDENT_ID_1> and {STUDENT}"


def test_settings_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("SECURITY_ASSISTANT_STUDENT_ID_REGEX", r"\bCS\d{4}\b")
    monkeypatch.setenv("SECURITY_ASSISTANT_PII_KNOWN_NAMES", "Priya Nair, Tom Hall")
    pii = PIIRedactor.from_env()
    assert pii.redact_plain("CS1234 by Priya Nair") == "<STUDENT_ID_1> by <NAME_1>"


@pytest.mark.parametrize("line,expected", [
    (f"# Author: {PERSON}", "# Author: <NAME_1>"),
    (f"/** @author {PERSON} */", "/** @author <NAME_1> */"),
    (f"// Maintainer: {PERSON}", "// Maintainer: <NAME_1>"),
    (f"# Written by {PERSON}", "# Written by <NAME_1>"),
    (f"# Created by: {PERSON}", "# Created by: <NAME_1>"),
    (f"# Copyright (c) 2024 {PERSON}. All rights reserved.", "# Copyright (c) 2024 <NAME_1>. All rights reserved."),
    (f"# Contact: {PERSON} <a@b.org>", "# Contact: <NAME_1> <<EMAIL_1>>"),
    (f"# Authors: {PERSON}, {JANE}", "# Authors: <NAME_1>, <NAME_2>"),
])
def test_names_on_labelled_lines(line, expected):
    assert PIIRedactor().redact_plain(line) == expected


def test_a_name_seen_on_a_label_is_redacted_everywhere_afterwards():
    pii = PIIRedactor()
    pii.redact_plain(f"# Author: {PERSON}")
    assert pii.redact_plain("fixed by Kasun, reviewed by perera") == "fixed by <NAME_1>, reviewed by <NAME_1>"


def test_name_detection_is_label_based_and_misses_unlabelled_names():
    """Documented limitation: a name that never appeared on a label is not found."""
    assert PIIRedactor().redact_plain("thanks to Priya Nair for the idea") == "thanks to Priya Nair for the idea"


def test_code_mode_touches_comments_and_strings_only_and_keeps_every_identifier():
    pii = PIIRedactor()
    out = pii.redact_code(APP_PY)
    assert code_outside_comments_and_strings(out) == code_outside_comments_and_strings(APP_PY)  # code outside comments/strings: identical
    assert out.count("\n") == APP_PY.count("\n")
    for identifier in ("def login(author_name, email_address):", "hashlib.md5(author_name.encode()).hexdigest()", "return pw"):
        assert identifier in out
    for original in (PERSON, EMAIL, PHONE_PLUS, PHONE_LOCAL, STUDENT):
        assert original not in out


def test_an_identifier_that_looks_like_an_id_or_email_is_not_changed_in_code():
    code = f"class {STUDENT}Service:\n    {STUDENT.lower()}_value = 1\n    email_address = get_email()\n"
    assert PIIRedactor().redact_code(code) == code


def test_round_trip_through_the_mapping_restores_exactly_what_was_changed():
    pii = PIIRedactor()
    text = f'# Author: {PERSON}\nmail = "{EMAIL}"  # {PHONE_PLUS}\nx = 1\n'
    out = pii.redact_code(text)
    restored = out
    for placeholder, original in pii.mapping.items():
        restored = restored.replace(placeholder, original)
    assert restored == text


def test_git_metadata_is_redacted():
    pii = PIIRedactor()
    meta = pii.redact_git_metadata(PERSON, EMAIL, f"Fix by {PERSON} ({STUDENT}), mail {EMAIL}; Kasun will review")
    assert meta["author"] == "<NAME_1>" and meta["email"] == "<EMAIL_1>"
    assert meta["message"] == "Fix by <NAME_1> (<STUDENT_ID_1>), mail <EMAIL_1>; <NAME_1> will review"


def test_a_name_inside_a_path_gets_a_placeholder_and_stays_traceable():
    pii = PIIRedactor(known_names=[PERSON])
    assert pii.redact_path("submissions/kasun_perera/app.py") == "submissions/<NAME_1>/app.py"
    assert pii.redact_path(f"work/{STUDENT}/Main.java") == "work/<STUDENT_ID_1>/Main.java"
    assert pii.redact_path("src/main/java/demo/UserController.java") == "src/main/java/demo/UserController.java"
    assert pii.path_map == {"submissions/<NAME_1>/app.py": "submissions/kasun_perera/app.py",
                            "work/<STUDENT_ID_1>/Main.java": f"work/{STUDENT}/Main.java"}


def test_the_local_mapping_file(tmp_path):
    pii = PIIRedactor()
    assert pii.save_mapping(tmp_path / "m.json") is None  # nothing redacted, nothing written
    pii.redact_plain(f"mail {EMAIL}")
    saved = json.loads(pii.save_mapping(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert saved["placeholders"] == {"<EMAIL_1>": EMAIL} and "do not share" in saved["WARNING"]


# ---- the bundle and the prompt ------------------------------------------------------------------------------------------
def test_planted_personal_data_never_reaches_the_prompt(repo):
    pii = PIIRedactor()
    bundle = build_bundle(finding(), repo, extra=[commit_item()], pii=pii)
    system, user = build_prompt(finding(), bundle, pii)
    sent = system + "\n" + user
    for original in ORIGINALS:
        assert original not in sent, original
    for placeholder in ("<NAME_1>", "<EMAIL_1>", "<PHONE_1>", "<STUDENT_ID_1>"):
        assert placeholder in user
    # comments, strings (docstring and normal string) and the commit message were all covered
    assert "# Contact: <EMAIL_1>, phone <PHONE_1>, student <STUDENT_ID_1>" in user  # a comment
    assert "Written by <NAME_1> (<STUDENT_ID_1>)" in user  # a docstring
    assert "mail <EMAIL_1> or call <PHONE_" in user  # a string
    assert "Co-authored-by: <NAME_" in user and "reviewed for <STUDENT_ID_" in user  # the commit message


def test_code_identifiers_and_structure_survive_in_the_prompt(repo):
    pii = PIIRedactor()
    bundle = build_bundle(finding(), repo, pii=pii)
    _system, user = build_prompt(finding(), bundle, pii)
    assert "def login(author_name, email_address):" in user
    assert "pw = hashlib.md5(author_name.encode()).hexdigest()" in user
    assert ">   10 |" in user  # the finding line keeps its number and marker


def test_the_file_path_stays_traceable(repo):
    pii = PIIRedactor()
    f = finding()
    bundle = build_bundle(f, repo, pii=pii)
    _system, user = build_prompt(f, bundle, pii)
    assert "file_path: submissions/<NAME_1>/app.py" in user and "kasun_perera" not in user
    assert "code around submissions/<NAME_1>/app.py:10" in user
    assert pii.path_map["submissions/<NAME_1>/app.py"] == PATH  # local: placeholder path -> real path
    assert finding_key(f) == finding_key(finding())  # the finding itself, and its key, are untouched
    assert f.file_path == PATH


def test_the_mapping_is_not_in_the_prompt(repo):
    pii = PIIRedactor()
    bundle = build_bundle(finding(), repo, extra=[commit_item()], pii=pii)
    system, user = build_prompt(finding(), bundle, pii)
    sent = system + user
    assert pii.mapping and all(original not in sent for original in pii.mapping.values())
    assert "placeholders" not in sent and "path_map" not in sent and "WARNING" not in sent


def test_a_hand_built_bundle_is_redacted_at_prompt_time_too():
    f = Finding(category=Category.V4, tool="gitleaks", rule_id="generic-api-key", file_path="a.py", line=1, message="m")
    bundle = build_bundle(f)  # no repo: only E1
    bundle = bundle.model_copy(update={"items": [*bundle.items, EvidenceItem(
        id="E2", kind="code_snippet", label="note", content=f"   1 | # Author: {PERSON} {EMAIL} {STUDENT}\n   2 | x = 1")]})
    _s, user = build_prompt(f, bundle, PIIRedactor())
    assert PERSON not in user and EMAIL not in user and STUDENT not in user and "   2 | x = 1" in user


def test_the_interpreter_sends_redacted_prompts(repo):
    sent = []

    class Mock:
        model = "mock"

        async def complete(self, system, user):
            sent.append(system + user)
            return json.dumps({"status": "confirmed", "rationale": "ok", "evidence_ids": ["E1"], "confidence": 0.5})

    pii = PIIRedactor()
    bundle = build_bundle(finding(), repo, extra=[commit_item()], pii=pii)
    result = run(SemanticInterpreter(Mock(), pii).interpret(finding(), bundle))
    assert result.status == "confirmed" and result.finding_key == finding_key(finding())
    assert all(original not in sent[0] for original in ORIGINALS)


# ---- dry-run and the command ---------------------------------------------------------------------------------------------
@pytest.fixture
def saved_findings(tmp_path):
    f = finding(line=10).model_dump(mode="json")
    doc = {"scan": {"source": "demo", "languages": ["python"], "skipped_tools": []}, "coverage": {}, "runs": [
        {"tool": "config-scan", "status": "succeeded", "started_at": "2026-10-20T09:00:00Z", "findings_count": 1}],
        "findings": [f]}
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_dry_run_shows_the_redacted_bundle(repo, saved_findings, capsys):
    assert run(flow.main([str(saved_findings), str(repo), "--dry-run"])) == 0
    out = capsys.readouterr().out
    for original in ORIGINALS:
        assert original not in out, original
    assert "<NAME_1>" in out and "file_path: submissions/<NAME_1>/app.py" in out
    assert "Personal-data placeholders used in the prompts above:" in out and "never printed or sent" in out


def test_a_run_keeps_the_mapping_in_a_separate_local_file(repo, saved_findings, tmp_path):
    class Mock:
        model = "mock"

        async def complete(self, system, user):
            assert not any(original in system + user for original in ORIGINALS)
            return json.dumps({"status": "uncertain", "rationale": "see <NAME_1>", "evidence_ids": ["E1"], "confidence": 0.3})

    out = tmp_path / "out"
    assert run(flow.main([str(saved_findings), str(repo), "--allow-external-llm", "--out", str(out)], client=Mock())) == 0
    mapping = json.loads((out / "pii_mapping.local.json").read_text(encoding="utf-8"))
    assert mapping["placeholders"]["<EMAIL_1>"] == EMAIL and "do not share" in mapping["WARNING"]
    for name in ("interpreted.json", "report.md"):  # neither report carries the mapping
        text = (out / name).read_text(encoding="utf-8")
        assert '"<EMAIL_1>"' not in text and "do not share" not in text and "pii_mapping" not in text
    interpreted = (out / "interpreted.json").read_text(encoding="utf-8")
    assert EMAIL not in interpreted and PHONE_PLUS not in interpreted and STUDENT not in interpreted
    # report.md keeps the code snippets of the local scan report (the original code), like the scan's own report.md


def test_no_mapping_file_when_nothing_was_redacted(tmp_path, saved_findings):
    class Mock:
        model = "mock"

        async def complete(self, system, user):
            return json.dumps({"status": "uncertain", "rationale": "r", "evidence_ids": ["E1"], "confidence": 0.3})

    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "a.py").write_text("x = 1\n")
    doc = json.loads(saved_findings.read_text(encoding="utf-8"))
    doc["findings"][0].update(file_path="a.py", line=1)
    saved_findings.write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "out"
    run(flow.main([str(saved_findings), str(clean), "--allow-external-llm", "--out", str(out)], client=Mock()))
    assert not (out / "pii_mapping.local.json").exists()
