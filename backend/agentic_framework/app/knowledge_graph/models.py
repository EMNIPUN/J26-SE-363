"""Course knowledge graph DTOs (Neo4j-backed)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GraphModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LessonRecord(GraphModel):
    lesson_id: str = Field(min_length=1)
    title: str | None = None


class ConceptRelationship(GraphModel):
    """Directed relationship between concepts within the same course."""

    from_concept_id: str = Field(min_length=1)
    to_concept_id: str = Field(min_length=1)
    relationship_type: str = Field(min_length=1)


class ConceptRecord(GraphModel):
    concept_id: str = Field(min_length=1)
    concept_name: str | None = None
    concept_code: str | None = None
    module_id: str | None = None
    module_title: str | None = None
    topic_id: str | None = None
    topic_title: str | None = None
    lessons: list[LessonRecord] = Field(default_factory=list)
    prerequisite_concept_ids: list[str] = Field(default_factory=list)
    related_concept_ids: list[str] = Field(default_factory=list)


class CourseKnowledgeBundle(GraphModel):
    """All course-scoped concepts retrieved for required-knowledge identification."""

    course_id: str = Field(min_length=1)
    course_code: str | None = None
    course_title: str | None = None
    concepts: list[ConceptRecord] = Field(default_factory=list)
    relationships: list[ConceptRelationship] = Field(default_factory=list)
