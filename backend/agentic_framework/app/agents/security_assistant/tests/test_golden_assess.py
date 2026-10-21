"""The Python demo run (saved scan, mocked LLM, mock Tutor) produces exactly the output recorded before the LangGraph refactoring.

To re-record after an intended change: GOLDEN_UPDATE=1 pytest app/agents/security_assistant/tests/test_golden_assess.py"""

import json
import os
from pathlib import Path

import pytest

from app.agents.security_assistant.tests import golden
from app.agents.security_assistant.tests.test_assess import SAMPLES, SAVED, Mock, Forbidden, demo, go  # noqa: F401  (demo is a fixture)

GOLDEN = Path(__file__).parent / "golden" / "assess_python_demo.json"
GOLDEN_NO_LLM = Path(__file__).parent / "golden" / "assess_python_demo_no_llm.json"


def check(snapshot, path):
    if os.environ.get("GOLDEN_UPDATE"):
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    assert snapshot == json.loads(path.read_text(encoding="utf-8")), f"the run output differs from {path.name}"


def test_python_demo_full_run_is_identical_to_the_recorded_output(demo, tmp_path):
    report = go(demo, tmp_path, client=Mock(), req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")
    check(golden.snapshot(report, tmp_path), GOLDEN)


def test_python_demo_without_the_llm_is_identical_to_the_recorded_output(demo, tmp_path):
    report = go(demo, tmp_path, allow_external_llm=False, client=Forbidden())
    check(golden.snapshot(report, tmp_path), GOLDEN_NO_LLM)


GOLDEN_FIELDS = Path(__file__).parent / "golden" / "assess_python_demo_fields.json"


def fields_snapshot(report):
    """The report fields the frontend reads (added for the Security Assistant pages), normalised like the other snapshots."""
    n = golden.norm
    return {
        "meta_temperature": report["meta"]["temperature"],
        "findings": [{
            "group": f["group_id"], "cwe": f["cwe"], "message": n(f["message"]), "snippet": n(f["snippet"]) if f["snippet"] else None,
            "original_status": f["original_status"], "downgrade_reason": f["downgrade_reason"],
            "example": f["fix_guidance"]["example"] if f["fix_guidance"] else None,
            "references": f["fix_guidance"]["references"] if f["fix_guidance"] else None,
            "attempt_log": [[a["attempt"], a["hint_level"], n(a["text"]), a["score"], a["result"]] for a in f["probe"]["attempt_log"]] if f["probe"] else None,
        } for f in report["findings"]],
    }


def test_python_demo_frontend_fields_are_identical_to_the_recorded_output(demo, tmp_path):
    report = go(demo, tmp_path, client=Mock(), req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")
    check(fields_snapshot(report), GOLDEN_FIELDS)


def test_the_normaliser_hides_bare_dates_so_the_snapshots_do_not_depend_on_the_day():
    """Regression: the report's commit-date column holds the day the demo repository was made, so the recorded hash failed the next day."""
    assert golden.norm("| 2026-10-20 | x |") == golden.norm("| 2031-02-03 | x |") == "| <date> | x |"
    assert golden.norm("2026-10-20 14:03:09 UTC and 2026-10-20") == "<time> and <date>"
