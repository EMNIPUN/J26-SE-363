"""Security Assistant routes: who may read which team's runs, and what is in an overview."""

import json

import pytest

from app.main import app
from app.modules.security.reader import ResultsReader
from app.modules.security.router import get_reader
from tests.test_teams_api import join_all, lecturer, new_team, onboard, student

CODE = "TEAM-ALPHA"
RUN = "2026-10-21T0930-manual-a1b2c3d"
MINE = "C-0a1b2c3d"


def report(findings=None, complete=True):
    return {
        "report_version": "assessment-v1",
        "meta": {"source": "demo", "llm_model": "mock-model", "temperature": 0.0, "interpreter_prompt": "interpreter-v4",
                 "trace_prompt": "link-v1", "risk_version": "risk-v1", "threshold": 0.7},
        "run": {"complete": complete, "incomplete_reasons": [] if complete else ["stage interpret partial: x"], "llm_refused": False,
                "stages": [{"stage": "fetch", "status": "completed", "detail": "ok", "seconds": 0.1}]},
        "scan": {"languages": ["python"], "complete": complete, "skipped_tools": [], "warnings": [], "reused": False, "coverage_gaps": [],
                 "tool_runs": [{"tool": "semgrep", "status": "succeeded", "reason": "", "tool_version": "1.0", "duration_s": 1.0, "findings_count": 1}],
                 "coverage": {"V1": {"level": "FULL", "note": "semgrep ran", "tools": {}}}},
        "llm_usage": {"seed": 7, "total_tokens": 1234},
        "questions": {"meta": {"tutor_is_mock": True}, "summary": {}},
        "findings": findings if findings is not None else [
            {"group_id": "G1", "category": "V2", "status": "confirmed", "introducing_commit": {"sha": "abc1234", "contributor": MINE}},
            {"group_id": "G2", "category": "V4", "status": "dismissed", "introducing_commit": None}],
    }


@pytest.fixture
def results(tmp_path):
    app.dependency_overrides[get_reader] = lambda: ResultsReader(tmp_path)
    folder = tmp_path / CODE / RUN
    folder.mkdir(parents=True)
    (folder / "report.json").write_text(json.dumps(report()), encoding="utf-8")
    (folder / "run.json").write_text(json.dumps({"started_at": "2026-10-21T09:30:00Z", "trigger": "manual", "scan_type": "full",
                                                 "repo": "https://github.com/o/r", "commit_sha": "a" * 40, "checkout": {"kind": "clone-tempdir"}}), encoding="utf-8")
    (folder / "trace_mapping.local.json").write_text(json.dumps({"salt": "s", "contributors": {MINE: {"name": "Sam", "email": "sam@example.com"}}}),
                                                     encoding="utf-8")
    return tmp_path


@pytest.fixture
def team(api, results):
    """TEAM-ALPHA with a lecturer (ada) and students sam, kim, lee; zed is a student with no team."""
    lecturer(api, "ada")
    new_team(api)
    join_all(api)
    student(api, "zed")
    return CODE


def runs_url(code=CODE):
    return f"/security-assistant/teams/{code}/runs"


def as_user(api, sub):
    api.sign_in(sub, email=f"{sub}@example.com", name=sub.title())


def students_of(api):
    as_user(api, "ada")
    return api.get(f"/security-assistant/teams/{CODE}/students").json()


# ---- access ---------------------------------------------------------------------------------------------------------------------------
def test_a_route_without_a_token_is_401(api, team):
    api.sign_out()
    assert api.get(runs_url()).status_code == 401
    assert api.get(runs_url() + f"/{RUN}").status_code == 401
    assert api.get(f"/security-assistant/teams/{CODE}/students").status_code == 401


@pytest.mark.parametrize("who", ["sam", "ada"])
def test_members_of_the_team_can_list_its_runs(api, team, who):
    as_user(api, who)
    response = api.get(runs_url())
    assert response.status_code == 200
    body = response.json()
    assert body["demo_data"] is False and body["team"] == CODE and [r["run_id"] for r in body["runs"]] == [RUN]
    assert body["runs"][0]["counts"]["V2"]["confirmed"] == 1 and body["runs"][0]["trigger"] == "manual"


def test_a_student_of_another_team_and_a_missing_team_get_404(api, team):
    as_user(api, "zed")
    assert api.get(runs_url()).status_code == 404
    assert api.get(runs_url() + f"/{RUN}").status_code == 404
    as_user(api, "ada")
    assert api.get(runs_url("NO-SUCH-TEAM")).status_code == 404


def test_the_team_can_be_named_by_code_in_any_case(api, team):
    as_user(api, "sam")
    assert api.get(runs_url(CODE.lower())).status_code == 200


def test_an_administrator_can_read_every_team(api, team):
    api.sign_in("root", email="root@example.com", admin=True)
    assert api.get(runs_url()).status_code == 200
    assert api.get(runs_url() + f"/{RUN}").status_code == 200


