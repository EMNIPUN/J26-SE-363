"""Option C: baseline predefined BKT vs data-fitted BKT."""

from __future__ import annotations

import pytest

from app.agents.adaptive_tutor.competency import (
    DEFAULT_BKT_PARAMETERS,
    compare_baseline_and_fitted_bkt,
    fit_bkt_parameters,
    pooled_log_likelihood,
    sequence_log_likelihood,
)
from app.agents.adaptive_tutor.competency.bkt import run_bkt
from app.agents.adaptive_tutor.tests.fixtures.evidence_data import PERFORMANCE_EVIDENCE

STUDENT_ID = "student-1"
COURSE_ID = "course-101"
CONCEPT_ID = "concept-101"


def test_sequence_log_likelihood_is_finite_for_mock_path():
    ll = sequence_log_likelihood([False, True, True], DEFAULT_BKT_PARAMETERS)
    assert ll < 0.0
    assert ll == pytest.approx(
        pooled_log_likelihood([[False, True, True]], DEFAULT_BKT_PARAMETERS)
    )


def test_fit_bkt_parameters_from_mock_sequence():
    fit = fit_bkt_parameters([[False, True, True]])
    assert fit.fitted is True
    assert fit.parameters is not None
    assert fit.total_observations == 3
    assert fit.sequence_count == 1
    assert fit.log_likelihood is not None
    # Fitted LL must be at least as good as the default baseline on the same data.
    baseline_ll = pooled_log_likelihood([[False, True, True]], DEFAULT_BKT_PARAMETERS)
    assert fit.log_likelihood >= baseline_ll - 1e-9


def test_fit_rejects_insufficient_evidence():
    fit = fit_bkt_parameters([[True]])  # only 1 observation
    assert fit.fitted is False
    assert fit.parameters is None
    assert "Insufficient evidence" in fit.explanation


def test_compare_baseline_and_fitted_on_mock_evidence():
    report = compare_baseline_and_fitted_bkt(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID, "concept-other"],
        records=PERFORMANCE_EVIDENCE,
    )
    assert report.comparison_scope == "in_sample_provisional"
    assert report.fit.fitted is True
    assert report.baseline_log_likelihood is not None
    assert report.fitted_log_likelihood is not None
    assert report.preferred_model in {"baseline", "fitted", "inconclusive"}

    by_id = {row.concept_id: row for row in report.concepts}
    assert by_id[CONCEPT_ID].observation_count == 3
    assert by_id[CONCEPT_ID].baseline_mastery == pytest.approx(0.811764, rel=1e-5)
    assert by_id[CONCEPT_ID].fitted_mastery is not None
    assert by_id[CONCEPT_ID].mastery_delta is not None

    # Missing-concept row stays unknown under both models.
    assert by_id["concept-other"].observation_count == 0
    assert by_id["concept-other"].baseline_mastery is None
    assert by_id["concept-other"].fitted_mastery is None


def test_fitted_mastery_matches_run_bkt_with_fitted_params():
    report = compare_baseline_and_fitted_bkt(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
        records=PERFORMANCE_EVIDENCE,
    )
    assert report.fit.parameters is not None
    obs = [False, True, True]
    expected, _ = run_bkt(obs, report.fit.parameters)
    assert report.concepts[0].fitted_mastery == pytest.approx(expected)


def test_multi_concept_sequences_are_pooled_for_fit():
    # Build two short sequences via synthetic observation lists directly.
    fit = fit_bkt_parameters(
        [
            [False, True, True],
            [True, False, True, True],
        ]
    )
    assert fit.fitted is True
    assert fit.total_observations == 7
    assert fit.sequence_count == 2
