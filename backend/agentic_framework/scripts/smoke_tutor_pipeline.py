"""Live smoke: sprint context → required knowledge → MCP evidence → BKT competency.

Requires Neo4j, OpenAI, and a running SLAP MCP. Does not print secrets.

Usage (from backend/agentic_framework):
  .\\.venv\\Scripts\\python.exe scripts\\smoke_tutor_pipeline.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SLAP_SERVER = Path(
    r"D:\Accademic\SLIIT\4 Year\RP\Finalize Topic\A6 - Implementation\Project"
    r"\SELVIA-Learning-Assessment-Platform-SLAP-\server"
)

DEFAULT_ISSUER = "https://auth-mentor.duckdns.org/auth/realms/mentor"
DEFAULT_SUBJECT = "a1ff9478-cce0-427d-bbb9-ec91ed3b5566"


def _load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


async def _mint(slap_base: str, mint_token: str, issuer: str, subject: str) -> str:
    import httpx

    url = slap_base.rstrip("/") + "/api/v1/internal/tutor-access-tokens"
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
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
        raise RuntimeError(f"mint failed status={response.status_code}")
    token = (response.json().get("data") or {}).get("accessToken")
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("mint missing accessToken")
    return token.strip()


async def main() -> int:
    from shared.contracts import AgentRequest, ResultStatus

    from app.agents.adaptive_tutor.agent import AdaptiveTutorAgent
    from app.agents.adaptive_tutor.tests.fixtures.sprint_data import (
        COURSE_ID,
        PROJECT_ID,
        SPRINT_ID,
        STUDENT_ID,
        make_fixture_sprint_provider,
    )
    from app.core.config import settings
    from app.core.tutor_token_context import (
        reset_request_tutor_access_token,
        set_request_tutor_access_token,
    )

    print("neo4j_configured:", settings.neo4j_configured)
    print("openai_configured:", settings.openai_configured)
    print("student_id:", STUDENT_ID)
    print("course_id:", COURSE_ID)

    if not settings.neo4j_configured or not settings.openai_configured:
        print("FAIL: Neo4j/OpenAI not configured")
        return 2

    slap_env = _load_env(SLAP_SERVER / ".env")
    ai_env = _load_env(ROOT / ".env")
    mcp_url = (
        ai_env.get("AI_BACKEND_TUTOR_MCP_URL") or slap_env.get("MCP_RESOURCE_URL") or ""
    ).replace("localhost", "127.0.0.1")
    mint_token = slap_env.get("INTERNAL_TUTOR_MINT_TOKEN")
    if not mcp_url or not mint_token:
        print("FAIL: MCP URL or mint token missing")
        return 2

    issuer = slap_env.get("KEYCLOAK_ISSUER") or DEFAULT_ISSUER
    tutor_token = await _mint(
        "http://127.0.0.1:5000",
        mint_token,
        issuer,
        DEFAULT_SUBJECT,
    )
    reset = set_request_tutor_access_token(tutor_token)
    try:
        agent = AdaptiveTutorAgent(
            mcp_url=mcp_url,
            sprint_provider=make_fixture_sprint_provider(),
        )
        request = AgentRequest(
            action="tutor.estimate_competency",
            student_id=STUDENT_ID,
            project_id=PROJECT_ID,
            sprint_id=SPRINT_ID,
            input={},  # course from sprint; concepts from identify; evidence from MCP
        )
        response = await agent.handle(request)
    finally:
        reset_request_tutor_access_token(reset)

    print("status:", response.status.value)
    if response.error is not None:
        print("error_code:", response.error.code)
        print("error_message:", response.error.message)
    print("result:")
    print(json.dumps(response.result, indent=2, default=str))

    if response.status is ResultStatus.COMPLETED:
        print("OK: tutor pipeline (identify + MCP evidence + BKT) completed")
        return 0
    print("FAIL: expected completed status")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
