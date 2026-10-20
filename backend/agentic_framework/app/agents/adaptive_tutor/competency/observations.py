"""Build chronological BKT observations from performance evidence.

Learning-behaviour activities are intentionally excluded. Records without a
trusted concept id or scorable measurement are skipped (never invented).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from app.agents.adaptive_tutor.competency.params import DEFAULT_CORRECT_THRESHOLD
from app.agents.adaptive_tutor.evidence import (
    EvidenceNormalizationError,
    normalize_performance_evidence,
)
from app.agents.adaptive_tutor.schemas import (
    EvidenceItem,
    PerformanceEvidenceRecord,
)


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
    """
    allowed = (
        {concept_id.strip() for concept_id in concept_ids if concept_id and concept_id.strip()}
        if concept_ids is not None
        else None
    )
    course_filter = course_id.strip() if isinstance(course_id, str) and course_id.strip() else None

    items: list[EvidenceItem] = []
    for raw in records:
        record = _coerce_record(raw)
        if course_filter is not None and record.course_id != course_filter:
            continue
        try:
            item = normalize_performance_evidence(record, student_id)
        except EvidenceNormalizationError:
            continue
        if allowed is not None and item.concept_id not in allowed:
            continue
        items.append(item)

    items.sort(key=lambda item: (item.observed_at, item.evidence_id))

    grouped: dict[str, list[bool]] = defaultdict(list)
    for item in items:
        grouped[item.concept_id].append(item.score >= correct_threshold)
    return dict(grouped)


def _coerce_record(raw: PerformanceEvidenceRecord | dict) -> PerformanceEvidenceRecord:
    if isinstance(raw, PerformanceEvidenceRecord):
        return raw
    return PerformanceEvidenceRecord.model_validate(raw)
