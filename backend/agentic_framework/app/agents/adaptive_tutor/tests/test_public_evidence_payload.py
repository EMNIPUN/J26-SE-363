"""Public evidence payload must label BKT eligibility using observation-builder rules."""

from __future__ import annotations

from app.agents.adaptive_tutor.agent import AdaptiveTutorAgent
from app.agents.adaptive_tutor.competency import build_observations_by_concept

STUDENT_ID = "student-1"
COURSE_ID = "course-101"
CONCEPT_ID = "concept-101"


def _exercise_row(**overrides):
    base = {
        "id": "ex-1",
        "courseId": COURSE_ID,
        "conceptId": CONCEPT_ID,
        "sourceType": "EXERCISE_SUBMISSION",
        "sourceId": "submission-1",
        "score": 10,
        "maxScore": 10,
        "percentage": 100,
        "attemptNumber": 1,
        "status": "COMPLETED",
        "metadata": {"exercise_id": "exercise-1", "is_correct": True},
        "observedAt": "2026-10-15T12:00:00.000Z",
    }
    metadata = overrides.pop("metadata", None)
    if metadata is not None:
        base["metadata"] = metadata
    base.update(overrides)
    return base


def _assessment_row(**overrides):
    base = {
        "id": "a-1",
        "courseId": COURSE_ID,
        "conceptId": CONCEPT_ID,
        "sourceType": "ASSESSMENT_ANSWER",
        "sourceId": "answer-1",
        "score": 10,
        "maxScore": 10,
        "percentage": 100,
        "attemptNumber": 1,
        "status": "COMPLETED",
        "metadata": {"question_id": "q-1", "is_correct": True},
        "observedAt": "2026-10-15T12:00:00.000Z",
    }
    metadata = overrides.pop("metadata", None)
    if metadata is not None:
        base["metadata"] = metadata
    base.update(overrides)
    return base


def _payload(records, **kwargs):
    return AdaptiveTutorAgent._public_evidence_payload(
        records,
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
        **kwargs,
    )


def test_is_correct_false_with_high_score_sets_correct_false():
    _public, normalized = _payload(
        [
            _exercise_row(
                score=10,
                maxScore=10,
                percentage=100,
                metadata={"exercise_id": "exercise-1", "is_correct": False},
            )
        ]
    )
    assert len(normalized) == 1
    assert normalized[0]["used_for_bkt"] is True
    assert normalized[0]["correct"] is False
    assert normalized[0]["score"] == 1.0


def test_is_correct_true_with_partial_score_sets_correct_true():
    _public, normalized = _payload(
        [
            _assessment_row(
                score=4,
                maxScore=10,
                percentage=40,
                metadata={"question_id": "q-low", "is_correct": True},
            )
        ]
    )
    assert len(normalized) == 1
    assert normalized[0]["used_for_bkt"] is True
    assert normalized[0]["correct"] is True
    assert normalized[0]["score"] == 0.4


def test_missing_or_invalid_is_correct_is_not_used_for_bkt():
    missing = _payload(
        [_exercise_row(metadata={"exercise_id": "exercise-1"})]
    )[1]
    invalid = _payload(
        [_exercise_row(metadata={"exercise_id": "exercise-1", "is_correct": "false"})]
    )[1]
    assert missing == []
    assert invalid == []


def test_missing_item_or_exercise_identifier_is_not_used_for_bkt():
    no_exercise_id = _payload(
        [_exercise_row(metadata={"is_correct": True})]
    )[1]
    blank_exercise_id = _payload(
        [_exercise_row(metadata={"exercise_id": "   ", "is_correct": True})]
    )[1]
    no_question_id = _payload(
        [_assessment_row(metadata={"is_correct": True})]
    )[1]
    assert no_exercise_id == []
    assert blank_exercise_id == []
    assert no_question_id == []


def test_course_and_concept_filters_exclude_ineligible_rows():
    other_course_public, other_course = AdaptiveTutorAgent._public_evidence_payload(
        [_exercise_row(courseId="course-other")],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    other_concept_public, other_concept = AdaptiveTutorAgent._public_evidence_payload(
        [_exercise_row(conceptId="concept-other")],
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    assert other_course == []
    assert other_concept == []
    assert other_course_public == []
    assert other_concept_public == []


def test_public_list_keeps_required_concept_and_drops_other_courses():
    public, normalized = _payload(
        [
            _exercise_row(id="required"),
            _exercise_row(id="other-course", courseId="course-other"),
            _exercise_row(id="other-concept", conceptId="concept-other"),
            _exercise_row(
                id="required-not-bkt",
                metadata={"exercise_id": "exercise-1"},
            ),
        ]
    )
    assert [row["id"] for row in public] == ["required", "required-not-bkt"]
    assert [row["evidence_id"] for row in normalized] == ["required"]


def test_payload_correctness_matches_observation_builder():
    records = [
        _exercise_row(
            id="ex-high-false",
            score=10,
            percentage=100,
            metadata={"exercise_id": "exercise-1", "is_correct": False},
            observedAt="2026-10-15T12:00:00.000Z",
        ),
        _assessment_row(
            id="a-low-true",
            score=2,
            maxScore=10,
            percentage=20,
            metadata={"question_id": "q-1", "is_correct": True},
            observedAt="2026-10-15T12:01:00.000Z",
        ),
        _exercise_row(
            id="ex-skip",
            metadata={"exercise_id": "exercise-2"},
            observedAt="2026-10-15T12:02:00.000Z",
        ),
    ]
    observations = build_observations_by_concept(
        records,
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
    )
    _public, normalized = _payload(records)

    assert observations == {CONCEPT_ID: [False, True]}
    assert [row["correct"] for row in normalized] == [False, True]
    assert all(row["used_for_bkt"] is True for row in normalized)
    assert {row["evidence_id"] for row in normalized} == {"ex-high-false", "a-low-true"}


def test_public_rows_still_include_ineligible_sanitized_evidence():
    public, normalized = _payload(
        [_exercise_row(metadata={"exercise_id": "exercise-1"})]
    )
    assert len(public) == 1
    assert public[0]["id"] == "ex-1"
    assert "metadata" not in public[0]
    assert normalized == []
