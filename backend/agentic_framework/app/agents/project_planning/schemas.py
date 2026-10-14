"""Pydantic models for the Project Planning agent.

These ride *inside* the shared contract: an action-specific input travels in
``AgentRequest.input`` and the structured result in ``AgentResponse.result``.
The shared ``AgentRequest`` / ``AgentResponse`` contract is never forked.

Scope for the viva: Requirement Quality analysis (built first), then
Decomposition, then DART. Effort estimation is post-viva.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Quality analysis — the six IEEE 830 dimensions (decision 3)
# ---------------------------------------------------------------------------

QUALITY_DIMENSIONS: tuple[str, ...] = (
    "clarity",
    "completeness",
    "correctness",
    "testability",
    "consistency",
    "traceability",
)

DEFAULT_QUALITY_THRESHOLD = 75  # FR-04, decision 5


class RequirementType(str, Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    UNKNOWN = "unknown"


class GateStatus(str, Enum):
    PASSED = "passed"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class GateAction(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    DART = "dart"  # low confidence -> arbitration


# ----- input (inside AgentRequest.input) -----------------------------------


class RequirementInput(BaseModel):
    id: str
    text: str
    type: RequirementType = RequirementType.UNKNOWN


class QualityOptions(BaseModel):
    threshold: int = DEFAULT_QUALITY_THRESHOLD


class AnalyzeQualityInput(BaseModel):
    """Payload for the ``planning.analyze_quality`` action."""

    requirements: list[RequirementInput] = Field(default_factory=list)
    # Full SRS requirement texts, used by cross_req_checker for consistency/traceability.
    srs_context: dict = Field(default_factory=dict)
    options: QualityOptions = Field(default_factory=QualityOptions)


# ----- result (inside AgentResponse.result) --------------------------------


class DimensionScore(BaseModel):
    score: int  # 0-100
    rationale: str = ""
    issues: list[str] = Field(default_factory=list)


class Smell(BaseModel):
    type: str
    span: str = ""
    suggestion: str = ""


class RetrievalEvidence(BaseModel):
    """What the RAG/similarity tools retrieved while scoring (for UI transparency)."""

    standards: list[dict] = Field(default_factory=list)       # IEEE 830 / SMART criteria
    exemplars: list[dict] = Field(default_factory=list)       # graded example requirements
    cross_req_hits: list[dict] = Field(default_factory=list)  # similar other requirements


class RequirementQualityResult(BaseModel):
    id: str
    overall_score: int
    status: GateStatus
    gate_action: GateAction
    dimension_scores: dict[str, DimensionScore] = Field(default_factory=dict)
    smells: list[Smell] = Field(default_factory=list)
    suggested_rewrite: str | None = None
    confidence: float = 1.0
    dart_triggered: bool = False
    retrieval: RetrievalEvidence | None = None


class AnalyzeQualityResult(BaseModel):
    threshold: int = DEFAULT_QUALITY_THRESHOLD
    requirements: list[RequirementQualityResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Requirement extraction — SRS .docx -> requirement list (FR-01)
# ---------------------------------------------------------------------------


class ExtractOptions(BaseModel):
    # When true, also run quality analysis on the extracted requirements.
    analyze_quality: bool = False
    threshold: int = DEFAULT_QUALITY_THRESHOLD


class ExtractRequirementsInput(BaseModel):
    """Payload for ``planning.extract_requirements``.

    The Core API base64-encodes the uploaded .docx into ``file_base64``.
    """

    file_base64: str
    filename: str | None = None
    options: ExtractOptions = Field(default_factory=ExtractOptions)


class ExtractRequirementsResult(BaseModel):
    count: int
    requirements: list[RequirementInput] = Field(default_factory=list)
    quality: AnalyzeQualityResult | None = None
