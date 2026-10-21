"""The evidence for a dependency finding says where the package is used in the project.

Verification question: the LLM dismissed the advisories of the JS demo repo "although express is imported". They were all lodash
advisories (the fixture's package-lock.json lists lodash alone, express is only in package.json) and no source file mentions
lodash, so the evidence was right. These tests pin that the usage search works for a package that IS imported."""

import pytest

from app.agents.security_assistant.interpreter.evidence import build_bundle
from app.agents.security_assistant.schemas import Category, Finding
from app.agents.security_assistant.tools.tests.conftest import FIXTURES

JS = FIXTURES / "vuln_js_repo"


def usage(sink, repo=JS):
    finding = Finding(category=Category.V5, rule_id="GHSA-test", tool="osv-scanner", file_path="package-lock.json", sink=sink, message="m")
    item = next((i for i in build_bundle(finding, repo).items if "is used in the project" in i.label), None)
    return item.content if item else None


@pytest.mark.parametrize("sink, expected", [
    ("express@4.17.1 (npm)", "server.js:1"), ("express 4.17.1", "server.js:1"),
    ("jsonwebtoken@8.5.1 (npm)", "server.js:2"), ("express-session@1.17.0 (npm)", "server.js:4")])
def test_an_imported_package_is_found_with_the_line_that_imports_it(sink, expected):
    content = usage(sink)
    assert content.startswith(expected) and "require(" in content


def test_a_package_no_source_file_mentions_is_reported_as_unused():
    assert usage("lodash@4.17.15 (npm)") == "(no source file mentions it)"


def test_the_js_fixture_lockfile_lists_lodash_only_so_express_is_never_scanned():
    lock = (JS / "package-lock.json").read_text(encoding="utf-8")
    assert "node_modules/lodash" in lock and "node_modules/express" not in lock
    assert '"express"' in (JS / "package.json").read_text(encoding="utf-8")
