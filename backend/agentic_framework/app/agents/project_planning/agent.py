"""Project Planning agent — the single entry point for every ``planning.*`` action.

This whole component (requirement extraction, the Quality / Decomposition /
Estimation sub-agents, the quality gates and DART) is ONE registered agent. The
shared Main Orchestrator routes any ``planning.*`` action here; everything else
is internal Python behind ``handle()``. See PLAN.md and the Architecture & Build
Guide section 7.

SKELETON STAGE: ``handle()`` wires routing and the response shape with
placeholder scoring. The real ReAct component orchestrator replaces the
``_analyze_quality_stub`` body in a later step.
"""

from __future__ import annotations

from shared.contracts import (
    AgentName,
    AgentRequest,
    AgentResponse,
    ErrorInfo,
    ResultStatus,
)

from app.agents.project_planning.schemas import (
    AnalyzeQualityInput,
    AnalyzeQualityResult,
    DimensionScore,
    GateAction,
    GateStatus,
    QUALITY_DIMENSIONS,
    RequirementQualityResult,
)

# Actions this component owns (all under the ``planning.`` prefix).
ACTION_ANALYZE_QUALITY = "planning.analyze_quality"
ACTION_EXTRACT_REQUIREMENTS = "planning.extract_requirements"
ACTION_ANALYZE_DECOMPOSITION = "planning.analyze_decomposition"


class ProjectPlanningAgent:
    """Requirement Analysis & Project Planning component."""

    name = AgentName.PROJECT_PLANNING

    async def handle(self, request: AgentRequest) -> AgentResponse:
        if request.action == ACTION_ANALYZE_QUALITY:
            return self._analyze_quality_stub(request)

        # Known-but-not-yet-built actions return a clear, typed failure rather than crashing the orchestrator.
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

    # ------------------------------------------------------------------
    # Placeholder scoring — proves routing + response shape end-to-end.
    # Replaced by the Quality ReAct sub-agent (plan task 5).
    # ------------------------------------------------------------------
    def _analyze_quality_stub(self, request: AgentRequest) -> AgentResponse:
        payload = AnalyzeQualityInput.model_validate(request.input)
        threshold = payload.options.threshold

        results: list[RequirementQualityResult] = []
        for req in payload.requirements:
            placeholder = 80  # deterministic stub; real scores come from the agent
            dim_scores = {
                dim: DimensionScore(score=placeholder, rationale="placeholder (skeleton)")
                for dim in QUALITY_DIMENSIONS
            }
            status = (
                GateStatus.PASSED if placeholder >= threshold else GateStatus.BLOCKED
            )
            action = GateAction.PASS if placeholder >= threshold else GateAction.BLOCK
            results.append(
                RequirementQualityResult(
                    id=req.id,
                    overall_score=placeholder,
                    status=status,
                    gate_action=action,
                    dimension_scores=dim_scores,
                    confidence=1.0,
                    dart_triggered=False,
                )
            )

        result = AnalyzeQualityResult(threshold=threshold, requirements=results)
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result=result.model_dump(),
        )
