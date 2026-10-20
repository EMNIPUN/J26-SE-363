"""Competency estimation pipeline: required concepts + performance evidence → BKT."""

from __future__ import annotations

from collections.abc import Sequence

from shared.contracts import AgentRequest

from app.agents.adaptive_tutor.competency.estimate import estimate_concept_mastery_bkt
from app.agents.adaptive_tutor.competency.params import (
    DEFAULT_BKT_PARAMETERS,
    DEFAULT_CORRECT_THRESHOLD,
)
from app.agents.adaptive_tutor.knowledge import identify_required_knowledge
from app.agents.adaptive_tutor.knowledge.llm_selector import ConceptSelector
from app.agents.adaptive_tutor.schemas import (
    BktCompetencyEstimate,
    BktParameters,
    EstimateCompetencyInput,
    PerformanceEvidenceRecord,
    RequiredKnowledgeResult,
)
from app.agents.adaptive_tutor.context.provider import SprintDataProvider
from app.knowledge_graph.course_repository import CourseKnowledgeRepository
from pydantic import ValidationError


class CompetencyPipelineError(ValueError):
    """Raised when competency estimation cannot be completed."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


async def estimate_competency_for_request(
    request: AgentRequest,
    *,
    sprint_provider: SprintDataProvider,
    course_repository: CourseKnowledgeRepository,
    concept_selector: ConceptSelector,
    performance_records: Sequence[PerformanceEvidenceRecord | dict],
    params: BktParameters | None = None,
    correct_threshold: float = DEFAULT_CORRECT_THRESHOLD,
) -> tuple[list[BktCompetencyEstimate], RequiredKnowledgeResult | None]:
    """Estimate mastery for required (or explicit) concepts using performance evidence."""
    try:
        payload = EstimateCompetencyInput.model_validate(request.input)
    except ValidationError as exc:
        raise CompetencyPipelineError(
            "invalid_input",
            "tutor.estimate_competency input is invalid.",
        ) from exc

    student_id = _require_scope(request.student_id, "student_id")
    knowledge_result: RequiredKnowledgeResult | None = None
    concept_ids = list(payload.concept_ids)

    if not concept_ids:
        # identify_required_knowledge only accepts course_id in input (extra=forbid).
        knowledge_input: dict[str, str] = {}
        if payload.course_id:
            knowledge_input["course_id"] = payload.course_id
        knowledge_request = request.model_copy(update={"input": knowledge_input})
        knowledge_result = await identify_required_knowledge(
            knowledge_request,
            sprint_provider=sprint_provider,
            course_repository=course_repository,
            concept_selector=concept_selector,
        )
        concept_ids = _unique_concept_ids(knowledge_result)
        course_id = knowledge_result.course_id
    else:
        course_id = payload.course_id
        if not course_id:
            # Resolve course from sprint snapshot when concepts were supplied explicitly.
            snapshot = sprint_provider.get_sprint_snapshot(
                _require_scope(request.project_id, "project_id"),
                _require_scope(request.sprint_id, "sprint_id"),
            )
            course_id = snapshot.course_id
        if not course_id or not str(course_id).strip():
            raise CompetencyPipelineError(
                "missing_course_id",
                "course_id is required in input or on the sprint project.",
            )

    records = list(performance_records)
    if payload.performance_evidence:
        records = list(payload.performance_evidence)

    estimates = estimate_concept_mastery_bkt(
        student_id=student_id,
        course_id=str(course_id).strip(),
        concept_ids=concept_ids,
        records=records,
        params=params or DEFAULT_BKT_PARAMETERS,
        correct_threshold=correct_threshold,
    )
    return estimates, knowledge_result


def _unique_concept_ids(knowledge: RequiredKnowledgeResult) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for task in knowledge.tasks:
        for concept in task.required_concepts:
            if concept.concept_id not in seen:
                seen.add(concept.concept_id)
                ordered.append(concept.concept_id)
    return ordered


def _require_scope(value: str | None, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CompetencyPipelineError(
            f"missing_{field_name}",
            f"{field_name} is required for competency estimation.",
        )
    return value.strip()
