"""Project Planning agent — the single entry point for every ``planning.*`` action.

This whole component (requirement extraction, the Quality / Decomposition /
Estimation sub-agents, the quality gates and DART) is ONE registered agent. The
shared Main Orchestrator routes any ``planning.*`` action here; everything else
is internal Python behind ``handle()``. See PLAN.md and the Architecture & Build
Guide section 7.
"""

from __future__ import annotations

import asyncio
import base64
import binascii

from shared.contracts import (
    AgentName,
    AgentRequest,
    AgentResponse,
    ErrorInfo,
    Evidence,
    ResultStatus,
)

from app.agents.project_planning.extraction import extract_from_bytes
from app.agents.project_planning.schemas import (
    AnalyzeQualityInput,
    AnalyzeQualityResult,
    ExtractRequirementsInput,
    ExtractRequirementsResult,
    RequirementInput,
    RequirementQualityResult,
)
from app.agents.project_planning.subagents.quality.graph import run_quality_agent

# Actions this component owns (all under the ``planning.`` prefix).
ACTION_ANALYZE_QUALITY = "planning.analyze_quality"
ACTION_EXTRACT_REQUIREMENTS = "planning.extract_requirements"
ACTION_ANALYZE_DECOMPOSITION = "planning.analyze_decomposition"

# Keep concurrent LLM usage under the provider's tokens-per-minute limit.
_MAX_CONCURRENT_SCORING = 3


class ProjectPlanningAgent:
    """Requirement Analysis & Project Planning component."""

    name = AgentName.PROJECT_PLANNING

    async def handle(self, request: AgentRequest) -> AgentResponse:
        if request.action == ACTION_ANALYZE_QUALITY:
            return await self._analyze_quality(request)
        if request.action == ACTION_EXTRACT_REQUIREMENTS:
            return await self._extract_requirements(request)

        # Known-but-not-yet-built actions return a clear, typed failure.
        return self._failed(request, "action_not_implemented", f"Action '{request.action}' is not implemented yet.")

    # ------------------------------------------------------------------
    # planning.analyze_quality
    # ------------------------------------------------------------------
    async def _analyze_quality(self, request: AgentRequest) -> AgentResponse:
        payload = AnalyzeQualityInput.model_validate(request.input)
        scored = await self._score_requirements(payload.requirements, payload.options.threshold)
        result = AnalyzeQualityResult(threshold=payload.options.threshold, requirements=scored)
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result=result.model_dump(),
            evidence=[_evidence_for(r) for r in scored],
        )

    # ------------------------------------------------------------------
    # planning.extract_requirements  (SRS .docx -> requirement list, optional quality)
    # ------------------------------------------------------------------
    async def _extract_requirements(self, request: AgentRequest) -> AgentResponse:
        payload = ExtractRequirementsInput.model_validate(request.input)
        try:
            data = base64.b64decode(payload.file_base64, validate=True)
        except (binascii.Error, ValueError):
            return self._failed(request, "invalid_file", "file_base64 is not valid base64.")

        try:
            requirements = extract_from_bytes(data)
        except Exception as exc:  # noqa: BLE001 - surface any parse failure cleanly
            return self._failed(request, "extraction_failed", f"Could not parse the .docx: {exc}")

        quality: AnalyzeQualityResult | None = None
        evidence: list[Evidence] = []
        if payload.options.analyze_quality and requirements:
            scored = await self._score_requirements(requirements, payload.options.threshold)
            quality = AnalyzeQualityResult(threshold=payload.options.threshold, requirements=scored)
            evidence = [_evidence_for(r) for r in scored]

        result = ExtractRequirementsResult(
            count=len(requirements),
            requirements=requirements,
            quality=quality,
        )
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result=result.model_dump(),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # shared helpers
    # ------------------------------------------------------------------
    async def _score_requirements(
        self, requirements: list[RequirementInput], threshold: int
    ) -> list[RequirementQualityResult]:
        all_texts = [r.text for r in requirements]
        # Bound concurrency: the ReAct loop makes 2 LLM calls per requirement, so
        # firing every requirement at once trips the LLM tokens-per-minute limit.
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SCORING)

        async def _score_one(req: RequirementInput) -> RequirementQualityResult:
            async with semaphore:
                return await run_quality_agent(
                    req,
                    other_texts=[t for t in all_texts if t != req.text],
                    threshold=threshold,
                )

        scored = await asyncio.gather(*(_score_one(req) for req in requirements))
        return list(scored)

    def _failed(self, request: AgentRequest, code: str, message: str) -> AgentResponse:
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.FAILED,
            error=ErrorInfo(code=code, message=message, retryable=False),
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
