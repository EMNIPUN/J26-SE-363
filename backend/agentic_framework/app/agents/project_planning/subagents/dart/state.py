"""State passed between the DART ReAct graph nodes."""

from __future__ import annotations

from typing import TypedDict

from app.agents.project_planning.schemas import (
    AgentReasoningTrace,
    ConsultationRequest,
    ConsultationResponse,
    DartCaseResult,
    DartResolution,
    DiagnosticHypothesis,
)


class DartState(TypedDict, total=False):
    # inputs
    requirement_id: str
    requirement_text: str
    trigger_reason: str
    source_stage: str
    source_result: dict
    stories: list[dict]

    # working memory
    traces: list[AgentReasoningTrace]
    hypothesis: DiagnosticHypothesis | None
    consultation: ConsultationRequest | None
    consultation_response: ConsultationResponse | None
    resolution: DartResolution | None

    # control
    pending_step: str | None
    steps_run: list[str]
    iterations: int
    dart_iteration: int

    # output
    result: DartCaseResult
