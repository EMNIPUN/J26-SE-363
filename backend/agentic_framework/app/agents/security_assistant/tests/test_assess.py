"""End-to-end run on saved findings with a mocked LLM and the mock Tutor: no scanner, network or API key is used."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from app.agents.security_assistant import assess, questions as qs, risk as rk
from app.agents.security_assistant.interpreter.llm import LLMError
from app.agents.security_assistant.tools.tests.demo_repos import make_demo_repos

SAVED = Path(__file__).parent / "saved" / "python_full.json"
SAMPLES = Path(__file__).resolve().parents[1] / "traceability_samples"
STAGES = ["fetch", "scan", "governance", "interpret", "trace", "risk", "guidance", "questions"]


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class Mock:
    """Answers verdict calls (confirmed) and link calls (no link); records everything it is sent."""

    model = "mock-model"
    temperature = 0.0

    def __init__(self, fail=False):
        self.fail, self.prompts = fail, []

    async def complete(self, system, user, schema=None, schema_name="verdict"):
        self.prompts.append((schema_name, system, user))
        if self.fail:
            raise LLMError("service down")
        if schema_name == "link":
            return json.dumps({"story_id": "", "task_id": "", "rationale": "nothing fits", "evidence_ids": ["E1"], "confidence": 0.2})
        return json.dumps({"status": "confirmed", "rationale": "the evidence shows it", "evidence_ids": ["E1"],
                           "confidence": 0.8, "recommendation": ""})


class Forbidden:
    model = "forbidden"

    async def complete(self, *a, **k):
        raise AssertionError("the LLM was called")


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    return next(r for r in make_demo_repos(tmp_path_factory.mktemp("demo")) if r.name == "vuln_py_repo")


def go(demo, out, **kw):
    kw.setdefault("allow_external_llm", True)
    kw.setdefault("client", Mock())
    kw.setdefault("tutor", qs.MockTutor())
    return run(assess.run_pipeline(str(demo), kw.pop("req", None), kw.pop("tasks", None), kw.pop("skip", []),
                                   kw.pop("reuse", SAVED), out_dir=out, **kw))


def stage(report, name):
    return next(s for s in report["run"]["stages"] if s["stage"] == name)


# ---- a full run ----------------------------------------------------------------------------------------------------------------
def test_full_run_on_saved_findings_produces_one_json_and_one_markdown(demo, tmp_path):
    mock = Mock()
    report = go(demo, tmp_path, client=mock, req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")
    assert [s["stage"] for s in report["run"]["stages"]] == STAGES
    assert all(stage(report, n)["status"] == "completed" for n in STAGES), report["run"]["stages"]
    assert (tmp_path / "report.json").exists() and (tmp_path / "report.md").exists()
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["report_version"] == assess.REPORT_VERSION

    f = report["findings"]
    assert f and all(x["status"] == "confirmed" for x in f)
    one = next(x for x in f if x["category"] == "V1" or x["category"] == "V2")
    assert one["evidence_ids"] == ["E1"] and one["risk"]["rank"] >= 1
    assert round(sum(b["contribution"] for b in one["risk"]["breakdown"]), 2) == one["risk"]["score"]
    assert one["fix_guidance"]["steps"] and one["probe"]["tutor"]["mock"] is True and one["probe"]["decision"] in ("closed", "escalated") and one["probe"]["attempts"] >= 1
    assert one["introducing_commit"] is None or one["introducing_commit"]["contributor"].startswith("C-")
    assert [x["risk"]["rank"] for x in sorted(f, key=lambda x: x["risk"]["rank"])] == list(range(1, len(f) + 1))
    assert report["scan"]["tool_runs"] and report["scan"]["coverage"]["V1"]["level"]
    assert report["questions"]["meta"]["tutor_is_mock"] is True
    assert any("MOCK" in x for x in report["limitations"]) and any("not a measured probability" in x for x in report["limitations"])
    assert any(p[0] == "link" for p in mock.prompts)  # link proposals were asked for because requirement files were given


def test_the_markdown_has_every_section(demo, tmp_path):
    go(demo, tmp_path, req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")
    md = (tmp_path / "report.md").read_text(encoding="utf-8")
    for heading in ("# Security Assistant report", "## Stages", "## Findings overview", "## LLM interpretation", "## Traceability",
                    "## Risk prioritisation", "## Probe questions", "## Limitations", "Coverage", "MOCK TUTOR"):
        assert heading in md, heading
    assert "How to fix" in md or "how to fix" in md.lower()


def test_no_file_without_a_git_repo_path_or_author_data(demo, tmp_path):
    go(demo, tmp_path, req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")
    text = (tmp_path / "report.json").read_text(encoding="utf-8") + (tmp_path / "report.md").read_text(encoding="utf-8")
    assert str(demo) not in text and "demo@example.com" not in text
    assert (tmp_path / "trace_mapping.local.json").exists()


# ---- LLM gate ---------------------------------------------------------------------------------------------------------------------
def test_without_allow_external_llm_nothing_is_sent_and_the_run_is_incomplete(demo, tmp_path):
    report = go(demo, tmp_path, allow_external_llm=False, client=Forbidden())
    assert stage(report, "interpret")["status"] == "skipped" and "allow-external-llm" in stage(report, "interpret")["detail"]
    for name in ("trace", "risk", "questions"):
        assert stage(report, name)["status"] == "skipped" and "needs interpret" in stage(report, name)["detail"]
    assert stage(report, "scan")["status"] in ("completed", "partial") and stage(report, "guidance")["status"] == "completed"
    assert report["run"]["complete"] is False and report["run"]["llm_refused"] is True
    assert report["findings"] and all(x["status"] == "not interpreted" and x["risk"] is None for x in report["findings"])
    assert "INCOMPLETE RUN" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_the_command_exits_4_when_the_llm_stages_are_refused(demo, tmp_path, capsys):
    code = run(assess.main([str(demo), "--reuse-scan", str(SAVED), "--out", str(tmp_path)]))
    assert code == 4 and "INCOMPLETE" in capsys.readouterr().out


# ---- failure never looks clean ------------------------------------------------------------------------------------------------
def test_a_failing_llm_makes_the_run_incomplete(demo, tmp_path):
    report = go(demo, tmp_path, client=Mock(fail=True))
    assert stage(report, "interpret")["status"] == "partial" and report["run"]["complete"] is False
    assert all(x["status"] == "uncertain" for x in report["findings"])  # a failed call is never a guess
    assert any("stage interpret" in r for r in report["run"]["incomplete_reasons"])


def test_a_stage_that_raises_is_recorded_as_failed_and_the_rest_continues(demo, tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("scoring broke")

    monkeypatch.setattr(rk, "rank", boom)
    report = go(demo, tmp_path)
    assert stage(report, "risk")["status"] == "failed" and "scoring broke" in stage(report, "risk")["detail"]
    assert stage(report, "guidance")["status"] == "completed" and stage(report, "questions")["status"] == "completed"
    assert report["run"]["complete"] is False
    assert all(x["risk"] is None for x in report["findings"])


def test_a_missing_saved_scan_fails_the_scan_and_skips_what_depends_on_it(demo, tmp_path):
    report = go(demo, tmp_path, reuse=tmp_path / "nope.json")
    assert stage(report, "scan")["status"] == "failed"
    for name in ("interpret", "trace", "risk", "guidance", "questions"):
        assert stage(report, name)["status"] == "skipped"
    assert report["findings"] == [] and report["run"]["complete"] is False


def test_an_unfetchable_source_skips_everything(tmp_path):
    report = run(assess.run_pipeline(str(tmp_path / "missing"), out_dir=tmp_path / "o", allow_external_llm=True, client=Forbidden()))
    assert stage(report, "fetch")["status"] == "failed" and report["run"]["complete"] is False
    assert all(stage(report, n)["status"] == "skipped" for n in STAGES[1:])


def test_skipping_a_tool_is_a_coverage_gap_and_makes_the_run_incomplete(demo, tmp_path):
    report = go(demo, tmp_path, skip=["codeql"])
    assert report["scan"]["skipped_tools"] == ["codeql"] and report["run"]["complete"] is False
    assert any("tools skipped: codeql" in r for r in report["run"]["incomplete_reasons"])
    assert any("Skipped tools" in x for x in report["limitations"])


def test_an_unknown_tool_name_is_a_usage_error(demo, tmp_path, capsys):
    with pytest.raises(ValueError):
        go(demo, tmp_path, skip=["nope"])
    assert run(assess.main([str(demo), "--skip", "nope", "--out", str(tmp_path)])) == 3


def test_a_bad_requirements_file_fails_only_the_trace_stage(demo, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    report = go(demo, tmp_path / "o", req=bad)
    assert stage(report, "trace")["status"] == "failed" and stage(report, "risk")["status"] == "completed"
    assert report["run"]["complete"] is False


def test_without_requirement_files_the_trace_is_commits_only_and_still_complete_for_that_stage(demo, tmp_path):
    mock = Mock()
    report = go(demo, tmp_path, client=mock)
    assert stage(report, "trace")["status"] == "completed" and "commits only" in stage(report, "trace")["detail"]
    assert not any(p[0] == "link" for p in mock.prompts)
    assert any("No requirements or sprint-task file" in x for x in report["limitations"])


# ---- token accounting ------------------------------------------------------------------------------------------------------------
class TokenMock(Mock):
    """A Mock whose calls leave a call record with fixed token counts, like the Groq client does."""

    def __init__(self):
        super().__init__()
        from app.agents.security_assistant.interpreter.models import CallRecord
        self.last_call = CallRecord(model="mock-model", seed=7, prompt_tokens=100, completion_tokens=20, total_tokens=120)

    async def complete(self, system, user, schema=None, schema_name="verdict"):
        return await super().complete(system, user, schema, schema_name)


def test_the_report_counts_the_tokens_of_interpretation_and_link_proposals(demo, tmp_path):
    report = go(demo, tmp_path, client=TokenMock(), req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")
    u = report["llm_usage"]
    groups = report["interpretation"]["analysed_calls"]
    assert u["interpret"] == {"calls": groups, "prompt_tokens": 100 * groups, "completion_tokens": 20 * groups}
    assert u["link_proposals"]["calls"] > 0 and u["link_proposals"]["prompt_tokens"] == 100 * u["link_proposals"]["calls"]
    assert u["total_tokens"] == 120 * (groups + u["link_proposals"]["calls"]) and u["seed"] == 7 and u["model"] == "mock-model"
    assert f"LLM usage: {u['total_tokens']} tokens" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_a_run_without_the_llm_reports_zero_tokens(demo, tmp_path):
    report = go(demo, tmp_path, allow_external_llm=False, client=Forbidden())
    assert report["llm_usage"]["total_tokens"] == 0 and "LLM usage:" not in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_the_decision_trail_of_the_question_agent_is_in_the_run(demo, tmp_path):
    report = go(demo, tmp_path, tutor=qs.MockTutor(scores={}, default=0.2))  # nothing ever reaches the threshold
    trail = report["decision_trail"]["Question Generation"]
    assert trail and {e["chosen"].split(":")[0] for e in trail} == {"ask_question", "ask_followup", "escalate_to_lecturer"}
    assert all(f["probe"]["decision"] == "escalated" and f["probe"]["attempts"] == 3 for f in report["findings"] if f["probe"])
    md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "### Question Generation" in md and "escalated to lecturer review" in md
    lines = [json.loads(x) for x in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sum(1 for e in lines if e["event"] == "agent_decision" and e["component"] == "question agent") == len(trail)
