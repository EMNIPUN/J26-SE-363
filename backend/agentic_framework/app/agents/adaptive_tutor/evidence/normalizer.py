"""Convert external performance evidence into the tutor's internal EvidenceItem.

A normalized score is an observed measurement in [0, 1], not a competency estimate.
Learning behaviour is not performance evidence and is not handled here.
"""

from app.agents.adaptive_tutor.schemas import (
    EvidenceItem,
    EvidenceType,
    PerformanceEvidenceRecord,
    PerformanceSourceType,
)

# Explicit mappings only. LEARNING_ACTIVITY is an observation of behaviour, not a
# scored performance item, so it has no EvidenceType and is rejected.
SOURCE_TYPE_TO_EVIDENCE_TYPE: dict[PerformanceSourceType, EvidenceType] = {
    PerformanceSourceType.EXERCISE_SUBMISSION: EvidenceType.EXERCISE,
    PerformanceSourceType.ASSESSMENT_ANSWER: EvidenceType.QUIZ,
}

PERCENTAGE_TOLERANCE = 0.05


class EvidenceNormalizationError(ValueError):
    """Raised when a performance record cannot be represented as EvidenceItem."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def normalize_performance_evidence(
    record: PerformanceEvidenceRecord,
    student_id: str,
) -> EvidenceItem:
    """Map one validated performance record plus a trusted student_id to EvidenceItem."""
    trusted_student_id = _require_student_id(student_id)
    concept_id = _require_concept_id(record)
    evidence_type = _map_source_type(record)
    score = _normalize_score(record)

    return EvidenceItem(
        evidence_id=record.id,
        student_id=trusted_student_id,
        concept_id=concept_id,
        evidence_type=evidence_type,
        score=score,
        observed_at=record.observed_at,
        source_reference=record.source_id,
    )


def _require_student_id(student_id: str) -> str:
    if not isinstance(student_id, str) or student_id.strip() == "":
        raise EvidenceNormalizationError(
            "missing_student_id",
            "A trusted student_id must be supplied by the caller; it is not read from the evidence record.",
        )
    return student_id.strip()


def _require_concept_id(record: PerformanceEvidenceRecord) -> str:
    if record.concept_id is None or record.concept_id.strip() == "":
        raise EvidenceNormalizationError(
            "missing_concept_id",
            "conceptId is unknown on this record; a concept identifier will not be invented.",
        )
    return record.concept_id


def _map_source_type(record: PerformanceEvidenceRecord) -> EvidenceType:
    evidence_type = SOURCE_TYPE_TO_EVIDENCE_TYPE.get(record.source_type)
    if evidence_type is None:
        raise EvidenceNormalizationError(
            "unsupported_source_type",
            f"{record.source_type} is not a scored performance source that maps to EvidenceType.",
        )
    return evidence_type


def _normalize_score(record: PerformanceEvidenceRecord) -> float:
    ratio = _score_ratio(record)
    from_percentage = None if record.percentage is None else record.percentage / 100.0

    if ratio is not None and from_percentage is not None:
        if abs(ratio - from_percentage) > PERCENTAGE_TOLERANCE:
            raise EvidenceNormalizationError(
                "inconsistent_scores",
                "score/maxScore and percentage do not describe the same measurement.",
            )
        return ratio
    if ratio is not None:
        return ratio
    if from_percentage is not None:
        return from_percentage

    raise EvidenceNormalizationError(
        "insufficient_score_data",
        "Neither a valid score/maxScore pair nor a percentage is available; missing measurements are not treated as zero.",
    )


def _score_ratio(record: PerformanceEvidenceRecord) -> float | None:
    if record.score is None or record.max_score is None:
        return None
    if record.score > record.max_score:
        raise EvidenceNormalizationError(
            "inconsistent_scores",
            "score is greater than maxScore.",
        )
    return record.score / record.max_score
