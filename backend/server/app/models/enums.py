import enum


class PipelineStage(str, enum.Enum):
    PARSING = "parsing"
    QUALITY = "quality"
    DECOMPOSITION = "decomposition"
    EFFORT_ESTIMATION = "effort_estimation"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class QualityDimension(str, enum.Enum):
    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    CORRECTNESS = "correctness"
    TESTABILITY = "testability"
    CONSISTENCY = "consistency"
    TRACEABILITY = "traceability"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class AssessmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class InvestCriterion(str, enum.Enum):
    INDEPENDENT = "independent"
    NEGOTIABLE = "negotiable"
    VALUABLE = "valuable"
    ESTIMABLE = "estimable"
    SMALL = "small"
    TESTABLE = "testable"


class RequirementCategory(str, enum.Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    INTERFACE = "interface"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"


class ParseStatus(str, enum.Enum):
    PENDING = "pending"
    PARSED = "parsed"
    FAILED = "failed"


class GateDecision(str, enum.Enum):
    PASS = "pass"
    BLOCK = "block"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class TaskType(str, enum.Enum):
    STORY = "story"
    TASK = "task"
    SUBTASK = "subtask"


class StoryStatus(str, enum.Enum):
    """Lifecycle state of a persisted decomposition user story."""

    DRAFT = "draft"
    INVEST_PASSED = "invest_passed"
    ACCEPTED = "accepted"
    ESTIMATED = "estimated"
    IN_BACKLOG = "in_backlog"


class DecompositionTaskType(str, enum.Enum):
    TASK = "task"
    SUBTASK = "subtask"


class Priority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EstimationSource(str, enum.Enum):
    STUDENT_ONLY = "student_only"
    AI_ONLY = "ai_only"
    CONSENSUS = "consensus"


class EstimationTechnique(str, enum.Enum):
    PLANNING_POKER = "planning_poker"
    T_SHIRT = "t_shirt"
    FIBONACCI = "fibonacci"
    EXPERT_JUDGMENT = "expert_judgment"


class DartHypothesis(str, enum.Enum):
    COMPOUND = "compound"
    AMBIGUOUS = "ambiguous"
    STRUCTURAL = "structural"
    NOVEL = "novel"


class DartDecision(str, enum.Enum):
    RESOLVE = "resolve"
    RETRIEVE = "retrieve"
    RE_ROUTE = "re_route"
    ESCALATE = "escalate"


class DartStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"
    CIRCUIT_BROKEN = "circuit_broken"


class DartTriggerReason(str, enum.Enum):
    TOOL_CONFLICT = "tool_conflict"
    LOW_CONFIDENCE = "low_confidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CROSS_STAGE_CONFLICT = "cross_stage_conflict"
    SCORE_DIVERGENCE = "score_divergence"


class FeedbackStage(str, enum.Enum):
    QUALITY = "quality"
    DECOMPOSITION = "decomposition"
    TASK_VALIDATION = "task_validation"
    ESTIMATION = "estimation"
    DART = "dart"


class FeedbackType(str, enum.Enum):
    ACTIONABLE_IMPROVEMENT = "actionable_improvement"
    STRENGTH_ACKNOWLEDGMENT = "strength_acknowledgment"
    STANDARD_REFERENCE = "standard_reference"
    LEARNING_OPPORTUNITY = "learning_opportunity"
    REVISION_REQUIRED = "revision_required"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(str, enum.Enum):
    DART_ESCALATION = "dart_escalation"
    QUALITY_GATE_BLOCK = "quality_gate_block"
    CIRCUIT_BREAKER = "circuit_breaker"
    STUDENT_STRUGGLING = "student_struggling"


class DecompositionGateStatus(str, enum.Enum):
    """Deprecated — superseded by DecompositionReadiness. Kept only for any
    historical row / lingering consumer; never drives UI behavior anymore."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class DecompositionReadiness(str, enum.Enum):
    """Student-friendly, three-tier decomposition readiness. ALL three allow
    the student to proceed to effort estimation — there is no hard block.
    Coverage/traceability (C1-C10) dominates the tier; INVEST results are
    improvement guidance and can at most downgrade Ready one notch."""

    READY = "Ready"
    READY_WITH_IMPROVEMENTS = "Ready with Improvements"
    NEEDS_ATTENTION = "Needs Attention"


class QualityBand(str, enum.Enum):
    """Reporting band for the 0-4 decomposition-quality score. Feedback only -
    never overrides the gate decision."""

    EXCELLENT = "Excellent"
    GOOD = "Good"
    MODERATE = "Moderate"
    POOR = "Poor"
    VERY_POOR = "Very poor"


class InvestResult(str, enum.Enum):
    """Four-state per-criterion INVEST readiness verdict."""

    PASS = "Pass"
    PASS_WITH_NOTE = "Pass with note"
    FAIL = "Fail"
    CANNOT_ASSESS = "Cannot Assess"


class CoverageResult(str, enum.Enum):
    COVERED = "Covered"
    MISSING = "Missing"


class CheckResult(str, enum.Enum):
    """Pass/Fail outcome for one of the coverage gate's C1-C10 checks."""

    PASS = "Pass"
    FAIL = "Fail"


class CoverageElementType(str, enum.Enum):
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
    QUALITY_CONSTRAINT = "quality_constraint"


class TaskCriterion(str, enum.Enum):
    """The four criteria an AI task-validation run judges each task on."""

    RELEVANCE = "relevance"
    SCOPE = "scope"
    ACTIONABILITY = "actionability"
    DUPLICATION = "duplication"


class TaskCriterionOutcome(str, enum.Enum):
    """Four-state per-criterion task validation verdict (mirrors InvestResult)."""

    PASS = "Pass"
    NEEDS_IMPROVEMENT = "Needs Improvement"
    FAIL = "Fail"
    CANNOT_ASSESS = "Cannot Assess"


class TaskReadinessStatus(str, enum.Enum):
    """Student-friendly, three-tier task-validation readiness. ALL three allow
    the student to proceed to effort estimation — there is no hard block.
    Coverage Warning is reserved for a significant story-coverage gap in the
    task set as a whole; per-task issues alone can at most reach Needs
    Improvement."""

    VALID = "Valid"
    NEEDS_IMPROVEMENT = "Needs Improvement"
    COVERAGE_WARNING = "Coverage Warning"


class ReadyBacklogStatus(str, enum.Enum):
    """The four statuses of a Backlog Readiness Passport:
    - READY: All hard gates pass and story points assigned.
    - READY_WITH_WARNINGS: Hard gates pass, but non-blocking soft improvements exist.
    - NOT_READY: At least one hard gate fails (quality, coverage, INVEST, or points).
    - NEEDS_REVIEW: DART could not resolve uncertainty; lecturer review required.
    """

    READY = "ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    NOT_READY = "not_ready"
    NEEDS_REVIEW = "needs_review"
