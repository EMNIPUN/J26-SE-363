"""RQ1 comparison: ground truth parsing, metric arithmetic, and that nothing is invented. No LLM, scanner or network."""

import csv
import json
from pathlib import Path

import pytest

from app.agents.security_assistant import rq1
from app.agents.security_assistant.interpreter.seeded import load_cases

SAVED = Path(__file__).parent / "saved" / "python_full.json"


def bug(n, cat, file, lines=(), codeql=False, miss=False):
    return rq1.Bug("r", n, cat, "t", file, set(lines), codeql, miss)


def item(cat, file, line, status=None, rule="x"):
    return rq1.Item(cat, file, line, rule, status)


# ---- the ground truth file ---------------------------------------------------------------------------------------------------------
def test_planted_bugs_md_is_parsed_into_the_four_repositories():
    repos = rq1.parse_planted()
    assert {k: len(v) for k, v in repos.items()} == {"vuln_py_repo": 11, "vuln_js_repo": 12, "vuln_java_repo": 12, "vuln_java_gradle_repo": 13}
    py = {b.number: b for b in repos["vuln_py_repo"]}
    assert py[1].lines == {19, 20, 21, 22} and py[1].file == "app.py" and py[1].needs_codeql and py[1].category == "V1"
    assert py[7].file == "settings_old.py" and py[7].lines == set() and not py[7].needs_codeql
    assert py[9].file == "ci.yml" and py[9].lines == {1}
    js = {b.number: b for b in repos["vuln_js_repo"]}
    assert js[4].known_miss and js[5].known_miss and not js[1].known_miss
    assert {b.number: b.lines for b in repos["vuln_java_repo"]}[2] == {6}
    assert {b.number: b.lines for b in repos["vuln_java_gradle_repo"]}[12] == {4, 5, 6, 7, 8}


def test_matching_needs_category_file_name_and_a_listed_line():
    b = bug(1, "V1", "app.py", {19, 20})
    assert rq1.matches(b, "V1", "app.py", 19) and rq1.matches(b, "V1", "src/app.py", 20)
    assert not rq1.matches(b, "V2", "app.py", 19) and not rq1.matches(b, "V1", "other.py", 19) and not rq1.matches(b, "V1", "app.py", 99)
    assert rq1.matches(b, "V1", "app.py", None)  # no line number: matched on file alone (manifest advisories carry none)
    assert rq1.matches(bug(2, "V5", "requirements.txt"), "V5", "requirements.txt", None)  # no listed line: file alone
    assert rq1.matches(bug(3, "V5", "ci.yml", {1}), "V5", ".github/workflows/ci.yml", 1)


# ---- the arithmetic ------------------------------------------------------------------------------------------------------------------
def test_scanner_only_and_llm_columns_are_computed_from_the_statuses():
    bugs = [bug(1, "V1", "a.py", {5}), bug(2, "V3", "b.py", {2}), bug(3, "V5", "req.txt")]
    items = [item("V1", "a.py", 5, "confirmed"),  # true, kept
             item("V3", "b.py", 2, "dismissed"),  # true, dismissed by the model (lost)
             item("V2", "c.py", 9, "dismissed"),  # not planted, dismissed (removed false positive)
             item("V2", "c.py", 10, "confirmed"),  # not planted, kept
             item("V5", "req.txt", None, "dismissed"),  # file-only match, dismissed
             item("V4", "d.py", 1, "uncertain")]  # not planted, uncertain
    r = rq1.evaluate_repo("r", bugs, items, True, True, "m")
    assert (r["scanner_only_reported"], r["scanner_only_tp"], r["scanner_only_fp"], r["scanner_only_precision"]) == (6, 3, 3, "0.500")
    assert (r["llm_confirmed"], r["llm_dismissed"], r["llm_uncertain"]) == (2, 3, 1)
    assert (r["llm_tp_kept"], r["llm_fp_kept"], r["llm_precision"]) == (1, 1, "0.500")
    # the V3 dismissal is a lost true positive; the V5 dismissal is "dismissed as unreachable" in its own column
    assert (r["llm_fp_removed"], r["llm_true_findings_dismissed"], r["llm_dismissed_file_only"]) == (1, 1, 0)
    assert r["llm_v5_dismissed_unreachable"] == 1 and r["llm_bugs_set_aside_unreachable"] == 1
    assert (r["planted_expected"], r["scanner_only_bugs_found"], r["llm_bugs_found"]) == (3, 3, 1)
    assert (r["scanner_only_recall"], r["llm_recall"]) == ("1.000", "0.500")  # 1 of the 2 bugs not set aside as unreachable
    assert "lost true positives" in r["notes"] and "dismissed as unreachable" in r["notes"]


