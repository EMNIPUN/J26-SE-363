"""Tool functions for each step of the DART protocol.

Each function wraps an LLM call with the corresponding prompt, parses the
JSON response, and returns the structured Pydantic model.
"""

from __future__ import annotations

import asyncio
import logging

from app.agents.project_planning.knowledge import query_exemplars, query_standards
from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.schemas import (
    AgentReasoningTrace,
    ConsultationRequest,
    ConsultationResponse,
    DartCategory,
    DartResolution,
    DartResolutionAction,
    DiagnosticHypothesis,
)
from app.agents.project_planning.subagents.dart.prompts import (
    CATEGORIZE_SYSTEM,
    CONSULT_SYSTEM,
    GATHER_SYSTEM,
    RESOLVE_SYSTEM,
    RESPOND_SYSTEM,
    build_categorize_prompt,
    build_consult_prompt,
    build_gather_prompt,
    build_resolve_prompt,
    build_respond_prompt,
)

logger = logging.getLogger(__name__)


def _parse_category(raw: str) -> DartCategory:
    try:
        return DartCategory(raw.lower().strip())
    except ValueError:
        return DartCategory.AMBIGUOUS


def _parse_action(raw: str) -> DartResolutionAction:
    try:
        return DartResolutionAction(raw.lower().strip())
    except ValueError:
        return DartResolutionAction.ESCALATE


async def gather_traces(
    requirement_text: str,
    source_stage: str,
    source_result: dict,
) -> list[AgentReasoningTrace]:
    client = get_llm_client()
    data = await client.complete_json(
        GATHER_SYSTEM,
        build_gather_prompt(requirement_text, source_stage, source_result),
        max_tokens=3000,
    )
    raw_traces = data.get("traces", [])
    return [
        AgentReasoningTrace(
            agent_name=str(t.get("agent_name", source_stage)),
            diagnosis=str(t.get("diagnosis", "")),
            evidence=[str(e) for e in t.get("evidence", [])],
            criteria_used=[str(c) for c in t.get("criteria_used", [])],
            confidence=float(t.get("confidence", 0.5) or 0.5),
            recommended_action=str(t.get("recommended_action", "")),
            uncertainty_type=str(t.get("uncertainty_type", "")),
        )
        for t in raw_traces
        if isinstance(t, dict)
    ]


async def categorize_issue(
    requirement_text: str,
    traces: list[AgentReasoningTrace],
) -> DiagnosticHypothesis:
    client = get_llm_client()
    traces_dicts = [t.model_dump() for t in traces]
    data = await client.complete_json(
        CATEGORIZE_SYSTEM,
        build_categorize_prompt(requirement_text, traces_dicts),
        max_tokens=1000,
    )
    return DiagnosticHypothesis(
        category=_parse_category(str(data.get("category", "ambiguous"))),
        rationale=str(data.get("rationale", "")),
        supporting_evidence=[str(e) for e in data.get("supporting_evidence", [])],
        confidence=float(data.get("confidence", 0.5) or 0.5),
    )


async def formulate_consultation(
    requirement_text: str,
    hypothesis: DiagnosticHypothesis,
    traces: list[AgentReasoningTrace],
) -> ConsultationRequest:
    client = get_llm_client()
    data = await client.complete_json(
        CONSULT_SYSTEM,
        build_consult_prompt(
            requirement_text,
            hypothesis.model_dump(),
            [t.model_dump() for t in traces],
        ),
        max_tokens=1000,
    )
    return ConsultationRequest(
        target_agent=str(data.get("target_agent", "")),
        question=str(data.get("question", "")),
        context=data.get("context", {}) if isinstance(data.get("context"), dict) else {},
        category=_parse_category(str(data.get("category", hypothesis.category.value))),
    )


async def execute_consultation(
    requirement_text: str,
    consultation: ConsultationRequest,
    source_stage: str,
) -> ConsultationResponse:
    retrieval: list[dict] = []
    try:
        if source_stage == "quality":
            retrieval = await asyncio.to_thread(query_standards, requirement_text, 3)
            retrieval += await asyncio.to_thread(query_exemplars, requirement_text, 3)
        else:
            from app.agents.project_planning.knowledge import query_patterns
            retrieval = await asyncio.to_thread(query_patterns, requirement_text, 3)
    except (OSError, ValueError, RuntimeError):
        logger.warning("DART retrieval augmentation failed; proceeding without")

    client = get_llm_client()
    data = await client.complete_json(
        RESPOND_SYSTEM,
        build_respond_prompt(
            requirement_text,
            consultation.model_dump(),
            source_stage,
            retrieval or None,
        ),
        max_tokens=2000,
    )
    return ConsultationResponse(
        agent_name=str(data.get("agent_name", "dart_consultant")),
        answer=str(data.get("answer", "")),
        evidence=[str(e) for e in data.get("evidence", [])],
        confidence=float(data.get("confidence", 0.5) or 0.5),
        recommended_resolution=str(data.get("recommended_resolution", "")),
    )


async def determine_resolution(
    requirement_text: str,
    hypothesis: DiagnosticHypothesis,
    consultation: ConsultationRequest,
    response: ConsultationResponse,
    traces: list[AgentReasoningTrace],
    dart_iteration: int,
) -> DartResolution:
    client = get_llm_client()
    data = await client.complete_json(
        RESOLVE_SYSTEM,
        build_resolve_prompt(
            requirement_text,
            hypothesis.model_dump(),
            consultation.model_dump(),
            response.model_dump(),
            [t.model_dump() for t in traces],
            dart_iteration,
        ),
        max_tokens=1500,
    )

    action = _parse_action(str(data.get("action", "escalate")))
    confidence_agreement = float(data.get("confidence_agreement", 0.0) or 0.0)

    # Convergence rules
    if dart_iteration >= 2 and action in (DartResolutionAction.RETRIEVE, DartResolutionAction.REFINE):
        action = DartResolutionAction.ESCALATE
    if hypothesis.category == DartCategory.NOVEL and confidence_agreement < 40:
        action = DartResolutionAction.ESCALATE

    return DartResolution(
        action=action,
        rationale=str(data.get("rationale", "")),
        evidence_summary=[str(e) for e in data.get("evidence_summary", [])],
        confidence_agreement=confidence_agreement,
        actionable_feedback=str(data.get("actionable_feedback", "")),
    )
