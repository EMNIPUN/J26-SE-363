"""Required Knowledge Identification pipeline for the Adaptive AI Tutor."""

from __future__ import annotations

from shared.contracts import AgentRequest

from app.agents.adaptive_tutor.context.builder import (
    ContextBuildError,
    build_student_project_context,
)
from app.agents.adaptive_tutor.context.provider import (
    SprintDataProvider,
    SprintDataProviderError,
)
from app.agents.adaptive_tutor.knowledge.candidates import select_candidates_for_task
from app.agents.adaptive_tutor.knowledge.errors import (
    KnowledgeIdentificationError,
    KnowledgeLlmError,
    KnowledgeValidationError,
    MissingCourseIdError,
)
from app.agents.adaptive_tutor.knowledge.llm_selector import ConceptSelector
from app.agents.adaptive_tutor.knowledge.validate import validate_task_selections
from app.agents.adaptive_tutor.schemas import (
    IdentifyRequiredKnowledgeInput,
    RequiredKnowledgeResult,
    TaskRequiredKnowledge,
)
from app.knowledge_graph.course_repository import CourseKnowledgeRepository
from app.knowledge_graph.errors import (
    KnowledgeGraphConfigError,
    KnowledgeGraphError,
    KnowledgeGraphQueryError,
    UnknownCourseError,
)
from app.knowledge_graph.models import ConceptRecord
from pydantic import ValidationError


async def identify_required_knowledge(
    request: AgentRequest,
    *,
    sprint_provider: SprintDataProvider,
    course_repository: CourseKnowledgeRepository,
    concept_selector: ConceptSelector,
) -> RequiredKnowledgeResult:
    """Map the requesting student's assigned tasks to Neo4j course concepts."""
    try:
        knowledge_input = IdentifyRequiredKnowledgeInput.model_validate(request.input)
    except ValidationError as exc:
        raise MissingCourseIdError(
            "tutor.identify_required_knowledge requires a non-empty course_id in input."
        ) from exc

    try:
        snapshot = sprint_provider.get_sprint_snapshot(
            _require_request_id(request.project_id, "project_id"),
            _require_request_id(request.sprint_id, "sprint_id"),
        )
        context = build_student_project_context(request, snapshot)
    except ContextBuildError:
        raise
    except SprintDataProviderError:
        raise

    try:
        bundle = course_repository.get_course_knowledge(knowledge_input.course_id)
    except UnknownCourseError:
        raise
    except KnowledgeGraphConfigError:
        raise
    except KnowledgeGraphQueryError:
        raise
    except KnowledgeGraphError:
        raise

    course_concept_ids = {concept.concept_id for concept in bundle.concepts}
    candidates_by_task: dict[str, list[ConceptRecord]] = {}
    for task in context.assigned_tasks:
        candidates_by_task[task.task_id] = select_candidates_for_task(
            task,
            bundle,
            technology_stack=context.technology_stack,
        )

    try:
        raw_by_task = await concept_selector.select_for_tasks(
            context=context,
            bundle=bundle,
            candidates_by_task=candidates_by_task,
        )
    except KnowledgeLlmError:
        raise

    if set(raw_by_task) - {task.task_id for task in context.assigned_tasks}:
        raise KnowledgeValidationError(
            "LLM returned selections for a task that is not in the student context."
        )

    task_results: list[TaskRequiredKnowledge] = []
    for task in context.assigned_tasks:
        raw_selections = raw_by_task.get(task.task_id, [])
        task_results.append(
            validate_task_selections(
                task_id=task.task_id,
                task_title=task.title,
                raw_selections=raw_selections,
                candidates=candidates_by_task.get(task.task_id, []),
                course_concept_ids=course_concept_ids,
            )
        )

    return RequiredKnowledgeResult(
        student_id=context.student_id,
        project_id=context.project_id,
        sprint_id=context.sprint_id,
        course_id=bundle.course_id,
        course_code=bundle.course_code,
        course_title=bundle.course_title,
        tasks=task_results,
    )


def _require_request_id(value: str | None, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextBuildError(
            f"missing_{field_name}",
            f"{field_name} is required for required-knowledge identification.",
        )
    return value.strip()


# Re-export for callers that map error codes.
__all__ = [
    "identify_required_knowledge",
    "KnowledgeIdentificationError",
    "MissingCourseIdError",
    "KnowledgeLlmError",
    "KnowledgeValidationError",
]
