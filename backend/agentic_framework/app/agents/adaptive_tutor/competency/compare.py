"""Option C: compare predefined baseline BKT with data-fitted BKT.

Runs both models on the same concept-level observation sequences. Fit quality is
reported as in-sample log-likelihood (provisional research comparison).
"""

from __future__ import annotations

from collections.abc import Sequence

from app.agents.adaptive_tutor.competency.bkt import run_bkt
from app.agents.adaptive_tutor.competency.fit import (
    fit_bkt_parameters,
    pooled_log_likelihood,
)
from app.agents.adaptive_tutor.competency.observations import build_observations_by_concept
from app.agents.adaptive_tutor.competency.params import (
    DEFAULT_BKT_PARAMETERS,
    DEFAULT_CORRECT_THRESHOLD,
)
from app.agents.adaptive_tutor.schemas import (
    BktComparisonReport,
    BktConceptComparison,
    BktParameters,
    PerformanceEvidenceRecord,
)


def compare_baseline_and_fitted_bkt(
    *,
    student_id: str,
    course_id: str,
    concept_ids: Sequence[str],
    records: Sequence[PerformanceEvidenceRecord | dict],
    baseline_params: BktParameters | None = None,
    correct_threshold: float = DEFAULT_CORRECT_THRESHOLD,
) -> BktComparisonReport:
    """Estimate per-concept mastery with baseline and fitted params; compare LL."""
    trusted_student = _require_non_blank(student_id, "student_id")
    trusted_course = _require_non_blank(course_id, "course_id")
    requested = [_require_non_blank(cid, "concept_id") for cid in concept_ids]
    baseline = baseline_params or DEFAULT_BKT_PARAMETERS

    observations_by_concept = build_observations_by_concept(
        records,
        student_id=trusted_student,
        course_id=trusted_course,
        concept_ids=requested,
        correct_threshold=correct_threshold,
    )

    sequences = [observations_by_concept.get(cid, []) for cid in requested]
    usable_sequences = [seq for seq in sequences if seq]
    fit = fit_bkt_parameters(usable_sequences)

    baseline_ll = (
        pooled_log_likelihood(usable_sequences, baseline) if usable_sequences else None
    )
    fitted_ll = fit.log_likelihood if fit.fitted else None

    concepts: list[BktConceptComparison] = []
    for concept_id in requested:
        obs = observations_by_concept.get(concept_id, [])
        if not obs:
            concepts.append(
                BktConceptComparison(
                    concept_id=concept_id,
                    observation_count=0,
                    baseline_mastery=None,
                    fitted_mastery=None,
                    mastery_delta=None,
                    baseline_parameters=baseline,
                    fitted_parameters=fit.parameters if fit.fitted else None,
                )
            )
            continue

        baseline_mastery, count = run_bkt(obs, baseline)
        fitted_mastery: float | None = None
        delta: float | None = None
        if fit.fitted and fit.parameters is not None:
            fitted_mastery, _ = run_bkt(obs, fit.parameters)
            delta = fitted_mastery - baseline_mastery

        concepts.append(
            BktConceptComparison(
                concept_id=concept_id,
                observation_count=count,
                baseline_mastery=baseline_mastery,
                fitted_mastery=fitted_mastery,
                mastery_delta=delta,
                baseline_parameters=baseline,
                fitted_parameters=fit.parameters if fit.fitted else None,
            )
        )

    preferred, explanation = _prefer_model(baseline_ll, fitted_ll, fit.fitted)

    return BktComparisonReport(
        student_id=trusted_student,
        course_id=trusted_course,
        baseline_parameters=baseline,
        fit=fit,
        concepts=concepts,
        baseline_log_likelihood=baseline_ll,
        fitted_log_likelihood=fitted_ll,
        preferred_model=preferred,
        comparison_scope="in_sample_provisional",
        explanation=explanation,
    )


def _prefer_model(
    baseline_ll: float | None,
    fitted_ll: float | None,
    fitted: bool,
) -> tuple[str, str]:
    if not fitted or fitted_ll is None or baseline_ll is None:
        return (
            "baseline",
            "Using predefined baseline BKT. Fitted model unavailable or under-evidenced.",
        )
    if fitted_ll > baseline_ll:
        return (
            "fitted",
            "Fitted BKT has higher in-sample log-likelihood than the predefined baseline "
            "(provisional; same evidence used for fitting and scoring).",
        )
    if fitted_ll < baseline_ll:
        return (
            "baseline",
            "Predefined baseline BKT has higher in-sample log-likelihood than the fitted "
            "grid-search model (provisional comparison).",
        )
    return (
        "inconclusive",
        "Baseline and fitted BKT have equal in-sample log-likelihood (provisional).",
    )


def _require_non_blank(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()
