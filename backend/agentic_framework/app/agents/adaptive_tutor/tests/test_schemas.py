
import pytest
from pydantic import ValidationError

from app.agents.adaptive_tutor.schemas import (
    CompetencyEstimate,
    EvidenceItem,
    EvidenceType,
    InterventionDecision,
    InterventionType,
    KnowledgeGap,
    LearningBehaviourRecord,
    PerformanceEvidenceRecord,
    PerformanceEvidenceStatus,
    PerformanceSourceType,
    RequiredConcept,
    TutorRecommendation,
)

PERFORMANCE_EVIDENCE = {
    "id": "evidence-001",
    "courseId": "course-101",
    "conceptId": "concept-101",
    "sourceType": "EXERCISE_SUBMISSION",
    "sourceId": "submission-001",
    "score": 4,
    "maxScore": 10,
    "percentage": 40,
    "attemptNumber": 2,
    "timeSpentSeconds": 240,
    "hintsUsed": 3,
    "errorsCount": 5,
    "status": "COMPLETED",
    "metadata": {},
    "observedAt": "2026-10-15T09:30:00.000Z",
}

LEARNING_BEHAVIOUR = {
    "id": "activity-001",
    "activityType": "LESSON_VIEWED",
    "targetType": "LESSON",
    "targetId": "lesson-101",
    "courseId": "course-101",
    "conceptId": "concept-101",
    "startedAt": "2026-10-15T09:00:00.000Z",
    "endedAt": None,
    "durationSeconds": None,
    "metadata": {},
    "occurredAt": "2026-10-15T09:00:00.000Z",
    "createdAt": "2026-10-15T09:00:00.000Z",
}


def test_required_concept_accepts_valid_competency():
    concept = RequiredConcept(
        concept_id="jwt",
        concept_name="JWT Authentication",
        required_competency=0.8,
    )

    assert concept.required_competency == 0.8
    assert concept.prerequisite_concept_ids == []


def test_required_concept_rejects_competency_above_one():
    with pytest.raises(ValidationError):
        RequiredConcept(
            concept_id="jwt",
            concept_name="JWT Authentication",
            required_competency=1.2,
        )


def test_evidence_rejects_score_outside_normalized_range():
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev-1",
            student_id="student-1",
            concept_id="jwt",
            evidence_type=EvidenceType.QUIZ,
            score=1.5,
        )


def test_missing_evidence_does_not_mean_zero_competency():
    estimate = CompetencyEstimate(
        student_id="student-1",
        concept_id="jwt",
        estimated_competency=None,
        confidence=0.0,
        evidence_count=0,
        explanation="No evidence collected",
    )

    assert estimate.estimated_competency is None
    assert estimate.evidence_count == 0


def test_competency_and_confidence_are_separate_values():
    estimate = CompetencyEstimate(
        student_id="student-1",
        concept_id="jwt",
        estimated_competency=0.8,
        confidence=0.3,
        evidence_count=1,
        explanation="One assessment result is available",
    )

    assert estimate.estimated_competency == 0.8
    assert estimate.confidence == 0.3


def test_competency_estimate_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        CompetencyEstimate(
            student_id="student-1",
            concept_id="jwt",
            estimated_competency=0.8,
            confidence=1.5,
            evidence_count=1,
            explanation="Invalid confidence",
        )


def test_knowledge_gap_can_represent_unknown_competency():
    gap = KnowledgeGap(
        concept_id="jwt",
        required_competency=0.8,
        estimated_competency=None,
        gap_severity=None,
        status="unknown",
        explanation="Insufficient evidence to estimate competency",
    )

    assert gap.estimated_competency is None
    assert gap.gap_severity is None
    assert gap.status == "unknown"


def test_intervention_requires_at_least_one_reason():
    with pytest.raises(ValidationError):
        InterventionDecision(
            intervention_type=InterventionType.REVIEW_CONCEPT,
            target_concept_ids=["jwt"],
            reasons=[],
            priority=2,
        )


def test_intervention_priority_must_be_between_one_and_five():
    with pytest.raises(ValidationError):
        InterventionDecision(
            intervention_type=InterventionType.REVIEW_CONCEPT,
            target_concept_ids=["jwt"],
            reasons=["Competency is below the required level"],
            priority=6,
        )


def test_tutor_recommendation_accepts_estimates_gaps_and_decision():
    recommendation = TutorRecommendation(
        student_id="student-1",
        task_id="task-jwt",
        competency_estimates=[
            CompetencyEstimate(
                student_id="student-1",
                concept_id="jwt",
                estimated_competency=None,
                confidence=0.0,
                evidence_count=0,
                explanation="No evidence collected",
            )
        ],
        knowledge_gaps=[
            KnowledgeGap(
                concept_id="jwt",
                required_competency=0.8,
                estimated_competency=None,
                gap_severity=None,
                status="unknown",
                explanation="Insufficient evidence to estimate competency",
            )
        ],
        decision=InterventionDecision(
            intervention_type=InterventionType.REASSESSMENT,
            target_concept_ids=["jwt"],
            reasons=["There is not enough evidence to estimate competency"],
            priority=2,
        ),
    )

    assert recommendation.student_id == "student-1"
    assert recommendation.decision.intervention_type is InterventionType.REASSESSMENT
    assert recommendation.competency_estimates[0].estimated_competency is None