def test_a_removed_false_positive_raises_precision():
    bugs = [bug(1, "V1", "a.py", {5})]
    items = [item("V1", "a.py", 5, "confirmed")] + [item("V2", "x.py", n, "dismissed") for n in range(3)]
    r = rq1.evaluate_repo("r", bugs, items, True, True, "m")
    assert r["scanner_only_precision"] == "0.250" and r["llm_precision"] == "1.000" and r["llm_fp_removed"] == 3


def test_codeql_bugs_are_not_expected_when_codeql_did_not_run_and_known_misses_never_are():
    bugs = [bug(1, "V1", "a.py", {5}, codeql=True), bug(2, "V3", "b.py", {2}), bug(3, "V2", "c.js", {1}, codeql=True, miss=True)]
    r = rq1.evaluate_repo("r", bugs, [item("V3", "b.py", 2)], False, False, "scanner only")
    assert r["planted_expected"] == 1 and r["planted_known_miss"] == 1 and r["scanner_only_recall"] == "1.000"
    assert "CodeQL did not run" in r["notes"] and "llm_confirmed" not in r and "no saved LLM run" in r["notes"]
    assert rq1.evaluate_repo("r", bugs, [item("V3", "b.py", 2)], True, False, "x")["planted_expected"] == 2


def test_empty_denominators_give_blanks_not_zero_or_errors():
    r = rq1.evaluate_repo("r", [bug(1, "V1", "a.py", {5})], [item("V2", "z.py", 1, "dismissed")], True, True, "m")
    assert r["llm_precision"] == "" and r["scanner_only_precision"] == "0.000"


# ---- nothing is invented ------------------------------------------------------------------------------------------------------------
def test_a_repo_without_a_saved_scan_gets_a_row_that_says_so(tmp_path):
    rows, details, cases = rq1.run_comparison([], None)
    by = {r["name"]: r for r in rows}
    for name in ("vuln_py_repo", "vuln_js_repo", "vuln_java_repo", "vuln_java_gradle_repo"):
        assert by[name]["run"] == "none" and "no saved scan" in by[name]["notes"] and "scanner_only_reported" not in by[name]
    assert details == [] and "TOTAL (repos with a saved LLM run)" not in by


def test_the_deliberate_false_positives_report_scanner_only_without_llm_numbers():
    row, detail = rq1.seeded_suite(None)
    assert (row["scanner_only_reported"], row["scanner_only_tp"], row["scanner_only_fp"], row["scanner_only_precision"]) == (10, 5, 5, "0.500")
    assert "llm_confirmed" not in row and "no number is invented" in row["notes"]
    assert len(detail) == 10 and {d["ground_truth"] for d in detail} == {"confirmed", "dismissed"}
    assert all(d["llm_status"] == "" for d in detail)


def test_saved_seeded_results_fill_the_llm_columns_and_a_mock_is_labelled(tmp_path):
    cases = load_cases()
    perfect = {"model": "mock-oracle", "live": False, "cases": [{"id": c.id, "ground_truth": c.ground_truth, "status": c.ground_truth} for c in cases]}
    row, detail = rq1.seeded_suite(perfect)
    assert row["llm_precision"] == "1.000" and row["llm_fp_removed"] == 5 and row["llm_true_findings_dismissed"] == 0
    assert "MOCK ORACLE" in row["run"] and all(d["llm_correct"] == "True" for d in detail)
    live = dict(perfect, live=True, model="real-model")
    live["cases"] = [dict(c, status="confirmed") for c in perfect["cases"]]  # a model that confirms everything
    row, _ = rq1.seeded_suite(live)
    assert row["llm_precision"] == "0.500" and row["llm_fp_kept"] == 5 and "MOCK" not in row["run"]
    partial = dict(perfect, cases=perfect["cases"][:3])
    assert "3 of 10 cases" in rq1.seeded_suite(partial)[0]["notes"]


# ---- the files and the command ---------------------------------------------------------------------------------------------------
def interpreted_for(status_by_rule: dict, default="confirmed"):
    findings = json.loads(SAVED.read_text(encoding="utf-8"))["findings"]
    groups = [{"group_id": f"G{i}", "kind": "single", "package": None,
               "members": [{"category": f["category"], "file_path": f.get("file_path"), "line": f.get("line"), "rule_id": f["rule_id"]}],
               "result": {"status": status_by_rule.get(f["rule_id"], default)}} for i, f in enumerate(findings, 1)]
    return {"meta": {"model": "test-model", "prompt_version": "p"}, "groups": groups}


