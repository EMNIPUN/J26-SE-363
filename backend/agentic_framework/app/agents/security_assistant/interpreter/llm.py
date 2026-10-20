"""The LLM used by the Security Assistant only: Groq, over its OpenAI-compatible chat completions endpoint with plain
httpx, behind a one-method interface (`LLMClient`). Nothing here imports or reuses another agent's client.

Settings (environment or backend/agentic_framework/.env; the key is never printed or logged):
    SECURITY_ASSISTANT_LLM_API_KEY    a Groq key (starts with gsk_)
    SECURITY_ASSISTANT_LLM_MODEL      a Groq model id; there is deliberately no default, models get retired
    SECURITY_ASSISTANT_LLM_TIMEOUT    seconds per request (default 60)
    SECURITY_ASSISTANT_LLM_MAX_TOKENS output limit per call (default 4096; reasoning models spend it on thinking too)

Output format (Groq docs, structured outputs): models on the documented list get `json_schema` with `strict: true`, so
the output is constrained to the verdict schema; every other model gets JSON Object Mode (valid JSON, schema not enforced).
Either way the reply is validated again by the interpreter. If Groq answers 400 to the schema request, the call is
repeated once in JSON Object Mode and the call record says so.
"""

import asyncio
import os
from pathlib import Path
from typing import Protocol, runtime_checkable

import httpx
from dotenv import dotenv_values

from app.agents.security_assistant.interpreter.models import CallRecord

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Models Groq lists as supporting `strict: true` structured outputs (console.groq.com/docs/structured-outputs).
STRICT_SCHEMA_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b",
                                  "meta-models/muse-spark-open"})
DEFAULT_MAX_TOKENS = 4096
TEMPERATURE = 0.0  # the lowest value Groq accepts (range 0 to 2): the least random answers it can give
MAX_WAIT_S = 60.0  # never wait longer than this for one retry; a longer retry-after is reported instead
# backend/agentic_framework/.env, the same file the rest of the AI backend reads
ENV_FILE = Path(__file__).resolve().parents[4] / ".env"

# Same fields as interpreter.models.Verdict. minimum/maximum are not used because Groq does not document them for
# strict mode; the range of `confidence` is checked by the interpreter.
VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["confirmed", "dismissed", "uncertain"]},
        "rationale": {"type": "string"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
        "recommendation": {"type": "string"},
    },
    "required": ["status", "rationale", "evidence_ids", "confidence", "recommendation"],
    "additionalProperties": False,
}


class LLMError(Exception):
    """The model could not be called or returned no usable reply."""


class LLMNotConfigured(LLMError):
    """The key or the model is not set (or the key is not a Groq key), so no live call can be made."""


@runtime_checkable
class LLMClient(Protocol):
    model: str
    last_call: CallRecord | None  # about the most recent call; None for clients that do not record it

    async def complete(self, system: str, user: str) -> str:
        """Return the model text for one system + user prompt. Raise LLMError on failure."""
        ...


def _retry_after(resp: httpx.Response) -> float | None:
    try:
        return float(resp.headers["retry-after"])  # seconds; Groq sets it on 429 only
    except (KeyError, ValueError):
        return None


