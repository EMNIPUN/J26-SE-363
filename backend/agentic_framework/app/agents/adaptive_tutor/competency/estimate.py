"""Estimate per-concept mastery with classic BKT from performance evidence."""

from __future__ import annotations

from collections.abc import Sequence

from app.agents.adaptive_tutor.competency.bkt import run_bkt
from app.agents.adaptive_tutor.competency.observations import build_observations_by_concept
from app.agents.adaptive_tutor.competency.params import (
    DEFAULT_BKT_PARAMETERS,
    DEFAULT_CORRECT_THRESHOLD,
)
from app.agents.adaptive_tutor.schemas import (
    BktCompetencyEstimate,
    BktParameters,
    PerformanceEvidenceRecord,
)


def estimate_concept_mastery_bkt(
    *,
    student_id: str,
    course_id: str,
    concept_ids: Sequence[str],
    records: Sequence[PerformanceEvidenceRecord | dict],
    params: BktParameters | None = None,
    correct_threshold: float = DEFAULT_CORRECT_THRESHOLD,
) -> list[BktCompetencyEstimate]:
    """Estimate mastery for each requested concept using chronological evidence.

    Concepts with no usable observations return ``mastery_probability=None``
    (missing evidence is not treated as zero mastery).
    """
    trusted_student_id = _require_non_blank(student_id, "student_id")
    trusted_course_id = _require_non_blank(course_id, "course_id")
    resolved_params = params or DEFAULT_BKT_PARAMETERS
    requested = [_require_non_blank(concept_id, "concept_id") for concept_id in concept_ids]

    observations_by_concept = build_observations_by_concept(
        records,
        student_id=trusted_student_id,
        course_id=trusted_course_id,
        concept_ids=requested,
        correct_threshold=correct_threshold,
    )

    results: list[BktCompetencyEstimate] = []
    for concept_id in requested:
        observations = observations_by_concept.get(concept_id, [])
        if not observations:
            results.append(
                BktCompetencyEstimate(
                    student_id=trusted_student_id,
                    course_id=trusted_course_id,
                    concept_id=concept_id,
                    mastery_probability=None,
                    observation_count=0,
                    model="BKT",
                    parameters=resolved_params,
                    explanation="no_usable_evidence",
                )
            )
            continue

        mastery, count = run_bkt(observations, resolved_params)
        results.append(
            BktCompetencyEstimate(
                student_id=trusted_student_id,
                course_id=trusted_course_id,
                concept_id=concept_id,
                mastery_probability=mastery,
                observation_count=count,
                model="BKT",
                parameters=resolved_params,
                explanation=(
                    f"BKT updated from {count} chronological concept-level "
                    "performance observation(s)."
                ),
            )
        )
    return results


def _require_non_blank(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()
