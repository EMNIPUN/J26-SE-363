"""Small tools used by the verification phase: evaluate_seeded --save/--delay and the webhook replay retargeting."""

import asyncio
import json
import sys

from app.agents.security_assistant import replay_webhook as replay
from app.agents.security_assistant.interpreter import evaluate_seeded


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_evaluate_seeded_saves_status_rationale_evidence_and_error(tmp_path):
    out = tmp_path / "seeded.json"
    assert run(evaluate_seeded.main(["--save", str(out), "--delay", "5"])) == 0  # --delay only applies to live calls
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["live"] is False and len(saved["cases"]) == 10
    case = saved["cases"][0]
    assert {"id", "ground_truth", "status", "confidence", "evidence_ids", "rationale", "error"} <= set(case)
    assert case["error"] is None and case["evidence_ids"]


def test_retargeting_points_every_sample_at_the_given_repository():
    sha = "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
    apply = replay._retargeter("https://github.com/octocat/Hello-World.git", sha)
    push = json.loads((replay.SAMPLES / "push.json").read_text(encoding="utf-8"))
    apply(push)
    assert push["after"] == sha and push["head_commit"]["id"] == sha
    assert push["repository"]["clone_url"] == "https://github.com/octocat/Hello-World.git"
    pr = json.loads((replay.SAMPLES / "pull_request_merged.json").read_text(encoding="utf-8"))
    apply(pr)
    assert pr["pull_request"]["merge_commit_sha"] == sha and pr["repository"]["full_name"] == "octocat/Hello-World"


def test_the_tampered_delivery_is_rejected_whatever_the_repository(capsys):
    assert run(replay.main(["--repo-url", "https://github.com/octocat/Hello-World", "--sha", "a" * 40])) == 0
    out = capsys.readouterr().out
    assert "fetch https://github.com/octocat/Hello-World.git at aaaaaaaaaaaa" in out
    assert "rejected: invalid or missing X-Hub-Signature-256" in out and "processed: push" in out
