"""OpenAI-backed concept selection for Required Knowledge Identification.

Uses the configured OpenAI model with JSON-object responses. Unit tests inject
a fake selector; ordinary tests never call the network.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agents.adaptive_tutor.knowledge.errors import KnowledgeLlmError
from app.agents.adaptive_tutor.schemas import SprintTask, StudentProjectContext
from app.core.config import DEFAULT_OPENAI_MODEL, Settings, settings
from app.knowledge_graph.models import ConceptRecord, CourseKnowledgeBundle

MAX_RETRIES = 2


class LlmSelectionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str = Field(min_length=1)
    selection_role: str = Field(default="directly_required", min_length=1)
    reason: str = Field(min_length=1)


class LlmTaskSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    selected_concepts: list[LlmSelectionItem] = Field(default_factory=list)


class LlmSelectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tasks: list[LlmTaskSelection] = Field(default_factory=list)


class ConceptSelector(Protocol):
    async def select_for_tasks(
        self,
        *,
        context: StudentProjectContext,
        bundle: CourseKnowledgeBundle,
        candidates_by_task: dict[str, list[ConceptRecord]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Return raw selection dicts keyed by task_id."""


class OpenAIConceptSelector:
    """Calls OpenAI Chat Completions with a JSON object response."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        cfg: Settings | None = None,
        client: AsyncOpenAI | None = None,
        timeout_seconds: float = 45.0,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        active = cfg or settings
        self._api_key = api_key if api_key is not None else active.OPENAI_API_KEY
        self._model = model or active.OPENAI_MODEL or DEFAULT_OPENAI_MODEL
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        if client is not None:
            self._client = client
        elif self._api_key:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                timeout=timeout_seconds,
            )
        else:
            self._client = None

    async def select_for_tasks(
        self,
        *,
        context: StudentProjectContext,
        bundle: CourseKnowledgeBundle,
        candidates_by_task: dict[str, list[ConceptRecord]],
    ) -> dict[str, list[dict[str, Any]]]:
        if self._client is None:
            raise KnowledgeLlmError(
                "openai_not_configured",
                "OPENAI_API_KEY is not configured for required-knowledge identification.",
            )

        prompt_payload = _build_prompt_payload(context, bundle, candidates_by_task)
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                content = await self._complete(prompt_payload, attempt=attempt)
                parsed = LlmSelectionResponse.model_validate(json.loads(content))
                return {
                    item.task_id: [
                        selection.model_dump(mode="python")
                        for selection in item.selected_concepts
                    ]
                    for item in parsed.tasks
                }
            except (OpenAIError, TimeoutError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                last_error = exc
                continue

        raise KnowledgeLlmError(
            "openai_selection_failed",
            "OpenAI did not return a valid structured concept selection.",
        ) from last_error

    async def _complete(self, prompt_payload: dict[str, Any], *, attempt: int) -> str:
        assert self._client is not None
        repair = (
            " Previous output was invalid JSON or violated the schema."
            if attempt
            else ""
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You identify software-engineering concepts required for "
                        "student project tasks. Select concept_id values ONLY from "
                        "the supplied candidates. Never invent IDs or learning content. "
                        "Do not estimate competency or choose interventions. "
                        "Return JSON matching the schema."
                        + repair
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt_payload),
                },
            ],
        )
        message = response.choices[0].message.content
        if not isinstance(message, str) or not message.strip():
            raise ValueError("empty OpenAI content")
        return message


class StaticConceptSelector:
    """Deterministic test double returning preconfigured selections."""

    def __init__(self, selections_by_task: dict[str, list[dict[str, Any]]]):
        self._selections = selections_by_task

    async def select_for_tasks(
        self,
        *,
        context: StudentProjectContext,
        bundle: CourseKnowledgeBundle,
        candidates_by_task: dict[str, list[ConceptRecord]],
    ) -> dict[str, list[dict[str, Any]]]:
        return {
            task.task_id: list(self._selections.get(task.task_id, []))
            for task in context.assigned_tasks
        }


def _build_prompt_payload(
    context: StudentProjectContext,
    bundle: CourseKnowledgeBundle,
    candidates_by_task: dict[str, list[ConceptRecord]],
) -> dict[str, Any]:
    return {
        "instructions": {
            "select_only_from_candidates": True,
            "roles": sorted(
                ["directly_required", "prerequisite", "optional_related"]
            ),
            "return_empty_when_insufficient": True,
            "output_schema": {
                "tasks": [
                    {
                        "task_id": "string",
                        "selected_concepts": [
                            {
                                "concept_id": "string",
                                "selection_role": "directly_required|prerequisite|optional_related",
                                "reason": "string",
                            }
                        ],
                    }
                ]
            },
        },
        "course": {
            "course_id": bundle.course_id,
            "course_code": bundle.course_code,
            "course_title": bundle.course_title,
        },
        "student_context": {
            "student_id": context.student_id,
            "project_id": context.project_id,
            "project_title": context.project_title,
            "technology_stack": context.technology_stack,
            "sprint_id": context.sprint_id,
            "sprint_name": context.sprint_name,
            "sprint_goal": context.sprint_goal,
        },
        "tasks": [
            _task_payload(task, candidates_by_task.get(task.task_id, []))
            for task in context.assigned_tasks
        ],
    }


def _task_payload(task: SprintTask, candidates: list[ConceptRecord]) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "title": task.title,
        "description": task.description,
        "acceptance_criteria": task.acceptance_criteria or [],
        "requirements": task.requirements or [],
        "labels": task.labels,
        "priority": task.priority,
        "status": task.status,
        "candidates": [
            {
                "concept_id": concept.concept_id,
                "concept_name": concept.concept_name,
                "concept_code": concept.concept_code,
                "module_title": concept.module_title,
                "topic_title": concept.topic_title,
                "lessons": [
                    {"lesson_id": lesson.lesson_id, "title": lesson.title}
                    for lesson in concept.lessons
                ],
                "prerequisite_concept_ids": concept.prerequisite_concept_ids,
                "related_concept_ids": concept.related_concept_ids,
            }
            for concept in candidates
        ],
    }
