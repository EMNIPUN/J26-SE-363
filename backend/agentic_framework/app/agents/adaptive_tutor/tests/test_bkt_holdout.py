"""Step 4: chronological hold-out evaluation of baseline vs fitted BKT."""

from __future__ import annotations

import math

import pytest
from shared.contracts import AgentRequest, ResultStatus

from app.agents.adaptive_tutor.agent import AdaptiveTutorAgent
from app.agents.adaptive_tutor.competency import (
    DEFAULT_BKT_PARAMETERS,
    evaluate_baseline_and_fitted_bkt_holdout,
    fit_bkt_parameters,
    split_observations_by_concept,
    split_sequence_chronological,
)
from app.agents.adaptive_tutor.competency.bkt import update_mastery
from app.agents.adaptive_tutor.competency.evaluate import _score_holdout
from app.agents.adaptive_tutor.competency.split import ChronologicalSplit
from app.agents.adaptive_tutor.tests.fixtures.holdout_evidence import (
    HOLDOUT_PERFORMANCE_EVIDENCE,
)
from app.agents.adaptive_tutor.tests.fixtures.sprint_data import (
    PROJECT_ID,
    SPRINT_ID,
    STUDENT_ID as LIVE_STUDENT_ID,
)

STUDENT_ID = "student-1"
COURSE_ID = "course-101"
CONCEPT_ID = "concept-101"


def test_split_sequence_preserves_order_and_leave_last():
    seq = [False, True, True, True]
    split = split_sequence_chronological(seq)
    assert split is not None
    train, test = split
    assert train == [False, True, True]
    assert test == [True]


def test_split_rejects_short_sequences():
    assert split_sequence_chronological([True]) is None
    assert split_sequence_chronological([False, True]) is None
    assert split_sequence_chronological([False, True, True]) is not None


def test_split_observations_skips_short_concepts():
    usable, skipped = split_observations_by_concept(
        {
            CONCEPT_ID: [False, True, True, True],
            "concept-short": [True],
        },
        concept_ids=[CONCEPT_ID, "concept-short"],
    )
    assert len(usable) == 1
    assert usable[0].concept_id == CONCEPT_ID
    assert usable[0].train_count == 3
    assert usable[0].test_count == 1
    assert skipped == ["concept-short"]


def test_holdout_insufficient_evidence_not_evaluated():
    report = evaluate_baseline_and_fitted_bkt_holdout(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
        records=[
            {
                "id": "one",
                "courseId": COURSE_ID,
                "conceptId": CONCEPT_ID,
                "sourceType": "EXERCISE_SUBMISSION",
                "sourceId": "s1",
                "score": 10,
                "maxScore": 10,
                "percentage": 100,
                "attemptNumber": 1,
                "status": "COMPLETED",
                "metadata": {"exercise_id": "exercise-1", "is_correct": True},
                "observedAt": "2026-10-15T09:00:00.000Z",
            }
        ],
    )
    assert report.evaluated is False
    assert report.baseline_metrics is None
    assert report.fitted_metrics is None
    assert report.preferred_model == "baseline"
    assert report.evaluation_scope == "holdout_chronological"
    assert "skipped" in report.explanation.lower() or "need" in report.explanation.lower()


def test_fit_uses_train_only_not_test_observation():
    """Last observation is held out; fit LL equals train-only fit, not full-sequence fit."""
    seq = [False, True, True, False]  # last False held out
    train, test = split_sequence_chronological(seq)
    assert train == [False, True, True]
    assert test == [False]

    train_fit = fit_bkt_parameters([train])
    full_fit = fit_bkt_parameters([seq])
    assert train_fit.fitted is True
    assert full_fit.fitted is True
    # Different last bit can change optimal grid params / LL.
    assert train_fit.log_likelihood is not None
    assert full_fit.log_likelihood is not None

    report = evaluate_baseline_and_fitted_bkt_holdout(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID],
        records=[
            {
                "id": f"e{i}",
                "courseId": COURSE_ID,
                "conceptId": CONCEPT_ID,
                "sourceType": "EXERCISE_SUBMISSION",
                "sourceId": f"s{i}",
                "score": 10 if bit else 0,
                "maxScore": 10,
                "percentage": 100 if bit else 0,
                "attemptNumber": i,
                "status": "COMPLETED",
                "metadata": {
                    "exercise_id": f"exercise-{i}",
                    "is_correct": bit,
                },
                "observedAt": f"2026-10-15T09:{i:02d}:00.000Z",
            }
            for i, bit in enumerate(seq, start=1)
        ],
    )
    assert report.evaluated is True
    assert report.fit.fitted is True
    assert report.fit.total_observations == 3  # train only
    assert report.split.test_observations == 1
    assert report.fit.log_likelihood == pytest.approx(train_fit.log_likelihood)


