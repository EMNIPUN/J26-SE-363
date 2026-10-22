import pytest

from app.agents.adaptive_tutor.evidence import (
    EvidenceNormalizationError,
    normalize_performance_evidence,
)
from app.agents.adaptive_tutor.schemas import (
    EvidenceType,
    PerformanceEvidenceRecord,
    PerformanceSourceType,
)
from app.agents.adaptive_tutor.tests.fixtures.evidence_data import PERFORMANCE_EVIDENCE

STUDENT_ID = "student-1"


def _record(index: int, **overrides) -> PerformanceEvidenceRecord:
    return PerformanceEvidenceRecord.model_validate({**PERFORMANCE_EVIDENCE[index], **overrides})


def test_valid_performance_record_maps_identifiers_and_type():
    item = normalize_performance_evidence(_record(0), STUDENT_ID)

    assert item.evidence_id == "evidence-001"
    assert item.student_id == STUDENT_ID
    assert item.concept_id == "concept-101"
    assert item.evidence_type is EvidenceType.EXERCISE
    assert item.source_reference == "submission-001"
    assert item.observed_at.year == 2026


def test_score_four_out_of_ten_normalizes_to_zero_point_four():
    item = normalize_performance_evidence(
        _record(0, score=4, maxScore=10, percentage=40),
        STUDENT_ID,
    )

    assert item.score == 0.4


def test_percentage_is_used_when_score_is_unavailable():
    item = normalize_performance_evidence(_record(2), STUDENT_ID)

    assert item.score == 0.6
    assert item.evidence_type is EvidenceType.QUIZ


def test_missing_concept_id_is_not_invented():
    with pytest.raises(EvidenceNormalizationError, match="will not be invented") as exc_info:
        normalize_performance_evidence(_record(3), STUDENT_ID)

    assert exc_info.value.code == "missing_concept_id"


def test_missing_or_blank_student_id_is_rejected():
    record = _record(0)

    with pytest.raises(EvidenceNormalizationError) as missing:
        normalize_performance_evidence(record, "")
    with pytest.raises(EvidenceNormalizationError) as blank:
        normalize_performance_evidence(record, "   ")

    assert missing.value.code == "missing_student_id"
    assert blank.value.code == "missing_student_id"


def test_missing_score_and_percentage_are_not_converted_to_zero():
    record = _record(
        0,
        score=None,
        percentage=None,
        maxScore=10,
    )

    with pytest.raises(EvidenceNormalizationError, match="not treated as zero") as exc_info:
        normalize_performance_evidence(record, STUDENT_ID)

    assert exc_info.value.code == "insufficient_score_data"


def test_score_greater_than_max_score_is_rejected():
    record = _record(0, score=12, maxScore=10, percentage=None)

    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_performance_evidence(record, STUDENT_ID)

    assert exc_info.value.code == "inconsistent_scores"


def test_contradictory_percentage_is_rejected():
    record = _record(0, score=4, maxScore=10, percentage=80)

    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_performance_evidence(record, STUDENT_ID)

    assert exc_info.value.code == "inconsistent_scores"


def test_learning_activity_source_type_is_rejected():
    record = _record(
        0,
        sourceType=PerformanceSourceType.LEARNING_ACTIVITY,
    )

    with pytest.raises(EvidenceNormalizationError) as exc_info:
        normalize_performance_evidence(record, STUDENT_ID)

    assert exc_info.value.code == "unsupported_source_type"
