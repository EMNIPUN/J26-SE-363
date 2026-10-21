"""Risk prioritisation: the score is a transparent rule engine over saved interpreter output. No LLM, scanner or network."""

import copy
import json
import random
import subprocess
from pathlib import Path

import pytest

from app.agents.security_assistant import risk


def brief(rule, cat="V1", sev="high", fix="ownership-check", file="app.py", line=10, source=None, endpoint=None):
    return {"finding_key": rule, "category": cat, "tool": "t", "rule_id": rule, "file_path": file, "line": line,
            "fix_pattern": fix, "severity_tool": sev, "cwe": None, "source": source, "sink": None,
            "function_or_endpoint": endpoint, "message": ""}


def group(gid, rep, status="confirmed", confidence=0.9, members=None, package=None):
    return {"group_id": gid, "kind": "single", "package": package, "representative": rep, "members": members or [rep],
            "result": {"status": status, "confidence": confidence, "rationale": "r", "evidence_ids": ["E1"]}}


def doc(*groups):
    return {"meta": {}, "summary": {}, "merge_log": [], "groups": list(groups)}


def entry(g, repo=None):
    return risk.score_group(g, repo)


def by_factor(e):
    return {f["factor"]: f for f in e["factors"]}


# ---- the score ----------------------------------------------------------------------------------------------------------------------
def test_the_weights_add_up_to_one():
    assert sum(risk.WEIGHTS.values()) == pytest.approx(1.0)


def test_a_known_finding_scores_exactly_as_the_rules_say():
    e = entry(group("G01", brief("r"), confidence=0.9))
    f = by_factor(e)
    # severity high 0.8, category V1 1.0, confirmed 1.0, confidence 0.9, exposure ownership-check 0.9, current 1.0
    assert [f[k]["contribution"] for k in risk.WEIGHTS] == [24.0, 15.0, 20.0, 9.0, 13.5, 10.0]
    assert e["score"] == 91.5


def test_the_score_is_deterministic():
    g = group("G01", brief("r"), confidence=0.77)
    assert entry(g) == entry(copy.deepcopy(g))
    assert json.dumps(risk.rank(doc(g))) == json.dumps(risk.rank(doc(copy.deepcopy(g))))


@pytest.mark.parametrize("conf", [0.0, 0.123, 0.333, 0.5, 0.777, 0.999, 1.0])
@pytest.mark.parametrize("sev", ["critical", "7.5", "moderate", "weird", None])
def test_the_breakdown_sums_to_the_total(conf, sev):
    e = entry(group("G01", brief("r", sev=sev, cat="V3", fix="cookie-flags"), status="uncertain", confidence=conf))
    assert round(sum(f["contribution"] for f in e["factors"]), 2) == e["score"]
    recomputed = 100 * sum(f["weight"] * f["value"] for f in e["factors"])
    assert e["score"] == pytest.approx(recomputed, abs=0.03)  # only the rounding of each contribution to 2 decimals differs
    assert all(f["detail"] for f in e["factors"])  # every factor says why


def test_every_factor_is_stored_with_its_weight_value_and_contribution():
    e = entry(group("G01", brief("r")))
    assert [f["factor"] for f in e["factors"]] == list(risk.WEIGHTS)
    for f in e["factors"]:
        assert set(f) == {"factor", "weight", "value", "contribution", "detail"} and f["weight"] == risk.WEIGHTS[f["factor"]]


# ---- statuses -----------------------------------------------------------------------------------------------------------------------------
def test_dismissed_findings_are_excluded_and_listed_as_not_ranked():
    out = risk.rank(doc(group("G01", brief("a")), group("G02", brief("b"), status="dismissed", confidence=0.99)))
    assert [e["group_id"] for e in out["ranked"]] == ["G01"]
    assert out["excluded"][0]["group_id"] == "G02" and "false positive" in out["excluded"][0]["reason"]


def test_an_uncertain_finding_is_down_weighted_by_the_status_factor_only():
    c, u = entry(group("G01", brief("r"))), entry(group("G01", brief("r"), status="uncertain"))
    assert c["score"] - u["score"] == pytest.approx(100 * risk.WEIGHTS["llm_status"] * (1.0 - 0.4))
    assert u["score"] < c["score"]


# ---- the other factors -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw, value", [("CRITICAL", 1.0), ("High", 0.8), ("moderate", 0.5), ("MEDIUM", 0.5), ("low", 0.2),
                                        ("9.8", 1.0), ("7.0", 0.8), ("5.3", 0.5), ("2.0", 0.2), (None, 0.4), ("???", 0.4)])
def test_severity_is_normalised(raw, value):
    assert risk.severity_factor(raw)[0] == value


def test_a_package_group_uses_the_highest_severity_of_its_advisories():
    members = [brief("a", cat="V5", sev="low", fix="dependency-upgrade"), brief("b", cat="V5", sev="critical", fix="dependency-upgrade")]
    e = entry(group("G01", members[0], members=members, package="requests"))
    assert by_factor(e)["severity"]["value"] == 1.0 and "highest of the group" in by_factor(e)["severity"]["detail"]


