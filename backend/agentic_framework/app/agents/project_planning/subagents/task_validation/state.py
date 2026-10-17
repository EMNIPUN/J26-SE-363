"""State passed between the Task Validation graph nodes."""

from __future__ import annotations

from typing import TypedDict

from app.agents.project_planning.schemas import (
    TaskSetCoverage,
    TaskValidationItem,
    TaskValidationResult,
)


class TaskValidationState(TypedDict, total=False):
    # inputs
    story_ref: str
    story_text: str
    requirement_text: str
    tasks: list[dict]  # [{id, title, description}]

    # working memory
    items: list[TaskValidationItem]
    coverage: TaskSetCoverage
    analysis_failed: bool
    failure_reason: str | None

    # control
    pending_tool: str | None
    tools_run: list[str]

    # output
    result: TaskValidationResult