def test_score_holdout_matches_manual_warm_start():
    split = ChronologicalSplit(
        concept_id=CONCEPT_ID,
        train=[False, True, True],
        test=[True],
    )
    metrics = _score_holdout([split], DEFAULT_BKT_PARAMETERS)
    assert metrics.n_test_steps == 1

    p_l = DEFAULT_BKT_PARAMETERS.p_l0
    for correct in split.train:
        p_l = update_mastery(p_l, correct, DEFAULT_BKT_PARAMETERS)
    p_correct = p_l * (1.0 - DEFAULT_BKT_PARAMETERS.p_s) + (
        1.0 - p_l
    ) * DEFAULT_BKT_PARAMETERS.p_g
    expected_ll = math.log(max(p_correct, 1e-12))
    assert metrics.log_likelihood == pytest.approx(expected_ll)
    assert metrics.accuracy == 1.0
    assert metrics.brier_score == pytest.approx((p_correct - 1.0) ** 2)


def test_evaluate_on_holdout_fixture():
    report = evaluate_baseline_and_fitted_bkt_holdout(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_ids=[CONCEPT_ID, "concept-short"],
        records=HOLDOUT_PERFORMANCE_EVIDENCE,
    )
    assert report.evaluated is True
    assert report.evaluation_scope == "holdout_chronological"
    assert report.split.sequences_used == 1
    assert report.split.sequences_skipped == 1
    assert "concept-short" in report.split.skipped_concept_ids
    assert report.split.train_observations == 3
    assert report.split.test_observations == 1
    assert report.baseline_metrics is not None
    assert report.baseline_metrics.n_test_steps == 1
    assert report.baseline_metrics.log_likelihood is not None
    assert report.baseline_metrics.accuracy is not None
    assert report.baseline_metrics.brier_score is not None
    assert report.preferred_model in {"baseline", "fitted", "inconclusive"}
    if report.fit.fitted:
        assert report.fitted_metrics is not None
        assert report.fitted_metrics.n_test_steps == 1


@pytest.mark.asyncio
async def test_agent_evaluate_bkt_with_inline_evidence():
    from uuid import uuid4

    from app.agents.adaptive_tutor.context.provider import FixtureSprintDataProvider
    from app.agents.adaptive_tutor.knowledge import StaticConceptSelector
    from app.agents.adaptive_tutor.tests.fixtures.course_knowledge import (
        COURSE_ID as FIXTURE_COURSE_ID,
        make_course_bundle,
    )
    from app.agents.adaptive_tutor.tests.fixtures.sprint_data import CAMPUS_SPRINT_SNAPSHOT
    from app.knowledge_graph import InMemoryCourseKnowledgeRepository

    snapshot = CAMPUS_SPRINT_SNAPSHOT.model_copy(update={"course_id": "course-101"})
    agent = AdaptiveTutorAgent(
        sprint_provider=FixtureSprintDataProvider({(PROJECT_ID, SPRINT_ID): snapshot}),
        course_repository=InMemoryCourseKnowledgeRepository(
            {FIXTURE_COURSE_ID: make_course_bundle()}
        ),
        concept_selector=StaticConceptSelector({}),
    )
    response = await agent.handle(
        AgentRequest(
            request_id=str(uuid4()),
            action="tutor.evaluate_bkt",
            student_id=LIVE_STUDENT_ID,
            project_id=PROJECT_ID,
            sprint_id=SPRINT_ID,
            input={
                "course_id": "course-101",
                "concept_ids": [CONCEPT_ID],
                "performance_evidence": [
                    row
                    for row in HOLDOUT_PERFORMANCE_EVIDENCE
                    if row.get("conceptId") == CONCEPT_ID
                ],
            },
        )
    )
    assert response.status is ResultStatus.COMPLETED
    evaluation = response.result["bkt_holdout_evaluation"]
    assert evaluation["evaluation_scope"] == "holdout_chronological"
    assert evaluation["evaluated"] is True
    assert evaluation["split"]["test_observations"] == 1
    assert evaluation["split"]["train_observations"] == 3
