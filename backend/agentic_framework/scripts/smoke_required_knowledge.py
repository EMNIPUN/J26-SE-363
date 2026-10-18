"""Opt-in live smoke for tutor.identify_required_knowledge.

Uses real Neo4j + OpenAI from backend/agentic_framework/.env.
Does not print secrets.

Usage (from backend/agentic_framework):
  .\\.venv\\Scripts\\python.exe scripts\\smoke_required_knowledge.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Allow running as a script from backend/agentic_framework/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.contracts import AgentRequest, ResultStatus

from app.agents.adaptive_tutor.agent import AdaptiveTutorAgent
from app.agents.adaptive_tutor.tests.fixtures.sprint_data import (
    PROJECT_ID,
    SPRINT_ID,
    make_fixture_sprint_provider,
)
from app.core.config import settings

# Verified Course.id from the current Aura seed graph.
DEFAULT_COURSE_ID = "b55fea72-3a5b-4809-99f6-75f0505c501f"


async def main() -> int:
    print("neo4j_configured:", settings.neo4j_configured)
    print("openai_configured:", settings.openai_configured)
    print("openai_model:", settings.OPENAI_MODEL)

    if not settings.neo4j_configured:
        print("FAIL: Neo4j settings missing in .env")
        return 2
    if not settings.openai_configured:
        print("FAIL: OPENAI_API_KEY missing in .env")
        return 2

    agent = AdaptiveTutorAgent(sprint_provider=make_fixture_sprint_provider())
    request = AgentRequest(
        action="tutor.identify_required_knowledge",
        student_id="STU-001",
        project_id=PROJECT_ID,
        sprint_id=SPRINT_ID,
        input={"course_id": DEFAULT_COURSE_ID},
    )

    response = await agent.handle(request)
    print("status:", response.status.value)
    if response.error is not None:
        print("error_code:", response.error.code)
        print("error_message:", response.error.message)
    print("result:")
    print(json.dumps(response.result, indent=2, default=str))

    if response.status is ResultStatus.COMPLETED:
        print("OK: required-knowledge identification completed")
        return 0

    print("FAIL: expected completed status")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
