"""The LLM used by the Security Assistant only (separate from other agents), behind a tiny interface.

To change provider later, implement `LLMClient` (one async method) and return it from `get_default_client`;
nothing else in the interpreter depends on Gemini.
"""

import asyncio
import os
from typing import Protocol, runtime_checkable

import httpx

DEFAULT_MODEL = "gemini-2.5-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


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
                 transport: httpx.AsyncBaseTransport | None = None, retries: int = 2):
        self._key, self.model, self._timeout, self._transport, self._retries = api_key, model, timeout, transport, retries

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
                    if resp.status_code not in (429, 500, 503):
                        break  # a client error will not get better by retrying
                await asyncio.sleep(0.5 * (attempt + 1))
        raise LLMError(f"Gemini call failed: {last}")  # never include headers, so the key cannot leak


def get_default_client() -> LLMClient:
    """Gemini configured from the environment: SECURITY_ASSISTANT_LLM_API_KEY (or GEMINI_API_KEY),
    SECURITY_ASSISTANT_LLM_MODEL (default gemini-2.5-flash), SECURITY_ASSISTANT_LLM_TIMEOUT (seconds)."""
    key = os.environ.get("SECURITY_ASSISTANT_LLM_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMNotConfigured("set SECURITY_ASSISTANT_LLM_API_KEY (or GEMINI_API_KEY) to call the LLM")
    return GeminiClient(
        key,
        model=os.environ.get("SECURITY_ASSISTANT_LLM_MODEL", DEFAULT_MODEL),
        timeout=float(os.environ.get("SECURITY_ASSISTANT_LLM_TIMEOUT", "60")),
    )
