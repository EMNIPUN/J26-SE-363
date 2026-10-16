"""Public request/response models for the Core API tutor chat route."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from shared.contracts import ErrorInfo, Evidence, NextAction, ResultStatus

# Align with typical chat UX limits; no existing Core API message max was found.
TUTOR_MESSAGE_MAX_LENGTH = 4000


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