def test_an_endpoint_raises_exposure_but_never_lowers_it():
    assert risk.exposure_of(brief("r", fix="weak-password-hash", endpoint="/login"))[0] == 0.9
    assert risk.exposure_of(brief("r", fix="workflow-trigger", endpoint="/x"))[0] == 1.0
    assert risk.exposure_of(brief("r", fix="something-new"))[0] == risk.DEFAULT_EXPOSURE[0]


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=a", "-c", "user.email=a@b.org", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def secret_repo(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q")
    (r / "live.py").write_text('KEY = "AKIA' + 'QYLPMN5HHHFPZAM2"\n')
    (r / "gone.py").write_text('KEY = "AKIA' + 'QYLPMN5HHHFPZAM2"\n')
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "x")
    (r / "gone.py").unlink()
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "y")
    return r


def test_a_secret_only_in_the_history_scores_lower_than_one_still_in_the_files(secret_repo):
    live = group("G01", brief("aws", cat="V4", fix="hardcoded-secret", file="live.py", line=1, source="commit:" + "a" * 40))
    gone = group("G02", brief("aws", cat="V4", fix="hardcoded-secret", file="gone.py", line=1, source="commit:" + "a" * 40))
    a, b = entry(live, secret_repo), entry(gone, secret_repo)
    assert a["presence"] == "current" and b["presence"] == "history_only"
    assert a["score"] - b["score"] == pytest.approx(100 * risk.WEIGHTS["presence"] * 0.4)
    assert "not in the current files" in by_factor(b)["presence"]["detail"]


def test_a_scanner_finding_in_the_current_files_is_current_without_a_repo():
    assert risk.presence_of(brief("r"), None)[0] == "current"
    state, why = risk.presence_of(brief("r", source="commit:" + "b" * 40), None)
    assert state == "current" and "not checked" in why


# ---- the ranking ---------------------------------------------------------------------------------------------------------------------
def test_ranking_puts_the_riskier_finding_first():
    sql = group("G01", brief("sqli", cat="V2", fix="sql-injection"), confidence=0.9)
    old = group("G02", brief("old-dep", cat="V5", sev="low", fix="dependency-upgrade", file="requirements.txt"), confidence=0.6)
    unsure = group("G03", brief("sqli2", cat="V2", fix="sql-injection"), status="uncertain", confidence=0.4)
    out = risk.rank(doc(old, unsure, sql))
    assert [e["group_id"] for e in out["ranked"]] == ["G01", "G03", "G02"]
    assert [e["rank"] for e in out["ranked"]] == [1, 2, 3]
    assert out["ranked"][0]["score"] > out["ranked"][1]["score"] > out["ranked"][2]["score"]


def test_the_order_does_not_depend_on_the_input_order_and_ties_are_broken_by_rule():
    groups = [group(f"G{i:02d}", brief(rule), confidence=0.5) for i, rule in enumerate(["b", "a", "c", "a"], 1)]
    expected = [e["group_id"] for e in risk.rank(doc(*groups))["ranked"]]
    for seed in range(5):
        shuffled = groups[:]
        random.Random(seed).shuffle(shuffled)
        assert [e["group_id"] for e in risk.rank(doc(*shuffled))["ranked"]] == expected
    assert expected == ["G02", "G04", "G01", "G03"]  # equal score: rule id a, a, b, c; then group id


def test_equal_scores_are_ordered_by_group_id_last():
    a = group("G01", brief("z", cat="V5", sev="critical", fix="dependency-upgrade"))
    b = group("G02", brief("z", cat="V5", sev="critical", fix="dependency-upgrade"))
    assert [e["group_id"] for e in risk.rank(doc(b, a))["ranked"]] == ["G01", "G02"]


def test_the_score_uses_no_llm():
    source = Path(risk.__file__).read_text(encoding="utf-8")
    assert "interpreter.llm" not in source and "GroqClient" not in source and risk.rank(doc())["meta"]["uses_llm"] is False


# ---- the command ----------------------------------------------------------------------------------------------------------------------
def test_the_command_writes_risk_json_and_a_report_section(tmp_path, capsys):
    p = tmp_path / "interpreted.json"
    p.write_text(json.dumps(doc(group("G01", brief("sqli", cat="V2", fix="sql-injection")),
                                group("G02", brief("fp"), status="dismissed"))), encoding="utf-8")
    (tmp_path / "report.md").write_text("# scan\n", encoding="utf-8")
    assert risk.main([str(p)]) == 0
    data = json.loads((tmp_path / "risk.json").read_text(encoding="utf-8"))
    assert [e["group_id"] for e in data["ranked"]] == ["G01"] and data["excluded"][0]["group_id"] == "G02"
    md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "## Risk prioritisation" in md and "| 1 | G01 |" in md and "### Not ranked" in md and md.startswith("# scan")
    assert risk.main([str(p)]) == 0
    assert (tmp_path / "report.md").read_text(encoding="utf-8").count("## Risk prioritisation") == 1
    assert "1 ranked, 1 not ranked" in capsys.readouterr().out


def test_the_command_reports_a_bad_input(tmp_path, capsys):
    assert risk.main([str(tmp_path / "missing.json")]) == 3
    assert "cannot read the input" in capsys.readouterr().err
