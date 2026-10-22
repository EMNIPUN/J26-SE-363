"""Live smoke: single-student ``tutor.evaluate_bkt`` against MCP evidence.

Read-only: mints a tutor token, loads current evidence via MCP, runs chronological
hold-out evaluation. Does not create, modify, or delete evidence.

Does not print tokens, mint secrets, or raw evidence records.

``evaluated=false`` (insufficient chronological observations) is a valid outcome
when the agent call completes successfully.

Usage (from backend/agentic_framework):
  .\\.venv\\Scripts\\python.exe scripts\\smoke_evaluate_bkt.py

Identity: mint subject must be the Keycloak user linked to the fixture student
(``STUDENT_ID`` in ``tests/fixtures/sprint_data.py``). Defaults match the existing
competency smoke script.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SLAP_SERVER = Path(
    r"D:\Accademic\SLIIT\4 Year\RP\Finalize Topic\A6 - Implementation\Project"
    r"\SELVIA-Learning-Assessment-Platform-SLAP-\server"
)

DEFAULT_ISSUER = "https://auth-mentor.duckdns.org/auth/realms/mentor"
# Keycloak subject linked to STUDENT_ID via SLAP ExternalIdentity (same as other smokes).
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


def _mask_id(value: str | None) -> str:
    if not value or not str(value).strip():
        return "(unset)"
    text = str(value).strip()
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}…{text[-4:]}"


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


def _print_holdout_summary(result: dict[str, Any]) -> None:
    """Print aggregate evaluation fields only — no evidence payloads."""
    print("performance_evidence_count:", result.get("performance_evidence_count"))
    print("student_id (masked):", _mask_id(result.get("student_id")))
    print("project_id:", result.get("project_id"))
    print("sprint_id:", result.get("sprint_id"))

    evaluation = result.get("bkt_holdout_evaluation")
    if not isinstance(evaluation, dict):
        print("bkt_holdout_evaluation: (missing)")
        return

    print("evaluation_scope:", evaluation.get("evaluation_scope"))
    print("evaluated:", evaluation.get("evaluated"))
    print("preferred_model:", evaluation.get("preferred_model"))
    explanation = evaluation.get("explanation")
    if isinstance(explanation, str) and explanation.strip():
        print("explanation:", explanation.strip())

    split = evaluation.get("split") or {}
    if isinstance(split, dict):
        print(
            "split:",
            {
                "sequences_used": split.get("sequences_used"),
                "sequences_skipped": split.get("sequences_skipped"),
                "train_observations": split.get("train_observations"),
                "test_observations": split.get("test_observations"),
                "skipped_concept_count": len(split.get("skipped_concept_ids") or []),
            },
        )

    fit = evaluation.get("fit") or {}
    if isinstance(fit, dict):
        params = fit.get("parameters")
        print(
            "fit:",
            {
                "fitted": fit.get("fitted"),
                "total_observations": fit.get("total_observations"),
                "sequence_count": fit.get("sequence_count"),
                "log_likelihood": fit.get("log_likelihood"),
                "method": fit.get("method"),
                "parameters": params,
            },
        )

    for label in ("baseline_metrics", "fitted_metrics"):
        metrics = evaluation.get(label)
        if not isinstance(metrics, dict):
            print(f"{label}: (none)")
            continue
        print(
            f"{label}:",
            {
                "log_likelihood": metrics.get("log_likelihood"),
                "accuracy": metrics.get("accuracy"),
                "brier_score": metrics.get("brier_score"),
                "n_test_steps": metrics.get("n_test_steps"),
            },
        )


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

    slap_env = _load_env(SLAP_SERVER / ".env")
    ai_env = _load_env(ROOT / ".env")

    payload_input: dict[str, Any] = {}
    # Optional: skip LLM concept selection when you already know concept UUIDs.
    raw_concepts = (ai_env.get("SMOKE_CONCEPT_IDS") or slap_env.get("SMOKE_CONCEPT_IDS") or "").strip()
    if raw_concepts:
        payload_input["concept_ids"] = [part.strip() for part in raw_concepts.split(",") if part.strip()]
        payload_input["course_id"] = (
            ai_env.get("SMOKE_COURSE_ID") or slap_env.get("SMOKE_COURSE_ID") or COURSE_ID
        )

    print("smoke: tutor.evaluate_bkt (single student, MCP evidence)")
    print("neo4j_configured:", settings.neo4j_configured)
    print("openai_configured:", settings.openai_configured)
    print("trusted_student_id (masked):", _mask_id(STUDENT_ID))
    print("course_id (masked):", _mask_id(COURSE_ID))
    print("concept_ids_provided:", bool(payload_input.get("concept_ids")))

    # Required-knowledge path (no concept_ids) needs Neo4j + OpenAI.
    if not payload_input.get("concept_ids"):
        if not settings.neo4j_configured or not settings.openai_configured:
            print(
                "FAIL: Neo4j/OpenAI not configured, or set SMOKE_CONCEPT_IDS "
                "(and optionally SMOKE_COURSE_ID) to skip required-knowledge"
            )
            return 2

    mcp_url = (
        ai_env.get("AI_BACKEND_TUTOR_MCP_URL") or slap_env.get("MCP_RESOURCE_URL") or ""
    ).replace("localhost", "127.0.0.1")
    mint_token = slap_env.get("INTERNAL_TUTOR_MINT_TOKEN")
    slap_base = (
        ai_env.get("SMOKE_SLAP_BASE_URL")
        or slap_env.get("SMOKE_SLAP_BASE_URL")
        or "http://127.0.0.1:5000"
    ).replace("localhost", "127.0.0.1")

    if not mcp_url or not mint_token:
        print("FAIL: MCP URL or INTERNAL_TUTOR_MINT_TOKEN missing")
        return 2

    issuer = (
        ai_env.get("SMOKE_KEYCLOAK_ISSUER")
        or slap_env.get("KEYCLOAK_ISSUER")
        or DEFAULT_ISSUER
    )
    # Must resolve to the same SLAP student as STUDENT_ID (ExternalIdentity link).
    subject = (
        ai_env.get("SMOKE_KEYCLOAK_SUBJECT")
        or slap_env.get("SMOKE_KEYCLOAK_SUBJECT")
        or DEFAULT_SUBJECT
    )

    print("mcp_url_host:", mcp_url.split("://", 1)[-1].split("/", 1)[0])
    print("slap_base_host:", slap_base.split("://", 1)[-1].split("/", 1)[0])

    tutor_token = await _mint(slap_base, mint_token, issuer, subject)
    reset = set_request_tutor_access_token(tutor_token)
    try:
        agent = AdaptiveTutorAgent(
            mcp_url=mcp_url,
            sprint_provider=make_fixture_sprint_provider(),
        )
        request = AgentRequest(
            action="tutor.evaluate_bkt",
            student_id=STUDENT_ID,
            project_id=PROJECT_ID,
            sprint_id=SPRINT_ID,
            input=payload_input,
        )
        response = await agent.handle(request)
    finally:
        reset_request_tutor_access_token(reset)

    print("status:", response.status.value)
    if response.error is not None:
        print("error_code:", response.error.code)
        print("error_message:", response.error.message)

    if response.status is not ResultStatus.COMPLETED:
        print("FAIL: agent status is not completed")
        return 1

    result = response.result if isinstance(response.result, dict) else {}
    _print_holdout_summary(result)

    evaluation = result.get("bkt_holdout_evaluation")
    evaluated = isinstance(evaluation, dict) and evaluation.get("evaluated") is True
    if evaluated:
        print("OK: hold-out evaluation completed (evaluated=true)")
    else:
        print(
            "OK: agent completed; evaluated=false "
            "(insufficient chronological observations for hold-out — valid outcome)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
