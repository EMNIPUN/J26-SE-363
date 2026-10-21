"""The fields the Security Assistant pages read: additive report.json fields and the run.json manifest. Nothing existing changes."""

import json
import re

from app.agents.security_assistant import assess, manifest
from app.agents.security_assistant.tests.test_assess import SAMPLES, Forbidden, Mock, demo, go, run  # noqa: F401  (demo is a fixture)
from app.agents.security_assistant.tests.test_assess import SAVED

NEW_FINDING_KEYS = {"cwe", "message", "snippet", "original_status", "downgrade_reason"}


def full(demo, tmp_path):
    return go(demo, tmp_path, client=Mock(), req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")


def test_every_finding_carries_the_new_additive_fields(demo, tmp_path):
    report = full(demo, tmp_path)
    assert report["findings"] and all(NEW_FINDING_KEYS <= set(f) for f in report["findings"])
    assert any(f["cwe"] for f in report["findings"]) and any(f["message"] for f in report["findings"])
    assert any(f["snippet"] for f in report["findings"])
    saved = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert saved["findings"] == json.loads(json.dumps(report["findings"]))


def test_the_snippet_is_the_masked_one_and_never_shows_the_line_of_a_secret(demo, tmp_path):
    report = full(demo, tmp_path)
    secrets = [f for f in report["findings"] if f["category"] == "V4"]
    assert secrets  # (the saved scan's secret is at a line the fetched copy does not have, so there is no snippet; report.py tests the hidden line)
    assert all(f["snippet"] is None or "<line hidden: it holds the secret>" in f["snippet"] for f in secrets)
    assert any(f["snippet"] and f["snippet"].lstrip().startswith(("  ", ">")) for f in report["findings"] if f["category"] != "V4")
    text = (tmp_path / "report.json").read_text(encoding="utf-8")
    assert not re.search(r"AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|sk_live_", text)


def test_the_fix_guidance_has_an_example_and_references(demo, tmp_path):
    report = full(demo, tmp_path)
    g = [f["fix_guidance"] for f in report["findings"] if f["fix_guidance"]]
    assert g and all(x["steps"] and isinstance(x["references"], list) for x in g)
    assert any(x["example"] and x["example"]["language"] and x["example"]["code"] for x in g)
    assert any(r.startswith("https://") for x in g for r in x["references"])


def test_the_probe_has_the_attempt_log_with_hint_levels_and_scores(demo, tmp_path):
    report = full(demo, tmp_path)
    probes = [f["probe"] for f in report["findings"] if f["probe"] and f["probe"]["attempts"]]
    assert probes
    for p in probes:
        log = p["attempt_log"]
        assert len(log) == p["attempts"] and [a["score"] for a in log] == p["scores"]
        assert [a["attempt"] for a in log] == list(range(1, len(log) + 1)) and all(a["text"] and a["hint_level"] >= 0 for a in log)


def test_meta_has_the_temperature_and_the_manifest_is_written(demo, tmp_path):
    report = full(demo, tmp_path)
    assert report["meta"]["temperature"] == 0.0
    m = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert m["manifest_version"] == manifest.MANIFEST_VERSION and m["trigger"] == "manual" and m["scan_type"] == "reused-scan"
    assert m["checkout"] == {"kind": "local-folder", "read_only": True, "deleted_after": False, "code_executed": False}
    assert m["llm"]["model"] == "mock-model" and m["llm"]["temperature"] == 0.0
    assert m["tools"] and all({"tool", "version"} == set(t) for t in m["tools"])
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", m["started_at"]) and m["started_at"] <= m["finished_at"]


def test_the_manifest_never_holds_a_local_path_or_a_name(demo, tmp_path):
    full(demo, tmp_path)
    text = (tmp_path / "run.json").read_text(encoding="utf-8")
    assert str(demo) not in text and "demo@example.com" not in text and "\\" not in text.replace("\\n", "")
    assert json.loads(text)["repo"] == demo.name  # a local folder is shown by its folder name only


def test_a_url_checkout_is_recorded_as_a_deleted_clone():
    fake = {"scan": {"reused": False, "tool_runs": []}, "meta": {"llm_model": None, "interpreter_prompt": "p", "trace_prompt": "t"}}
    m = manifest.build(report=fake, is_url=True, label="repo", repo_url="https://github.com/o/r", commit_sha="a" * 40, seconds=3.0)
    assert m["repo"] == "https://github.com/o/r" and m["scan_type"] == "full" and m["commit_sha"] == "a" * 40
    assert m["checkout"] == {"kind": "clone-tempdir", "read_only": True, "deleted_after": True, "code_executed": False}


def test_a_run_without_the_llm_still_has_the_fields_and_the_manifest(demo, tmp_path):
    report = go(demo, tmp_path, allow_external_llm=False, client=Forbidden())
    assert report["findings"] and all(NEW_FINDING_KEYS <= set(f) for f in report["findings"])
    assert all(f["original_status"] is None and f["probe"] is None for f in report["findings"])
    m = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert m["llm"]["model"] is None and report["meta"]["temperature"] is None


def test_the_command_records_the_trigger(demo, tmp_path):
    code = run(assess.main([str(demo), "--reuse-scan", str(SAVED), "--out", str(tmp_path), "--trigger", "push"]))
    assert code == 4 and json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))["trigger"] == "push"


def test_an_unknown_trigger_is_refused(tmp_path):
    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    try:
        manifest.set_trigger(tmp_path, "nightly")
    except ValueError as exc:
        assert "trigger must be one of" in str(exc)
    else:
        raise AssertionError("an unknown trigger was accepted")
