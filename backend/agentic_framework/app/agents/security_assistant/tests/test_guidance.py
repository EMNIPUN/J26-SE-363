"""Fix guidance for students: the fixed table (every finding gets advice) and the LLM's tailored note (confirmed only).
Fast tests: saved findings, a mocked LLM, no scanner."""

import asyncio
import json
import re
import sys
from pathlib import Path

import pytest

from app.agents.security_assistant import guidance as guide
from app.agents.security_assistant import interpret as flow
from app.agents.security_assistant.interpreter.interpreter import InvalidLLMOutput, SemanticInterpreter, parse_verdict
from app.agents.security_assistant.interpreter.llm import VERDICT_SCHEMA
from app.agents.security_assistant.interpreter.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_prompt
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.interpreter.seeded import load_cases
from app.agents.security_assistant.report import build_report, from_json, render_markdown, to_json
from app.agents.security_assistant.schemas import Category, Finding
from app.agents.security_assistant.tools.tests.conftest import FIXTURES

SAVED = Path(__file__).parent / "saved"
REPO = FIXTURES / "vuln_py_repo"


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def f(category, rule_id, cwe=None, path="app.py", **kw):
    return Finding(category=category, tool="x", rule_id=rule_id, cwe=cwe, file_path=path, **kw)


# ---- every finding the tools can produce gets specific advice ---------------------------------------------------------------
RULES = [
    (Category.V1, "security-assistant/py/missing-ownership-check", "CWE-639", "ownership-check"),
    (Category.V1, "security-assistant/java/missing-ownership-check", "CWE-639", "ownership-check"),
    (Category.V1, "security-assistant/js/missing-ownership-check", "CWE-639", "ownership-check"),
    (Category.V1, "security-assistant-cfg-008", "CWE-862", "deny-by-default"),
    (Category.V1, "security-assistant-cfg-013", "CWE-306", "add-spring-security"),
    (Category.V1, "py/path-injection", "CWE-22", "path-traversal"),
    (Category.V2, "py/sql-injection", "CWE-89", "sql-injection"),
    (Category.V2, "java/sql-injection", "CWE-89", "sql-injection"),
    (Category.V2, "js/sql-injection", "CWE-89", "sql-injection"),
    (Category.V2, "js/command-line-injection", "CWE-78", "command-injection"),
    (Category.V2, "py/command-line-injection", "CWE-78", "command-injection"),
    (Category.V2, "js/reflected-xss", "CWE-79", "xss"),
    (Category.V2, "java/xss", "CWE-79", "xss"),
    (Category.V3, "security-assistant-cfg-001", "CWE-613", "token-expiry"),
    (Category.V3, "security-assistant-cfg-012", "CWE-613", "token-expiry"),
    (Category.V3, "security-assistant-cfg-003", "CWE-614", "cookie-flags"),
    (Category.V3, "js/clear-text-cookie", "CWE-614", "cookie-flags"),
    (Category.V3, "security-assistant-cfg-004", "CWE-489", "debug-and-actuator"),
    (Category.V3, "security-assistant-cfg-005", "CWE-916", "weak-password-hash"),
    (Category.V3, "py/weak-sensitive-data-hashing", "CWE-327", "weak-password-hash"),
    (Category.V3, "security-assistant-cfg-006", "CWE-352", "csrf-protection"),
    (Category.V3, "security-assistant-cfg-007", "CWE-307", "login-rate-limit"),
    (Category.V3, "js/missing-rate-limiting", "CWE-307", "login-rate-limit"),
    (Category.V3, "security-assistant-cfg-011", "CWE-259", "default-password"),
    (Category.V4, "aws-access-token", "CWE-798", "hardcoded-secret"),
    (Category.V4, "generic-api-key", "CWE-798", "hardcoded-secret"),
    (Category.V4, "AWS", "CWE-798", "hardcoded-secret"),
    (Category.V4, "js/hardcoded-credentials", "CWE-321", "hardcoded-secret"),
    (Category.V5, "PYSEC-2018-28", "CWE-1104", "dependency-upgrade"),
    (Category.V5, "GHSA-p6mc-m468-83gw", "CWE-1321", "dependency-upgrade"),
    (Category.V5, "1106913", "CWE-77", "dependency-upgrade"),
    (Category.V5, "zizmor:dangerous-triggers", "CWE-829", "workflow-trigger"),
    (Category.V5, "zizmor:template-injection", "CWE-77", "workflow-trigger"),
    (Category.V5, "zizmor:excessive-permissions", "CWE-732", "workflow-permissions"),
    (Category.V5, "zizmor:unpinned-uses", "CWE-829", "workflow-pinning"),
    (Category.V5, "zizmor:artipacked", "CWE-522", "workflow-credentials"),
    (Category.V5, "actionlint:expression", "CWE-829", "workflow-lint"),
]