def test_a_team_with_no_results_has_an_empty_list_not_an_error(api, results):
    lecturer(api, "ada")
    new_team(api, name="Team Beta")
    assert api.get(runs_url("TEAM-BETA")).json()["runs"] == []


# ---- students -------------------------------------------------------------------------------------------------------------------------
def test_the_student_list_is_for_lecturers_and_admins_only(api, team):
    students = students_of(api)
    assert sorted(s["display_name"] for s in students) == ["Kim", "Lee", "Sam"]
    assert all(set(s) == {"id", "display_name", "github_username"} for s in students) and "@" not in json.dumps(students)
    as_user(api, "sam")
    assert api.get(f"/security-assistant/teams/{CODE}/students").status_code == 403


# ---- the overview ---------------------------------------------------------------------------------------------------------------------
def test_the_overview_has_provenance_stages_tool_runs_coverage_counts_and_llm_facts(api, team):
    as_user(api, "kim")
    body = api.get(runs_url() + f"/{RUN}").json()
    assert body["manifest"]["repo"] == "https://github.com/o/r" and body["manifest"]["checkout"]["kind"] == "clone-tempdir"
    assert body["stages"][0]["stage"] == "fetch" and body["run"]["complete"] is True
    assert body["scan"]["tool_runs"][0]["tool"] == "semgrep" and body["scan"]["coverage"]["V1"]["level"] == "FULL"
    assert body["counts"]["V2"]["confirmed"] == 1 and body["counts"]["V4"]["dismissed"] == 1
    assert body["llm"] == {"model": "mock-model", "temperature": 0.0, "seed": 7, "interpreter_prompt": "interpreter-v4", "trace_prompt": "link-v1",
                           "risk_version": "risk-v1", "threshold": 0.7, "total_tokens": 1234, "tutor_is_mock": True}
    assert body["my_contributor_ids"] == []  # kim's e-mail is not in the mapping


def test_an_unknown_run_or_a_bad_run_name_is_404(api, team):
    as_user(api, "sam")
    assert api.get(runs_url() + "/no-such-run").status_code == 404
    assert api.get(runs_url() + "/..%2F..").status_code == 404


def test_a_student_sees_their_own_contributor_id_and_never_the_mapping(api, team):
    as_user(api, "sam")
    response = api.get(runs_url() + f"/{RUN}")
    assert response.json()["my_contributor_ids"] == [MINE]
    text = response.text + api.get(runs_url()).text
    assert "sam@example.com" not in text and "salt" not in text and '"Sam"' not in text


def test_a_student_cannot_look_through_another_student(api, team):
    sam = next(s for s in students_of(api) if s["display_name"] == "Sam")
    as_user(api, "kim")
    assert api.get(runs_url() + f"/{RUN}?student={sam['id']}").json()["my_contributor_ids"] == []


def test_a_lecturer_can_view_through_a_student_of_the_team_only(api, team):
    sam = next(s for s in students_of(api) if s["display_name"] == "Sam")
    as_user(api, "ada")
    assert api.get(runs_url() + f"/{RUN}?student={sam['id']}").json()["my_contributor_ids"] == [MINE]
    assert api.get(runs_url() + f"/{RUN}").json()["my_contributor_ids"] == []
    assert api.get(runs_url() + f"/{RUN}?student=not-a-uuid").status_code == 404
    other = onboard(api, "outsider", "student")  # a student who is in no team, so not in this one
    as_user(api, "ada")
    assert api.get(runs_url() + f"/{RUN}?student={other}").status_code == 404


# ---- the answers never hold what must not leave ----------------------------------------------------------------------------------------
def test_a_secret_or_an_email_in_a_report_is_removed_before_it_leaves(api, team, results):
    path = results / CODE / RUN / "report.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["run"]["stages"][0]["detail"] = "key AKIAIOSFODNN7EXAMPLE sent to jane@example.org"
    path.write_text(json.dumps(doc), encoding="utf-8")
    as_user(api, "sam")
    text = api.get(runs_url() + f"/{RUN}").text
    assert "AKIAIOSFODNN7EXAMPLE" not in text and "jane@example.org" not in text


def test_demo_mode_is_off_by_default_and_reads_the_bundled_sample_only_when_turned_on(monkeypatch):
    from app.core.config import settings
    app.dependency_overrides.pop(get_reader, None)
    monkeypatch.setattr(settings, "SECURITY_ASSISTANT_RESULTS_DIR", "does-not-exist")
    assert settings.SECURITY_ASSISTANT_DEMO_MODE is False and get_reader().root.name == "does-not-exist"
    monkeypatch.setattr(settings, "SECURITY_ASSISTANT_DEMO_MODE", True)
    assert get_reader().root.name == "sample_results"


# ---- step 3: findings and "mine" -------------------------------------------------------------------------------------------------------
def finding(gid, category="V2", status="confirmed", rank=None, contributor=None, **extra):
    return {"group_id": gid, "category": category, "status": status, "rule_id": f"rule-{gid}", "tool": "semgrep", "message": f"message {gid}",
            "cwe": "CWE-89", "file_path": "app.py", "line": 10, "confidence": 0.8,
            "risk": {"rank": rank, "score": 5.0 if rank else None, "breakdown": []} if rank else None,
            "introducing_commit": {"sha": "abc1234", "contributor": contributor} if contributor else None,
            "links": [{"kind": "story", "id": "US-1", "status": "verified", "methods": [], "evidence": "x", "confidence": 0.9}],
            "probe": {"decision": "closed"}, "snippet": "  9 | a\n>10 | b", **extra}


