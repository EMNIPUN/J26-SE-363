"""Provider-agnostic LLM client for the Project Planning agent.

Every provider is reached through the OpenAI-compatible ``chat/completions`` API,
so one client speaks to any of them by changing the base URL + model + key.
``PlanningLLM`` tries the configured providers in order (primary first) and fails
over to the next. Gemini is the default; OpenAI is pre-wired for when a key is
added. Adding another OpenAI-compatible provider is one entry in ``PROVIDERS``.

Config (backend/agentic_framework/.env):
    PLANNING_LLM_PROVIDER      primary provider: "gemini" (default) or "openai"
    PLANNING_GEMINI_API_KEYS   comma-separated Google AI Studio keys (aistudio.google.com)
    PLANNING_GEMINI_MODEL      default gemini-3.5-flash-lite
    PLANNING_OPENAI_API_KEYS   comma-separated OpenAI keys (future)
    PLANNING_OPENAI_MODEL      default gpt-4o-mini

A provider is used only if it has at least one key.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from functools import lru_cache
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# HTTP 429 handling: wait for the per-minute window to free up (bounded).
RATE_LIMIT_MAX_WAITS = 3
RATE_LIMIT_WAIT_CAP = 20.0

# Provider registry. Each provider is an OpenAI-compatible chat/completions endpoint.
PROVIDERS: dict[str, dict[str, Any]] = {
    "gemini": {
        "label": "Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_env": ("PLANNING_GEMINI_API_KEYS", "PLANNING_GEMINI_API_KEY", "GEMINI_API_KEYS", "GEMINI_API_KEY"),
        "model_env": ("PLANNING_GEMINI_MODEL",),
        # Gemini 2.0 Flash was shut down. 2.5 access is also restricted for
        # newly-created AI Studio projects, so use a currently available
        # low-latency model as the default for structured grading requests.
        "model": "gemini-3.5-flash-lite",
        "fallback_model": "gemini-3.8-flash",
        # 2.5 models "think" by default, which consumes the output budget and
        # truncates JSON. Disable it for this structured scoring task.
        "extra_payload": {"reasoning_effort": "none"},
    },
    "openai": {
        "label": "OpenAI",
        "url": "https://api.openai.com/v1/chat/completions",
        "key_env": ("PLANNING_OPENAI_API_KEYS", "PLANNING_OPENAI_API_KEY", "OPENAI_API_KEYS", "OPENAI_API_KEY"),
        "model_env": ("PLANNING_OPENAI_MODEL",),
        "model": "gpt-4o-mini",
        "fallback_model": "gpt-4o",
    },
}

DEFAULT_PRIMARY = "gemini"


class LLMConfigError(RuntimeError):
    """No LLM provider has an API key configured."""


def _first_env(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def _retry_after_seconds(resp: httpx.Response) -> float:
    header = resp.headers.get("retry-after")
    if header:
        try:
            return min(float(header), RATE_LIMIT_WAIT_CAP)
        except ValueError:
            pass
    match = re.search(r"try again in ([0-9.]+)s", resp.text)
    if match:
        try:
            return min(float(match.group(1)) + 0.5, RATE_LIMIT_WAIT_CAP)
        except ValueError:
            pass
    return 5.0


class OpenAICompatClient:
    """One OpenAI-compatible provider (e.g. Gemini, OpenAI) with key rotation,
    model fallback and 429 back-off."""

    def __init__(
        self,
        label: str,
        url: str,
        api_keys: list[str],
        model: str,
        fallback_model: str,
        timeout: float = 45.0,
        extra_payload: dict[str, Any] | None = None,
    ) -> None:
        self.label = label
        self.url = url
        self.api_keys = api_keys
        self.primary_model = model
        self.fallback_model = fallback_model
        self.timeout = timeout
        self.extra_payload = extra_payload or {}
        self._key_index = 0

    @property
    def configured(self) -> bool:
        return bool(self.api_keys)

    def _rotate(self, reason: str) -> None:
        old = self._key_index
        self._key_index = (self._key_index + 1) % len(self.api_keys)
        logger.warning("[%s] key %d failed (%s); rotated to %d", self.label, old + 1, reason, self._key_index + 1)

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
        if not self.configured:
            raise LLMConfigError(f"{self.label} has no API key configured.")

        target_model = model or self.primary_model
        last_error: str | None = None
        fallback_attempted = target_model == self.fallback_model
        rate_limit_waits = 0
        max_attempts = len(self.api_keys) * 2 + RATE_LIMIT_MAX_WAITS

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
                if self.extra_payload:
                    payload.update(self.extra_payload)

                try:
                    resp = await client.post(
                        self.url,
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
                    last_error = f"HTTP 404 for model {target_model}: {resp.text[:500]}"
                    if fallback_attempted:
                        logger.error("[%s] fallback model %s was also unavailable", self.label, target_model)
                        break
                    logger.warning(
                        "[%s] model %s not found; falling back to %s",
                        self.label,
                        target_model,
                        self.fallback_model,
                    )
                    target_model = self.fallback_model
                    fallback_attempted = True
                    continue
                if resp.status_code == 429:  # rate limited -> try another key, then wait
                    last_error = f"HTTP 429: {resp.text[:200]}"
                    self._rotate("HTTP 429")
                    if rate_limit_waits < RATE_LIMIT_MAX_WAITS:
                        rate_limit_waits += 1
                        wait = _retry_after_seconds(resp)
                        logger.warning(
                            "[%s] rate limited; waiting %.1fs then retrying (%d/%d)",
                            self.label, wait, rate_limit_waits, RATE_LIMIT_MAX_WAITS,
                        )
                        await asyncio.sleep(wait)
                        continue
                    break
                if resp.status_code in (401, 503):
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    self._rotate(f"HTTP {resp.status_code}")
                    continue
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                self._rotate(f"HTTP {resp.status_code}")

        raise RuntimeError(f"All {self.label} attempts failed. Last error: {last_error}")


class PlanningLLM:
    """Ordered set of providers; each call tries them in order until one succeeds."""

    def __init__(self, providers: list[OpenAICompatClient]) -> None:
        self._providers = providers

    @property
    def configured(self) -> bool:
        return bool(self._providers)

    @property
    def provider_labels(self) -> list[str]:
        return [p.label for p in self._providers]

    async def complete(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        if not self._providers:
            raise LLMConfigError(
                "No LLM provider configured. Set PLANNING_GEMINI_API_KEYS (or "
                "PLANNING_OPENAI_API_KEYS) in backend/agentic_framework/.env"
            )
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                return await provider.complete(system_prompt, user_prompt, **kwargs)
            except Exception as exc:  # noqa: BLE001 - fail over to the next provider
                last_error = exc
                logger.warning("[llm] provider %s failed (%s); trying next", provider.label, exc)
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    async def complete_json(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> dict[str, Any]:
        content = await self.complete(system_prompt, user_prompt, json_mode=True, **kwargs)
        return _parse_json_object(content)


def _parse_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating code fences or surrounding prose."""
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise


def _build_provider(name: str) -> OpenAICompatClient | None:
    cfg = PROVIDERS[name]
    raw_keys = _first_env(*cfg["key_env"])
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
    if not api_keys:
        return None
    model = _first_env(*cfg["model_env"]) or cfg["model"]
    return OpenAICompatClient(
        cfg["label"], cfg["url"], api_keys, model, cfg["fallback_model"],
        extra_payload=cfg.get("extra_payload"),
    )


def _ordered_provider_names() -> list[str]:
    primary = (os.getenv("PLANNING_LLM_PROVIDER") or DEFAULT_PRIMARY).strip().lower()
    ordered = [primary, *[n for n in PROVIDERS if n != primary]]
    seen: set[str] = set()
    result: list[str] = []
    for name in ordered:
        if name in PROVIDERS and name not in seen:
            seen.add(name)
            result.append(name)
    return result


@lru_cache
def get_llm_client() -> PlanningLLM:
    providers = [p for name in _ordered_provider_names() if (p := _build_provider(name))]
    if providers:
        logger.info("[llm] providers (in order): %s", ", ".join(p.label for p in providers))
    else:
        logger.warning("[llm] no provider configured (no Gemini or OpenAI key)")
    return PlanningLLM(providers)
