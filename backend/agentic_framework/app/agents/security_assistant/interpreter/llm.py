"""The LLM used by the Security Assistant only (separate from other agents), behind a tiny interface.

To change provider later, implement `LLMClient` (one async method) and return it from `get_default_client`;
nothing else in the interpreter depends on Gemini.
"""

import asyncio
import os
from pathlib import Path
from typing import Protocol, runtime_checkable

import httpx
from dotenv import dotenv_values

DEFAULT_MODEL = "gemini-3.5-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# backend/agentic_framework/.env, the same file the rest of the AI backend reads
ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class LLMError(Exception):
    """The model could not be called or returned no usable text."""


class LLMNotConfigured(LLMError):
    """No API key is set, so no live call can be made."""


@runtime_checkable
class LLMClient(Protocol):
    model: str

    async def complete(self, system: str, user: str) -> str:
        """Return the model text for one system + user prompt. Raise LLMError on failure."""
        ...


class GeminiClient:
    """Google Gemini over its REST API (httpx, no extra dependency). The key goes in a header, never a URL."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, timeout: float = 60.0,
                 transport: httpx.AsyncBaseTransport | None = None, retries: int = 2, backoff: float = 0.5):
        self._key, self.model, self._timeout, self._transport, self._retries = api_key, model, timeout, transport, retries
        self._backoff = backoff  # seconds; the wait before retry n is backoff * n

    async def complete(self, system: str, user: str) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 1024, "responseMimeType": "application/json"},
        }
        url = GEMINI_URL.format(model=self.model)
        last = "no attempt made"
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as http:
            for attempt in range(self._retries + 1):
                try:
                    resp = await http.post(url, json=body, headers={"x-goog-api-key": self._key})
                except httpx.HTTPError as exc:
                    last = f"{type(exc).__name__}"
                else:
                    if resp.status_code == 200:
                        try:
                            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                        except (KeyError, IndexError, ValueError, TypeError) as exc:
                            raise LLMError("Gemini returned no usable text") from exc
                    last = f"HTTP {resp.status_code}"
                    try:  # Google explains the problem (unknown model, quota, ...); the message never holds the key
                        last += ": " + str(resp.json()["error"]["message"])[:200].replace(self._key, "<key>")
                    except (KeyError, ValueError, TypeError):
                        pass
                    if resp.status_code not in (429, 500, 503):
                        break  # a client error will not get better by retrying
                await asyncio.sleep(self._backoff * (attempt + 1))
        raise LLMError(f"Gemini call failed: {last}")  # never include headers, so the key cannot leak


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
    """Gemini configured from the environment or backend/agentic_framework/.env:
    SECURITY_ASSISTANT_LLM_API_KEY (or GEMINI_API_KEY), SECURITY_ASSISTANT_LLM_MODEL (default gemini-3.5-flash),
    SECURITY_ASSISTANT_LLM_TIMEOUT (seconds). A real environment variable wins over the file."""
    key = _setting("SECURITY_ASSISTANT_LLM_API_KEY") or _setting("GEMINI_API_KEY")
    if not key:
        raise LLMNotConfigured(
            "no API key found: set SECURITY_ASSISTANT_LLM_API_KEY (or GEMINI_API_KEY) in the environment "
            f"or in {ENV_FILE}")
    return GeminiClient(
        key,
        model=_setting("SECURITY_ASSISTANT_LLM_MODEL") or DEFAULT_MODEL,
        timeout=float(_setting("SECURITY_ASSISTANT_LLM_TIMEOUT") or "60"),
        retries=retries,
        backoff=backoff,
    )
