
"""Tutor-specific data models for competency analysis and adaptation."""

from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TutorModel(BaseModel):
    """Base configuration shared by tutor-specific models."""

    model_config = ConfigDict(extra="forbid")


# Align with Core API tutor chat message limits.
TUTOR_CHAT_MESSAGE_MAX_LENGTH = 4000


class TutorChatInput(TutorModel):
    """Validated ``AgentRequest.input`` for ``tutor.chat`` (no identity or token fields)."""

    message: str = Field(min_length=1, max_length=TUTOR_CHAT_MESSAGE_MAX_LENGTH)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        return stripped


class EvidenceType(StrEnum):
    QUIZ = "quiz"
    EXERCISE = "exercise"
    EXAM = "exam"
    PROJECT = "project"
    SELF_REFLECTION = "self_reflection"


class InterventionType(StrEnum):
    REVIEW_CONCEPT = "review_concept"
    GUIDED_PRACTICE = "guided_practice"
    PREREQUISITE_REVIEW = "prerequisite_review"
    REASSESSMENT = "reassessment"
    PROJECT_GUIDANCE = "project_guidance"
    NO_INTERVENTION = "no_intervention"


class DecisionAction(StrEnum):
    """Baseline Adaptive Decision Engine actions (Step 7).

    Maps onto existing ``InterventionType`` values where applicable:
    ``PRACTICE_CONCEPT`` → ``GUIDED_PRACTICE``,
    ``STUDY_PREREQUISITE`` → ``PREREQUISITE_REVIEW``,
    ``PROCEED_TO_TASK`` → ``PROJECT_GUIDANCE``.
    """

    REVIEW_CONCEPT = "review_concept"
    PRACTICE_CONCEPT = "practice_concept"
    STUDY_PREREQUISITE = "study_prerequisite"
    PROCEED_TO_TASK = "proceed_to_task"


class DecisionPolicyConfig(TutorModel):
    """Configurable provisional thresholds for the baseline decision policy.

    These values are research defaults for evaluation, not validated mastery cutoffs.
    """

    policy_id: str = Field(default="baseline_v1_provisional", min_length=1)
    # Provisional: treat mastery at/above this as sufficient for the task concept.
    mastery_sufficient: float = Field(default=0.75, ge=0.0, le=1.0)
    # Provisional: below this (with evidence) → review; between this and sufficient → practice.
    mastery_practice_min: float = Field(default=0.45, ge=0.0, le=1.0)
    # Provisional: prerequisite mastery below this triggers STUDY_PREREQUISITE.
    prerequisite_sufficient: float = Field(default=0.60, ge=0.0, le=1.0)

    @field_validator("mastery_practice_min")
    @classmethod
    def practice_min_must_not_exceed_sufficient(cls, value: float, info) -> float:
        sufficient = info.data.get("mastery_sufficient")
        if sufficient is not None and value > sufficient:
            raise ValueError("mastery_practice_min must be <= mastery_sufficient")
        return value


class DecisionConceptRef(TutorModel):
    """A required concept considered by the decision engine."""

    concept_id: str = Field(min_length=1)
    concept_name: str | None = None
    prerequisite_concept_ids: list[str] = Field(default_factory=list)
    learning_resource_ids: list[str] = Field(default_factory=list)
    selection_role: str | None = None


class LearnerStateEstimate(TutorModel):
    """Learner-model estimate for one concept (BKT or generic competency interface).

    ``mastery_probability`` / ``estimated_competency`` may be ``None`` when evidence
    is missing — never invent zero mastery.
    """

    concept_id: str = Field(min_length=1)
    mastery_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    estimated_competency: float | None = Field(default=None, ge=0.0, le=1.0)
    observation_count: int = Field(default=0, ge=0)
    evidence_count: int = Field(default=0, ge=0)
    model: str | None = None
    explanation: str | None = None

    def resolved_mastery(self) -> float | None:
        """Prefer BKT mastery; fall back to generic competency estimate."""
        if self.mastery_probability is not None:
            return self.mastery_probability
        return self.estimated_competency

    def has_usable_evidence(self) -> bool:
        if self.resolved_mastery() is not None:
            return True
        return self.observation_count > 0 or self.evidence_count > 0


class DecisionEvidenceRef(TutorModel):
    """Supporting evidence reference for an explainable decision."""

    evidence_id: str = Field(min_length=1)
    concept_id: str | None = None
    source_reference: str | None = None


