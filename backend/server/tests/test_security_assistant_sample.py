"""The checked-in sample runs (synthetic repository, MOCK LLM, MOCK Tutor) load through the reader and the routes in demo mode."""

import json

import pytest

from app.core.config import settings
from app.main import app
from app.modules.security.reader import ResultsReader
from app.modules.security.router import SAMPLE_DIR, get_reader
from tests.test_security_assistant_api import as_user
from tests.test_teams_api import join_all, lecturer, new_team

TEAM = "J26-SE-363"
FULL, NO_LLM = "sample-python-demo", "sample-python-no-llm"


@pytest.fixture
def reader():
    return ResultsReader(SAMPLE_DIR)


@pytest.fixture
def demo_team(api, monkeypatch):
    """The J26-SE-363 team with a lecturer and the students sam, kim and lee, and demo mode switched on (explicitly)."""
    app.dependency_overrides.pop(get_reader, None)
    monkeypatch.setattr(settings, "SECURITY_ASSISTANT_DEMO_MODE", True)
    lecturer(api, "ada")
    new_team(api, code=TEAM)
    join_all(api)
    return TEAM


def test_the_sample_has_two_runs_of_the_same_repository(reader):
    rows = {r["run_id"]: r for r in reader.summaries(TEAM)}
    assert set(rows) == {FULL, NO_LLM} and rows[FULL]["repo"] == rows[NO_LLM]["repo"] == "vuln_py_repo"
    assert rows[FULL]["trigger"] == "manual" and rows[FULL]["scan_type"] == "reused-scan"


def test_the_full_sample_ran_every_stage_with_the_mock_llm_and_the_mock_tutor(reader):
    run = reader.run(TEAM, FULL)
    rep = run["report"]
    assert [s["status"] for s in rep["run"]["stages"]] == ["completed"] * 8 and rep["run"]["complete"] is True
    assert rep["meta"]["llm_model"] == "mock-model" and rep["questions"]["meta"]["tutor_is_mock"] is True
    assert any(f["probe"] for f in rep["findings"]) and any(f["fix_guidance"]["example"] for f in rep["findings"] if f["fix_guidance"])


def test_the_sample_without_the_llm_is_incomplete_and_says_why_and_is_not_a_clean_result(reader):
    rep = reader.run(TEAM, NO_LLM)["report"]
    assert rep["run"]["complete"] is False and rep["run"]["llm_refused"] is True
    assert any("allow-external-llm" in s["detail"] for s in rep["run"]["stages"] if s["stage"] == "interpret")
    assert rep["findings"] and all(f["status"] == "not interpreted" for f in rep["findings"])


def test_nothing_personal_or_secret_is_in_the_sample_as_it_leaves_the_reader(reader):
    text = json.dumps([reader.run(TEAM, r) for r in (FULL, NO_LLM)]) + json.dumps([reader.audit(TEAM, r) for r in (FULL, NO_LLM)])
    assert "demo@example.com" not in text and "Users" not in text and "[REDACTED by API]" not in text  # nothing needed redacting
    assert not any(f.name.endswith(".local.json") for f in SAMPLE_DIR.rglob("*"))  # a mapping is never part of the sample


def test_the_shared_files_are_there(reader):
    assert "graph TD;" in reader.shared("workflow.mmd") and "WORKFLOW" in reader.shared("WORKFLOW.md").upper()
    assert reader.shared("rq1_comparison.csv").startswith("suite,name,run")


def test_in_demo_mode_the_routes_serve_the_sample_to_team_members_and_say_it_is_demo_data(api, demo_team):
    as_user(api, "sam")
    body = api.get(f"/security-assistant/teams/{TEAM}/runs").json()
    assert body["demo_data"] is True and {r["run_id"] for r in body["runs"]} == {FULL, NO_LLM}
    overview = api.get(f"/security-assistant/teams/{TEAM}/runs/{FULL}").json()
    assert overview["demo_data"] is True and overview["llm"]["model"] == "mock-model" and overview["llm"]["tutor_is_mock"] is True
    assert api.get(f"/security-assistant/teams/{TEAM}/runs/{NO_LLM}").json()["run"]["complete"] is False


def test_demo_mode_does_not_open_the_sample_to_people_outside_the_team(api, demo_team):
    from tests.test_teams_api import student
    student(api, "zed")
    assert api.get(f"/security-assistant/teams/{TEAM}/runs").status_code == 404


def test_compare_of_the_two_sample_runs_shows_every_finding_changing_from_not_interpreted_to_a_verdict(api, demo_team):
    as_user(api, "sam")
    body = api.get(f"/security-assistant/teams/{TEAM}/compare?a={NO_LLM}&b={FULL}").json()
    assert body["added"] == [] and body["removed"] == [] and body["unchanged_count"] == 0
    assert body["changed"] and all(c["from"] == "not interpreted" and c["to"] == "confirmed" for c in body["changed"])


def test_demo_mode_is_off_unless_it_is_switched_on():
    assert settings.SECURITY_ASSISTANT_DEMO_MODE is False
