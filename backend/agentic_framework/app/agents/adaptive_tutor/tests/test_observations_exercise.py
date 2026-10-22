"""Limitation #3: EXERCISE_SUBMISSION uses Boolean is_correct, not score threshold."""

from __future__ import annotations

from app.agents.adaptive_tutor.competency import build_observations_by_concept
from app.agents.adaptive_tutor.tests.fixtures.evidence_data import PERFORMANCE_EVIDENCE

STUDENT_ID = "student-1"
COURSE_ID = "course-101"
CONCEPT_ID = "concept-101"


def _exercise_row(**overrides):
    base = {
        "id": "ex-1",
        "courseId": COURSE_ID,
        "conceptId": CONCEPT_ID,
        "sourceType": "EXERCISE_SUBMISSION",
        "sourceId": "activity-1",
        "score": 10,
        "maxScore": 10,
        "percentage": 100,
        "attemptNumber": 1,
        "status": "COMPLETED",
        "metadata": {
            "exercise_id": "exercise-1",
            "is_correct": True,
        },
        "observedAt": "2026-10-15T12:00:00.000Z",
    }
    metadata = overrides.pop("metadata", None)
    if metadata is not None:
        base["metadata"] = metadata
    base.update(overrides)
    return base


def test_is_correct_false_with_full_score_produces_false():
    observations = build_observations_by_concept(
        [
            _exercise_row(
                score=10,
                maxScore=10,
                percentage=100,
                metadata={"exercise_id": "exercise-1", "is_correct": False},
            )
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {CONCEPT_ID: [False]}


def test_is_correct_true_with_zero_score_produces_true():
    observations = build_observations_by_concept(
        [
            _exercise_row(
                score=0,
                maxScore=10,
                percentage=0,
                metadata={"exercise_id": "exercise-1", "is_correct": True},
            )
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {CONCEPT_ID: [True]}


def test_missing_is_correct_is_skipped():
    observations = build_observations_by_concept(
        [_exercise_row(metadata={"exercise_id": "exercise-1"})],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {}


def test_non_boolean_is_correct_is_skipped():
    observations = build_observations_by_concept(
        [_exercise_row(metadata={"exercise_id": "exercise-1", "is_correct": "false"})],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {}


def test_missing_or_blank_exercise_id_is_skipped():
    missing = build_observations_by_concept(
        [_exercise_row(metadata={"is_correct": True})],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    blank = build_observations_by_concept(
        [_exercise_row(metadata={"exercise_id": "   ", "is_correct": True})],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert missing == {}
    assert blank == {}


def test_missing_concept_id_is_still_excluded():
    observations = build_observations_by_concept(
        [
            _exercise_row(
                conceptId=None,
                metadata={"exercise_id": "exercise-1", "is_correct": True},
            )
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {}


def test_course_and_concept_allow_list_filtering():
    other_course = build_observations_by_concept(
        [_exercise_row(courseId="course-other")],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    other_concept = build_observations_by_concept(
        [_exercise_row(conceptId="concept-other")],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert other_course == {}
    assert other_concept == {}


def test_chronological_ordering_is_preserved():
    observations = build_observations_by_concept(
        [
            _exercise_row(
                id="later",
                observedAt="2026-10-15T14:00:00.000Z",
                metadata={"exercise_id": "exercise-1", "is_correct": False},
                score=0,
                percentage=0,
            ),
            _exercise_row(
                id="earlier",
                observedAt="2026-10-15T13:00:00.000Z",
                metadata={"exercise_id": "  exercise-2  ", "is_correct": True},
            ),
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {CONCEPT_ID: [True, False]}


def test_assessment_answer_behaviour_remains_unchanged():
    observations = build_observations_by_concept(
        [
            {
                "id": "a1",
                "courseId": COURSE_ID,
                "conceptId": CONCEPT_ID,
                "sourceType": "ASSESSMENT_ANSWER",
                "sourceId": "ans-1",
                "score": 10,
                "maxScore": 10,
                "percentage": 100,
                "attemptNumber": 1,
                "status": "COMPLETED",
                "metadata": {"question_id": "q-1", "is_correct": False},
                "observedAt": "2026-10-15T12:00:00.000Z",
            }
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {CONCEPT_ID: [False]}


def test_exercise_failing_normalization_is_excluded():
    """Scorable fields missing → normalizer rejects even with valid exercise metadata."""
    observations = build_observations_by_concept(
        [
            _exercise_row(
                score=None,
                maxScore=None,
                percentage=None,
                metadata={"exercise_id": "exercise-1", "is_correct": True},
            )
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert observations == {}


def test_baseline_fixture_exercise_sequence():
    exercises_only = build_observations_by_concept(
        [
            row
            for row in PERFORMANCE_EVIDENCE
            if row["sourceType"] == "EXERCISE_SUBMISSION" and row.get("conceptId")
        ],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert exercises_only == {CONCEPT_ID: [False, True]}
