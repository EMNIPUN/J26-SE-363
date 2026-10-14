"""State passed between the Quality ReAct graph nodes."""

from __future__ import annotations

from typing import TypedDict

from app.agents.project_planning.schemas import RequirementQualityResult, Smell


class QualityState(TypedDict, total=False):
    # inputs
    requirement_id: str
    requirement_text: str
    other_texts: list[str]
    threshold: int

    # working memory (the agent's accumulated evidence)
    smells: list[Smell]
    smell_spans: list[str]
    dimensions_raw: dict  # last LLM payload: {dimensions, confidence, suggested_rewrite}
    reflection_note: str | None  # set when reflect asks for a re-score
    reflection_confidence: float | None

    # control
    pending_tool: str | None
    tools_run: list[str]
    iterations: int
    reflect_count: int
    scoring_failed: bool

    # output
    result: RequirementQualityResult
