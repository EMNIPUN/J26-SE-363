"""Project Planning agent — the single entry point for every ``planning.*`` action.

This whole component (requirement extraction, the Quality / Decomposition /
Estimation sub-agents, the quality gates and DART) is ONE registered agent. The
shared Main Orchestrator routes any ``planning.*`` action here; everything else
is internal Python behind ``handle()``. See PLAN.md and the Architecture & Build
Guide section 7.
"""

from __future__ import annotations

import asyncio

from shared.contracts import (
    AgentName,
    AgentRequest,
    AgentResponse,
    ErrorInfo,
    Evidence,
    ResultStatus,
)

from app.agents.project_planning.schemas import (
    AnalyzeQualityInput,
    AnalyzeQualityResult,
    RequirementQualityResult,
)
from app.agents.project_planning.subagents.quality.scorer import score_requirement

# Actions this component owns (all under the ``planning.`` prefix).
ACTION_ANALYZE_QUALITY = "planning.analyze_quality"
ACTION_EXTRACT_REQUIREMENTS = "planning.extract_requirements"
ACTION_ANALYZE_DECOMPOSITION = "planning.analyze_decomposition"


class ProjectPlanningAgent:
    """Requirement Analysis & Project Planning component."""

    name = AgentName.PROJECT_PLANNING

    async def handle(self, request: AgentRequest) -> AgentResponse:
        if request.action == ACTION_ANALYZE_QUALITY:
            return await self._analyze_quality(request)

        # Known-but-not-yet-built actions return a clear, typed failure.
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.FAILED,
            error=ErrorInfo(
                code="action_not_implemented",
                message=f"Action '{request.action}' is not implemented yet.",
                retryable=False,
            ),
        )

    async def _analyze_quality(self, request: AgentRequest) -> AgentResponse:
        payload = AnalyzeQualityInput.model_validate(request.input)
        threshold = payload.options.threshold
        all_texts = [r.text for r in payload.requirements]

        # Score every requirement; each one also sees the others (consistency/traceability).
        scored: list[RequirementQualityResult] = await asyncio.gather(
            *(
                score_requirement(
                    req,
                    other_texts=[t for t in all_texts if t != req.text],
                    threshold=threshold,
                )
                for req in payload.requirements
            )
        )

        result = AnalyzeQualityResult(threshold=threshold, requirements=list(scored))
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result=result.model_dump(),
            evidence=[_evidence_for(r) for r in scored],
        )


def _evidence_for(r: RequirementQualityResult) -> Evidence:
    """One transparency record per requirement (NFR-05)."""
    return Evidence(
        source="quality_agent",
        description=(
            f"{r.id}: {r.overall_score}/100 ({r.status.value}); "
            f"{len(r.smells)} smell(s); confidence {r.confidence:.2f}"
        ),
        data={
            "requirement_id": r.id,
            "gate_action": r.gate_action.value,
            "dart_triggered": r.dart_triggered,
            "smells": [s.model_dump() for s in r.smells],
        },
    )