@pytest.mark.parametrize("category,rule,cwe,expected", RULES)
def test_each_rule_the_tools_produce_gets_its_own_advice(category, rule, cwe, expected):
    assert guide.guidance_for(f(category, rule, cwe)).id == expected


def test_an_unknown_rule_falls_back_to_the_cwe_then_to_the_category():
    assert guide.guidance_for(f(Category.V2, "py/some-new-rule", "CWE-89")).id == "sql-injection"
    for category in Category:
        assert guide.guidance_for(f(category, "unknown-rule", "CWE-12345")).id == f"general-{ {Category.V1: 'access-control', Category.V2: 'input-handling', Category.V3: 'authentication', Category.V4: 'secrets', Category.V5: 'supply-chain'}[category] }"


def test_every_entry_is_complete_and_short():
    ids = [g.id for g in guide.GUIDANCE]
    assert len(ids) == len(set(ids))
    for g in guide.GUIDANCE:
        assert g.title and len(g.why) > 30 and 2 <= len(g.steps) <= 4, g.id
        assert g.reference.startswith("https://"), g.id
        for language, code in g.examples.items():
            assert language in {"python", "javascript", "java", "ci"} and code.strip(), (g.id, language)
            assert code.count("\n") + 1 <= 12, f"{g.id} {language}: examples are a few lines"
            assert redact_text(code) == code, f"{g.id} {language}: the example looks like it holds a secret"


def test_the_secret_advice_says_rotate_first_and_clean_the_history():
    g = guide.by_id("hardcoded-secret")
    text = " ".join(g.steps).lower()
    assert "rotate" in g.steps[0].lower() and "history" in text and "environment variable" in text


def test_the_example_matches_the_language_of_the_file():
    g = guide.by_id("weak-password-hash")
    for path, language in [("app.py", "python"), ("server.js", "javascript"), ("client.ts", "javascript"),
                           ("src/main/java/demo/SecurityConfig.java", "java")]:
        assert guide.example_for(g, f(Category.V3, "x", path=path))[0] == language
    assert guide.language_of(f(Category.V5, "x", path=".github/workflows/ci.yml")) == "ci"
    assert guide.language_of(f(Category.V5, "x", path="pom.xml")) == "java"
    assert guide.language_of(f(Category.V5, "x", path="requirements.txt")) == "python"
    assert guide.example_for(guide.by_id("dependency-upgrade"), f(Category.V5, "x", path="package-lock.json"))[0] == "javascript"
    assert guide.example_for(guide.by_id("general-secrets"), f(Category.V4, "x")) is None  # general entries have no example


# ---- the reports ---------------------------------------------------------------------------------------------------------------
def saved_report():
    result, skipped = from_json((SAVED / "python_full.json").read_text(encoding="utf-8"))
    return build_report(result, skipped=skipped, source="vuln_py_repo", repo=REPO)


def test_report_md_has_a_how_to_fix_section_with_steps_and_a_python_example():
    md = render_markdown(saved_report())
    assert "## How to fix (by type of issue)" in md
    assert "### V3: Hash passwords with bcrypt or Argon2" in md and "bcrypt.hashpw" in md
    assert "### V2: Use parameterised queries instead of building SQL text" in md and 'db.execute("SELECT * FROM orders WHERE user_id = ?' in md
    assert "### V4: Remove the secret, rotate it, and keep secrets out of code" in md and "Treat the secret as leaked" in md
    assert "### V5: Pin actions to a full commit SHA" in md and "Applies to: `.github/workflows/ci.yml:6`" in md
    assert "Read more: https://cheatsheetseries.owasp.org/" in md and "https://cwe.mitre.org/data/definitions/89.html" in md
    assert "Example (python):" in md and "Example (javascript)" not in md  # only languages that occur in the findings


def test_each_finding_points_to_its_advice_and_findings_json_records_the_id():
    rep = saved_report()
    md = render_markdown(rep)
    assert md.count("- **How to fix:**") == 12
    assert "- **How to fix:** Use parameterised queries instead of building SQL text (see \"How to fix\" below)" in md
    ids = {x["rule_id"]: x["fix_pattern"] for x in json.loads(to_json(rep))["findings"]}
    assert ids["py/sql-injection"] == "sql-injection" and ids["zizmor:unpinned-uses"] == "workflow-pinning"
    assert ids["PYSEC-2018-28"] == "dependency-upgrade"


