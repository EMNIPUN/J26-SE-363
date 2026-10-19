"""Evidence builder and the Gemini client. HTTP is mocked with httpx.MockTransport; nothing leaves the machine."""

import asyncio
import json

import httpx
import pytest

from app.agents.security_assistant.interpreter.evidence import build_bundle
from app.agents.security_assistant.interpreter import llm as llm_module
from app.agents.security_assistant.interpreter.llm import (
    DEFAULT_MODEL, GeminiClient, LLMError, LLMNotConfigured, get_default_client,
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


# ---- Gemini client (mocked HTTP) --------------------------------------------------------------------------------------
def _client(handler, **kw):
    return GeminiClient("KEY-123", transport=httpx.MockTransport(handler), retries=kw.pop("retries", 0), **kw)


def test_gemini_request_shape_and_key_in_header_only():
    seen = {}

    def handler(request):
        seen.update(url=str(request.url), headers=dict(request.headers), body=json.loads(request.content))
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]})

    assert run(_client(handler).complete("SYS", "USER")) == '{"ok": true}'
    assert "KEY-123" not in seen["url"] and seen["headers"]["x-goog-api-key"] == "KEY-123"
    assert DEFAULT_MODEL in seen["url"]
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "SYS"
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "USER"
    assert seen["body"]["generationConfig"]["temperature"] == 0


@pytest.mark.parametrize("response", [
    httpx.Response(500, text="boom KEY-123"), httpx.Response(401, text="bad key KEY-123"),
    httpx.Response(200, json={"candidates": []}), httpx.Response(200, text="not json"),
])
def test_gemini_errors_become_llm_error_without_leaking_the_key(response):
    with pytest.raises(LLMError) as err:
        run(_client(lambda r: response).complete("s", "u"))
    assert "KEY-123" not in str(err.value)


def test_gemini_retries_transient_errors():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})

    assert run(_client(handler, retries=2).complete("s", "u")) == "{}" and len(calls) == 3


def _no_settings(monkeypatch, tmp_path, env_text=None):
    """Ignore the developer's real environment and .env file."""
    for name in ("SECURITY_ASSISTANT_LLM_API_KEY", "GEMINI_API_KEY", "SECURITY_ASSISTANT_LLM_MODEL",
                 "SECURITY_ASSISTANT_LLM_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / ".env"
    if env_text is not None:
        env_file.write_text(env_text)
    monkeypatch.setattr(llm_module, "ENV_FILE", env_file)


def test_key_and_model_are_read_from_the_env_file(monkeypatch, tmp_path):
    _no_settings(monkeypatch, tmp_path, "SECURITY_ASSISTANT_LLM_API_KEY=file-key\nSECURITY_ASSISTANT_LLM_MODEL=m-1\n"
                 "SECURITY_ASSISTANT_LLM_TIMEOUT=12\n")
    client = get_default_client()
    assert (client._key, client.model, client._timeout) == ("file-key", "m-1", 12.0)


def test_a_real_environment_variable_wins_over_the_env_file(monkeypatch, tmp_path):
    _no_settings(monkeypatch, tmp_path, "SECURITY_ASSISTANT_LLM_API_KEY=file-key\n")
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_API_KEY", "env-key")
    assert get_default_client()._key == "env-key"


def test_commented_out_or_empty_keys_in_the_env_file_do_not_count(monkeypatch, tmp_path):
    _no_settings(monkeypatch, tmp_path, "# SECURITY_ASSISTANT_LLM_API_KEY=commented\nSECURITY_ASSISTANT_LLM_API_KEY=\n")
    with pytest.raises(LLMNotConfigured, match="no API key found"):
        get_default_client()


def test_default_client_needs_a_key_and_reads_the_model(monkeypatch, tmp_path):
    _no_settings(monkeypatch, tmp_path)
    with pytest.raises(LLMNotConfigured):
        get_default_client()
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert get_default_client().model == DEFAULT_MODEL
    monkeypatch.setenv("SECURITY_ASSISTANT_LLM_MODEL", "other-model")
    assert get_default_client().model == "other-model"


# ---- live (only on request: uv run pytest -m live) ----------------------------------------------------------------------
@pytest.mark.live
def test_live_gemini_returns_a_schema_valid_verdict():
    from app.agents.security_assistant.interpreter.interpreter import SemanticInterpreter
    from app.agents.security_assistant.interpreter.seeded import load_cases
    try:
        client = get_default_client()
    except LLMNotConfigured:
        pytest.skip("no API key configured")
    case = load_cases()[0]
    result = run(SemanticInterpreter(client).interpret(case.finding, case.bundle))
    assert not result.error and not result.output_rejected


def test_google_error_message_is_shown_but_never_the_key():
    body = {"error": {"message": "This model models/x is no longer available. (used key KEY-123)"}}
    with pytest.raises(LLMError) as err:
        run(_client(lambda r: httpx.Response(404, json=body)).complete("s", "u"))
    assert "no longer available" in str(err.value) and "HTTP 404" in str(err.value)
    assert "KEY-123" not in str(err.value)
