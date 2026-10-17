"""State passed between the Decomposition ReAct graph nodes."""

from __future__ import annotations

from typing import TypedDict

from app.agents.project_planning.schemas import (
    CoverageAnalysis,
    DecompositionResult,
    InvestGateResult,
    StoryInvest,
)


class DecompositionState(TypedDict, total=False):
    # inputs
    requirement_id: str
    requirement_text: str
    stories: list[dict]  # [{id, title, description, linked_parent_requirement}]
    threshold: int

    # working memory
    coverage: CoverageAnalysis
    invest_results: list[StoryInvest]
    invest_gate: InvestGateResult
    retrieved_patterns: list[dict]

    # control
    pending_tool: str | None
    tools_run: list[str]
    iterations: int

    # output
    result: DecompositionResult
