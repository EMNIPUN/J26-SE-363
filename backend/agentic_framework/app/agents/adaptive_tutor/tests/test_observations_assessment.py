"""Limitation #3: ASSESSMENT_ANSWER must be item-level for BKT observations."""

from __future__ import annotations

from app.agents.adaptive_tutor.competency import build_observations_by_concept
from app.agents.adaptive_tutor.tests.fixtures.evidence_data import PERFORMANCE_EVIDENCE

STUDENT_ID = "student-1"
COURSE_ID = "course-101"
CONCEPT_ID = "concept-101"


def _assessment_row(**overrides):
    base = {
        "id": "assess-1",
        "courseId": COURSE_ID,
        "conceptId": CONCEPT_ID,
        "sourceType": "ASSESSMENT_ANSWER",
        "sourceId": "answer-1",
        "score": 1,
        "maxScore": 1,
        "percentage": 100,
        "attemptNumber": 1,
        "status": "COMPLETED",
        "metadata": {
            "question_id": "q-1",
            "is_correct": True,
        },
        "observedAt": "2026-10-15T12:00:00.000Z",
    }
    metadata = overrides.pop("metadata", None)
    if metadata is not None:
        base["metadata"] = metadata
    base.update(overrides)
    return base


def test_is_correct_false_with_high_score_produces_false():
    observations = build_observations_by_concept(
        [
            _assessment_row(
                score=10,
                maxScore=10,
                percentage=100,
                metadata={"question_id": "q-high", "is_correct": False},
            )
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {CONCEPT_ID: [False]}


def test_is_correct_true_with_low_score_produces_true():
    observations = build_observations_by_concept(
        [
            _assessment_row(
                score=1,
                maxScore=10,
                percentage=10,
                metadata={"question_id": "q-low", "is_correct": True},
            )
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {CONCEPT_ID: [True]}


def test_question_id_and_assessment_question_id_are_both_accepted():
    by_question = build_observations_by_concept(
        [_assessment_row(metadata={"question_id": "  q-a  ", "is_correct": True})],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    by_aq = build_observations_by_concept(
        [
            _assessment_row(
                id="assess-2",
                metadata={"assessment_question_id": "aq-1", "is_correct": False},
            )
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert by_question == {CONCEPT_ID: [True]}
    assert by_aq == {CONCEPT_ID: [False]}


def test_missing_item_id_is_skipped():
    observations = build_observations_by_concept(
        [_assessment_row(metadata={"is_correct": True})],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {}


def test_blank_item_id_is_skipped():
    observations = build_observations_by_concept(
        [_assessment_row(metadata={"question_id": "   ", "is_correct": True})],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {}


def test_missing_or_non_boolean_is_correct_is_skipped():
    missing = build_observations_by_concept(
        [_assessment_row(metadata={"question_id": "q-1"})],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    as_string = build_observations_by_concept(
        [_assessment_row(metadata={"question_id": "q-1", "is_correct": "true"})],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert missing == {}
    assert as_string == {}


def test_missing_concept_id_is_still_excluded():
    observations = build_observations_by_concept(
        [
            _assessment_row(
                conceptId=None,
                metadata={"question_id": "q-1", "is_correct": True},
            )
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {}


def test_chronological_ordering_is_preserved():
    observations = build_observations_by_concept(
        [
            _assessment_row(
                id="later",
                observedAt="2026-10-15T14:00:00.000Z",
                metadata={"question_id": "q-later", "is_correct": False},
            ),
            _assessment_row(
                id="earlier",
                observedAt="2026-10-15T13:00:00.000Z",
                metadata={"assessment_question_id": "aq-earlier", "is_correct": True},
            ),
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {CONCEPT_ID: [True, False]}


def test_assessment_answer_behaviour_unchanged_with_updated_exercise_fixtures():
    """Baseline fixture sequence stays False, True, True after exercise metadata update."""
    observations = build_observations_by_concept(
        PERFORMANCE_EVIDENCE,
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {CONCEPT_ID: [False, True, True]}
