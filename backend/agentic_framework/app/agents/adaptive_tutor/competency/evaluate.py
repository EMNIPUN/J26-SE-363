"""Hold-out evaluation of baseline vs fitted BKT (Step 4).

Fits parameters on chronological train slices only, then scores next-step
predictions on held-out later answers. Does not reuse test observations for fit.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from app.agents.adaptive_tutor.competency.bkt import update_mastery
from app.agents.adaptive_tutor.competency.fit import fit_bkt_parameters
from app.agents.adaptive_tutor.competency.observations import build_observations_by_concept
from app.agents.adaptive_tutor.competency.params import (
    DEFAULT_BKT_PARAMETERS,
    DEFAULT_CORRECT_THRESHOLD,
)
from app.agents.adaptive_tutor.competency.split import (
    DEFAULT_MIN_TEST,
    DEFAULT_MIN_TRAIN,
    DEFAULT_TEST_SIZE,
    ChronologicalSplit,
    split_observations_by_concept,
)
from app.agents.adaptive_tutor.schemas import (
    BktFitResult,
    BktHoldoutEvaluationReport,
    BktHoldoutModelMetrics,
    BktHoldoutSplitSummary,
    BktParameters,
    PerformanceEvidenceRecord,
)


def evaluate_baseline_and_fitted_bkt_holdout(
    *,
    student_id: str,
    course_id: str,
    concept_ids: Sequence[str],
    records: Sequence[PerformanceEvidenceRecord | dict],
    baseline_params: BktParameters | None = None,
    correct_threshold: float = DEFAULT_CORRECT_THRESHOLD,
    test_size: int = DEFAULT_TEST_SIZE,
    min_train: int = DEFAULT_MIN_TRAIN,
    min_test: int = DEFAULT_MIN_TEST,
) -> BktHoldoutEvaluationReport:
    """Fit on train only; score baseline and fitted models on held-out steps."""
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

    splits, skipped = split_observations_by_concept(
        observations_by_concept,
        concept_ids=requested,
        test_size=test_size,
        min_train=min_train,
        min_test=min_test,
    )

    train_obs = sum(s.train_count for s in splits)
    test_obs = sum(s.test_count for s in splits)
    split_summary = BktHoldoutSplitSummary(
        sequences_used=len(splits),
        sequences_skipped=len(skipped),
        train_observations=train_obs,
        test_observations=test_obs,
        skipped_concept_ids=skipped,
    )

    empty_fit = BktFitResult(
        fitted=False,
        parameters=None,
        total_observations=train_obs,
        sequence_count=len(splits),
        log_likelihood=None,
        method="grid_search_pooled",
        explanation=(
            "Hold-out evaluation skipped: need ≥1 concept sequence with "
            f"≥{min_train + test_size} chronological observations "
            f"(min_train={min_train}, test_size={test_size})."
        ),
    )

    if not splits:
        return BktHoldoutEvaluationReport(
            student_id=trusted_student,
            course_id=trusted_course,
            evaluated=False,
            baseline_parameters=baseline,
            fit=empty_fit,
            split=split_summary,
            baseline_metrics=None,
            fitted_metrics=None,
            preferred_model="baseline",
            evaluation_scope="holdout_chronological",
            explanation=empty_fit.explanation,
        )

    train_sequences = [s.train for s in splits]
    fit = fit_bkt_parameters(train_sequences)

    baseline_metrics = _score_holdout(splits, baseline)
    fitted_metrics: BktHoldoutModelMetrics | None = None
    if fit.fitted and fit.parameters is not None:
        fitted_metrics = _score_holdout(splits, fit.parameters)

    preferred, explanation = _prefer_model(
        baseline_metrics,
        fitted_metrics,
        fit.fitted,
    )

    return BktHoldoutEvaluationReport(
        student_id=trusted_student,
        course_id=trusted_course,
        evaluated=True,
        baseline_parameters=baseline,
        fit=fit,
        split=split_summary,
        baseline_metrics=baseline_metrics,
        fitted_metrics=fitted_metrics,
        preferred_model=preferred,
        evaluation_scope="holdout_chronological",
        explanation=explanation,
    )


def _score_holdout(
    splits: Sequence[ChronologicalSplit],
    params: BktParameters,
) -> BktHoldoutModelMetrics:
    """Warm-start on train; score each held-out observation as a next-step prediction."""
    total_ll = 0.0
    correct_preds = 0
    brier_sum = 0.0
    n = 0

    for split in splits:
        p_l = params.p_l0
        for correct in split.train:
            p_l = update_mastery(p_l, correct, params)

        for correct in split.test:
            p_correct = p_l * (1.0 - params.p_s) + (1.0 - p_l) * params.p_g
            p_correct = _clamp_probability(p_correct)
            y = 1.0 if correct else 0.0
            p_obs = p_correct if correct else (1.0 - p_correct)
            total_ll += math.log(max(p_obs, 1e-12))
            if (p_correct >= 0.5) == correct:
                correct_preds += 1
            brier_sum += (p_correct - y) ** 2
            n += 1
            p_l = update_mastery(p_l, correct, params)

    if n == 0:
        return BktHoldoutModelMetrics(
            log_likelihood=None,
            accuracy=None,
            brier_score=None,
            n_test_steps=0,
        )

    return BktHoldoutModelMetrics(
        log_likelihood=total_ll,
        accuracy=correct_preds / n,
        brier_score=brier_sum / n,
        n_test_steps=n,
    )


def _prefer_model(
    baseline: BktHoldoutModelMetrics,
    fitted: BktHoldoutModelMetrics | None,
    fitted_ok: bool,
) -> tuple[str, str]:
    if not fitted_ok or fitted is None or fitted.log_likelihood is None:
        return (
            "baseline",
            "Hold-out evaluation used predefined baseline BKT. Fitted model "
            "unavailable or under-evidenced on the train slice.",
        )
    if baseline.log_likelihood is None:
        return (
            "fitted",
            "Hold-out evaluation used fitted BKT (baseline metrics unavailable).",
        )
    if fitted.log_likelihood > baseline.log_likelihood:
        return (
            "fitted",
            "Fitted BKT has higher held-out log-likelihood than the predefined "
            "baseline (params fitted on earlier answers only).",
        )
    if fitted.log_likelihood < baseline.log_likelihood:
        return (
            "baseline",
            "Predefined baseline BKT has higher held-out log-likelihood than the "
            "fitted grid-search model (params fitted on earlier answers only).",
        )
    return (
        "inconclusive",
        "Baseline and fitted BKT have equal held-out log-likelihood.",
    )


def _clamp_probability(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _require_non_blank(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()
