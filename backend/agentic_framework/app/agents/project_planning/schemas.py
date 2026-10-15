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


# ---------------------------------------------------------------------------
# Decomposition analysis — INVEST + coverage (Function 2)
# ---------------------------------------------------------------------------

INVEST_CRITERIA: tuple[str, ...] = (
    "independent",
    "negotiable",
    "valuable",
    "estimable",
    "small",
    "testable",
)

DEFAULT_DECOMPOSITION_THRESHOLD = 75


class StoryInput(BaseModel):
    id: str
    title: str
    acceptance_criteria: str = ""


class DecompositionOptions(BaseModel):
    threshold: int = DEFAULT_DECOMPOSITION_THRESHOLD


class AnalyzeDecompositionInput(BaseModel):
    """Payload for ``planning.analyze_decomposition``."""

    requirement: RequirementInput
    stories: list[StoryInput] = Field(default_factory=list)
    options: DecompositionOptions = Field(default_factory=DecompositionOptions)


# ----- result ----------------------------------------------------------------


class InvestCriterion(BaseModel):
    passed: bool
    note: str = ""


class StoryInvest(BaseModel):
    story_id: str
    independent: InvestCriterion = Field(default_factory=lambda: InvestCriterion(passed=True))
    negotiable: InvestCriterion = Field(default_factory=lambda: InvestCriterion(passed=True))
    valuable: InvestCriterion = Field(default_factory=lambda: InvestCriterion(passed=True))
    estimable: InvestCriterion = Field(default_factory=lambda: InvestCriterion(passed=True))
    small: InvestCriterion = Field(default_factory=lambda: InvestCriterion(passed=True))
    testable: InvestCriterion = Field(default_factory=lambda: InvestCriterion(passed=True))
    overall_pass: bool = True


class CoverageAspect(BaseModel):
    id: str
    label: str
    covered: bool = False


class DecompositionResult(BaseModel):
    requirement_ref: str
    overall_score: int
    status: GateStatus
    gate_action: GateAction
    coverage: float = 0.0
    aspects: list[CoverageAspect] = Field(default_factory=list)
    gaps: list[CoverageAspect] = Field(default_factory=list)
    stories: list[StoryInvest] = Field(default_factory=list)
    patterns: list[dict] = Field(default_factory=list)
    summary: str = ""
    confidence: float = 1.0
    dart_triggered: bool = False
    retrieval: dict = Field(default_factory=dict)


class AnalyzeDecompositionResult(BaseModel):
    threshold: int = DEFAULT_DECOMPOSITION_THRESHOLD
    result: DecompositionResult | None = None


# ---------------------------------------------------------------------------
# DART — Diagnostic Arbitration using Reasoning Traces (Function 3 / Novelty)
# ---------------------------------------------------------------------------


class DartCategory(str, Enum):
    COMPOUND = "compound"
    AMBIGUOUS = "ambiguous"
    STRUCTURAL = "structural"
    NOVEL = "novel"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class DartResolutionAction(str, Enum):
    RESOLVE = "resolve"
    RETRIEVE = "retrieve"
    REFINE = "refine"
    ESCALATE = "escalate"


class DartCaseStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class DartTriggerReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MANUAL = "manual"


class AgentReasoningTrace(BaseModel):
    agent_name: str
    diagnosis: str = ""
    evidence: list[str] = Field(default_factory=list)
    criteria_used: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    recommended_action: str = ""
    uncertainty_type: str = ""


class DiagnosticHypothesis(BaseModel):
    category: DartCategory
    rationale: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class ConsultationRequest(BaseModel):
    target_agent: str = ""
    question: str = ""
    context: dict = Field(default_factory=dict)
    category: DartCategory = DartCategory.AMBIGUOUS


class ConsultationResponse(BaseModel):
    agent_name: str = ""
    answer: str = ""
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    recommended_resolution: str = ""


class DartResolution(BaseModel):
    action: DartResolutionAction
    rationale: str = ""
    evidence_summary: list[str] = Field(default_factory=list)
    confidence_agreement: float = 0.0
    actionable_feedback: str = ""


class ArbitrateDartInput(BaseModel):
    requirement: RequirementInput
    trigger_reason: DartTriggerReason = DartTriggerReason.LOW_CONFIDENCE
    source_stage: str = "quality"
    source_result: dict = Field(default_factory=dict)
    stories: list[StoryInput] = Field(default_factory=list)


class DartCaseResult(BaseModel):
    case_id: str = ""
    requirement_ref: str = ""
    category: DartCategory = DartCategory.AMBIGUOUS
    status: DartCaseStatus = DartCaseStatus.OPEN
    trigger_reason: DartTriggerReason = DartTriggerReason.LOW_CONFIDENCE
    source_stage: str = "quality"
    traces: list[AgentReasoningTrace] = Field(default_factory=list)
    hypothesis: DiagnosticHypothesis | None = None
    consultation: ConsultationRequest | None = None
    response: ConsultationResponse | None = None
    resolution: DartResolution | None = None
    iteration: int = 1
    created_at: str = ""


class ArbitrateDartResult(BaseModel):
    case: DartCaseResult
