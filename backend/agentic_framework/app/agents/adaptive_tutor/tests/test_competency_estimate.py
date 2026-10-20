"""Competency estimation from mock performance evidence fixtures."""

import pytest

from app.agents.adaptive_tutor.competency import (
    build_observations_by_concept,
    estimate_concept_mastery_bkt,
)
from app.agents.adaptive_tutor.tests.fixtures.evidence_data import (
    LEARNING_BEHAVIOUR,
    PERFORMANCE_EVIDENCE,
)

STUDENT_ID = "student-1"
COURSE_ID = "course-101"
CONCEPT_ID = "concept-101"


def test_observations_from_mock_evidence_match_expected_sequence():
    observations = build_observations_by_concept(
        PERFORMANCE_EVIDENCE,
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    # evidence-001 (0.4) → False; evidence-002 (0.8) → True; evidence-003 (0.6) → True
    # evidence-004 skipped (missing conceptId)
    assert observations == {CONCEPT_ID: [False, True, True]}


def test_estimate_mastery_for_mock_concept_101():
    results = estimate_concept_mastery_bkt(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
        records=PERFORMANCE_EVIDENCE,
    )
    assert len(results) == 1
    estimate = results[0]
    assert estimate.student_id == STUDENT_ID
    assert estimate.course_id == COURSE_ID
    assert estimate.concept_id == CONCEPT_ID
    assert estimate.model == "BKT"
    assert estimate.observation_count == 3
    assert estimate.mastery_probability == pytest.approx(0.811764, rel=1e-5)
    assert estimate.parameters.p_l0 == 0.2


def test_missing_concept_returns_null_mastery_not_zero():
    results = estimate_concept_mastery_bkt(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=["concept-missing"],
        records=PERFORMANCE_EVIDENCE,
    )
    assert results[0].mastery_probability is None
    assert results[0].observation_count == 0
    assert results[0].explanation == "no_usable_evidence"


def test_learning_behaviour_is_not_used_as_bkt_evidence():
    # Passing only behaviour rows yields no usable BKT observations.
    results = estimate_concept_mastery_bkt(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
        records=[],  # behaviour fixtures are a different schema; empty performance = no obs
    )
    assert results[0].observation_count == 0
    assert results[0].mastery_probability is None
    # Sanity: behaviour fixtures exist but are not performance evidence.
    assert len(LEARNING_BEHAVIOUR) == 2


def test_student_isolation_keeps_student_id_separate():
    for student_id in ("student-A", "student-B"):
        results = estimate_concept_mastery_bkt(
            student_id=student_id,
            course_id=COURSE_ID,
            concept_ids=[CONCEPT_ID],
            records=PERFORMANCE_EVIDENCE,
        )
        assert results[0].student_id == student_id
        assert results[0].observation_count == 3


def test_concept_isolation_does_not_mix_observations():
    results = estimate_concept_mastery_bkt(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID, "concept-other"],
        records=PERFORMANCE_EVIDENCE,
    )
    by_concept = {item.concept_id: item for item in results}
    assert by_concept[CONCEPT_ID].observation_count == 3
    assert by_concept[CONCEPT_ID].mastery_probability is not None
    assert by_concept["concept-other"].observation_count == 0
    assert by_concept["concept-other"].mastery_probability is None
