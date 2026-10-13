"""Async Groq client for the Project Planning agent.

Mirrors the pattern of the performance agent's ``GroqMultiKeyClient`` (multi-key
round-robin with model fallback) but is async (the agent's ``handle()`` is async)
and lives in THIS agent's folder — we never import another agent's protected code.

Config (from backend/agentic_framework/.env, PLANNING_ prefix per team convention,
falling back to the generic GROQ_ names):
    PLANNING_GROQ_API_KEYS   comma-separated Groq keys (or PLANNING_GROQ_API_KEY)
    PLANNING_GROQ_MODEL      primary model     (default openai/gpt-oss-120b)
    PLANNING_GROQ_FALLBACK_MODEL  fallback on 404 (default qwen/qwen3.8-27b)
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "qwen/qwen3.8-27b"


class GroqConfigError(RuntimeError):
    """Raised when no Groq API key is configured."""


class PlanningGroqClient:
    def __init__(self, timeout: float = 45.0) -> None:
        raw = (os.getenv("PLANNING_GROQ_API_KEYS"))
        self.api_keys = [k.strip() for k in raw.split(",") if k.strip()]
        self.primary_model = os.getenv("PLANNING_GROQ_MODEL") or os.getenv("GROQ_MODEL", DEFAULT_MODEL)
        self.fallback_model = (
            os.getenv("PLANNING_GROQ_FALLBACK_MODEL") or os.getenv("GROQ_FALLBACK_MODEL", FALLBACK_MODEL)
        )
        self.timeout = timeout
        self._key_index = 0

    @property
    def configured(self) -> bool:
        return bool(self.api_keys)

    def _rotate(self, reason: str) -> None:
        old = self._key_index
        self._key_index = (self._key_index + 1) % len(self.api_keys)
        logger.warning("[groq] key %d failed (%s); rotated to %d", old + 1, reason, self._key_index + 1)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        json_mode: bool = True,
        model: str | None = None,
    ) -> str:
        """Return the model's message content. Raises on exhaustion/misconfig."""
        if not self.configured:
            raise GroqConfigError(
                "No Groq API key. Set PLANNING_GROQ_API_KEYS in backend/agentic_framework/.env"
            )

        target_model = model or self.primary_model
        last_error: str | None = None
        max_attempts = len(self.api_keys) * 2

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for _ in range(max_attempts):
                key = self.api_keys[self._key_index]
                payload: dict[str, Any] = {
                    "model": target_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                try:
                    resp = await client.post(
                        GROQ_API_URL,
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json=payload,
                    )
                except httpx.HTTPError as exc:  # network/transport error -> try next key
                    last_error = str(exc)
                    self._rotate(f"exception: {exc}")
                    continue

                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"].get("content", "")
                if resp.status_code == 404:  # model missing -> fallback once
                    logger.warning("[groq] model %s not found; falling back to %s", target_model, self.fallback_model)
                    target_model = self.fallback_model
                    continue
                if resp.status_code in (401, 429, 503):
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    self._rotate(f"HTTP {resp.status_code}")
                    continue
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                self._rotate(f"HTTP {resp.status_code}")

        raise RuntimeError(f"All Groq attempts failed. Last error: {last_error}")

    async def complete_json(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Like ``complete`` but parses the JSON object the model returns."""
        content = await self.complete(system_prompt, user_prompt, json_mode=True, **kwargs)
        return _parse_json_object(content)


def _parse_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating ```json fences or surrounding prose."""
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise


@lru_cache
def get_groq_client() -> PlanningGroqClient:
    return PlanningGroqClient()
