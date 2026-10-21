"""The same place seen twice is one LLM call (rules in dedupe.py); different weaknesses are never merged."""

from app.agents.security_assistant import interpret as flow
from app.agents.security_assistant.dedupe import dedupe
from app.agents.security_assistant.schemas import Category, Finding, ScanResult


def f(cat, tool, rule, file, line, source=None, severity=None, message=""):
    return Finding(category=cat, tool=tool, rule_id=rule, file_path=file, line=line, source=source, severity_tool=severity, message=message)


def test_two_tools_on_the_same_line_and_category_are_one_group_and_the_others_are_listed():
    a = f(Category.V3, "config-scan", "cfg-005", "app.py", 13, message="weak hash")
    b = f(Category.V3, "codeql", "py/weak-sensitive-data-hashing", "app.py", 13, severity="HIGH", message="md5 of a password")
    groups, log = dedupe([a, b])
    assert len(groups) == 1 and groups[0].kind == "location" and groups[0].members == [a, b]
    assert groups[0].representative is b  # the higher severity wins, ties keep the first
    assert [x["id"] for x in groups[0].advisories] == ["cfg-005"]
    assert log == [{"type": "same place reported by several tools", "package": "app.py:13", "kept": "codeql:py/weak-sensitive-data-hashing",
                    "merged": ["config-scan:cfg-005"]}]


def test_different_weaknesses_of_one_tool_on_one_line_stay_separate():
    groups, _ = dedupe([f(Category.V1, "codeql", "ownership", "app.py", 22), f(Category.V2, "codeql", "sql-injection", "app.py", 22)])
    assert [g.kind for g in groups] == ["single", "single"]
    groups, _ = dedupe([f(Category.V5, "zizmor", "excessive-permissions", "ci.yml", 1), f(Category.V5, "zizmor", "dangerous-triggers", "ci.yml", 1)])
    assert len(groups) == 2  # same tool: not a duplicate


def test_different_categories_or_lines_or_files_are_not_merged():
    groups, _ = dedupe([f(Category.V3, "config-scan", "x", "app.py", 13), f(Category.V2, "codeql", "y", "app.py", 13),
                        f(Category.V3, "codeql", "z", "app.py", 14), f(Category.V3, "codeql", "w", "other.py", 13)])
    assert len(groups) == 4


def test_a_key_pair_found_by_two_secret_scanners_on_adjacent_lines_is_one_group():
    commit = "commit:" + "a" * 40
    findings = [f(Category.V4, "gitleaks", "aws-access-token", "settings_old.py", 1, commit),
                f(Category.V4, "gitleaks", "generic-api-key", "settings_old.py", 2, commit),
                f(Category.V4, "trufflehog", "AWS", "settings_old.py", 1, commit)]
    groups, log = dedupe(findings)
    assert len(groups) == 1 and len(groups[0].members) == 3 and groups[0].kind == "location"
    assert log[0]["type"] == "same place reported by several tools" and len(log[0]["merged"]) == 2


def test_secrets_far_apart_or_from_another_commit_or_file_are_not_merged():
    c1, c2 = "commit:" + "a" * 40, "commit:" + "b" * 40
    groups, _ = dedupe([f(Category.V4, "gitleaks", "k", "s.py", 1, c1), f(Category.V4, "gitleaks", "k", "s.py", 10, c1),  # far apart
                        f(Category.V4, "gitleaks", "k", "s.py", 2, c2),  # another commit
                        f(Category.V4, "gitleaks", "k", "t.py", 1, c1)])  # another file
    assert len(groups) == 4


def test_the_group_keeps_the_position_of_its_first_member_and_ids_stay_sequential():
    findings = [f(Category.V1, "codeql", "a", "a.py", 1), f(Category.V3, "config-scan", "b", "b.py", 5),
                f(Category.V2, "codeql", "c", "c.py", 2), f(Category.V3, "codeql", "d", "b.py", 5)]
    groups, _ = dedupe(findings)
    assert [g.id for g in groups] == ["G01", "G02", "G03"] and [g.representative.rule_id for g in groups] == ["a", "b", "c"]
    assert groups[1].kind == "location" and len(groups[1].members) == 2


def test_the_merged_call_carries_the_other_findings_as_evidence_and_covers_all_members(tmp_path):
    (tmp_path / "app.py").write_text("x = 1\n" * 20, encoding="utf-8")
    result = ScanResult(run_id="r", repo_path=str(tmp_path), findings=[
        f(Category.V3, "config-scan", "cfg-005", "app.py", 13, message="weak hash"),
        f(Category.V3, "codeql", "py/weak-hash", "app.py", 13, message="md5 of a password")])
    plan = flow.make_plan(result, tmp_path)
    assert len(plan.calls) == 1 and plan.selected_findings == 2 and len(plan.calls[0].group.members) == 2
    extra = [i for i in plan.calls[0].bundle.items if "same place" in i.label]
    # the first member is the representative (equal severity), so the evidence lists the other one
    assert extra and "py/weak-hash" in extra[0].content and "reported by codeql" in extra[0].content
    assert "MERGED" in flow.render_dry_run(plan, "m") and "same place" not in flow.render_dry_run(plan, "m").split("MERGED")[0]
