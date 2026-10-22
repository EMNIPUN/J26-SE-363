"""Agent-level competency estimation using explicit concepts + fixture evidence."""

from __future__ import annotations

from uuid import uuid4

import pytest
from shared.contracts import AgentRequest, ResultStatus

from app.agents.adaptive_tutor.agent import AdaptiveTutorAgent
from app.agents.adaptive_tutor.knowledge import StaticConceptSelector
from app.agents.adaptive_tutor.tests.fixtures.course_knowledge import (
    COURSE_ID as FIXTURE_COURSE_ID,
    JWT_CONCEPT_ID,
    make_course_bundle,
)
from app.agents.adaptive_tutor.tests.fixtures.evidence_data import PERFORMANCE_EVIDENCE
from app.agents.adaptive_tutor.tests.fixtures.sprint_data import (
    CAMPUS_SPRINT_SNAPSHOT,
    PROJECT_ID,
    SPRINT_ID,
    STUDENT_ID,
)
from app.agents.adaptive_tutor.context.provider import FixtureSprintDataProvider
from app.knowledge_graph import InMemoryCourseKnowledgeRepository


@pytest.mark.asyncio
async def test_estimate_competency_with_fixture_evidence_and_explicit_concepts():
    # Align sprint course_id with mock PERFORMANCE_EVIDENCE course-101 for this unit test.
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
            action="tutor.estimate_competency",
            student_id=STUDENT_ID,
            project_id=PROJECT_ID,
            sprint_id=SPRINT_ID,
            input={
                "course_id": "course-101",
                "concept_ids": ["concept-101", "concept-missing"],
                "performance_evidence": PERFORMANCE_EVIDENCE,
            },
        )
    )
    assert response.status is ResultStatus.COMPLETED
    estimates = response.result["estimates"]
    assert estimates[0]["concept_id"] == "concept-101"
    assert estimates[0]["observation_count"] == 3
    assert estimates[0]["mastery_probability"] == pytest.approx(0.811764, rel=1e-5)
    assert estimates[0]["student_id"] == STUDENT_ID
    assert estimates[1]["mastery_probability"] is None
    assert "required_knowledge" not in response.result
    normalized = response.result["normalized_evidence"]
    assert [row["correct"] for row in normalized] == [False, True, True]
    assert all(row["used_for_bkt"] is True for row in normalized)


@pytest.mark.asyncio
async def test_estimate_competency_without_evidence_source_is_unavailable():
    agent = AdaptiveTutorAgent(
        sprint_provider=FixtureSprintDataProvider(
            {(PROJECT_ID, SPRINT_ID): CAMPUS_SPRINT_SNAPSHOT}
        ),
        course_repository=InMemoryCourseKnowledgeRepository(
            {FIXTURE_COURSE_ID: make_course_bundle()}
        ),
        concept_selector=StaticConceptSelector({}),
        mcp_url=None,
    )
    response = await agent.handle(
        AgentRequest(
            request_id=str(uuid4()),
            action="tutor.estimate_competency",
            student_id=STUDENT_ID,
            project_id=PROJECT_ID,
            sprint_id=SPRINT_ID,
            input={"concept_ids": [JWT_CONCEPT_ID]},
        )
    )
    assert response.status is ResultStatus.UNAVAILABLE
    assert response.error is not None
    assert response.error.code == "mcp_not_configured"
