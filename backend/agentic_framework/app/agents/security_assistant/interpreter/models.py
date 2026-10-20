"""Data shapes of the LLM Semantic Interpreter.

The interpreter judges ONE scanner finding. It has no way to create findings: its input is a Finding
produced by a deterministic tool, and its output only refers to that finding.
"""

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agents.security_assistant.schemas import Category, Finding

Status = Literal["confirmed", "dismissed", "uncertain"]
EVIDENCE_ID = re.compile(r"^E\d{1,2}$")
MAX_EVIDENCE_ITEMS = 8


def finding_key(f: Finding) -> str:
    """Stable id of a scanner finding, so a verdict can be tied to exactly one finding."""
    raw = "|".join(str(x) for x in (f.tool, f.rule_id, f.file_path, f.line, f.sink, f.category.value))
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


class EvidenceItem(BaseModel):
    """One labelled piece of evidence the model may cite by its id (E1, E2, ...)."""

    id: str
    kind: Literal["finding", "code_snippet", "context"]
    label: str
    content: str

    @field_validator("id")
    @classmethod
    def _id_shape(cls, v: str) -> str:
        if not EVIDENCE_ID.match(v):
            raise ValueError("evidence id must look like E1, E2, ...")
        return v


class EvidenceBundle(BaseModel):
    """The limited set of evidence sent with a finding. Ids are unique."""

    items: list[EvidenceItem] = Field(default_factory=list, max_length=MAX_EVIDENCE_ITEMS)

    @model_validator(mode="after")
    def _unique_ids(self):
        ids = [i.id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence ids must be unique")
        return self

    @property
    def ids(self) -> set[str]:
        return {i.id for i in self.items}


class Verdict(BaseModel):
    """What the model must return. Anything else (extra fields, wrong types) is rejected."""

    model_config = ConfigDict(extra="forbid")

    status: Status
    rationale: str = Field(min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(max_length=MAX_EVIDENCE_ITEMS)
    confidence: float = Field(ge=0.0, le=1.0)


class CallRecord(BaseModel):
    """What is known about one LLM call, without the model's text: for diagnosing rejected or failed answers."""

    model: str | None = None
    response_format: str | None = None  # json_schema (strict) or json_object
    attempts: int = 0
    http_status: int | None = None
    finish_reason: str | None = None  # "stop" normally; "length" = the output limit cut the answer
    output_chars: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    waited_s: float = 0.0  # time spent waiting between retries


class InterpretationResult(BaseModel):
    """The interpreter's answer for one finding, including why a verdict was downgraded or rejected."""

    finding_key: str
    category: Category
    rule_id: str
    status: Status
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    original_status: Status | None = None  # what the model said before a downgrade
    downgraded: bool = False
    downgrade_reason: str | None = None
    output_rejected: bool = False  # the model output failed schema validation
    error: str | None = None  # the LLM could not be called
    model: str | None = None
    prompt_version: str = ""
    call: CallRecord | None = None  # finish reason, output length and token usage; never the model's text
