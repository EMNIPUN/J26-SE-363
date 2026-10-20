"""The interpret command: dedupe, dry-run, gate, outputs. The LLM is a scripted mock and the findings come from saved
JSON files; no scanner, no network and no API key are used."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from app.agents.security_assistant import interpret as flow
from app.agents.security_assistant.dedupe import dedupe, package_of
from app.agents.security_assistant.interpreter.llm import GeminiClient, LLMError, get_default_client
from app.agents.security_assistant.interpreter.models import finding_key
from app.agents.security_assistant.report import from_json
from app.agents.security_assistant.schemas import Category
from app.agents.security_assistant.tools.tests.conftest import FIXTURES

SAVED = Path(__file__).parent / "saved"
FULL, DEPS = SAVED / "python_full.json", SAVED / "python_deps.json"
REPO = FIXTURES / "vuln_py_repo"


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class Mock:
    """Scripted LLM: returns a verdict (or an error / raw text) and records every prompt."""

    model = "mock-model"

    def __init__(self, reply=None):
        self.reply = reply if reply is not None else {"status": "confirmed", "rationale": "the evidence shows it",
                                                     "evidence_ids": ["E1"], "confidence": 0.8}
        self.prompts = []

    async def complete(self, system, user):
        self.prompts.append((system, user))
        r = self.reply(system, user) if callable(self.reply) else self.reply
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, str) else json.dumps(r)


class Forbidden:
    """A client that must never be called."""

    model = "forbidden"

    async def complete(self, system, user):
        raise AssertionError("the LLM was called")


def load(path):
    return from_json(path.read_text(encoding="utf-8"))[0]


def go(argv, client=None):
    return run(flow.main([str(a) for a in argv], client=client))


# ---- dedupe and grouping -------------------------------------------------------------------------------------------
def test_package_parsing():
    f = load(DEPS).findings
    assert [package_of(x) for x in f] == [("requests", "2.19.0"), ("requests", "2.19.0"), ("requests", "2.19.0"),
                                          ("flask", "1.0"), ("flask", "1.0"), ("lodash", "<4.17.21"), ("lodash", "4.17.15"), None]
    assert package_of(load(DEPS).findings[0].model_copy(update={"tool": "zizmor"})) is None


def test_same_advisory_is_merged_and_dependencies_are_grouped_per_package():
    findings = load(DEPS).findings
    groups, log = dedupe(findings)
    assert [g.id for g in groups] == ["G01", "G02", "G03", "G04"]  # requests, flask, lodash + the config finding
    requests_g, flask_g, lodash_g, single = groups
    assert (requests_g.kind, requests_g.package, len(requests_g.members)) == ("package", "requests", 3)
    assert {a["id"] for a in requests_g.advisories} == {"PYSEC-2018-28", "GHSA-x84v-xcm2-53pg"}  # 3 findings, 2 advisories
    assert requests_g.representative.rule_id == "GHSA-x84v-xcm2-53pg"  # highest severity represents the package
    assert (len(flask_g.members), len(flask_g.advisories)) == (2, 1)
    assert len(lodash_g.advisories) == 2  # different ids from different tools are not guessed to be the same
    assert single.kind == "single" and single.representative.category is Category.V3
    merged = [m for m in log if m["type"].startswith("same advisory")]
    assert {(m["package"], m["advisory"], m["kept"], tuple(m["merged"])) for m in merged} == {
        ("requests", "PYSEC-2018-28", "osv-scanner:PYSEC-2018-28", ("pip-audit:PYSEC-2018-28",)),
        ("flask", "PYSEC-2023-62", "osv-scanner:PYSEC-2023-62", ("pip-audit:PYSEC-2023-62",))}
    grouped = {m["package"]: m for m in log if m["type"] == "grouped per package"}
    assert grouped["requests"]["findings_in_group"] == 3 and grouped["lodash"]["versions_seen"] == ["4.17.15", "<4.17.21"]


def test_nothing_is_dropped_every_original_finding_is_a_member():
    findings = load(DEPS).findings
    groups, _ = dedupe(findings)
    members = [finding_key(m) for g in groups for m in g.members]
    assert sorted(members) == sorted(finding_key(f) for f in findings)


def test_non_dependency_findings_are_never_grouped():
    findings = load(FULL).findings
    groups, log = dedupe(findings)
    zizmor = [g for g in groups if g.representative.tool == "zizmor"]
    assert len(zizmor) == 2 and all(g.kind == "single" for g in zizmor)
    assert len(groups) == 11  # 12 findings; osv-scanner and pip-audit report the same requests advisory
    assert any(m["type"] == "grouped per package" and m["package"] == "requests" for m in log)  # osv + pip-audit repeat


# ---- the plan --------------------------------------------------------------------------------------------------------------
def test_plan_filters_by_category_and_caps_the_calls():
    result = load(FULL)
    only = flow.make_plan(result, REPO, only=[Category.V4])
    assert only.selected_findings == 2 and len(only.calls) == 2 and only.total_findings == 12
    capped = flow.make_plan(result, REPO, max_findings=3)
    assert len(capped.calls) == 3 and capped.groups_cut == capped.groups_total - 3


def test_package_group_bundle_carries_the_advisories():
    plan = flow.make_plan(load(DEPS), REPO, only=[Category.V5])
    call = plan.calls[0]
    advisories = [i for i in call.bundle.items if "advisories the scanners reported" in i.label]
    assert advisories and "PYSEC-2018-28" in advisories[0].content and "GHSA-x84v-xcm2-53pg" in advisories[0].content
    assert call.bundle.items[0].id == "E1" and len({i.id for i in call.bundle.items}) == len(call.bundle.items)


def test_parse_categories():
    assert flow.parse_categories(["V1,v4", "V2"]) == [Category.V1, Category.V4, Category.V2]
    assert flow.parse_categories(None) is None
    with pytest.raises(ValueError, match="--only-category"):
        flow.parse_categories(["V9"])


# ---- dry run ----------------------------------------------------------------------------------------------------------------
def test_dry_run_prints_exactly_what_would_be_sent_and_calls_nothing(capsys):
    code = go([DEPS, REPO, "--dry-run"], client=Forbidden())
    out = capsys.readouterr().out
    assert code == 0 and out.startswith("DRY RUN - nothing is sent. 4 LLM call(s) would be made")
    assert "7 selected" not in out and "Findings in file: 8; selected: 8; after merging and grouping: 4 group(s)" in out
    assert "merged  requests PYSEC-2018-28: kept osv-scanner:PYSEC-2018-28, merged pip-audit:PYSEC-2018-28" in out
    assert "grouped lodash: 2 finding(s)" in out
    assert out.count("SYSTEM PROMPT (identical in every call)") == 1 and out.count("<evidence id=\"E1\"") == 4
    assert "UNTRUSTED DATA" in out and "TOTAL: 4 call(s)" in out


def test_dry_run_needs_no_flag_and_no_key(capsys, monkeypatch):
    monkeypatch.delenv("SECURITY_ASSISTANT_LLM_API_KEY", raising=False)
    assert go([FULL, REPO, "--dry-run", "--only-category", "V2"]) == 0
    assert "1 LLM call(s)" in capsys.readouterr().out


def test_dry_run_shows_redacted_content(tmp_path, capsys):
    (tmp_path / "app.py").write_text('x = 1\nDB_PASSWORD = "hunter2hunter2"\ny = 2\n')
    doc = json.loads(FULL.read_text(encoding="utf-8"))
    doc["findings"] = [dict(doc["findings"][0], category="V3", file_path="app.py", line=2, tool="config-scan")]
    saved = tmp_path / "f.json"
    saved.write_text(json.dumps(doc))
    assert go([saved, tmp_path, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "hunter2hunter2" not in out and "[REDACTED secret" in out


# ---- the gate --------------------------------------------------------------------------------------------------------------
def test_refuses_to_call_the_llm_without_the_flag(capsys, tmp_path):
    client = Forbidden()
    code = go([FULL, REPO, "--out", tmp_path / "o"], client=client)
    err = capsys.readouterr().err
    assert code == 4 and "REFUSED" in err and "--allow-external-llm" in err
    assert "external LLM (Google Gemini)" in err and "secrets are masked" in err and "Not sent:" in err
    assert not (tmp_path / "o").exists()


def test_the_notice_is_printed_when_the_llm_is_allowed(capsys, tmp_path):
    go([FULL, REPO, "--allow-external-llm", "--max-findings", "1", "--out", tmp_path / "o"], client=Mock())
    assert flow.NOTICE in capsys.readouterr().out


def test_without_a_key_a_real_run_stops_with_a_clear_message(capsys, monkeypatch, tmp_path):
    from app.agents.security_assistant.interpreter import llm as llm_module
    for name in ("SECURITY_ASSISTANT_LLM_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(llm_module, "ENV_FILE", tmp_path / "no.env")
    assert go([FULL, REPO, "--allow-external-llm", "--out", tmp_path / "o"]) == 3
    assert "no API key found" in capsys.readouterr().err


# ---- a run ---------------------------------------------------------------------------------------------------------------------
def test_run_writes_interpreted_json_and_a_report_section(tmp_path, capsys):
    out = tmp_path / "o"
    mock = Mock()
    code = go([DEPS, REPO, "--allow-external-llm", "--out", out], client=mock)
    assert code == 0 and len(mock.prompts) == 4
    doc = json.loads((out / "interpreted.json").read_text(encoding="utf-8"))
    s = doc["summary"]
    assert (s["scanner_only_findings"], s["confirmed"], s["dismissed"], s["uncertain"], s["not_analysed_findings"]) == (8, 8, 0, 0, 0)
    assert doc["meta"]["calls_made"] == 4 and len(doc["merge_log"]) == 5 and doc["meta"]["model"] == "mock-model"
    pkg = next(g for g in doc["groups"] if g["package"] == "requests")
    assert len(pkg["members"]) == 3 and pkg["result"]["status"] == "confirmed" and pkg["result"]["evidence_ids"] == ["E1"]
    md = (out / "report.md").read_text(encoding="utf-8")
    assert md.count("## LLM interpretation") == 1 and "# Security scan report" in md
    assert "| 8 | 8 | 0 | 0 | 0 |" in md and "### Merged and grouped before the calls" in md
    assert "| G01 | V5 | GHSA-x84v-xcm2-53pg | requests (3 findings) | **confirmed** | 0.80 | E1 | the evidence shows it |" in md
    assert "scanner-only findings 8 -> confirmed 8" in capsys.readouterr().out


def test_running_again_replaces_the_section_instead_of_appending(tmp_path):
    out = tmp_path / "o"
    go([DEPS, REPO, "--allow-external-llm", "--out", out], client=Mock())
    go([DEPS, REPO, "--allow-external-llm", "--out", out], client=Mock())
    assert (out / "report.md").read_text(encoding="utf-8").count("## LLM interpretation") == 1


def test_default_output_is_next_to_findings_json(tmp_path):
    copy = tmp_path / "findings.json"
    copy.write_text(DEPS.read_text(encoding="utf-8"), encoding="utf-8")
    go([copy, REPO, "--allow-external-llm", "--only-category", "V3"], client=Mock())
    assert (tmp_path / "interpreted.json").exists() and (tmp_path / "report.md").exists()


def test_only_category_and_max_findings(tmp_path):
    mock = Mock()
    go([FULL, REPO, "--allow-external-llm", "--only-category", "V3,V4", "--max-findings", "2", "--out", tmp_path / "o"], client=mock)
    doc = json.loads((tmp_path / "o" / "interpreted.json").read_text(encoding="utf-8"))
    s = doc["summary"]
    assert len(mock.prompts) == 2 and s["scanner_only_findings"] == 6 and s["analysed_findings"] == 2
    assert s["not_analysed_findings"] == 4 and s["not_selected_findings"] == 6


def test_delay_between_calls_but_not_after_the_last(tmp_path, monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(flow.asyncio, "sleep", fake_sleep)
    go([DEPS, REPO, "--allow-external-llm", "--delay", "6", "--out", tmp_path / "o"], client=Mock())
    assert sleeps == [6.0, 6.0, 6.0]  # four calls


def test_retries_are_bounded_and_passed_to_the_client(monkeypatch):
    from app.agents.security_assistant.interpreter import llm as llm_module
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_API_KEY", "k")
    client = get_default_client(retries=1, backoff=6)
    assert isinstance(client, GeminiClient) and (client._retries, client._backoff) == (1, 6)


# ---- the existing safety checks still hold through the flow ----------------------------------------------------------
def test_the_llm_cannot_add_findings(tmp_path):
    smuggle = {"status": "confirmed", "rationale": "x", "evidence_ids": ["E1"], "confidence": 0.9,
               "new_findings": [{"rule_id": "invented", "file_path": "evil.py", "line": 1}]}
    go([DEPS, REPO, "--allow-external-llm", "--out", tmp_path / "o"], client=Mock(smuggle))
    doc = json.loads((tmp_path / "o" / "interpreted.json").read_text(encoding="utf-8"))
    known = {finding_key(f) for f in load(DEPS).findings}
    assert {m["finding_key"] for g in doc["groups"] for m in g["members"]} == known  # only scanner findings appear
    assert "invented" not in json.dumps(doc)
    assert doc["summary"]["uncertain_because"]["output_rejected"] == 8 and doc["summary"]["confirmed"] == 0


def test_a_fake_evidence_id_downgrades_to_uncertain(tmp_path):
    fake = {"status": "dismissed", "rationale": "x", "evidence_ids": ["E99"], "confidence": 1.0}
    go([DEPS, REPO, "--allow-external-llm", "--out", tmp_path / "o"], client=Mock(fake))
    s = json.loads((tmp_path / "o" / "interpreted.json").read_text(encoding="utf-8"))["summary"]
    assert (s["dismissed"], s["uncertain"], s["uncertain_because"]["downgraded"]) == (0, 8, 8)


def test_a_failed_call_is_uncertain_never_a_guess(tmp_path, capsys):
    code = go([DEPS, REPO, "--allow-external-llm", "--out", tmp_path / "o"], client=Mock(LLMError("Gemini call failed: HTTP 429")))
    doc = json.loads((tmp_path / "o" / "interpreted.json").read_text(encoding="utf-8"))
    assert code == 2 and doc["summary"]["uncertain"] == 8 and doc["summary"]["uncertain_because"]["llm_error"] == 8
    assert all(g["result"]["status"] == "uncertain" and "429" in g["result"]["error"] for g in doc["groups"])
    md = (tmp_path / "o" / "report.md").read_text(encoding="utf-8")
    assert "(LLM error)" in md and "HTTP 429" in md


def test_mixed_answers_are_counted_per_finding(tmp_path):
    def reply(system, user):  # dismiss the lodash package, confirm the rest
        status = "dismissed" if "'lodash'" in user else "confirmed"
        return {"status": status, "rationale": "r", "evidence_ids": ["E1"], "confidence": 0.7}

    go([DEPS, REPO, "--allow-external-llm", "--out", tmp_path / "o"], client=Mock(reply))
    s = json.loads((tmp_path / "o" / "interpreted.json").read_text(encoding="utf-8"))["summary"]
    assert (s["confirmed"], s["dismissed"], s["uncertain"]) == (6, 2, 0)  # lodash covers 2 findings


def test_bad_input_is_a_usage_error(tmp_path, capsys):
    assert go([tmp_path / "missing.json", REPO]) == 3
    assert go([FULL, tmp_path / "no_such_dir", "--dry-run"]) == 3
    assert go([FULL, REPO, "--dry-run", "--only-category", "V9"]) == 3