@pytest.fixture
def many(team, results):
    path = results / CODE / RUN / "report.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["findings"] = [finding("A", "V2", "confirmed", rank=2, contributor=MINE), finding("B", "V2", "dismissed", rank=1, contributor="C-99999999"),
                       finding("C", "V1", "uncertain"), finding("D", "V4", "confirmed", rank=3, contributor=MINE, snippet="x = '<line hidden: it holds the secret>'"),
                       finding("E", "V5", "not interpreted")]
    path.write_text(json.dumps(doc), encoding="utf-8")
    return team


def findings_url(suffix="", code=CODE):
    return f"/security-assistant/teams/{code}/runs/{RUN}/findings{suffix}"


def test_findings_are_sorted_by_risk_rank_with_unranked_last(api, many):
    as_user(api, "sam")
    body = api.get(findings_url()).json()
    assert [f["group_id"] for f in body["findings"]] == ["B", "A", "D", "C", "E"]
    assert body["counts"]["V2"] == {"confirmed": 1, "dismissed": 1, "uncertain": 0, "not interpreted": 0} and body["counts"]["V5"]["not interpreted"] == 1


def test_findings_can_be_filtered_by_category_and_status(api, many):
    as_user(api, "sam")
    assert [f["group_id"] for f in api.get(findings_url("?category=V2")).json()["findings"]] == ["B", "A"]
    assert [f["group_id"] for f in api.get(findings_url("?category=V2&status=dismissed")).json()["findings"]] == ["B"]
    assert [f["group_id"] for f in api.get(findings_url("?status=uncertain")).json()["findings"]] == ["C"]
    assert api.get(findings_url("?category=V9")).status_code == 422 and api.get(findings_url("?status=bad")).status_code == 422


def test_the_summary_counts_match_the_list(api, many):
    as_user(api, "sam")
    body = api.get(findings_url()).json()
    for category, row in body["counts"].items():
        listed = [f for f in body["findings"] if f["category"] == category]
        assert sum(row.values()) == len(listed)


def test_mine_keeps_only_findings_whose_introducing_commit_is_the_viewers(api, many):
    as_user(api, "sam")
    body = api.get(findings_url("?mine=true")).json()
    assert [f["group_id"] for f in body["findings"]] == ["A", "D"] and all(f["mine"] for f in body["findings"]) and body["my_contributor_ids"] == [MINE]
    assert [f["mine"] for f in api.get(findings_url()).json()["findings"]] == [False, True, True, False, False]


def test_mine_is_empty_for_a_student_who_is_not_in_the_mapping(api, many):
    as_user(api, "kim")
    body = api.get(findings_url("?mine=true")).json()
    assert body["findings"] == [] and body["my_contributor_ids"] == []


def test_a_lecturer_sees_mine_through_a_chosen_student(api, many):
    sam = next(s for s in students_of(api) if s["display_name"] == "Sam")
    assert [f["group_id"] for f in api.get(findings_url(f"?mine=true&student={sam['id']}")).json()["findings"]] == ["A", "D"]


def test_findings_are_team_checked_like_the_runs(api, many):
    as_user(api, "zed")
    assert api.get(findings_url()).status_code == 404 and api.get(findings_url("/A")).status_code == 404
    as_user(api, "sam")
    assert api.get(findings_url(code="NO-TEAM")).status_code == 404


def test_one_finding_comes_with_everything_and_unknown_ones_are_404(api, many):
    as_user(api, "sam")
    card = api.get(findings_url("/A")).json()
    assert card["group_id"] == "A" and card["links"][0]["id"] == "US-1" and card["probe"]["decision"] == "closed" and card["mine"] is True
    assert card["introducing_commit"]["contributor"] == MINE and "snippet_note" not in card
    assert api.get(findings_url("/NOPE")).status_code == 404


def test_a_secret_finding_says_the_code_line_is_hidden(api, many):
    as_user(api, "sam")
    assert api.get(findings_url("/D")).json()["snippet_note"] == "Code line hidden for secrets"


def test_no_email_name_or_secret_is_in_any_findings_answer(api, many, results):
    path = results / CODE / RUN / "report.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["findings"][0]["rationale"] = "see jane@example.org and ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2"
    doc["findings"][0]["introducing_commit"]["contributor"] = "Jane Doe"
    path.write_text(json.dumps(doc), encoding="utf-8")
    as_user(api, "sam")
    text = api.get(findings_url()).text + api.get(findings_url("/A")).text + api.get(findings_url("?mine=true")).text
    for bad in ("jane@example.org", "ghp_a1B2", "Jane Doe", "sam@example.com", "salt"):
        assert bad not in text
