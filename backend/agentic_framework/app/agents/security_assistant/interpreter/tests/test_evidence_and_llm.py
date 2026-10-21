"""Evidence builder and the Groq client. HTTP is mocked with httpx.MockTransport; nothing leaves the machine."""

import asyncio
import json

import httpx
import pytest

from app.agents.security_assistant.interpreter.evidence import build_bundle
from app.agents.security_assistant.interpreter import llm as llm_module
from app.agents.security_assistant.interpreter.llm import (
    DEFAULT_MAX_TOKENS, STRICT_SCHEMA_MODELS, GroqClient, LLMError, LLMNotConfigured, get_default_client,
)
from app.agents.security_assistant.interpreter.models import EvidenceItem
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.schemas import Category, Finding


def run(coro):
    return asyncio.run(coro)


# ---- redaction ------------------------------------------------------------------------------------------------------
def test_redaction_keeps_code_that_only_reads_a_password():
    code = 'pw = hashlib.md5(request.form["password"].encode()).hexdigest()\npassword = request.form["password"]'
    assert redact_text(code) == code


def test_redaction_marks_placeholder_like_values():
    out = redact_text('API_KEY = "test_key_0000000000000000"')
    assert "placeholder_like=yes" in out and "test_key_0000" not in out
    assert "placeholder_like=no" in redact_text('API_KEY = "q8Zr2LmT9xW4vB7nC1"')


def test_known_secrets_are_removed_wherever_they_appear():
    out = redact_text("log line: xyzzy-plugh-1234", known_secrets=("xyzzy-plugh-1234",))
    assert "xyzzy-plugh-1234" not in out


# ---- evidence builder ------------------------------------------------------------------------------------------------
def _repo(tmp_path):
    (tmp_path / "app").mkdir(exist_ok=True)
    (tmp_path / "app/orders.py").write_text(
        "\n".join(f"line {i}" for i in range(1, 30)) + '\nSECRET_TOKEN = "abcdef0123456789abcdef"\n')
    (tmp_path / "app/auth.py").write_text("@login_required\ndef guard():\n    return current_user\n")
    (tmp_path / "package-lock.json").write_text('{"lodash": "4.17.15"}')
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src/settings.js").write_text("const _ = require('lodash')\nconst m = _.merge({}, a, b)\n")
    return tmp_path


def _finding(**kw):
    base = dict(category=Category.V1, tool="codeql", rule_id="r", file_path="app/orders.py", line=10, message="m")
    return Finding(**{**base, **kw})


def test_bundle_has_finding_snippet_and_context_with_unique_ids(tmp_path):
    bundle = build_bundle(_finding(), _repo(tmp_path))
    assert [i.id for i in bundle.items] == ["E1", "E2", "E3"]
    assert [i.kind for i in bundle.items] == ["finding", "code_snippet", "context"]
    snippet = bundle.items[1].content
    assert ">   10 | line 10" in snippet and "line 2 " not in snippet  # radius is limited, the finding line is marked
    assert "app/auth.py" in bundle.items[2].content  # the V1 search found authorisation code elsewhere


def test_bundle_without_repository_has_only_the_finding():
    assert [i.id for i in build_bundle(_finding()).items] == ["E1"]


def test_snippet_is_redacted(tmp_path):
    bundle = build_bundle(_finding(line=30), _repo(tmp_path))
    assert "abcdef0123456789abcdef" not in bundle.items[1].content and "[REDACTED" in bundle.items[1].content


def test_path_outside_the_repository_is_not_read(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("top secret")
    repo = tmp_path / "repo"
    repo.mkdir()
    bundle = build_bundle(_finding(file_path="../outside.txt", line=1), repo)
    assert all("top secret" not in i.content for i in bundle.items)


def test_v5_context_shows_where_the_package_is_used(tmp_path):
    f = _finding(category=Category.V5, file_path="package-lock.json", line=None, sink="lodash@4.17.15")
    bundle = build_bundle(f, _repo(tmp_path))
    usage = bundle.items[-1]
    assert "lodash" in usage.label and "src/settings.js" in usage.content and "package-lock.json:" not in usage.content


def test_extra_evidence_gets_the_next_ids_and_the_bundle_is_capped(tmp_path):
    extra = [EvidenceItem(id="E1", kind="context", label=f"x{n}", content="c") for n in range(10)]
    with pytest.raises(ValueError):  # more than 8 items is refused
        build_bundle(_finding(), _repo(tmp_path), extra=extra)
    ok = build_bundle(_finding(), _repo(tmp_path), extra=extra[:2])
    assert [i.id for i in ok.items][-2:] == ["E4", "E5"]


# ---- Groq client (mocked HTTP) ------------------------------------------------------------------------------------------
KEY = "gsk_TESTKEY123"
OK_BODY = {"choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
           "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}}


def _client(handler, model="llama-3.3-70b-versatile", **kw):
    return GroqClient(KEY, model, transport=httpx.MockTransport(handler), retries=kw.pop("retries", 0), **kw)


def test_request_shape_key_in_header_only_and_json_object_mode():
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), headers=dict(request.headers), body=json.loads(request.content))
        return httpx.Response(200, json=OK_BODY)

    client = _client(handler)
    assert run(client.complete("SYS", "USER")) == '{"ok": true}'
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert KEY not in seen["url"] and seen["headers"]["authorization"] == f"Bearer {KEY}"
    body = seen["body"]
    assert body["model"] == "llama-3.3-70b-versatile" and body["temperature"] == 0
    assert body["messages"] == [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]
    assert body["response_format"] == {"type": "json_object"}  # a model without structured output support
    assert body["max_completion_tokens"] == DEFAULT_MAX_TOKENS and "max_tokens" not in body
    assert client.last_call.response_format == "json_object"


