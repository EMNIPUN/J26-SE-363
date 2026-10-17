"""Validate LLM concept selections against Neo4j candidate records."""

from __future__ import annotations

from app.agents.adaptive_tutor.knowledge.errors import KnowledgeValidationError
from app.agents.adaptive_tutor.schemas import (
    SelectedRequiredConcept,
    TaskRequiredKnowledge,
)
from app.knowledge_graph.models import ConceptRecord

ALLOWED_SELECTION_ROLES = frozenset(
    {"directly_required", "prerequisite", "optional_related"}
)


def validate_task_selections(
    *,
    task_id: str,
    task_title: str | None,
    raw_selections: list[dict],
    candidates: list[ConceptRecord],
    course_concept_ids: set[str],
) -> TaskRequiredKnowledge:
    """Validate one task's LLM selections; raise on invented or out-of-scope IDs."""
    if not isinstance(raw_selections, list):
        raise KnowledgeValidationError(
            f"LLM selections for task {task_id!r} must be a list."
        )

    by_id = {concept.concept_id: concept for concept in candidates}
    candidate_ids = set(by_id)
    seen: set[str] = set()
    validated: list[SelectedRequiredConcept] = []

    for index, item in enumerate(raw_selections):
        if not isinstance(item, dict):
            raise KnowledgeValidationError(
                f"Selection at index {index} for task {task_id!r} must be an object."
            )
        concept_id = item.get("concept_id")
        if not isinstance(concept_id, str) or not concept_id.strip():
            raise KnowledgeValidationError(
                f"Selection at index {index} for task {task_id!r} is missing concept_id."
            )
        concept_id = concept_id.strip()
        if concept_id in seen:
            continue
        if concept_id not in candidate_ids:
            if concept_id not in course_concept_ids:
                raise KnowledgeValidationError(
                    f"Concept {concept_id!r} is not in the resolved course catalogue."
                )
            raise KnowledgeValidationError(
                f"Concept {concept_id!r} was not in the candidate set for task {task_id!r}."
            )

        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise KnowledgeValidationError(
                f"Selection for concept {concept_id!r} is missing a reason."
            )
        role = item.get("selection_role") or "directly_required"
        if not isinstance(role, str) or role.strip() not in ALLOWED_SELECTION_ROLES:
            raise KnowledgeValidationError(
                f"Selection for concept {concept_id!r} has an invalid selection_role."
            )

        concept = by_id[concept_id]
        lesson_ids = [
            lesson.lesson_id for lesson in concept.lessons if lesson.lesson_id
        ]
        validated.append(
            SelectedRequiredConcept(
                concept_id=concept.concept_id,
                concept_name=concept.concept_name,
                concept_code=concept.concept_code,
                selection_role=role.strip(),
                reason=reason.strip(),
                source_lesson_ids=lesson_ids,
                provenance=["neo4j_course_graph", "llm_selection"],
            )
        )
        seen.add(concept_id)

    return TaskRequiredKnowledge(
        task_id=task_id,
        task_title=task_title,
        required_concepts=validated,
    )
