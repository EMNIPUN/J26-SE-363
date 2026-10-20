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