class GroqClient:
    """Groq chat completions (OpenAI-compatible). The key goes in the Authorization header only."""

    def __init__(self, api_key: str, model: str, timeout: float = 60.0, max_tokens: int = DEFAULT_MAX_TOKENS,
                 transport: httpx.AsyncBaseTransport | None = None, retries: int = 2, backoff: float = 0.5):
        self._key, self.model, self._timeout, self._max_tokens = api_key, model, timeout, max_tokens
        self._transport, self._retries, self._backoff = transport, retries, backoff
        self.temperature = TEMPERATURE
        self.last_call: CallRecord | None = None

    def _body(self, system: str, user: str, schema_mode: bool) -> dict:
        response_format = ({"type": "json_schema", "json_schema": {"name": "verdict", "strict": True, "schema": VERDICT_SCHEMA}}
                           if schema_mode else {"type": "json_object"})
        return {"model": self.model, "temperature": self.temperature, "max_completion_tokens": self._max_tokens,
                "response_format": response_format,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}

    def _scrub(self, text: str) -> str:
        return text.replace(self._key, "<key>")

    async def complete(self, system: str, user: str) -> str:
        schema_mode = self.model in STRICT_SCHEMA_MODELS
        record = self.last_call = CallRecord(model=self.model, temperature=self.temperature,
                                             response_format="json_schema (strict)" if schema_mode else "json_object")
        last = "no attempt made"
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as http:
            for attempt in range(self._retries + 1):
                record.attempts = attempt + 1
                try:
                    resp = await http.post(GROQ_URL, json=self._body(system, user, schema_mode),
                                           headers={"Authorization": f"Bearer {self._key}"})
                except httpx.HTTPError as exc:
                    last, wait = type(exc).__name__, None
                else:
                    record.http_status = resp.status_code
                    if resp.status_code == 200:
                        return self._read(resp, record)
                    last = f"HTTP {resp.status_code}"
                    try:  # Groq explains the problem (unknown model, quota, ...); the message never holds the key
                        last += ": " + self._scrub(str(resp.json()["error"]["message"])[:200])
                    except (KeyError, ValueError, TypeError):
                        pass
                    if resp.status_code == 400 and schema_mode:
                        schema_mode = False  # the schema request was refused: try JSON Object Mode once
                        record.response_format = "json_object (fallback after HTTP 400 for json_schema)"
                        continue
                    if resp.status_code not in (429, 500, 502, 503, 504):
                        break  # a client error will not get better by retrying
                    wait = _retry_after(resp)
                    if wait is not None and wait > MAX_WAIT_S:
                        last += f" (Groq asks to retry after {wait:g} s; not waiting that long)"
                        break
                if attempt < self._retries:
                    pause = min(MAX_WAIT_S, max(self._backoff * (attempt + 1), wait or 0.0))
                    record.waited_s += pause
                    await asyncio.sleep(pause)
        raise LLMError(f"Groq call failed: {last}")

    @staticmethod
    def _read(resp: httpx.Response, record: CallRecord) -> str:
        try:
            data = resp.json()
            choice = data["choices"][0]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise LLMError("Groq returned no usable reply (no choices)") from exc
        text = (choice.get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}
        record.finish_reason = choice.get("finish_reason")
        record.output_chars = len(text)
        record.prompt_tokens = usage.get("prompt_tokens")
        record.completion_tokens = usage.get("completion_tokens")
        record.total_tokens = usage.get("total_tokens")
        return text  # an empty or cut-off reply is not an error here: the interpreter rejects it with these diagnostics


def _setting(name: str) -> str | None:
    """A setting from the process environment, else from the .env file (values are never logged)."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        return dotenv_values(ENV_FILE).get(name) or None
    except OSError:
        return None


def get_default_client(retries: int = 2, backoff: float = 0.5) -> LLMClient:
    """A Groq client configured from the environment or backend/agentic_framework/.env (see the module docstring)."""
    key, model = _setting("SECURITY_ASSISTANT_LLM_API_KEY"), _setting("SECURITY_ASSISTANT_LLM_MODEL")
    missing = [n for n, v in (("SECURITY_ASSISTANT_LLM_API_KEY", key), ("SECURITY_ASSISTANT_LLM_MODEL", model)) if not v]
    if missing:
        raise LLMNotConfigured(
            f"not configured: set {' and '.join(missing)} in the environment or in {ENV_FILE}. The key is a Groq API "
            "key (gsk_...); the model is a Groq model id (there is no default, models get retired).")
    if not key.startswith("gsk_"):  # never send some other service's credential to Groq
        raise LLMNotConfigured("SECURITY_ASSISTANT_LLM_API_KEY does not look like a Groq API key (they start with gsk_), "
                               "so it was not used.")
    return GroqClient(
        key, model,
        timeout=float(_setting("SECURITY_ASSISTANT_LLM_TIMEOUT") or "60"),
        max_tokens=int(_setting("SECURITY_ASSISTANT_LLM_MAX_TOKENS") or DEFAULT_MAX_TOKENS),
        retries=retries, backoff=backoff,
    )