def test_a_report_without_findings_has_no_how_to_fix_section():
    assert guide_section_empty()


def guide_section_empty():
    from app.agents.security_assistant.report import how_to_fix_section
    return how_to_fix_section([]) == []


# ---- the LLM's tailored note ---------------------------------------------------------------------------------------------------
class Mock:
    model = "mock"

    def __init__(self, **fields):
        self.fields, self.prompts = fields, []

    async def complete(self, system, user):
        self.prompts.append((system, user))
        base = {"status": "confirmed", "rationale": "the evidence shows it", "evidence_ids": ["E1"], "confidence": 0.9,
                "recommendation": "Hash the password with bcrypt.hashpw instead of hashlib.md5."}
        return json.dumps({**base, **self.fields})


def interpret(**fields):
    case = load_cases()[0]
    client = Mock(**fields)
    return run(SemanticInterpreter(client).interpret(case.finding, case.bundle)), client


def test_a_confirmed_finding_keeps_the_tailored_advice():
    result, _ = interpret()
    assert result.status == "confirmed" and result.recommendation == "Hash the password with bcrypt.hashpw instead of hashlib.md5."


@pytest.mark.parametrize("status", ["dismissed", "uncertain"])
def test_dismissed_and_uncertain_findings_get_no_advice_from_the_llm(status):
    result, _ = interpret(status=status)
    assert result.status == status and result.recommendation == ""


def test_a_downgraded_finding_gets_no_advice():
    result, _ = interpret(evidence_ids=["E99"])
    assert result.downgraded and result.status == "uncertain" and result.recommendation == ""


def test_secrets_in_the_advice_are_masked():
    result, _ = interpret(recommendation='Remove DB_PASSWORD = "hunter2hunter2" from the code.')
    assert "hunter2hunter2" not in result.recommendation and "[REDACTED" in result.recommendation


def test_advice_that_is_too_long_is_rejected_like_any_other_schema_error():
    with pytest.raises(InvalidLLMOutput, match="recommendation"):
        parse_verdict(json.dumps({"status": "confirmed", "rationale": "x", "evidence_ids": ["E1"], "confidence": 0.5,
                                  "recommendation": "x" * 901}))


def test_the_recommendation_is_optional_for_older_answers_and_the_schema_requires_it():
    assert parse_verdict(json.dumps({"status": "confirmed", "rationale": "x", "evidence_ids": ["E1"], "confidence": 0.5})).recommendation == ""
    assert "recommendation" in VERDICT_SCHEMA["required"] and set(VERDICT_SCHEMA["required"]) == set(VERDICT_SCHEMA["properties"])


def test_the_prompt_carries_the_reference_guidance_and_the_instruction():
    case = load_cases()[0]
    system, user = build_prompt(case.finding, case.bundle)
    assert PROMPT_VERSION == "interpreter-v3"
    assert '"recommendation"' in system and "at most 6 lines" in system and "do not invent APIs" in system
    assert "Never write a version number, commit SHA, URL" in system and "fixed version named in the advisory" in system
    assert "Reference fix guidance for this kind of issue" in user and "do not cite it" in user
    assert "Check that the logged-in user owns the record" in user and "(1) Find the query" in user
    assert user.index("Reference fix guidance") < user.index("<evidence")  # guidance is not inside an evidence block
    assert "Example (python)" in user


def test_the_interpreted_report_lists_the_advice_for_confirmed_findings(tmp_path):
    out = tmp_path / "o"
    code = run(flow.main([str(SAVED / "python_full.json"), str(REPO), "--allow-external-llm", "--only-category", "V3",
                          "--out", str(out)], client=Mock()))
    assert code == 0
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "### How to fix the confirmed findings" in md
    assert md.count("Hash the password with bcrypt.hashpw instead of hashlib.md5.") == 4  # one per confirmed V3 finding
    assert "(standard advice: Hash passwords with bcrypt or Argon2)" in md
    doc = json.loads((out / "interpreted.json").read_text(encoding="utf-8"))
    assert all(g["result"]["recommendation"] for g in doc["groups"]) and doc["meta"]["prompt_version"] == "interpreter-v3"
    assert all(g["representative"]["fix_pattern"] for g in doc["groups"])


def test_no_advice_section_when_nothing_is_confirmed(tmp_path):
    out = tmp_path / "o"
    run(flow.main([str(SAVED / "python_full.json"), str(REPO), "--allow-external-llm", "--only-category", "V3", "--out", str(out)],
                  client=Mock(status="dismissed")))
    assert "### How to fix the confirmed findings" not in (out / "report.md").read_text(encoding="utf-8")