class AdaptiveDecisionInput(TutorModel):
    """Typed input for the Adaptive Decision Engine (consumes upstream module outputs)."""

    student_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    task_title: str | None = None
    required_concepts: list[DecisionConceptRef] = Field(default_factory=list)
    learner_states: list[LearnerStateEstimate] = Field(default_factory=list)
    evidence_refs: list[DecisionEvidenceRef] = Field(default_factory=list)
    # Optional explicit prerequisite mastery map (concept_id → estimate); otherwise
    # prerequisites are resolved from ``learner_states`` when present.
    prerequisite_states: list[LearnerStateEstimate] = Field(default_factory=list)
    policy: DecisionPolicyConfig = Field(default_factory=DecisionPolicyConfig)


class AdaptiveDecisionResult(TutorModel):
    """Explainable next-action decision produced by the baseline policy."""

    action: DecisionAction
    intervention_type: InterventionType
    target_concept_id: str | None = None
    target_concept_name: str | None = None
    learning_resource_id: str | None = None
    reasons: list[str] = Field(min_length=1)
    evidence_refs: list[DecisionEvidenceRef] = Field(default_factory=list)
    policy_id: str = Field(min_length=1)
    priority: int = Field(ge=1, le=5)
    thresholds_provisional: bool = True


class PerformanceSourceType(StrEnum):
    ASSESSMENT_ANSWER = "ASSESSMENT_ANSWER"
    EXERCISE_SUBMISSION = "EXERCISE_SUBMISSION"
    LEARNING_ACTIVITY = "LEARNING_ACTIVITY"


class PerformanceEvidenceStatus(StrEnum):
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    ABANDONED = "ABANDONED"
    TIMED_OUT = "TIMED_OUT"


