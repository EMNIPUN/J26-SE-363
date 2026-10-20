"""The seed sent to Groq: sent, recorded, configurable, and dropped for a model that refuses it. HTTP is a mock transport."""

import asyncio
import json
import sys

import httpx
import pytest

from app.agents.security_assistant.interpreter import llm as llm_module
from app.agents.security_assistant.interpreter.llm import SEED, GroqClient, get_default_client

OK = {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}}


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def client(handler, **kw):
    return GroqClient("gsk_test", "openai/gpt-oss-20b", transport=httpx.MockTransport(handler), backoff=0.0, **kw)


def test_the_seed_is_sent_and_recorded():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=OK)

    c = client(handler)
    run(c.complete("s", "u"))
    assert bodies[0]["seed"] == SEED and c.last_call.seed == SEED and bodies[0]["temperature"] == 0.0


def test_a_model_that_refuses_the_seed_is_called_again_without_it():
    bodies = []

    def handler(request):
        body = json.loads(request.content)
        bodies.append(body)
        if "seed" in body:
            return httpx.Response(400, json={"error": {"message": "'seed' : property 'seed' is not supported with this model"}})
        return httpx.Response(200, json=OK)

    c = client(handler)
    run(c.complete("s", "u"))
    assert ["seed" in b for b in bodies] == [True, False] and c.last_call.seed is None and c.seed is None
    run(c.complete("s", "u"))  # remembered: the next call does not send it either
    assert "seed" not in bodies[-1]


def test_an_unrelated_400_is_not_mistaken_for_a_seed_problem():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(400, json={"error": {"message": "invalid model"}})

    c = client(handler)
    with pytest.raises(llm_module.LLMError):
        run(c.complete("s", "u"))
    assert len(calls) == 2 and c.seed == SEED  # the schema-mode fallback may retry once; the seed is kept


def test_the_seed_can_be_configured_or_switched_off(monkeypatch):
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_API_KEY", "gsk_x")
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_MODEL", "m")
    assert get_default_client().seed == SEED
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_SEED", "123")
    assert get_default_client().seed == 123
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_SEED", "off")
    assert get_default_client().seed is None
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_SEED", "not a number")
    assert get_default_client().seed == SEED