def test_reference_links_are_https_and_cheat_sheet_names_are_the_checked_ones():
    """The OWASP names below were opened and returned a page when this was written."""
    ok = {"Authentication", "Authorization", "Cross-Site_Request_Forgery_Prevention", "Cross_Site_Scripting_Prevention",
          "Error_Handling", "Input_Validation", "Insecure_Direct_Object_Reference_Prevention", "JSON_Web_Token",
          "OS_Command_Injection_Defense", "Password_Storage", "SQL_Injection_Prevention", "Secrets_Management",
          "Session_Management", "Vulnerable_Dependency_Management"}
    for g in guide.GUIDANCE:
        if g.reference.startswith(guide.OWASP):
            assert re.fullmatch(r"(.+)_Cheat_Sheet\.html", g.reference[len(guide.OWASP):]).group(1) in ok, g.reference


# ---- the model must not make up versions, SHAs or URLs ------------------------------------------------------------------------
def dep_case():
    from app.agents.security_assistant.interpreter.evidence import build_bundle
    finding = f(Category.V5, "GHSA-m2qf-hxjv-5gpq", "CWE-1104", path="requirements.txt", sink="flask@1.0 (PyPI)",
                message="CVE-2023-30861: cookie set on cached responses")
    return finding, build_bundle(finding, REPO)


def interpret_dep(recommendation):
    finding, bundle = dep_case()
    client = Mock(recommendation=recommendation)
    return run(SemanticInterpreter(client).interpret(finding, bundle))


def test_advice_that_names_a_version_not_in_the_evidence_is_dropped():
    result = interpret_dep("Upgrade Flask to a version that fixes the CVE, e.g. flask>=2.0.0 in requirements.txt.")
    assert result.status == "confirmed"  # the verdict stays
    assert result.recommendation == "" and "'2.0.0'" in result.recommendation_dropped


def test_advice_may_repeat_a_version_that_is_in_the_evidence():
    result = interpret_dep("The project pins flask==1.0; replace it with the fixed version named in the advisory.")
    assert result.recommendation.startswith("The project pins flask==1.0") and result.recommendation_dropped is None


def test_a_made_up_commit_sha_or_url_is_dropped_but_the_placeholder_is_fine():
    sha = "a1b2c3d4e5f67890123456789abcdef123456789"
    assert interpret_dep(f"Pin it: uses: actions/checkout@{sha}").recommendation_dropped
    assert interpret_dep("See https://example.org/fix-guide for details.").recommendation_dropped
    assert interpret_dep("Pin it: uses: actions/checkout@<full commit sha>").recommendation.endswith("<full commit sha>")


def test_numbers_that_are_not_versions_do_not_trigger_the_check():
    result = interpret_dep("Limit login to 5 attempts per minute and use HS256 with a 30 minute expiry.")
    assert result.recommendation and result.recommendation_dropped is None


def test_the_standard_dependency_examples_hold_no_concrete_version():
    for language, code in guide.by_id("dependency-upgrade").examples.items():
        assert not re.search(r"\d+\.\d+", code), (language, code)
    assert not re.search(r"\d+\.\d+", " ".join(guide.by_id("dependency-upgrade").steps))


def test_the_report_says_when_the_note_was_not_kept(tmp_path):
    out = tmp_path / "o"
    run(flow.main([str(SAVED / "python_deps.json"), str(REPO), "--allow-external-llm", "--only-category", "V5", "--out", str(out)],
                  client=Mock(recommendation="Use flask>=9.9.9 which does not exist in the evidence.")))
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "The model's note was not kept: the note named '9.9.9'" in md and "Use the standard advice." in md