class ExternalEvidenceModel(TutorModel):
    """External learning-application records that arrive as camelCase JSON."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RequiredConcept(TutorModel):
    """A concept required to complete a project task."""

    concept_id: str = Field(min_length=1)
    concept_name: str = Field(min_length=1)
    required_competency: float = Field(ge=0.0, le=1.0)
    prerequisite_concept_ids: list[str] = Field(default_factory=list)


class IdentifyRequiredKnowledgeInput(TutorModel):
    """Validated ``AgentRequest.input`` for ``tutor.identify_required_knowledge``.

    ``course_id`` may be omitted when the sprint snapshot already carries one.
    """

    course_id: str | None = None

    @field_validator("course_id")
    @classmethod
    def course_id_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("course_id must not be empty")
        return stripped


class EstimateCompetencyInput(TutorModel):
    """Validated ``AgentRequest.input`` for ``tutor.estimate_competency``.

    ``course_id`` may be omitted when the sprint project carries one.
    ``concept_ids`` may be omitted to derive concepts from required-knowledge first.
    ``performance_evidence`` allows offline/fixture records (MCP is used when omitted).
    """

    course_id: str | None = None
    concept_ids: list[str] = Field(default_factory=list)
    performance_evidence: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("course_id")
    @classmethod
    def course_id_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("course_id must not be empty")
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


class SelectedRequiredConcept(TutorModel):
    """One Neo4j-grounded concept selected as required for a task."""

    concept_id: str = Field(min_length=1)
    concept_name: str | None = None
    concept_code: str | None = None
    selection_role: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source_lesson_ids: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)


class TaskRequiredKnowledge(TutorModel):
    """Required concepts identified for one assigned sprint task."""

    task_id: str = Field(min_length=1)
    task_title: str | None = None
    required_concepts: list[SelectedRequiredConcept] = Field(default_factory=list)


class RequiredKnowledgeResult(TutorModel):
    """Structured output of the Required Knowledge Identification mechanism."""

    student_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    sprint_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    course_code: str | None = None
    course_title: str | None = None
    tasks: list[TaskRequiredKnowledge] = Field(default_factory=list)


class EvidenceItem(TutorModel):
    """A normalized item of student learning or assessment evidence."""

    evidence_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    evidence_type: EvidenceType
    score: float = Field(ge=0.0, le=1.0)
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source_reference: str | None = None


class CompetencyEstimate(TutorModel):
    """Estimated student competency and confidence in that estimate."""

    student_id: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    estimated_competency: float | None = Field(
        default=None, ge=0.0, le=1.0
    )
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)
    explanation: str = Field(min_length=1)


class BktParameters(TutorModel):
    """Fixed baseline BKT parameters (not trained or optimized)."""

    p_l0: float = Field(default=0.2, gt=0.0, lt=1.0)
    p_t: float = Field(default=0.1, gt=0.0, lt=1.0)
    p_g: float = Field(default=0.2, gt=0.0, lt=0.5)
    p_s: float = Field(default=0.1, gt=0.0, lt=0.5)


class BktCompetencyEstimate(TutorModel):
    """Mastery probability for one student/course/concept from classic BKT."""

    student_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    mastery_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    observation_count: int = Field(ge=0)
    model: str = Field(default="BKT", min_length=1)
    parameters: BktParameters
    explanation: str = Field(min_length=1)


class BktFitResult(TutorModel):
    """Result of estimating BKT parameters from observation sequences."""

    fitted: bool
    parameters: BktParameters | None = None
    total_observations: int = Field(ge=0)
    sequence_count: int = Field(ge=0)
    log_likelihood: float | None = None
    method: str = Field(default="grid_search_pooled", min_length=1)
    explanation: str = Field(min_length=1)


class BktConceptComparison(TutorModel):
    """Side-by-side baseline vs fitted mastery for one concept."""

    concept_id: str = Field(min_length=1)
    observation_count: int = Field(ge=0)
    baseline_mastery: float | None = Field(default=None, ge=0.0, le=1.0)
    fitted_mastery: float | None = Field(default=None, ge=0.0, le=1.0)
    mastery_delta: float | None = None
    baseline_parameters: BktParameters
    fitted_parameters: BktParameters | None = None


class BktComparisonReport(TutorModel):
    """Option C: compare predefined baseline BKT with data-fitted BKT."""

    student_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    baseline_parameters: BktParameters
    fit: BktFitResult
    concepts: list[BktConceptComparison] = Field(default_factory=list)
    baseline_log_likelihood: float | None = None
    fitted_log_likelihood: float | None = None
    preferred_model: str = Field(min_length=1)
    comparison_scope: str = Field(
        default="in_sample_provisional",
        min_length=1,
        description="Honest label: comparison uses the same evidence used for fitting.",
    )
    explanation: str = Field(min_length=1)


class BktHoldoutSplitSummary(TutorModel):
    """Counts for chronological train/test participation."""

    sequences_used: int = Field(ge=0)
    sequences_skipped: int = Field(ge=0)
    train_observations: int = Field(ge=0)
    test_observations: int = Field(ge=0)
    skipped_concept_ids: list[str] = Field(default_factory=list)


class BktHoldoutModelMetrics(TutorModel):
    """Hold-out next-step prediction metrics for one parameter set."""

    log_likelihood: float | None = None
    accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    brier_score: float | None = Field(default=None, ge=0.0)
    n_test_steps: int = Field(ge=0)


class BktHoldoutEvaluationReport(TutorModel):
    """Step 4: fit on earlier answers; score baseline vs fitted on unseen later answers."""

    student_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    evaluated: bool
    baseline_parameters: BktParameters
    fit: BktFitResult
    split: BktHoldoutSplitSummary
    baseline_metrics: BktHoldoutModelMetrics | None = None
    fitted_metrics: BktHoldoutModelMetrics | None = None
    preferred_model: str = Field(min_length=1)
    evaluation_scope: str = Field(
        default="holdout_chronological",
        min_length=1,
        description="Honest label: params fitted on train only; metrics on held-out steps.",
    )
    explanation: str = Field(min_length=1)


class KnowledgeGap(TutorModel):
    """Comparison between task requirements and estimated competency."""

    concept_id: str = Field(min_length=1)
    required_competency: float = Field(ge=0.0, le=1.0)
    estimated_competency: float | None = Field(
        default=None, ge=0.0, le=1.0
    )
    gap_severity: float | None = Field(default=None, ge=0.0, le=1.0)
    status: str
    explanation: str = Field(min_length=1)


class InterventionDecision(TutorModel):
    """An explainable decision about the student's next learning activity."""

    intervention_type: InterventionType
    target_concept_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(min_length=1)
    priority: int = Field(ge=1, le=5)


class TutorRecommendation(TutorModel):
    """Structured recommendation produced by the Adaptive AI Tutor."""

    student_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    competency_estimates: list[CompetencyEstimate] = Field(
        default_factory=list
    )
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)
    decision: InterventionDecision
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class PerformanceEvidenceRecord(ExternalEvidenceModel):
    """Observed performance evidence from the external learning application."""

    id: str = Field(min_length=1)
    course_id: str = Field(min_length=1, alias="courseId")
    concept_id: str | None = Field(default=None, alias="conceptId")
    source_type: PerformanceSourceType = Field(alias="sourceType")
    source_id: str | None = Field(default=None, alias="sourceId")
    score: float | None = Field(default=None, ge=0.0)
    max_score: float | None = Field(default=None, gt=0.0, alias="maxScore")
    percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    attempt_number: int | None = Field(default=None, ge=1, alias="attemptNumber")
    time_spent_seconds: int | None = Field(default=None, ge=0, alias="timeSpentSeconds")
    hints_used: int | None = Field(default=None, ge=0, alias="hintsUsed")
    errors_count: int | None = Field(default=None, ge=0, alias="errorsCount")
    status: PerformanceEvidenceStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime = Field(alias="observedAt")


