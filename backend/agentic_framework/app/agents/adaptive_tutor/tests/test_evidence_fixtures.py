
from app.agents.adaptive_tutor.schemas import (
    LearningBehaviourRecord,
    PerformanceEvidenceRecord,
)
from app.agents.adaptive_tutor.tests.fixtures.evidence_data import (
    LEARNING_BEHAVIOUR,
    PERFORMANCE_EVIDENCE,
)


def test_performance_fixtures_load_into_schema():
    records = [
        PerformanceEvidenceRecord.model_validate(item)
        for item in PERFORMANCE_EVIDENCE
    ]

    assert len(records) == 4
    assert records[0].concept_id == records[1].concept_id
    assert records[0].percentage == 0
    assert records[1].percentage == 100


def test_missing_score_remains_none():
    record = PerformanceEvidenceRecord.model_validate(
        PERFORMANCE_EVIDENCE[2]
    )

    assert record.score is None


def test_missing_concept_id_remains_none():
    record = PerformanceEvidenceRecord.model_validate(
        PERFORMANCE_EVIDENCE[3]
    )

    assert record.concept_id is None


def test_learning_behaviour_fixtures_load_into_schema():
    records = [
        LearningBehaviourRecord.model_validate(item)
        for item in LEARNING_BEHAVIOUR
    ]

    assert len(records) == 2
    assert records[0].activity_type == "LESSON_VIEWED"
    assert records[0].duration_seconds is None
    assert records[1].duration_seconds == 240