def test_performance_evidence_accepts_external_json():
    record = PerformanceEvidenceRecord.model_validate(PERFORMANCE_EVIDENCE)

    assert record.id == "evidence-001"
    assert record.course_id == "course-101"
    assert record.concept_id == "concept-101"
    assert record.source_type is PerformanceSourceType.EXERCISE_SUBMISSION
    assert record.source_id == "submission-001"
    assert record.score == 4
    assert record.max_score == 10
    assert record.percentage == 40
    assert record.attempt_number == 2
    assert record.time_spent_seconds == 240
    assert record.hints_used == 3
    assert record.errors_count == 5
    assert record.status is PerformanceEvidenceStatus.COMPLETED
    assert record.metadata == {}
    assert record.observed_at.year == 2026


def test_performance_evidence_accepts_snake_case_field_names():
    record = PerformanceEvidenceRecord.model_validate(
        {
            "id": "evidence-002",
            "course_id": "course-101",
            "concept_id": None,
            "source_type": PerformanceSourceType.ASSESSMENT_ANSWER,
            "source_id": None,
            "score": None,
            "max_score": None,
            "percentage": None,
            "attempt_number": None,
            "time_spent_seconds": 0,
            "hints_used": 0,
            "errors_count": 0,
            "status": PerformanceEvidenceStatus.SKIPPED,
            "metadata": {"questionId": "q-1"},
            "observed_at": "2026-10-15T09:30:00.000Z",
        }
    )

    assert record.source_type is PerformanceSourceType.ASSESSMENT_ANSWER
    assert record.status is PerformanceEvidenceStatus.SKIPPED
    assert record.concept_id is None
    assert record.score is None
    assert record.source_id is None


def test_learning_behaviour_accepts_external_json():
    record = LearningBehaviourRecord.model_validate(LEARNING_BEHAVIOUR)

    assert record.id == "activity-001"
    assert record.activity_type == "LESSON_VIEWED"
    assert record.target_type == "LESSON"
    assert record.target_id == "lesson-101"
    assert record.course_id == "course-101"
    assert record.concept_id == "concept-101"
    assert record.started_at is not None
    assert record.ended_at is None
    assert record.duration_seconds is None
    assert record.occurred_at.year == 2026
    assert record.created_at.year == 2026


def test_missing_performance_score_and_source_id_remain_none():
    payload = {**PERFORMANCE_EVIDENCE}
    del payload["score"]
    del payload["sourceId"]

    record = PerformanceEvidenceRecord.model_validate(payload)

    assert record.score is None
    assert record.source_id is None


def test_missing_concept_id_remains_none():
    performance = {**PERFORMANCE_EVIDENCE}
    del performance["conceptId"]
    behaviour = {**LEARNING_BEHAVIOUR}
    del behaviour["conceptId"]

    assert PerformanceEvidenceRecord.model_validate(performance).concept_id is None
    assert LearningBehaviourRecord.model_validate(behaviour).concept_id is None


def test_missing_learning_duration_remains_none():
    payload = {**LEARNING_BEHAVIOUR}
    del payload["durationSeconds"]

    record = LearningBehaviourRecord.model_validate(payload)

    assert record.duration_seconds is None


def test_invalid_numeric_constraints_are_rejected():
    with pytest.raises(ValidationError):
        PerformanceEvidenceRecord.model_validate({**PERFORMANCE_EVIDENCE, "score": -1})

    with pytest.raises(ValidationError):
        PerformanceEvidenceRecord.model_validate({**PERFORMANCE_EVIDENCE, "percentage": 101})

    with pytest.raises(ValidationError):
        PerformanceEvidenceRecord.model_validate({**PERFORMANCE_EVIDENCE, "maxScore": 0})

    with pytest.raises(ValidationError):
        PerformanceEvidenceRecord.model_validate({**PERFORMANCE_EVIDENCE, "attemptNumber": 0})

    with pytest.raises(ValidationError):
        LearningBehaviourRecord.model_validate({**LEARNING_BEHAVIOUR, "durationSeconds": -1})


def test_unsupported_performance_source_type_or_status_is_rejected():
    with pytest.raises(ValidationError):
        PerformanceEvidenceRecord.model_validate(
            {**PERFORMANCE_EVIDENCE, "sourceType": "QUIZ"}
        )

    with pytest.raises(ValidationError):
        PerformanceEvidenceRecord.model_validate(
            {**PERFORMANCE_EVIDENCE, "status": "GRADED"}
        )


def test_empty_required_identifiers_are_rejected():
    with pytest.raises(ValidationError):
        PerformanceEvidenceRecord.model_validate({**PERFORMANCE_EVIDENCE, "id": ""})

    with pytest.raises(ValidationError):
        LearningBehaviourRecord.model_validate({**LEARNING_BEHAVIOUR, "targetId": ""})


def test_unexpected_top_level_field_is_rejected():
    with pytest.raises(ValidationError):
        PerformanceEvidenceRecord.model_validate(
            {**PERFORMANCE_EVIDENCE, "studentId": "student-1"}
        )

    with pytest.raises(ValidationError):
        LearningBehaviourRecord.model_validate(
            {**LEARNING_BEHAVIOUR, "studentId": "student-1"}
        )