def test_command_writes_the_three_csv_files_from_saved_findings(tmp_path, capsys):
    interp = tmp_path / "i.json"
    interp.write_text(json.dumps(interpreted_for({"zizmor:unpinned-uses": "dismissed"})), encoding="utf-8")
    assert rq1.main(["--repo", f"vuln_py_repo={SAVED},{interp}", "--out", str(tmp_path / "out")]) == 0
    rows = list(csv.DictReader(open(tmp_path / "out" / "rq1_comparison.csv", encoding="utf-8")))
    py = next(r for r in rows if r["name"] == "vuln_py_repo")
    assert py["findings_analysed"] == "12" and py["run"] == "test-model / p" and py["llm_dismissed"] == "1"
    assert int(py["planted_expected"]) >= 9  # python_full.json has a succeeded CodeQL run, so V1 and V2 are expected
    findings = list(csv.DictReader(open(tmp_path / "out" / "rq1_findings.csv", encoding="utf-8")))
    assert len(findings) == 12 and {"matches_planted_bug", "ground_truth", "llm_status"} <= set(findings[0])
    assert len(list(csv.DictReader(open(tmp_path / "out" / "rq1_cases.csv", encoding="utf-8")))) == 10
    assert "Wrote" in capsys.readouterr().out


def test_scanner_only_input_has_no_llm_columns(tmp_path):
    rows, _, _ = rq1.run_comparison([f"vuln_py_repo={SAVED}"], None)
    py = next(r for r in rows if r["name"] == "vuln_py_repo")
    assert py["run"] == "scanner only" and "llm_confirmed" not in py and py["scanner_only_reported"] == 12


def test_unknown_repository_and_missing_file_are_usage_errors(tmp_path, capsys):
    assert rq1.main(["--repo", "nope=x.json", "--out", str(tmp_path)]) == 3
    assert rq1.main(["--repo", f"vuln_py_repo={tmp_path / 'missing.json'}", "--out", str(tmp_path)]) == 3
    assert "cannot run" in capsys.readouterr().err


def test_a_dependency_advisory_without_a_line_matches_a_bug_that_lists_manifest_lines():
    """Regression: vuln_java_repo lists pom.xml:6,8 but OSV reports pom.xml findings without a line, so the bug was reported missed."""
    bugs = rq1.parse_planted()["vuln_java_repo"]
    pom = next(b for b in bugs if b.file == "pom.xml")
    assert pom.lines and rq1.matches(pom, "V5", "pom.xml", None)
    assert not rq1.matches(pom, "V5", "other.xml", None) and not rq1.matches(pom, "V4", "pom.xml", None)
    assert not rq1.matches(pom, "V5", "pom.xml", 99)  # a line that is given must still be one of the listed lines


def test_an_assess_report_json_is_accepted_as_the_llm_run(tmp_path):
    """assess writes report.json without the group members; rq1 regroups the scan the same way and reads the statuses."""
    from app.agents.security_assistant.dedupe import dedupe
    from app.agents.security_assistant.report import from_json

    findings_doc = json.loads(SAVED.read_text(encoding="utf-8"))
    groups, _ = dedupe(from_json(SAVED.read_text(encoding="utf-8"))[0].findings)
    report = {"report_version": "assessment-v1", "meta": {"llm_model": "m", "interpreter_prompt": "p"},
              "findings": [{"group_id": g.id, "status": "dismissed" if g.representative.category.value == "V5" else "confirmed"} for g in groups]}
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    rows, _, _ = rq1.run_comparison([f"vuln_py_repo={SAVED},{path}"], None)
    py = next(r for r in rows if r["name"] == "vuln_py_repo")
    assert py["run"] == "m / p" and py["findings_analysed"] == 12
    assert py["llm_confirmed"] + py["llm_dismissed"] == 12 and py["llm_dismissed"] == 4  # the four V5 findings were dismissed



def test_v5_dismissals_are_not_lost_recall_but_a_non_v5_dismissal_is():
    bugs = [bug(1, "V5", "req.txt"), bug(2, "V5", "pom.xml", {6}), bug(3, "V1", "a.py", {5})]
    items = [item("V5", "req.txt", None, "dismissed"), item("V5", "req.txt", None, "confirmed"),  # bug 1 keeps a confirmed finding
             item("V5", "pom.xml", None, "dismissed"), item("V5", "pom.xml", None, "dismissed"),  # bug 2: only unreachable dismissals
             item("V1", "a.py", 5, "dismissed")]  # bug 3 really lost
    r = rq1.evaluate_repo("r", bugs, items, True, True, "m")
    assert r["llm_v5_dismissed_unreachable"] == 3 and r["llm_true_findings_dismissed"] == 1
    assert (r["llm_bugs_found"], r["llm_bugs_set_aside_unreachable"], r["llm_recall"]) == (1, 1, "0.500")  # 1 of (3 - 1 set aside)
    total = rq1.total_row([r])
    assert total["llm_v5_dismissed_unreachable"] == 3 and total["llm_recall"] == "0.500"
