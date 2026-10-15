"""State passed between the Decomposition ReAct graph nodes."""

from __future__ import annotations

from typing import TypedDict

from app.agents.project_planning.schemas import DecompositionResult, StoryInvest


class DecompositionState(TypedDict, total=False):
    # inputs
    requirement_id: str
    requirement_text: str
    stories: list[dict]  # [{id, title, acceptance_criteria}]
    threshold: int

    # working memory
    invest_results: list[StoryInvest]
    coverage: float
    aspects: list[dict]  # [{id, label, covered, best_similarity}]
    retrieved_patterns: list[dict]
    score_raw: dict  # LLM payload: {overall_score, summary, confidence}
    reflection_note: str | None
    reflection_confidence: float | None

    # control
    pending_tool: str | None
    tools_run: list[str]
    iterations: int
    reflect_count: int
    scoring_failed: bool

    # output
    result: DecompositionResult