# ---- OSV fix versions (parsed from OSV's own output, ecosystem ranges of the affected package only) --------------------------
OSV_RAW = {"results": [{"source": {"path": "/repo/requirements.txt"}, "packages": [{
    "package": {"name": "flask", "version": "1.0", "ecosystem": "PyPI"},
    "vulnerabilities": [{
        "id": "GHSA-m2qf-hxjv-5gpq", "aliases": ["CVE-2023-30861"], "summary": "cookie set on cached responses",
        "affected": [
            {"package": {"name": "flask", "ecosystem": "PyPI"}, "ranges": [
                {"type": "GIT", "repo": "https://github.com/pallets/flask",
                 "events": [{"introduced": "0"}, {"fixed": "70f906c51ce49c485f1d355703e9cc3386b1cc2b"}]},
                {"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "2.2.5"}]},
                {"type": "ECOSYSTEM", "events": [{"introduced": "2.3.0"}, {"fixed": "2.3.2"}]}]},
            {"package": {"name": "some-other-package", "ecosystem": "PyPI"},
             "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "9.9.9"}]}]},
            {"package": {"name": "flask", "ecosystem": "npm"},
             "ranges": [{"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "7.7.7"}]}]},
        ]}, {
        "id": "GHSA-no-fix", "summary": "no fix yet",
        "affected": [{"package": {"name": "flask", "ecosystem": "PyPI"},
                      "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}]}]}]}]}]}]}


def test_osv_fixed_versions_use_only_the_package_own_ecosystem_ranges():
    from app.agents.security_assistant.tools.dependencies import parse_osv
    found = {x.rule_id: x for x in parse_osv(OSV_RAW, Path("/repo"))}
    assert found["GHSA-m2qf-hxjv-5gpq"].fixed_versions == ["2.2.5", "2.3.2"]  # no hash, no other package, no other ecosystem
    assert found["GHSA-no-fix"].fixed_versions == []


@pytest.mark.parametrize("versions,expected", [
    (["2.10.0", "2.9.1", "2.2.5"], ["2.2.5", "2.9.1", "2.10.0"]),  # numeric order, not text order
    (["1.0", "1.0.1"], ["1.0", "1.0.1"]),
])
def test_fixed_versions_are_sorted_as_versions(versions, expected):
    from app.agents.security_assistant.tools.dependencies import fixed_versions_for
    vuln = {"affected": [{"package": {"name": "p", "ecosystem": "PyPI"},
                          "ranges": [{"type": "ECOSYSTEM", "events": [{"fixed": v} for v in versions]}]}]}
    assert fixed_versions_for(vuln, {"name": "P", "ecosystem": "PyPI"}) == expected


def test_a_maven_package_matches_by_its_full_name():
    from app.agents.security_assistant.tools.dependencies import fixed_versions_for
    vuln = {"affected": [{"package": {"name": "org.apache.logging.log4j:log4j-core", "ecosystem": "Maven"},
                          "ranges": [{"type": "ECOSYSTEM", "events": [{"fixed": "2.15.0"}]}]}]}
    info = {"name": "org.apache.logging.log4j:log4j-core", "ecosystem": "Maven"}
    assert fixed_versions_for(vuln, info) == ["2.15.0"]
    assert fixed_versions_for(vuln, {"name": "other:artifact", "ecosystem": "Maven"}) == []


def test_fixed_versions_reach_the_evidence_so_the_model_may_name_them():
    from app.agents.security_assistant.interpreter.evidence import build_bundle
    from app.agents.security_assistant.tools.dependencies import parse_osv
    finding = parse_osv(OSV_RAW, Path("/repo"))[0]
    bundle = build_bundle(finding)
    assert "fixed_versions: 2.2.5, 2.3.2" in bundle.items[0].content
    # the model may therefore name 2.2.5 (it is in the evidence) but not an invented version
    client = Mock(recommendation="Upgrade Flask to 2.3.2 or 2.2.5 in requirements.txt.")
    ok = run(SemanticInterpreter(client).interpret(finding, bundle))
    assert ok.recommendation and ok.recommendation_dropped is None
    bad = run(SemanticInterpreter(Mock(recommendation="Upgrade Flask to 2.0.0.")).interpret(finding, bundle))
    assert bad.recommendation == "" and "'2.0.0'" in bad.recommendation_dropped


def test_the_package_group_advisory_list_and_the_report_show_the_fixed_versions(tmp_path):
    from app.agents.security_assistant.dedupe import dedupe
    from app.agents.security_assistant.tools.dependencies import parse_osv
    findings = parse_osv(OSV_RAW, Path("/repo"))
    for x in findings:
        x.tool = "osv-scanner"  # the adapter base class stamps this after parsing
    groups, _ = dedupe(findings)
    assert groups[0].advisories[0]["fixed_versions"] == ["2.2.5", "2.3.2"]
    item = flow._advisory_item(groups[0])
    assert "GHSA-m2qf-hxjv-5gpq" in item.content and "fixed in 2.2.5, 2.3.2" in item.content
    from app.agents.security_assistant.schemas import ScanResult
    rep = build_report(ScanResult(run_id="x", repo_path="r", findings=findings), source="demo")
    assert "- **Fixed in:** 2.2.5, 2.3.2 (from the advisory)" in render_markdown(rep)
    assert json.loads(to_json(rep))["findings"][0]["fixed_versions"] == ["2.2.5", "2.3.2"]
