#!/usr/bin/env python3
"""Opt-in live MCP smoke test for a dedicated SLAP test instance.

Disabled by default. Never prints tokens, Authorization headers, or secrets.
Does not call the public Core API tutor route. Does not write to any database.

Required to run:
  SELVIA_MCP_SMOKE_TEST=1
  AI_BACKEND_TUTOR_MCP_URL=<dedicated test MCP resource URL>

Token (choose one):
  SELVIA_MCP_SMOKE_TUTOR_TOKEN=<already-minted short-lived tutor token>
  or mint via trusted Core-side credential:
    SLAP_BASE_URL + INTERNAL_TUTOR_MINT_TOKEN + SELVIA_MCP_SMOKE_ISSUER + SELVIA_MCP_SMOKE_SUBJECT

Exit codes:
  0 success, 2 missing/unsafe config, 3 MCP/auth failure, 4 unexpected error

Prerequisites and matching rules (placeholders only):
  docs/MCP_LIVE_TEST_CHECKLIST.md
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

# Ensure backend/agentic_framework is on the path when run as a script.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _fail(code: int, message: str) -> int:
    print(f"MCP smoke test: {message}", file=sys.stderr)
    return code


class _EnvTokenProvider:
    def __init__(self, token: str) -> None:
        self._token = token

    async def get_access_token(self) -> str:
        return self._token


async def _mint_tutor_token(
    *,
    slap_base_url: str,
    mint_token: str,
    issuer: str,
    subject: str,
) -> str:
    import httpx

    url = slap_base_url.rstrip("/") + "/api/v1/internal/tutor-access-tokens"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {mint_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"issuer": issuer, "subject": subject},
        )
    if response.status_code != 200:
        raise RuntimeError(f"mint failed with status {response.status_code}")
    payload: dict[str, Any] = response.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    token = data.get("accessToken") if isinstance(data, dict) else None
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("mint response missing accessToken")
    return token


async def _run() -> int:
    if _env("SELVIA_MCP_SMOKE_TEST") != "1":
        return _fail(
            2,
            "disabled (set SELVIA_MCP_SMOKE_TEST=1 to opt in on a dedicated test MCP)",
        )

    mcp_url = _env("AI_BACKEND_TUTOR_MCP_URL") or _env("TUTOR_MCP_URL")
    if not mcp_url:
        return _fail(2, "AI_BACKEND_TUTOR_MCP_URL is not configured")

    # Refuse obvious non-test remote hosts without an explicit override.
    host = mcp_url.lower()
    allow_remote = _env("SELVIA_MCP_SMOKE_ALLOW_REMOTE") == "1"
    if not allow_remote and not any(
        marker in host for marker in ("localhost", "127.0.0.1", ".local/")
    ):
        return _fail(
            2,
            "MCP URL host is not localhost; set SELVIA_MCP_SMOKE_ALLOW_REMOTE=1 "
            "only for an explicitly approved dedicated test instance",
        )

    tutor_token = _env("SELVIA_MCP_SMOKE_TUTOR_TOKEN")
    if not tutor_token:
        slap_base = _env("SLAP_BASE_URL")
        mint_token = _env("INTERNAL_TUTOR_MINT_TOKEN")
        issuer = _env("SELVIA_MCP_SMOKE_ISSUER")
        subject = _env("SELVIA_MCP_SMOKE_SUBJECT")
        if not all([slap_base, mint_token, issuer, subject]):
            return _fail(
                2,
                "no tutor token: set SELVIA_MCP_SMOKE_TUTOR_TOKEN, or configure "
                "SLAP_BASE_URL + INTERNAL_TUTOR_MINT_TOKEN + "
                "SELVIA_MCP_SMOKE_ISSUER + SELVIA_MCP_SMOKE_SUBJECT",
            )
        try:
            tutor_token = await _mint_tutor_token(
                slap_base_url=slap_base,
                mint_token=mint_token,
                issuer=issuer,
                subject=subject,
            )
        except Exception:
            return _fail(3, "trusted mint request failed (details omitted)")

    from app.integrations.selvia_tutor_mcp import (
        SelviaMcpAuthError,
        SelviaMcpError,
        SelviaTutorMcpClient,
    )

    client = SelviaTutorMcpClient(mcp_url, _EnvTokenProvider(tutor_token))

    try:
        evidence = await client.get_current_evidence()
        activities = await client.get_learning_activities(limit=5)
    except SelviaMcpAuthError:
        return _fail(3, "MCP authentication rejected")
    except SelviaMcpError:
        return _fail(3, "MCP tool call failed")
    except Exception:
        return _fail(4, "unexpected MCP client failure")

    # Summarize counts only — never dump records that may contain personal data in CI logs
    # unless explicitly requested for a local debugging session.
    print(
        "MCP smoke test: OK "
        f"evidence_records={len(evidence)} activity_records={len(activities)}"
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    finally:
        # Drop any lingering references; do not print env or tokens.
        pass


if __name__ == "__main__":
    raise SystemExit(main())
