"""The frontend's demo data is what the routes answer for the checked-in sample runs, so it cannot drift from the API.

The pages show it only when their demo flag is on (VITE_SECURITY_ASSISTANT_DEMO=true) and then say "demo data".
To refresh it after an intended change:  SECURITY_DEMO_BUNDLE_UPDATE=1 pytest tests/test_security_assistant_demo_bundle.py
"""

import json
import os
import shutil
from pathlib import Path

from app.core.config import settings
from app.main import app
from app.modules.security.reader import ResultsReader
from app.modules.security.router import SAMPLE_DIR, get_reader
from tests.test_security_assistant_api import as_user
from tests.test_teams_api import join_all, lecturer, new_team

TEAM, FULL, NO_LLM, HOSTILE = "J26-SE-363", "sample-python-demo", "sample-python-no-llm", "sample-hostile-readme"
BUNDLE = Path(__file__).resolve().parents[3] / "frontend" / "src" / "modules" / "security" / "assistant" / "demo" / "demoBundle.json"
DEMO_STUDENT = "sam"  # a synthetic student; the e-mail below exists only in the temporary copy of the sample


def collect(api, tmp_path, monkeypatch):
    work = tmp_path / "sample"
    shutil.copytree(SAMPLE_DIR, work)
    report = json.loads((work / TEAM / FULL / "report.json").read_text(encoding="utf-8"))
    mine = next(f["introducing_commit"]["contributor"] for f in report["findings"] if f["introducing_commit"])
    for run in (FULL, NO_LLM, HOSTILE):
        (work / TEAM / run / "trace_mapping.local.json").write_text(
            json.dumps({"salt": "demo", "contributors": {mine: {"name": "demo", "email": f"{DEMO_STUDENT}@example.com"}}}), encoding="utf-8")
    app.dependency_overrides[get_reader] = lambda: ResultsReader(work)
    monkeypatch.setattr(settings, "SECURITY_ASSISTANT_DEMO_MODE", True)
    lecturer(api, "ada")
    new_team(api, code=TEAM)
    join_all(api)

    base = f"/security-assistant/teams/{TEAM}"
    get = lambda url: api.get(url).json()  # noqa: E731
    bundle = {"note": "Generated from the routes by tests/test_security_assistant_demo_bundle.py. Synthetic repository, MOCK LLM, MOCK Tutor.",
              "team": TEAM, "mine": {}, "runs": {}, "students": None, "overview": {}, "findings": {}, "finding": {}, "learning": {}, "agents": {},
              "workflow": {}, "audit": {}, "evidence": {}, "compare": {}}
    as_user(api, "ada")
    # the ids are random per database; the demo needs only stable keys
    bundle["students"] = [{**s, "id": f"demo-student-{s['display_name'].lower()}"} for s in sorted(get(f"{base}/students"), key=lambda s: s["display_name"])]
    bundle["runs"] = get(f"{base}/runs")
    for run in (FULL, NO_LLM, HOSTILE):
        as_user(api, "ada")
        bundle["audit"][run] = get(f"{base}/runs/{run}/audit")
        as_user(api, DEMO_STUDENT)
        r = f"{base}/runs/{run}"
        bundle["overview"][run] = get(r)
        bundle["findings"][run] = get(f"{r}/findings")
        bundle["finding"][run] = {f["group_id"]: get(f"{r}/findings/{f['group_id']}") for f in bundle["findings"][run]["findings"]}
        bundle["learning"][run] = get(f"{r}/learning")
        bundle["agents"][run] = get(f"{r}/agents")
        bundle["workflow"][run] = get(f"{r}/workflow")
        bundle["evidence"][run] = get(f"{base}/evidence?run={run}")
    bundle["compare"][f"{NO_LLM}|{FULL}"] = get(f"{base}/compare?a={NO_LLM}&b={FULL}")
    return bundle


def test_the_demo_bundle_is_what_the_routes_answer_for_the_sample(api, tmp_path, monkeypatch):
    bundle = collect(api, tmp_path, monkeypatch)
    text = json.dumps(bundle, indent=1, ensure_ascii=False) + "\n"
    if os.environ.get("SECURITY_DEMO_BUNDLE_UPDATE"):
        BUNDLE.parent.mkdir(parents=True, exist_ok=True)
        BUNDLE.write_text(text, encoding="utf-8")
    assert json.loads(BUNDLE.read_text(encoding="utf-8")) == bundle, "demo data is out of date: SECURITY_DEMO_BUNDLE_UPDATE=1 pytest this file"


def test_the_demo_bundle_says_demo_data_and_holds_no_email_secret_or_mapping(api, tmp_path, monkeypatch):
    bundle = collect(api, tmp_path, monkeypatch)
    text = json.dumps(bundle)
    assert bundle["runs"]["demo_data"] is True and all(o["demo_data"] is True for o in bundle["overview"].values())
    assert "@example.com" not in text and '"salt"' not in text and "AKIA" not in text and "Users" not in text
    assert bundle["overview"][FULL]["my_contributor_ids"] and bundle["overview"][NO_LLM]["my_contributor_ids"]
    assert bundle["overview"][FULL]["llm"]["tutor_is_mock"] is True and bundle["overview"][NO_LLM]["run"]["complete"] is False
