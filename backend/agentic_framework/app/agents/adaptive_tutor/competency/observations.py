"""Build chronological BKT observations from performance evidence.

Learning-behaviour activities are intentionally excluded. Records without a
trusted concept id or scorable measurement are skipped (never invented).

``ASSESSMENT_ANSWER`` rows must carry item-level metadata (question id and a
boolean ``is_correct``). ``EXERCISE_SUBMISSION`` rows must carry ``exercise_id``
and a boolean ``is_correct``. Correctness is never derived from the score
threshold for those source types.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from app.agents.adaptive_tutor.competency.params import DEFAULT_CORRECT_THRESHOLD
from app.agents.adaptive_tutor.evidence import (
    EvidenceNormalizationError,
    normalize_performance_evidence,
)
from app.agents.adaptive_tutor.schemas import (
    EvidenceItem,
    PerformanceEvidenceRecord,
    PerformanceSourceType,
)

_ITEM_ID_KEYS = ("question_id", "assessment_question_id")


@dataclass(frozen=True)
class _PendingObservation:
    concept_id: str
    observed_at: datetime
    evidence_id: str
    correct: bool


def resolve_bkt_observation(
    raw: PerformanceEvidenceRecord | dict,
    *,
    student_id: str,
    course_id: str | None = None,
    concept_ids: Iterable[str] | None = None,
) -> tuple[EvidenceItem, bool] | None:
    """Return ``(EvidenceItem, correct)`` when a record is BKT-eligible, else ``None``.

    Applies the same course filter, source-specific metadata gates, normalizer
    checks, and concept allow-list as ``build_observations_by_concept``.
    """
    record = _coerce_record(raw)
    course_filter = (
        course_id.strip() if isinstance(course_id, str) and course_id.strip() else None
    )
    if course_filter is not None and record.course_id != course_filter:
        return None

    if record.source_type is PerformanceSourceType.ASSESSMENT_ANSWER:
        correct = _assessment_answer_correctness(record)
    elif record.source_type is PerformanceSourceType.EXERCISE_SUBMISSION:
        correct = _exercise_submission_correctness(record)
    else:
        return None
    if correct is None:
        return None

    allowed = (
        {concept_id.strip() for concept_id in concept_ids if concept_id and concept_id.strip()}
        if concept_ids is not None
        else None
    )
    try:
        item = normalize_performance_evidence(record, student_id)
    except EvidenceNormalizationError:
        return None
    if allowed is not None and item.concept_id not in allowed:
        return None
    return item, correct


def build_observations_by_concept(
    records: Sequence[PerformanceEvidenceRecord | dict],
    *,
    student_id: str,
    course_id: str | None = None,
    concept_ids: Iterable[str] | None = None,
    correct_threshold: float = DEFAULT_CORRECT_THRESHOLD,
) -> dict[str, list[bool]]:
    """Return ``concept_id → [correct, ...]`` in chronological order.

    ``student_id`` is supplied by the caller (MCP records do not carry it).
    When ``concept_ids`` is provided, only those concepts appear in the result
    keys that have at least one usable observation.

    ``correct_threshold`` is retained for API compatibility but is not used for
    ``ASSESSMENT_ANSWER`` or ``EXERCISE_SUBMISSION`` rows.
    """
    _ = correct_threshold  # Kept for call-site compatibility; not used for typed sources.

    pending: list[_PendingObservation] = []
    for raw in records:
        resolved = resolve_bkt_observation(
            raw,
            student_id=student_id,
            course_id=course_id,
            concept_ids=concept_ids,
        )
        if resolved is None:
            continue
        item, correct = resolved
        pending.append(
            _PendingObservation(
                concept_id=item.concept_id,
                observed_at=item.observed_at,
                evidence_id=item.evidence_id,
                correct=correct,
            )
        )

    pending.sort(key=lambda row: (row.observed_at, row.evidence_id))

    grouped: dict[str, list[bool]] = defaultdict(list)
    for row in pending:
        grouped[row.concept_id].append(row.correct)
    return dict(grouped)


def _assessment_answer_correctness(record: PerformanceEvidenceRecord) -> bool | None:
    """Return item-level correctness, or ``None`` when the assessment row is ambiguous."""
    meta = record.metadata
    if not isinstance(meta, dict):
        return None
    if not _has_item_identifier(meta):
        return None
    return _boolean_is_correct(meta)


def _exercise_submission_correctness(record: PerformanceEvidenceRecord) -> bool | None:
    """Return exercise-attempt correctness, or ``None`` when the exercise row is ambiguous."""
    meta = record.metadata
    if not isinstance(meta, dict):
        return None
    exercise_id = meta.get("exercise_id")
    if not isinstance(exercise_id, str) or not exercise_id.strip():
        return None
    return _boolean_is_correct(meta)


def _boolean_is_correct(metadata: dict) -> bool | None:
    is_correct = metadata.get("is_correct")
    if not isinstance(is_correct, bool):
        return None
    return is_correct


def _has_item_identifier(metadata: dict) -> bool:
    for key in _ITEM_ID_KEYS:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _coerce_record(raw: PerformanceEvidenceRecord | dict) -> PerformanceEvidenceRecord:
    if isinstance(raw, PerformanceEvidenceRecord):
        return raw
    return PerformanceEvidenceRecord.model_validate(raw)
