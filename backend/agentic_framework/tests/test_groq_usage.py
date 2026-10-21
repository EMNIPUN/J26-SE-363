"""The Groq usage ledger and its endpoints: per key, per model across keys, and a verdict on whether the limits are near."""

import pytest
from fastapi.testclient import TestClient

from app.core import groq_usage
from app.main import app

MODEL = "openai/gpt-oss-120b"
KEYS = ["gsk_first_secret", "gsk_second_secret"]


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(groq_usage, "LEDGER", tmp_path / "usage.sqlite")
    monkeypatch.setattr(groq_usage, "SETTINGS_FILE", tmp_path / "none.env")
    monkeypatch.setenv("ASSESSMENT_GROQ_API_KEYS", ",".join(KEYS))
    monkeypatch.setenv("ASSESSMENT_GROQ_MODEL", MODEL)
    monkeypatch.setenv("ASSESSMENT_GROQ_FALLBACK_MODEL", "qwen/qwen3.8-27b")


def call(key, tokens, ok=True, **kw):
    groq_usage.record(key, MODEL, ok=ok, status=200 if ok else 429, usage={"prompt_tokens": tokens, "completion_tokens": 0} if ok else None, **kw)


def test_each_key_is_counted_on_its_own_and_all_together():
    for _ in range(3):
        call(KEYS[0], 20_000)  # 60K of key 1's 200K
    call(KEYS[1], 10_000)
    snap = groq_usage.snapshot()
    first, second = snap["keys"]
    assert first["models"][MODEL]["tokens_24h"] == 60_000 and first["models"][MODEL]["tokens_left_today"] == 140_000
    assert second["models"][MODEL]["tokens_24h"] == 10_000
    total = snap["models"][MODEL]
    assert total["tokens_24h"] == 70_000 and total["daily_budget"]["tokens"] == 400_000 and total["tokens_left_today"] == 330_000
    assert total["keys_usable"] == 2 and snap["verdict"]["ready_for_demo"] is True


def test_a_key_that_hit_its_daily_limit_is_left_out_of_what_is_left():
    call(KEYS[0], 0, ok=False, error_kind="quota", error_text="Rate limit reached for model (TPD). Please try again in 1h30m0s.")
    snap = groq_usage.snapshot()
    assert snap["keys"][0]["models"][MODEL]["level"] == "exhausted"
    assert snap["keys"][0]["models"][MODEL]["blocked_for_seconds"] > 5000
    total = snap["models"][MODEL]
    assert total["keys_exhausted"] == 1 and total["tokens_left_today"] == 200_000


def test_the_verdict_warns_when_the_budget_is_nearly_gone():
    for key in KEYS:
        for _ in range(9):
            call(key, 20_000)  # 180K of 200K on each key
    snap = groq_usage.snapshot()
    assert snap["models"][MODEL]["level"] == "critical" and snap["verdict"]["level"] == "critical"
    assert snap["verdict"]["ready_for_demo"] is False


def test_the_response_headers_are_kept_and_no_key_is_stored():
    call(KEYS[0], 100, headers={"x-ratelimit-remaining-requests": "942", "x-ratelimit-remaining-tokens": "7900"})
    snap = groq_usage.snapshot()
    assert snap["keys"][0]["models"][MODEL]["reported_by_groq"]["requests_left_today"] == 942
    assert "gsk_first_secret" not in str(snap) and "gsk_first_secret" not in groq_usage.LEDGER.read_bytes().decode("latin-1")


def test_a_call_made_with_no_ledger_folder_still_works(monkeypatch, tmp_path):
    monkeypatch.setattr(groq_usage, "LEDGER", tmp_path / "missing" / "deep" / "usage.sqlite")
    call(KEYS[0], 5)
    assert groq_usage.snapshot()["models"][MODEL]["tokens_24h"] == 5


def test_the_usage_endpoint_is_public_and_answers(monkeypatch):
    call(KEYS[1], 1234)
    with TestClient(app) as client:
        report = client.get("/api/v1/usage/groq").json()
    assert report["percent_used"] == 0.3 and report["percent_left"] == 99.7  # 1,234 of the two keys' 400,000 tokens
    assert report["models"][MODEL]["keys"] == {"Key 1": 0.0, "Key 2": 0.6}
