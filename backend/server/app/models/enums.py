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
