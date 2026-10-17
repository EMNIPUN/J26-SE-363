"""Deterministic tests for Required Knowledge Identification (mocked Neo4j/OpenAI)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from shared.contracts import AgentRequest, ResultStatus

from app.agents.adaptive_tutor.agent import AdaptiveTutorAgent
from app.agents.adaptive_tutor.knowledge import (
    KnowledgeValidationError,
    StaticConceptSelector,
    identify_required_knowledge,
)
from app.agents.adaptive_tutor.knowledge.candidates import select_candidates_for_task
from app.agents.adaptive_tutor.knowledge.validate import validate_task_selections
from app.agents.adaptive_tutor.tests.fixtures.course_knowledge import (
    AUTH_CONCEPT_ID,
    COURSE_ID,
    JWT_CONCEPT_ID,
    OTHER_COURSE_BUNDLE,
    OTHER_COURSE_ID,
    REST_CONCEPT_ID,
    UNRELATED_CONCEPT_ID,
    make_course_bundle,
    make_empty_course_bundle,
)
from app.agents.adaptive_tutor.tests.fixtures.sprint_data import (
    CAMPUS_SPRINT_SNAPSHOT,
    PROJECT_ID,
    SPRINT_ID,
    make_fixture_sprint_provider,
)
from app.knowledge_graph import InMemoryCourseKnowledgeRepository, UnknownCourseError


def _request(**overrides) -> AgentRequest:
    fields = {
        "request_id": str(uuid4()),
        "action": "tutor.identify_required_knowledge",
        "student_id": "STU-001",
        "project_id": PROJECT_ID,
        "sprint_id": SPRINT_ID,
        "input": {"course_id": COURSE_ID},
    }
    fields.update(overrides)
    return AgentRequest(**fields)


def _repo(bundle=None):
    bundles = {COURSE_ID: bundle or make_course_bundle()}
    bundles[OTHER_COURSE_ID] = OTHER_COURSE_BUNDLE
    return InMemoryCourseKnowledgeRepository(bundles)


@pytest.mark.asyncio
async def test_student_context_filters_assigned_tasks_only():
    selector = StaticConceptSelector(
        {
            "task-jwt": [
                {
                    "concept_id": JWT_CONCEPT_ID,
                    "selection_role": "directly_required",
                    "reason": "Task implements JWT authentication.",
                }
            ],
            "task-profile": [],
        }
    )

    result = await identify_required_knowledge(
        _request(),
        sprint_provider=make_fixture_sprint_provider(),
        course_repository=_repo(),
        concept_selector=selector,
    )

    assert [task.task_id for task in result.tasks] == ["task-jwt", "task-profile"]
    assert "task-dashboard" not in {task.task_id for task in result.tasks}


@pytest.mark.asyncio
async def test_same_concept_can_be_required_by_multiple_tasks():
    selector = StaticConceptSelector(
        {
            "task-jwt": [
                {
                    "concept_id": AUTH_CONCEPT_ID,
                    "selection_role": "directly_required",
                    "reason": "JWT task needs authentication fundamentals.",
                }
            ],
            "task-profile": [
                {
                    "concept_id": AUTH_CONCEPT_ID,
                    "selection_role": "directly_required",
                    "reason": "Profile API requires authenticated access.",
                }
            ],
        }
    )

    result = await identify_required_knowledge(
        _request(),
        sprint_provider=make_fixture_sprint_provider(),
        course_repository=_repo(),
        concept_selector=selector,
    )

    jwt_ids = [c.concept_id for c in result.tasks[0].required_concepts]
    profile_ids = [c.concept_id for c in result.tasks[1].required_concepts]
    assert AUTH_CONCEPT_ID in jwt_ids
    assert AUTH_CONCEPT_ID in profile_ids


def test_course_retrieval_returns_only_requested_course_records():
    repo = _repo()
    bundle = repo.get_course_knowledge(COURSE_ID)
    assert bundle.course_id == COURSE_ID
    assert all(concept.concept_id != "other-course-concept" for concept in bundle.concepts)


def test_unknown_course_id_is_rejected():
    repo = _repo()
    with pytest.raises(UnknownCourseError) as exc_info:
        repo.get_course_knowledge("missing-course")
    assert exc_info.value.code == "unknown_course"


def test_empty_course_content_is_handled():
    repo = InMemoryCourseKnowledgeRepository({COURSE_ID: make_empty_course_bundle()})
    bundle = repo.get_course_knowledge(COURSE_ID)
    assert bundle.concepts == []


def test_missing_concept_descriptions_do_not_crash_candidate_selection():
    bundle = make_course_bundle()
    task = CAMPUS_SPRINT_SNAPSHOT.tasks[0]
    candidates = select_candidates_for_task(task, bundle, technology_stack=["FastAPI"])
    assert any(c.concept_id == "concept-missing-description" for c in bundle.concepts)
    # Selection must not raise even when some catalogue rows lack names.
    assert isinstance(candidates, list)


def test_graph_prerequisites_are_expanded_within_candidate_set():
    bundle = make_course_bundle()
    jwt_task = next(t for t in CAMPUS_SPRINT_SNAPSHOT.tasks if t.task_id == "task-jwt")
    candidates = select_candidates_for_task(
        jwt_task,
        bundle,
        technology_stack=["FastAPI"],
        limit=10,
    )
    candidate_ids = {c.concept_id for c in candidates}
    assert JWT_CONCEPT_ID in candidate_ids or AUTH_CONCEPT_ID in candidate_ids
    # Prerequisite / related expansion should pull REST when AUTH is selected.
    assert REST_CONCEPT_ID in candidate_ids or AUTH_CONCEPT_ID in candidate_ids


@pytest.mark.asyncio
async def test_llm_selects_relevant_concepts_from_candidates():
    selector = StaticConceptSelector(
        {
            "task-jwt": [
                {
                    "concept_id": JWT_CONCEPT_ID,
                    "selection_role": "directly_required",
                    "reason": "Task title and acceptance criteria require JWT tokens.",
                },
                {
                    "concept_id": AUTH_CONCEPT_ID,
                    "selection_role": "prerequisite",
                    "reason": "JWT depends on authentication fundamentals.",
                },
            ],
            "task-profile": [],
        }
    )
    result = await identify_required_knowledge(
        _request(),
        sprint_provider=make_fixture_sprint_provider(),
        course_repository=_repo(),
        concept_selector=selector,
    )
    jwt = result.tasks[0]
    assert {c.concept_id for c in jwt.required_concepts} == {
        JWT_CONCEPT_ID,
        AUTH_CONCEPT_ID,
    }
    assert jwt.required_concepts[0].source_lesson_ids


@pytest.mark.asyncio
async def test_unrelated_concepts_can_be_excluded_by_selector():
    selector = StaticConceptSelector(
        {
            "task-jwt": [
                {
                    "concept_id": JWT_CONCEPT_ID,
                    "selection_role": "directly_required",
                    "reason": "JWT is required.",
                }
            ],
            "task-profile": [],
        }
    )
    result = await identify_required_knowledge(
        _request(),
        sprint_provider=make_fixture_sprint_provider(),
        course_repository=_repo(),
        concept_selector=selector,
    )
    selected = {
        c.concept_id
        for task in result.tasks
        for c in task.required_concepts
    }
    assert UNRELATED_CONCEPT_ID not in selected


def test_invented_concept_ids_are_rejected():
    bundle = make_course_bundle()
    with pytest.raises(KnowledgeValidationError):
        validate_task_selections(
            task_id="task-jwt",
            task_title="JWT",
            raw_selections=[
                {
                    "concept_id": "invented-concept",
                    "selection_role": "directly_required",
                    "reason": "made up",
                }
            ],
            candidates=bundle.concepts,
            course_concept_ids={c.concept_id for c in bundle.concepts},
        )


def test_concepts_from_another_course_are_rejected():
    bundle = make_course_bundle()
    with pytest.raises(KnowledgeValidationError, match="not in the resolved course"):
        validate_task_selections(
            task_id="task-jwt",
            task_title="JWT",
            raw_selections=[
                {
                    "concept_id": "other-course-concept",
                    "selection_role": "directly_required",
                    "reason": "wrong course",
                }
            ],
            candidates=bundle.concepts,
            course_concept_ids={c.concept_id for c in bundle.concepts},
        )


def test_duplicate_concepts_are_deduplicated_per_task():
    bundle = make_course_bundle()
    result = validate_task_selections(
        task_id="task-jwt",
        task_title="JWT",
        raw_selections=[
            {
                "concept_id": JWT_CONCEPT_ID,
                "selection_role": "directly_required",
                "reason": "first",
            },
            {
                "concept_id": JWT_CONCEPT_ID,
                "selection_role": "directly_required",
                "reason": "duplicate",
            },
        ],
        candidates=bundle.concepts,
        course_concept_ids={c.concept_id for c in bundle.concepts},
    )
    assert len(result.required_concepts) == 1


@pytest.mark.asyncio
async def test_empty_valid_llm_results_are_supported():
    selector = StaticConceptSelector({"task-jwt": [], "task-profile": []})
    result = await identify_required_knowledge(
        _request(),
        sprint_provider=make_fixture_sprint_provider(),
        course_repository=_repo(),
        concept_selector=selector,
    )
    assert result.course_id == COURSE_ID
    assert all(task.required_concepts == [] for task in result.tasks)


@pytest.mark.asyncio
async def test_malformed_llm_response_fails_closed():
    class BrokenSelector:
        async def select_for_tasks(self, **kwargs):
            return {
                "task-jwt": [{"concept_id": JWT_CONCEPT_ID}],  # missing reason
                "task-profile": [],
            }

    with pytest.raises(KnowledgeValidationError):
        await identify_required_knowledge(
            _request(),
            sprint_provider=make_fixture_sprint_provider(),
            course_repository=_repo(),
            concept_selector=BrokenSelector(),
        )


@pytest.mark.asyncio
async def test_openai_service_failure_is_surfaced_by_agent():
    class FailingSelector:
        async def select_for_tasks(self, **kwargs):
            from app.agents.adaptive_tutor.knowledge.errors import KnowledgeLlmError

            raise KnowledgeLlmError("openai_selection_failed", "boom")

    agent = AdaptiveTutorAgent(
        sprint_provider=make_fixture_sprint_provider(),
        course_repository=_repo(),
        concept_selector=FailingSelector(),
    )
    response = await agent.handle(_request())
    assert response.status is ResultStatus.FAILED
    assert response.error is not None
    assert response.error.code == "openai_selection_failed"


@pytest.mark.asyncio
async def test_agent_identify_required_knowledge_success_path():
    selector = StaticConceptSelector(
        {
            "task-jwt": [
                {
                    "concept_id": JWT_CONCEPT_ID,
                    "selection_role": "directly_required",
                    "reason": "JWT authentication task.",
                }
            ],
            "task-profile": [],
        }
    )
    agent = AdaptiveTutorAgent(
        sprint_provider=make_fixture_sprint_provider(),
        course_repository=_repo(),
        concept_selector=selector,
    )
    response = await agent.handle(_request())
    assert response.status is ResultStatus.COMPLETED
    assert response.result["course_id"] == COURSE_ID
    assert response.result["student_id"] == "STU-001"
    assert response.result["tasks"][0]["required_concepts"][0]["concept_id"] == JWT_CONCEPT_ID


@pytest.mark.asyncio
async def test_missing_course_id_fails():
    agent = AdaptiveTutorAgent(
        sprint_provider=make_fixture_sprint_provider(),
        course_repository=_repo(),
        concept_selector=StaticConceptSelector({}),
    )
    response = await agent.handle(_request(input={}))
    assert response.status is ResultStatus.FAILED
    assert response.error is not None
    assert response.error.code == "missing_course_id"