class LearningBehaviourRecord(ExternalEvidenceModel):
    """Observed learning-behaviour activity from the external learning application."""

    id: str = Field(min_length=1)
    activity_type: str = Field(min_length=1, alias="activityType")
    target_type: str = Field(min_length=1, alias="targetType")
    target_id: str = Field(min_length=1, alias="targetId")
    course_id: str = Field(min_length=1, alias="courseId")
    concept_id: str | None = Field(default=None, alias="conceptId")
    started_at: datetime | None = Field(default=None, alias="startedAt")
    ended_at: datetime | None = Field(default=None, alias="endedAt")
    duration_seconds: int | None = Field(default=None, ge=0, alias="durationSeconds")
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(alias="occurredAt")
    created_at: datetime = Field(alias="createdAt")


class ProjectInfo(TutorModel):
    """Project metadata for a sprint-scoped tutoring dataset."""

    project_id: str = Field(min_length=1)
    project_name: str = Field(min_length=1)
    course_id: str | None = None
    description: str | None = None
    technology_stack: list[str] = Field(default_factory=list)


class SprintInfo(TutorModel):
    """Sprint metadata for a sprint-scoped tutoring dataset."""

    sprint_id: str = Field(min_length=1)
    name: str | None = None
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None


class FixtureStudent(TutorModel):
    """A student enrolled in the fixture project/sprint."""

    student_id: str = Field(min_length=1)
    name: str | None = None


class SprintTask(TutorModel):
    """A project task within a sprint snapshot (tutor-local; richer than shared TaskContext)."""

    task_id: str = Field(min_length=1)
    title: str | None = None
    sprint_id: str | None = None
    assignee_ids: list[str] = Field(default_factory=list)
    description: str | None = None
    requirements: list[str] | None = None
    acceptance_criteria: list[str] | None = None
    concept_ids: list[str] | None = None
    status: str | None = None
    priority: str | None = None
    labels: list[str] = Field(default_factory=list)
    story_points: int | None = Field(default=None, ge=0)


class SprintDataset(TutorModel):
    """Nested project/sprint/students/tasks payload (fixture or future planning provider)."""

    project: ProjectInfo
    sprint: SprintInfo
    students: list[FixtureStudent] = Field(default_factory=list)
    tasks: list[SprintTask] = Field(default_factory=list)


class SprintSnapshot(TutorModel):
    """Flattened sprint-scoped view used by the context builder and providers."""

    project_id: str = Field(min_length=1)
    project_title: str | None = None
    project_description: str | None = None
    course_id: str | None = None
    technology_stack: list[str] = Field(default_factory=list)
    sprint_id: str = Field(min_length=1)
    sprint_name: str | None = None
    sprint_goal: str | None = None
    sprint_status: str | None = None
    sprint_number: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    students: list[FixtureStudent] = Field(default_factory=list)
    tasks: list[SprintTask] = Field(default_factory=list)

    @classmethod
    def from_dataset(cls, dataset: SprintDataset) -> "SprintSnapshot":
        """Flatten a nested SprintDataset into the builder-facing snapshot shape."""
        sprint_id = dataset.sprint.sprint_id
        return cls(
            project_id=dataset.project.project_id,
            project_title=dataset.project.project_name,
            project_description=dataset.project.description,
            course_id=dataset.project.course_id,
            technology_stack=list(dataset.project.technology_stack),
            sprint_id=sprint_id,
            sprint_name=dataset.sprint.name,
            sprint_goal=dataset.sprint.goal,
            sprint_status=dataset.sprint.status,
            start_date=dataset.sprint.start_date,
            end_date=dataset.sprint.end_date,
            students=list(dataset.students),
            tasks=[
                task.model_copy(update={"sprint_id": task.sprint_id or sprint_id})
                for task in dataset.tasks
            ],
        )


class StudentProjectContext(TutorModel):
    """Validated student/project/sprint context with only that student's assigned tasks."""

    student_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    project_title: str | None = None
    project_description: str | None = None
    course_id: str | None = None
    technology_stack: list[str] = Field(default_factory=list)
    group_id: str | None = None
    sprint_id: str = Field(min_length=1)
    sprint_name: str | None = None
    sprint_goal: str | None = None
    sprint_status: str | None = None
    sprint_number: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    assigned_tasks: list[SprintTask] = Field(default_factory=list)

