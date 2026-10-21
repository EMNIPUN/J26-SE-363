"""A V4 (secret) finding may only be dismissed with deterministic support: a test or example path, or a placeholder pattern
that the redactor recognised on the flagged line. Otherwise the dismissal becomes "uncertain" and the reason is recorded.
The LLM is a scripted mock; the prompt is untouched."""

import asyncio
import json

import pytest

from app.agents.security_assistant.interpreter.evidence import build_bundle
from app.agents.security_assistant.interpreter.interpreter import SemanticInterpreter, v4_dismissal_support
from app.agents.security_assistant.interpreter.models import EvidenceBundle, EvidenceItem
from app.agents.security_assistant.interpreter.prompts import SYSTEM_PROMPT
from app.agents.security_assistant.interpreter.seeded import load_cases
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.schemas import Category, Finding
from app.agents.security_assistant.tools.tests.conftest import FIXTURES


class Client:
    model = "mock"

    def __init__(self, status):
        self.status = status

    async def complete(self, system, user):
        return json.dumps({"status": self.status, "rationale": "it is only a placeholder", "evidence_ids": ["E1"], "confidence": 0.95})


def judge(finding, bundle, status="dismissed"):
    return asyncio.run(SemanticInterpreter(Client(status), PIIRedactor()).interpret(finding, bundle))


def snippet_bundle(finding, code_line):
    """E1 the finding, E2 a numbered snippet whose flagged line is `code_line` (as the redactor leaves it)."""
    return EvidenceBundle(items=[
        EvidenceItem(id="E1", kind="finding", label="finding", content=f"{finding.rule_id} {finding.file_path}:{finding.line}"),
        EvidenceItem(id="E2", kind="code_snippet", label="code", content=f"   1 | before\n>  2 | {code_line}\n   3 | after")])


def finding(path, line=2, rule="generic-api-key"):
    return Finding(category=Category.V4, rule_id=rule, tool="gitleaks", file_path=path, line=line, message="secret")


# ---- the two cases that were asked for ------------------------------------------------------------------------------------------------
def test_the_hardcoded_jwt_key_of_the_js_demo_is_not_dismissed():
    """vuln_js_repo/server.js:9 signs with the literal 'key'. The model called it a placeholder; nothing deterministic agrees."""
    f = Finding(category=Category.V4, rule_id="js/hardcoded-credentials", tool="codeql", file_path="server.js", line=9,
                message='The hard-coded value "key" is used as jwt key.')
    bundle = build_bundle(f, FIXTURES / "vuln_js_repo")
    assert "placeholder_like" not in "\n".join(i.content for i in bundle.items)  # the redactor sees no secret pattern here
    result = judge(f, bundle)
    assert result.status == "uncertain" and result.downgraded and result.original_status == "dismissed"
    assert "deterministic support" in result.downgrade_reason and "test or example file" in result.downgrade_reason


def test_a_placeholder_key_in_a_test_file_is_still_dismissed():
    f = finding("tests/test_client.py", line=2, rule="stripe-access-token")
    bundle = snippet_bundle(f, 'STRIPE_TEST_KEY = "[REDACTED secret kind=stripe_key len=32 placeholder_like=yes]"')
    result = judge(f, bundle)
    assert result.status == "dismissed" and not result.downgraded and result.original_status is None


# ---- each kind of support, on its own ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("path", ["tests/test_client.py", "src/test/java/demo/ConfigTest.java", "app/__tests__/auth.js", "client.spec.ts",
                                  "docs/examples/settings.py", "fixtures/keys.json", "conftest.py", ".env.example", "test_settings.py",
                                  "src\\tests\\keys.py"])
def test_a_test_or_example_path_supports_a_dismissal_even_for_a_value_that_is_not_a_known_placeholder(path):
    f = finding(path)
    bundle = snippet_bundle(f, 'KEY = "[REDACTED secret kind=credential len=24 placeholder_like=no]"')
    assert "test or example" in v4_dismissal_support(f, bundle)
    assert judge(f, bundle).status == "dismissed"


def test_a_recognised_placeholder_pattern_supports_a_dismissal_outside_test_paths():
    f = finding("config/settings.py")
    result = judge(f, snippet_bundle(f, 'API_KEY = "[REDACTED secret kind=credential len=20 placeholder_like=yes]"'))
    assert result.status == "dismissed" and not result.downgraded


def test_the_secret_details_item_can_carry_the_placeholder_support():
    f = finding("config/settings.py")
    bundle = EvidenceBundle(items=[
        EvidenceItem(id="E1", kind="finding", label="finding", content="x"),
        EvidenceItem(id="E9", kind="context", label="details about the secret",
                     content="kind: credential; length: 20 characters; looks like a placeholder: yes")])
    assert "placeholder" in v4_dismissal_support(f, bundle) and judge(f, bundle).status == "dismissed"


@pytest.mark.parametrize("path", ["src/main/config.py", "latest/prod.py", "contest/app.py", "protests.txt", "app/attest.js", None])
def test_other_paths_give_no_support_and_a_placeholder_marker_elsewhere_in_the_snippet_does_not_count(path):
    f = finding(path)
    bundle = snippet_bundle(f, 'KEY = "[REDACTED secret kind=credential len=24 placeholder_like=no]"')
    bundle.items[1].content += '\n   9 | OTHER = "[REDACTED secret kind=credential len=8 placeholder_like=yes]"'  # not the flagged line
    assert v4_dismissal_support(f, bundle) is None
    result = judge(f, bundle)
    assert result.status == "uncertain" and result.downgraded and result.original_status == "dismissed"


# ---- nothing else changes ------------------------------------------------------------------------------------------------------------------
def test_confirmed_and_uncertain_v4_verdicts_and_other_categories_are_untouched():
    f = finding("src/main/config.py")
    bundle = snippet_bundle(f, 'KEY = "[REDACTED secret kind=credential len=24 placeholder_like=no]"')
    assert judge(f, bundle, "confirmed").status == "confirmed" and not judge(f, bundle, "confirmed").downgraded
    assert judge(f, bundle, "uncertain").status == "uncertain" and not judge(f, bundle, "uncertain").downgraded
    v5 = Finding(category=Category.V5, rule_id="GHSA-x", tool="osv-scanner", file_path="requirements.txt", message="m")
    assert judge(v5, snippet_bundle(v5, "requests==2.19.0")).status == "dismissed"


def test_the_seeded_false_positive_is_still_dismissed_and_the_real_key_is_not_dismissable():
    cases = {c.id: c for c in load_cases()}
    fp, real = cases["v4-fp-test-api-key"], cases["v4-real-aws-keys-in-prod-settings"]
    assert judge(fp.finding, fp.bundle).status == "dismissed"
    assert judge(real.finding, real.bundle).status == "uncertain"  # a mistaken dismissal of a real key can no longer pass


def test_the_prompt_was_not_changed():
    assert "deterministic support" not in SYSTEM_PROMPT and "test or example" not in SYSTEM_PROMPT
