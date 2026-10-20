"""Fetch live MCP performance evidence and write a fixture snapshot.

Usage (from backend/agentic_framework, SLAP running):
  .\\.venv\\Scripts\\python.exe scripts\\fetch_live_evidence_fixture.py

Loads mint credentials from SLAP server/.env. Does not print secrets.
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
OUT_PATH = (
    ROOT
    / "app"
    / "agents"
    / "adaptive_tutor"
    / "tests"
    / "fixtures"
    / "live_performance_evidence.py"
)

# Linked Keycloak subject for STUDENT_ID in sprint_data.py
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
    last_error: Exception | None = None
    for attempt in range(3):
        try:
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
        except Exception as exc:  # noqa: BLE001 - retry transient local HTTP stalls
            last_error = exc
            await asyncio.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"mint failed after retries: {type(last_error).__name__}")


async def main() -> int:
    from app.agents.adaptive_tutor.tests.fixtures.sprint_data import COURSE_ID, STUDENT_ID
    from app.integrations.selvia_tutor_mcp import SelviaTutorMcpClient

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
    subject = DEFAULT_SUBJECT
    tutor_token = await _mint("http://127.0.0.1:5000", mint_token, issuer, subject)

    class _Provider:
        async def get_access_token(self) -> str:
            return tutor_token

    client = SelviaTutorMcpClient(mcp_url, _Provider())
    evidence = await client.get_current_evidence(course_id=COURSE_ID)
    activities = await client.get_learning_activities(course_id=COURSE_ID, limit=50)

    evidence_dicts = [row.model_dump(mode="json", by_alias=True) for row in evidence]
    activity_dicts = [row.model_dump(mode="json", by_alias=True) for row in activities]

    import pprint

    # Pretty Python literals (None instead of JSON null).
    content = (
        '"""Live MCP snapshot for the sprint fixture student/course.\n\n'
        "Regenerate with: python scripts/fetch_live_evidence_fixture.py\n"
        '"""\n\n'
        f'STUDENT_ID = "{STUDENT_ID}"\n'
        f'COURSE_ID = "{COURSE_ID}"\n\n'
        "LIVE_PERFORMANCE_EVIDENCE = "
        + pprint.pformat(evidence_dicts, width=100, sort_dicts=False)
        + "\n\nLIVE_LEARNING_ACTIVITIES = "
        + pprint.pformat(activity_dicts, width=100, sort_dicts=False)
        + "\n"
    )
    OUT_PATH.write_text(content, encoding="utf-8")
    print("wrote:", OUT_PATH)
    print("student_id:", STUDENT_ID)
    print("course_id:", COURSE_ID)
    print("evidence_count:", len(evidence_dicts))
    print("activity_count:", len(activity_dicts))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
