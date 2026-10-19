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


class QualityBand(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    MODERATE = "Moderate"
    POOR = "Poor"
    VERY_POOR = "Very poor"


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
    score: int  # 0-100 percentage for UI and DB backward-compatibility
    raw_score: int | None = None  # 0-4 on ISO/IEC/IEEE 29148 rubric; None if N/A or C/A
    applicability: str = "applicable"  # "applicable", "not_applicable", "cannot_assess"
    rationale: str = ""  # Evidence / justification supporting the rating
    issues: list[str] = Field(default_factory=list)
    remedy: str = ""
    standard_reference: str = ""


class Smell(BaseModel):
    type: str
    span: str = ""
    suggestion: str = ""


class RetrievalEvidence(BaseModel):
    """What the RAG/similarity tools retrieved while scoring (for UI transparency)."""

    standards: list[dict] = Field(default_factory=list)       # IEEE / ISO criteria
    exemplars: list[dict] = Field(default_factory=list)       # graded example requirements
    cross_req_hits: list[dict] = Field(default_factory=list)  # similar other requirements


class RequirementQualityResult(BaseModel):
    id: str
    overall_score: int  # 0-100 percentage (round(Q_i / 4.0 * 100))
    overall_score_4: float = 0.0  # 0.0-4.0 mean of applicable dimensions (Q_i)
    quality_band: QualityBand = QualityBand.VERY_POOR
    status: GateStatus
    gate_action: GateAction
    dimension_scores: dict[str, DimensionScore] = Field(default_factory=dict)
    applicable_dimensions: list[str] = Field(default_factory=list)
    na_dimensions: list[str] = Field(default_factory=list)
    cannot_assess_dimensions: list[str] = Field(default_factory=list)
    smells: list[Smell] = Field(default_factory=list)
    suggested_rewrite: str | None = None
    confidence: float = 1.0
    dart_triggered: bool = False
    retrieval: RetrievalEvidence | None = None
    # Names of the tools that actually ran for this assessment. This is
    # evidence for the UI, not a static list of claimed capabilities.
    tools_used: list[str] = Field(default_factory=list)


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
# Decomposition analysis — user-story INVEST quality (Function 2)
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
    description: str = ""
    # Informational only: acceptance criteria are stored but are not part of
    # the user-story quality evaluation.
    acceptance_criteria: list[str] = Field(default_factory=list)
    # Populated by the Core API from the owning requirement's id (stories are
    # always scoped to one requirement per analyze_decomposition call). Used
    # by the deterministic C1 parent-linkage check.
    linked_parent_requirement: str = ""


class DecompositionOptions(BaseModel):
    # Kept for input-compat only; the two-level mandatory gate below does not
    # use a percentage threshold.
    threshold: int = DEFAULT_DECOMPOSITION_THRESHOLD


class AnalyzeDecompositionInput(BaseModel):
    """Payload for ``planning.analyze_decomposition``."""

    requirement: RequirementInput
    stories: list[StoryInput] = Field(default_factory=list)
    options: DecompositionOptions = Field(default_factory=DecompositionOptions)


# ----- result: coverage gate (C1-C10) -----------------------------------------


class CoverageElementType(str, Enum):
    """Taxonomy of coverage elements extracted from a parent requirement."""

    ACTOR = "actor"
    TRIGGER = "trigger"
    PRECONDITION = "precondition"
    MAIN_ACTION = "main_action"
    INPUT_DATA = "input_data"
    OUTPUT_RESULT = "output_result"
    BUSINESS_RULE = "business_rule"
    CONSTRAINT = "constraint"
    PERMISSION_RULE = "permission_rule"
    EXCEPTION_BEHAVIOR = "exception_behavior"
    ERROR_HANDLING = "error_handling"
    RECOVERY_RETRY = "recovery_retry"
    QUALITY_CONSTRAINT = "quality_constraint"  # perf/security/usability/legal


class CoverageResult(str, Enum):
    COVERED = "Covered"
    MISSING = "Missing"


class CoverageElement(BaseModel):
    element_id: str
    element_type: CoverageElementType
    description: str
    required: bool = True
    covered_by: list[str] = Field(default_factory=list)  # story_ids
    coverage_result: CoverageResult = CoverageResult.MISSING
    evidence: str = ""  # why the LLM judged it covered/missing


class CheckResult(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"


class CoverageCheck(BaseModel):
    check_id: str  # "C1".."C10"; C10 verifies story traceability and assigned-behavior coverage.
    result: CheckResult
    rationale: str = ""
    evidence: list[str] = Field(default_factory=list)  # element_ids / story_ids
    # Concrete "how to fix" guidance for a Fail result - what the research-doc
    # feedback rules call an "example", not just a diagnosis. Empty on Pass.
    suggestion: str = ""


class CoverageGateResult(BaseModel):
    checks: dict[str, CoverageCheck] = Field(default_factory=dict)  # "C1".."C10"
    passed: bool = False
    duplicate_elements: list[str] = Field(default_factory=list)
    orphan_stories: list[str] = Field(default_factory=list)
    out_of_scope_stories: list[str] = Field(default_factory=list)


class CoverageAnalysis(BaseModel):
    elements: list[CoverageElement] = Field(default_factory=list)
    coverage_percentage: float = 0.0  # feedback-only, never the gate decision
    gate: CoverageGateResult = Field(default_factory=CoverageGateResult)
    needs_review: bool = False
    needs_review_reason: str | None = None
    # True only when the coverage LLM call itself could not run (unavailable or
    # errored) - distinct from a real analysis that concluded incomplete. All
    # ten checks being Fail in this state is a placeholder, not a finding.
    analysis_failed: bool = False
    failure_reason: str | None = None
    # Story-quality-only analysis intentionally skips requirement coverage.
    # This is distinct from a failed coverage call and must not be presented
    # as an AI-service error.
    analysis_skipped: bool = False


# ----- result: INVEST readiness gate (4-state per criterion) ------------------


class InvestResult(str, Enum):
    PASS = "Pass"
    PASS_WITH_NOTE = "Pass with note"
    FAIL = "Fail"
    CANNOT_ASSESS = "Cannot Assess"


class InvestCriterionResult(BaseModel):
    result: InvestResult = InvestResult.CANNOT_ASSESS
    note: str = ""
    evidence: str = ""


class StoryInvest(BaseModel):
    story_id: str
    story_text: str = ""
    linked_parent_requirement: str = ""
    coverage_percentage: float = 0.0  # this story's share, feedback-only
    independent: InvestCriterionResult = Field(default_factory=InvestCriterionResult)
    negotiable: InvestCriterionResult = Field(default_factory=InvestCriterionResult)
    valuable: InvestCriterionResult = Field(default_factory=InvestCriterionResult)
    estimable: InvestCriterionResult = Field(default_factory=InvestCriterionResult)
    small: InvestCriterionResult = Field(default_factory=InvestCriterionResult)
    testable: InvestCriterionResult = Field(default_factory=InvestCriterionResult)
    story_ready: bool = False  # True only if all 6 are Pass or Pass with note


class InvestGateResult(BaseModel):
    all_stories_ready: bool = False
    failed_stories: list[str] = Field(default_factory=list)  # story_ids with >=1 Fail/Cannot Assess


# ----- result: final gate + score ----------------------------------------------


class DecompositionGateStatus(str, Enum):
    """Deprecated — superseded by DecompositionReadiness. Kept only so any
    remaining consumer that reads gate_status keeps working; it is now a
    best-effort projection of the readiness tier (see gate.py), never a hard
    block on its own."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class DecompositionReadiness(str, Enum):
    """Student-friendly, three-tier decomposition readiness. Replaces the
    strict pass/fail gate: ALL three outcomes allow the student to proceed to
    effort estimation — there is no hard block. The tier only changes how
    prominently the UI warns them and what it asks them to improve first.
    In story-quality-only mode, the tier is based on INVEST results alone."""

    READY = "Ready"
    READY_WITH_IMPROVEMENTS = "Ready with Improvements"
    NEEDS_ATTENTION = "Needs Attention"


class DecompositionResult(BaseModel):
    requirement_ref: str
    coverage: CoverageAnalysis = Field(default_factory=CoverageAnalysis)
    stories: list[StoryInvest] = Field(default_factory=list)
    invest_gate: InvestGateResult = Field(default_factory=InvestGateResult)
    decomposition_quality_score: float = 0.0  # 0-4, computed from gate evidence
    quality_band: QualityBand = QualityBand.VERY_POOR
    # Authoritative status - see DecompositionReadiness. Never a hard block:
    # the student can always proceed to effort estimation regardless of tier.
    readiness: DecompositionReadiness = DecompositionReadiness.NEEDS_ATTENTION
    readiness_reason: str = ""  # 1-2 sentence explanation of the tier
    gate_status: DecompositionGateStatus = DecompositionGateStatus.INCOMPLETE  # deprecated, see above
    needs_review_reason: str | None = None
    student_feedback: list[str] = Field(default_factory=list)
    patterns: list[dict] = Field(default_factory=list)
    confidence: float = 1.0
    dart_triggered: bool = False
    retrieval: dict = Field(default_factory=dict)
    # Mirrors coverage.analysis_failed at the top level so every consumer
    # (service layer, API, frontend) can check it without deep nesting. When
    # true, decomposition_quality_score/quality_band are NOT a real
    # assessment - they are mechanically derived from an all-Fail placeholder
    # state and must not be shown to the student as if they were.
    analysis_failed: bool = False
    failure_reason: str | None = None


class AnalyzeDecompositionResult(BaseModel):
    threshold: int = DEFAULT_DECOMPOSITION_THRESHOLD
    result: DecompositionResult | None = None


# ---------------------------------------------------------------------------
# Task validation — relevance/scope/actionability/duplication per task, plus
# whether the task set as a whole covers the story's main work.
# ---------------------------------------------------------------------------

TASK_CRITERIA: tuple[str, ...] = (
    "relevance",
    "scope",
    "actionability",
    "duplication",
)


class TaskInput(BaseModel):
    id: str
    title: str
    description: str = ""


class AnalyzeTaskValidationInput(BaseModel):
    """Payload for the ``planning.validate_tasks`` action."""

    story: StoryInput
    # Parent requirement text, for context when a task's relevance to the
    # story is ambiguous. Optional - most judgments only need the story.
    requirement_text: str = ""
    tasks: list[TaskInput] = Field(default_factory=list)


class TaskCriterionOutcome(str, Enum):
    """Four-state per-criterion task validation verdict (mirrors InvestResult)."""

    PASS = "Pass"
    NEEDS_IMPROVEMENT = "Needs Improvement"
    FAIL = "Fail"
    CANNOT_ASSESS = "Cannot Assess"


class TaskCriterionResult(BaseModel):
    result: TaskCriterionOutcome = TaskCriterionOutcome.CANNOT_ASSESS
    note: str = ""
    evidence: str = ""


class TaskValidationItem(BaseModel):
    task_id: str
    relevance: TaskCriterionResult = Field(default_factory=TaskCriterionResult)
    scope: TaskCriterionResult = Field(default_factory=TaskCriterionResult)
    actionability: TaskCriterionResult = Field(default_factory=TaskCriterionResult)
    duplication: TaskCriterionResult = Field(default_factory=TaskCriterionResult)
    task_ready: bool = False  # True only if all 4 are Pass or Needs Improvement


class TaskSetCoverage(BaseModel):
    coverage_percentage: float = 0.0  # feedback-only, never the sole gate input
    missing_work_items: list[str] = Field(default_factory=list)


class TaskReadiness(str, Enum):
    """Student-friendly, three-tier task-validation readiness. ALL three allow
    the student to proceed to effort estimation — there is no hard block.
    Coverage Warning is reserved for a significant gap in the task set's
    coverage of the story's main work; per-task issues alone can at most
    reach Needs Improvement."""

    VALID = "Valid"
    NEEDS_IMPROVEMENT = "Needs Improvement"
    COVERAGE_WARNING = "Coverage Warning"


class TaskValidationResult(BaseModel):
    story_ref: str
    coverage: TaskSetCoverage = Field(default_factory=TaskSetCoverage)
    tasks: list[TaskValidationItem] = Field(default_factory=list)
    quality_score: float = 0.0  # 0-4, computed from gate evidence
    quality_band: QualityBand = QualityBand.VERY_POOR
    # Authoritative status - see TaskReadiness. Never a hard block: the
    # student can always proceed to effort estimation regardless of tier.
    readiness: TaskReadiness = TaskReadiness.COVERAGE_WARNING
    readiness_reason: str = ""  # 1-2 sentence explanation of the tier
    student_feedback: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    # True only when the validation LLM call itself could not run (unavailable
    # or errored) - distinct from a real run that concluded Needs Improvement
    # / Coverage Warning. When true, quality_score/quality_band/readiness are
    # a mechanical placeholder, not a real assessment.
    analysis_failed: bool = False
    failure_reason: str | None = None


class AnalyzeTaskValidationResult(BaseModel):
    result: TaskValidationResult | None = None


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
