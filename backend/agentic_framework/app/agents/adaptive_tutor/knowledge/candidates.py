"""Baseline candidate selector for Required Knowledge Identification.

This is NOT vector RAG. No embedding model or Neo4j vector index exists in the
repository yet. Candidates are scored with bounded lexical overlap against task
text, then expanded through optional in-course graph relationships.

A future SemanticCandidateSelector can replace or wrap this without changing
the identify pipeline contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.agents.adaptive_tutor.schemas import SprintTask
from app.knowledge_graph.models import ConceptRecord, CourseKnowledgeBundle

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
DEFAULT_CANDIDATE_LIMIT = 25


@dataclass(frozen=True)
class ScoredCandidate:
    concept: ConceptRecord
    score: float
    provenance: tuple[str, ...]


def select_candidates_for_task(
    task: SprintTask,
    bundle: CourseKnowledgeBundle,
    *,
    technology_stack: list[str] | None = None,
    limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> list[ConceptRecord]:
    """Return a bounded, deduplicated candidate set for one task."""
    if not bundle.concepts:
        return []

    task_tokens = _tokenize(_task_text(task, technology_stack or []))
    scored: list[ScoredCandidate] = []
    for concept in bundle.concepts:
        score, provenance = _score_concept(concept, task_tokens)
        scored.append(
            ScoredCandidate(concept=concept, score=score, provenance=tuple(provenance))
        )

    scored.sort(
        key=lambda item: (
            -item.score,
            item.concept.concept_code or "",
            item.concept.concept_id,
        )
    )

    # Always keep a floor of top lexical hits; include zero-score concepts only
    # when the course is tiny so the LLM still has something to reject.
    selected: list[ConceptRecord] = []
    selected_ids: set[str] = set()
    for item in scored:
        if len(selected) >= limit:
            break
        if item.score <= 0 and len(bundle.concepts) > limit:
            continue
        selected.append(item.concept)
        selected_ids.add(item.concept.concept_id)

    # Graph expansion: prerequisites / related of selected concepts (same course).
    by_id = {c.concept_id: c for c in bundle.concepts}
    expansion: list[ConceptRecord] = []
    for concept in list(selected):
        for related_id in (
            *concept.prerequisite_concept_ids,
            *concept.related_concept_ids,
        ):
            if related_id in selected_ids:
                continue
            related = by_id.get(related_id)
            if related is None:
                continue
            expansion.append(related)
            selected_ids.add(related_id)
            if len(selected) + len(expansion) >= limit:
                break
        if len(selected) + len(expansion) >= limit:
            break

    combined = selected + expansion
    return combined[:limit]


def _task_text(task: SprintTask, technology_stack: list[str]) -> str:
    parts = [
        task.title or "",
        task.description or "",
        " ".join(task.acceptance_criteria or []),
        " ".join(task.requirements or []),
        " ".join(task.labels or []),
        task.priority or "",
        " ".join(technology_stack),
    ]
    return " ".join(parts)


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _score_concept(
    concept: ConceptRecord,
    task_tokens: set[str],
) -> tuple[float, list[str]]:
    if not task_tokens:
        return 0.0, ["course_catalogue"]

    fields = {
        "concept_name": concept.concept_name or "",
        "concept_code": concept.concept_code or "",
        "topic_title": concept.topic_title or "",
        "module_title": concept.module_title or "",
        "lesson_titles": " ".join(
            lesson.title or "" for lesson in concept.lessons
        ),
    }
    score = 0.0
    provenance = ["course_catalogue"]
    for field_name, value in fields.items():
        tokens = _tokenize(value)
        overlap = task_tokens & tokens
        if not overlap:
            continue
        weight = 3.0 if field_name == "concept_name" else 1.5 if field_name == "concept_code" else 1.0
        score += weight * len(overlap)
        provenance.append(f"lexical:{field_name}")
    return score, provenance