@pytest.mark.parametrize("model", sorted(STRICT_SCHEMA_MODELS))
def test_models_with_structured_outputs_get_the_strict_verdict_schema(model):
    seen = {}

    def handler(request):
        seen.update(body=json.loads(request.content))
        return httpx.Response(200, json=OK_BODY)

    client = _client(handler, model=model)
    run(client.complete("s", "u"))
    fmt = seen["body"]["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    schema = fmt["json_schema"]["schema"]
    assert schema["additionalProperties"] is False and set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["status"]["enum"] == ["confirmed", "dismissed", "uncertain"]
    assert client.last_call.response_format == "json_schema (strict)"


def test_schema_request_refused_with_400_falls_back_to_json_object_once():
    formats = []

    def handler(request):
        formats.append(json.loads(request.content)["response_format"]["type"])
        if len(formats) == 1:
            return httpx.Response(400, json={"error": {"message": "schema not supported"}})
        return httpx.Response(200, json=OK_BODY)

    client = _client(handler, model="openai/gpt-oss-120b", retries=2)
    assert run(client.complete("s", "u")) == '{"ok": true}'
    assert formats == ["json_schema", "json_object"] and "fallback" in client.last_call.response_format


def test_call_record_has_finish_reason_sizes_and_tokens_but_not_the_text():
    client = _client(lambda r: httpx.Response(200, json=OK_BODY))
    run(client.complete("s", "u"))
    record = client.last_call
    assert (record.finish_reason, record.output_chars, record.prompt_tokens, record.completion_tokens,
            record.total_tokens, record.http_status, record.attempts) == ("stop", 12, 120, 30, 150, 200, 1)
    assert '{"ok": true}' not in record.model_dump_json()


@pytest.mark.parametrize("response", [
    httpx.Response(500, text="boom gsk_TESTKEY123"), httpx.Response(401, text="bad key gsk_TESTKEY123"),
    httpx.Response(200, json={"choices": []}), httpx.Response(200, text="not json"),
])
def test_errors_become_llm_error_without_leaking_the_key(response):
    with pytest.raises(LLMError) as err:
        run(_client(lambda r: response).complete("s", "u"))
    assert KEY not in str(err.value)


def test_the_error_message_from_groq_is_shown_without_the_key():
    body = {"error": {"message": f"The model `x` does not exist or you do not have access to it. ({KEY})"}}
    client = _client(lambda r: httpx.Response(404, json=body), retries=2)
    with pytest.raises(LLMError) as err:
        run(client.complete("s", "u"))
    assert "HTTP 404" in str(err.value) and "does not exist" in str(err.value) and KEY not in str(err.value)
    assert client.last_call.attempts == 1  # a client error is not retried


def test_transient_errors_are_retried_with_a_bounded_number_of_attempts(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(llm_module.asyncio, "sleep", fake_sleep)
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, json=OK_BODY)

    client = _client(handler, retries=2, backoff=2)
    assert run(client.complete("s", "u")) == '{"ok": true}' and len(calls) == 3
    assert sleeps == [2, 4] and client.last_call.attempts == 3 and client.last_call.waited_s == 6

    calls.clear()
    with pytest.raises(LLMError, match="HTTP 503"):
        run(_client(lambda r: (calls.append(1), httpx.Response(503))[1], retries=1).complete("s", "u"))
    assert len(calls) == 2  # retries=1 means two attempts, then it gives up


def test_retry_after_is_honoured_up_to_a_limit(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(llm_module.asyncio, "sleep", fake_sleep)
    answers = [httpx.Response(429, headers={"retry-after": "7"}, json={"error": {"message": "rate limit"}}),
               httpx.Response(200, json=OK_BODY)]
    assert run(_client(lambda r: answers.pop(0), retries=2, backoff=0.5).complete("s", "u")) == '{"ok": true}'
    assert sleeps == [7.0]  # the longer of the backoff (0.5) and retry-after (7)

    sleeps.clear()
    too_long = lambda r: httpx.Response(429, headers={"retry-after": "3600"}, json={"error": {"message": "daily limit"}})
    with pytest.raises(LLMError, match="not waiting that long"):
        run(_client(too_long, retries=2).complete("s", "u"))
    assert sleeps == []  # it did not sleep for an hour


def test_a_truncated_empty_reply_is_returned_with_diagnostics_not_raised():
    body = {"choices": [{"message": {"content": None}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 900, "completion_tokens": 4096, "total_tokens": 4996}}
    client = _client(lambda r: httpx.Response(200, json=body))
    assert run(client.complete("s", "u")) == ""
    assert (client.last_call.finish_reason, client.last_call.output_chars, client.last_call.completion_tokens) == ("length", 0, 4096)


def test_output_limit_is_configurable():
    seen = {}

    def handler(request):
        seen.update(body=json.loads(request.content))
        return httpx.Response(200, json=OK_BODY)

    run(_client(handler, max_tokens=8000).complete("s", "u"))
    assert seen["body"]["max_completion_tokens"] == 8000


# ---- configuration ---------------------------------------------------------------------------------------------------------
def _no_settings(monkeypatch, tmp_path, env_text=None):
    """Ignore the developer's real environment and .env file."""
    for name in ("SECURITY_ASSISTANT_LLM_API_KEY", "SECURITY_ASSISTANT_LLM_MODEL", "SECURITY_ASSISTANT_LLM_TIMEOUT",
                 "SECURITY_ASSISTANT_LLM_MAX_TOKENS"):
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / ".env"
    if env_text is not None:
        env_file.write_text(env_text)
    monkeypatch.setattr(llm_module, "ENV_FILE", env_file)


def test_key_and_model_are_read_from_the_env_file(monkeypatch, tmp_path):
    _no_settings(monkeypatch, tmp_path, f"SECURITY_ASSISTANT_LLM_API_KEY={KEY}\nSECURITY_ASSISTANT_LLM_MODEL=m-1\n"
                 "SECURITY_ASSISTANT_LLM_TIMEOUT=12\nSECURITY_ASSISTANT_LLM_MAX_TOKENS=2000\n")
    client = get_default_client()
    assert (client._key, client.model, client._timeout, client._max_tokens) == (KEY, "m-1", 12.0, 2000)


def test_a_real_environment_variable_wins_over_the_env_file(monkeypatch, tmp_path):
    _no_settings(monkeypatch, tmp_path, f"SECURITY_ASSISTANT_LLM_API_KEY=gsk_file\nSECURITY_ASSISTANT_LLM_MODEL=m\n")
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_API_KEY", "gsk_env")
    assert get_default_client()._key == "gsk_env"


def test_there_is_no_default_model_and_both_settings_are_required(monkeypatch, tmp_path):
    _no_settings(monkeypatch, tmp_path)
    with pytest.raises(LLMNotConfigured) as err:
        get_default_client()
    assert "SECURITY_ASSISTANT_LLM_API_KEY and SECURITY_ASSISTANT_LLM_MODEL" in str(err.value)
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_API_KEY", KEY)
    with pytest.raises(LLMNotConfigured) as err:
        get_default_client()
    assert "set SECURITY_ASSISTANT_LLM_MODEL in" in str(err.value) and "no default" in str(err.value)
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_MODEL", "some-model")
    assert get_default_client().model == "some-model"


def test_commented_out_or_empty_entries_in_the_env_file_do_not_count(monkeypatch, tmp_path):
    _no_settings(monkeypatch, tmp_path, "# SECURITY_ASSISTANT_LLM_API_KEY=gsk_x\nSECURITY_ASSISTANT_LLM_API_KEY=\n"
                 "SECURITY_ASSISTANT_LLM_MODEL=m\n")
    with pytest.raises(LLMNotConfigured, match="not configured"):
        get_default_client()


def test_a_key_that_is_not_a_groq_key_is_never_used(monkeypatch, tmp_path):
    """A key of another service (left over in .env) must not be sent to Groq."""
    _no_settings(monkeypatch, tmp_path, "SECURITY_ASSISTANT_LLM_API_KEY=AIzaSyFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE12\n"
                 "SECURITY_ASSISTANT_LLM_MODEL=some-other-model\n")
    with pytest.raises(LLMNotConfigured) as err:
        get_default_client()
    assert "does not look like a Groq API key" in str(err.value) and "AIza" not in str(err.value)


# ---- live (only on request: uv run pytest -m live) ----------------------------------------------------------------------
@pytest.mark.live
def test_live_groq_returns_a_schema_valid_verdict():
    from app.agents.security_assistant.interpreter.interpreter import SemanticInterpreter
    from app.agents.security_assistant.interpreter.seeded import load_cases
    try:
        client = get_default_client()
    except LLMNotConfigured:
        pytest.skip("no Groq key and model configured")
    case = load_cases()[0]
    result = run(SemanticInterpreter(client).interpret(case.finding, case.bundle))
    assert not result.error and not result.output_rejected
