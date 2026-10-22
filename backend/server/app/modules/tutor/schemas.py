"""Public request/response models for the Core API tutor routes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from shared.contracts import ErrorInfo, Evidence, NextAction, ResultStatus

# Align with typical chat UX limits; no existing Core API message max was found.
TUTOR_MESSAGE_MAX_LENGTH = 4000

# PP1 demo defaults aligned with the Sprint 1 fixture (P-ETCS / sprint-01).
PP1_DEFAULT_PROJECT_ID = "P-ETCS"
PP1_DEFAULT_SPRINT_ID = "sprint-01"
PP1_DEFAULT_STUDENT_ID = "36841e50-ac3f-4bf2-952e-08eb4315becd"


class TutorChatRequest(BaseModel):
    """Browser-facing tutor chat body. Identity and routing are never accepted here."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=TUTOR_MESSAGE_MAX_LENGTH)
    request_id: UUID | None = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        return stripped


class TutorChatResponse(BaseModel):
    """Public tutor result fields aligned with OrchestrationResponse (no secrets or IDs)."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: ResultStatus
    result: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    next_action: NextAction | None = None
    error: ErrorInfo | None = None


class TutorCompetencyRequest(BaseModel):
    """Browser-facing competency analysis body. Identity is never accepted here."""

    model_config = ConfigDict(extra="forbid")

    project_id: str | None = None
    sprint_id: str | None = None
    concept_ids: list[str] = Field(default_factory=list)
    request_id: UUID | None = None

    @field_validator("project_id", "sprint_id")
    @classmethod
    def optional_ids_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty when provided")
        return stripped

    @field_validator("concept_ids")
    @classmethod
    def concept_ids_must_not_be_blank(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("concept_ids entries must be non-empty strings")
            cleaned.append(item.strip())
        return cleaned


class TutorCompetencyResponse(BaseModel):
    """Public competency analysis result (no secrets)."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: ResultStatus
    result: dict[str, Any] = Field(default_factory=dict)
    error: ErrorInfo | None = None
