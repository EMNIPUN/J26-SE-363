"""handle_github_event: signature, classification, dedupe and URL checks (no network, no git)."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from app.agents.security_assistant.schemas import ScanResult
from app.agents.security_assistant.webhook import (
    DedupeStore, SECRET_ENV, classify, handle_github_event, sign, verify_signature,
)

SAMPLES = Path(__file__).parents[1] / "webhook_samples"
SECRET = "test-secret"


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def payload(name, **edit):
    data = json.loads((SAMPLES / name).read_text(encoding="utf-8"))
    for dotted, value in edit.items():  # edit("pull_request.draft", True)
        node = data
        *parents, last = dotted.split(".")
        for p in parents:
            node = node[p]
        node[last] = value
    return data


def delivery(event, data, secret=SECRET, signature=None):
    raw = json.dumps(data).encode()
    return {"X-GitHub-Event": event, "X-Hub-Signature-256": signature or sign(secret, raw)}, raw


class Recorder:
    """Stands in for run_pipeline."""

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    async def __call__(self, repo_url, sha, scan_type="full", **_):
        self.calls.append((repo_url, sha, scan_type))
        if self.fail:
            raise RuntimeError("clone failed")
        return ScanResult(run_id="t", repo_path="-")


def handle(event, data, pipeline=None, store=None, **kw):
    headers, raw = delivery(event, data)
    pipeline = pipeline or Recorder()
    result = run(handle_github_event(headers, raw, secret=SECRET, pipeline=pipeline,
                                     dedupe=store or DedupeStore(), **kw))
    return result, pipeline


PUSH_SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
MERGE_SHA = "b2c3d4e5f60718293a4b5c6d7e8f901234567890"


# ---- signature -------------------------------------------------------------------------------------
def test_valid_signature_is_accepted():
    result, pipe = handle("push", payload("push.json"))
    assert result.status == "processed" and len(pipe.calls) == 1


@pytest.mark.parametrize("make", [
    lambda raw: sign("wrong-secret", raw),            # signed with another secret
    lambda raw: "sha256=" + "0" * 64,                  # garbage
    lambda raw: sign(SECRET, raw).replace("sha256=", "sha1="),  # wrong scheme
])
def test_bad_signature_is_rejected_and_pipeline_not_called(make):
    data = payload("push.json")
    raw = json.dumps(data).encode()
    pipe = Recorder()
    res = run(handle_github_event({"X-GitHub-Event": "push", "X-Hub-Signature-256": make(raw)}, raw,
                                  secret=SECRET, pipeline=pipe, dedupe=DedupeStore()))
    assert res.status == "rejected" and "signature" in res.reason.lower() and not pipe.calls


def test_body_changed_after_signing_is_rejected():
    headers, raw = delivery("push", payload("push.json"))
    pipe = Recorder()
    res = run(handle_github_event(headers, raw.replace(b"demo-shop", b"evil-shop"), secret=SECRET,
                                  pipeline=pipe, dedupe=DedupeStore()))
    assert res.status == "rejected" and not pipe.calls


def test_missing_signature_header_is_rejected():
    raw = json.dumps(payload("push.json")).encode()
    res = run(handle_github_event({"X-GitHub-Event": "push"}, raw, secret=SECRET,
                                  pipeline=Recorder(), dedupe=DedupeStore()))
    assert res.status == "rejected"


def test_no_configured_secret_rejects_everything(monkeypatch):
    monkeypatch.delenv(SECRET_ENV, raising=False)
    headers, raw = delivery("push", payload("push.json"))
    res = run(handle_github_event(headers, raw, pipeline=Recorder(), dedupe=DedupeStore()))
    assert res.status == "rejected" and SECRET_ENV in res.reason


def test_secret_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv(SECRET_ENV, SECRET)
    headers, raw = delivery("push", payload("push.json"))
    res = run(handle_github_event(headers, raw, pipeline=Recorder(), dedupe=DedupeStore()))
    assert res.status == "processed"


def test_verify_signature_unit():
    assert verify_signature("s", b"x", sign("s", b"x"))
    assert not verify_signature("s", b"x", None)
    assert not verify_signature("", b"x", sign("", b"x"))


# ---- classification ----------------------------------------------------------------------------------
@pytest.mark.parametrize("event,name,edits,action,sha", [
    ("push", "push.json", {}, "secrets_only", PUSH_SHA),
    ("pull_request", "pull_request_merged.json", {}, "full", MERGE_SHA),
    ("pull_request", "pull_request_merged.json", {"pull_request.draft": True}, "ignore", None),
    ("pull_request", "pull_request_merged.json", {"pull_request.merged": False}, "ignore", None),
    ("pull_request", "pull_request_merged.json", {"action": "opened"}, "ignore", None),
    ("pull_request", "pull_request_merged.json", {"action": "synchronize"}, "ignore", None),
    ("push", "push.json", {"deleted": True}, "ignore", None),
    ("push", "push.json", {"after": "0" * 40}, "ignore", None),
    ("ping", "push.json", {}, "ignore", None),
    ("issues", "push.json", {}, "ignore", None),
])
def test_event_classification(event, name, edits, action, sha):
    got_action, reason, got_sha = classify(event, payload(name, **edits))
    assert (got_action, got_sha) == (action, sha)
    assert reason  # always explains why


def test_ignored_events_never_run_the_pipeline_and_say_why():
    for event, data in [
        ("pull_request", payload("pull_request_merged.json", **{"pull_request.draft": True})),
        ("pull_request", payload("pull_request_merged.json", **{"pull_request.merged": False})),
        ("ping", {}),
    ]:
        result, pipe = handle(event, data)
        assert result.status == "ignored" and result.reason and not pipe.calls


def test_pipeline_receives_repo_url_sha_and_scan_type():
    _, push = handle("push", payload("push.json"))
    assert push.calls == [("https://github.com/example-student/demo-shop.git", PUSH_SHA, "secrets_only")]
    _, pr = handle("pull_request", payload("pull_request_merged.json"))
    assert pr.calls == [("https://github.com/example-student/demo-shop.git", MERGE_SHA, "full")]


# ---- dedupe --------------------------------------------------------------------------------------------
def test_duplicate_delivery_runs_only_once():
    store, pipe = DedupeStore(), Recorder()
    first, _ = handle("push", payload("push.json"), pipeline=pipe, store=store)
    second, _ = handle("push", payload("push.json"), pipeline=pipe, store=store)
    assert (first.status, second.status) == ("processed", "duplicate")
    assert len(pipe.calls) == 1


def test_push_then_merged_pr_for_the_same_commit_runs_secrets_then_full():
    store, pipe = DedupeStore(), Recorder()
    sha_edit = {"after": MERGE_SHA}
    handle("push", payload("push.json", **sha_edit), pipeline=pipe, store=store)
    handle("pull_request", payload("pull_request_merged.json"), pipeline=pipe, store=store)
    assert [c[2] for c in pipe.calls] == ["secrets_only", "full"]


def test_full_scan_makes_a_later_secrets_only_scan_of_the_same_sha_redundant():
    store, pipe = DedupeStore(), Recorder()
    handle("pull_request", payload("pull_request_merged.json"), pipeline=pipe, store=store)
    later, _ = handle("push", payload("push.json", after=MERGE_SHA), pipeline=pipe, store=store)
    assert later.status == "duplicate" and len(pipe.calls) == 1


def test_a_crashed_pipeline_can_be_retried_on_redelivery():
    store = DedupeStore()
    failed, _ = handle("push", payload("push.json"), pipeline=Recorder(fail=True), store=store)
    retry, pipe = handle("push", payload("push.json"), store=store)
    assert failed.status == "failed" and "clone failed" in failed.reason
    assert retry.status == "processed" and len(pipe.calls) == 1


def test_dedupe_store_is_bounded():
    store = DedupeStore(max_entries=2)
    for sha in ("a" * 40, "b" * 40, "c" * 40):
        assert store.claim(sha, "full")
    assert store.claim("a" * 40, "full")  # the oldest entry was evicted


# ---- repository URL ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("clone_url", [
    "https://gitlab.com/example/demo-shop.git",
    "http://github.com/example/demo-shop.git",
    "git@github.com:example/demo-shop.git",
    "https://github.com.evil.example/o/r.git",
    "https://user:token@github.com/o/r.git",
    "file:///etc/passwd",
    "",
])
def test_non_github_urls_are_rejected(clone_url):
    data = payload("push.json")
    data["repository"]["clone_url"] = clone_url
    data["repository"]["html_url"] = clone_url
    result, pipe = handle("push", data)
    assert result.status == "rejected" and not pipe.calls


def test_malformed_sha_in_payload_is_rejected():
    result, pipe = handle("push", payload("push.json", after="not-a-sha"))
    assert result.status == "rejected" and not pipe.calls
