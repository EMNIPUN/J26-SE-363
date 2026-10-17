"""Course-scoped concept retrieval from Neo4j.

Verified live schema (Aura):
  (:Course)-[:HAS_MODULE]->(:Module)-[:HAS_TOPIC]->(:Topic)
    -[:HAS_CONCEPT]->(:Concept)-[:HAS_LESSON]->(:Lesson)

Optional concept-concept relationships (PREREQUISITE_OF, REQUIRES, RELATED_TO)
are queried when present; the current seed graph does not include them yet.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.core.config import Settings, settings
from app.knowledge_graph.client import run_read_query
from app.knowledge_graph.errors import UnknownCourseError
from app.knowledge_graph.models import (
    ConceptRecord,
    ConceptRelationship,
    CourseKnowledgeBundle,
    LessonRecord,
)

# Bounded retrieval defaults (prevent unbounded expansion).
DEFAULT_CONCEPT_LIMIT = 200
DEFAULT_PREREQ_DEPTH = 2
DEFAULT_RELATED_LIMIT = 50

COURSE_EXISTS_CYPHER = """
MATCH (c:Course {id: $course_id})
RETURN c.id AS course_id, c.code AS course_code, c.title AS course_title
LIMIT 1
"""

COURSE_CONCEPTS_CYPHER = """
MATCH (c:Course {id: $course_id})-[:HAS_MODULE]->(m:Module)
      -[:HAS_TOPIC]->(t:Topic)-[:HAS_CONCEPT]->(n:Concept)
OPTIONAL MATCH (n)-[:HAS_LESSON]->(l:Lesson)
WITH c, m, t, n, collect(DISTINCT l) AS lesson_nodes
RETURN
  c.id AS course_id,
  c.code AS course_code,
  c.title AS course_title,
  n.id AS concept_id,
  n.name AS concept_name,
  n.code AS concept_code,
  m.id AS module_id,
  m.title AS module_title,
  t.id AS topic_id,
  t.title AS topic_title,
  [x IN lesson_nodes WHERE x IS NOT NULL | {lesson_id: x.id, title: x.title}] AS lessons
ORDER BY coalesce(n.code, n.name, n.id)
LIMIT $concept_limit
"""

# Optional edges: only match if they exist in the graph.
CONCEPT_RELATIONSHIPS_CYPHER = """
MATCH (c:Course {id: $course_id})-[:HAS_MODULE]->(:Module)
      -[:HAS_TOPIC]->(:Topic)-[:HAS_CONCEPT]->(a:Concept)
MATCH (a)-[r:PREREQUISITE_OF|REQUIRES|RELATED_TO]->(b:Concept)
MATCH (c)-[:HAS_MODULE]->(:Module)-[:HAS_TOPIC]->(:Topic)-[:HAS_CONCEPT]->(b)
RETURN DISTINCT
  a.id AS from_concept_id,
  b.id AS to_concept_id,
  type(r) AS relationship_type
LIMIT $relationship_limit
"""


class CourseKnowledgeRepository(Protocol):
    def get_course_knowledge(self, course_id: str) -> CourseKnowledgeBundle:
        """Return course-scoped concepts, lessons, and optional relationships."""


class Neo4jCourseKnowledgeRepository:
    """Reads course knowledge using parameterized Cypher against the shared driver."""

    def __init__(
        self,
        *,
        cfg: Settings | None = None,
        concept_limit: int = DEFAULT_CONCEPT_LIMIT,
        relationship_limit: int = DEFAULT_RELATED_LIMIT,
        prereq_depth: int = DEFAULT_PREREQ_DEPTH,
    ) -> None:
        self._cfg = cfg or settings
        self._concept_limit = concept_limit
        self._relationship_limit = relationship_limit
        self._prereq_depth = prereq_depth

    def get_course_knowledge(self, course_id: str) -> CourseKnowledgeBundle:
        if not isinstance(course_id, str) or not course_id.strip():
            raise UnknownCourseError(course_id if isinstance(course_id, str) else "")

        resolved_id = course_id.strip()
        course_rows = run_read_query(
            COURSE_EXISTS_CYPHER,
            {"course_id": resolved_id},
            cfg=self._cfg,
        )
        if not course_rows:
            raise UnknownCourseError(resolved_id)

        concept_rows = run_read_query(
            COURSE_CONCEPTS_CYPHER,
            {
                "course_id": resolved_id,
                "concept_limit": self._concept_limit,
            },
            cfg=self._cfg,
        )
        relationship_rows = run_read_query(
            CONCEPT_RELATIONSHIPS_CYPHER,
            {
                "course_id": resolved_id,
                "relationship_limit": self._relationship_limit,
            },
            cfg=self._cfg,
        )

        return self._assemble_bundle(
            course_meta=course_rows[0],
            concept_rows=concept_rows,
            relationship_rows=relationship_rows,
        )

    def _assemble_bundle(
        self,
        *,
        course_meta: dict[str, Any],
        concept_rows: list[dict[str, Any]],
        relationship_rows: list[dict[str, Any]],
    ) -> CourseKnowledgeBundle:
        prereq_map: dict[str, list[str]] = {}
        related_map: dict[str, list[str]] = {}
        relationships: list[ConceptRelationship] = []

        for row in relationship_rows:
            from_id = row.get("from_concept_id")
            to_id = row.get("to_concept_id")
            rel_type = row.get("relationship_type")
            if not from_id or not to_id or not rel_type:
                continue
            relationships.append(
                ConceptRelationship(
                    from_concept_id=str(from_id),
                    to_concept_id=str(to_id),
                    relationship_type=str(rel_type),
                )
            )
            if rel_type in {"PREREQUISITE_OF", "REQUIRES"}:
                prereq_map.setdefault(str(from_id), []).append(str(to_id))
            elif rel_type == "RELATED_TO":
                related_map.setdefault(str(from_id), []).append(str(to_id))

        concepts: list[ConceptRecord] = []
        for row in concept_rows:
            concept_id = row.get("concept_id")
            if not concept_id:
                continue
            cid = str(concept_id)
            lessons_raw = row.get("lessons") or []
            lessons: list[LessonRecord] = []
            for item in lessons_raw:
                if not isinstance(item, dict):
                    continue
                lesson_id = item.get("lesson_id")
                if not lesson_id:
                    continue
                lessons.append(
                    LessonRecord(
                        lesson_id=str(lesson_id),
                        title=item.get("title"),
                    )
                )
            concepts.append(
                ConceptRecord(
                    concept_id=cid,
                    concept_name=row.get("concept_name"),
                    concept_code=row.get("concept_code"),
                    module_id=_optional_str(row.get("module_id")),
                    module_title=row.get("module_title"),
                    topic_id=_optional_str(row.get("topic_id")),
                    topic_title=row.get("topic_title"),
                    lessons=lessons,
                    prerequisite_concept_ids=_dedupe(prereq_map.get(cid, [])),
                    related_concept_ids=_dedupe(related_map.get(cid, [])),
                )
            )

        return CourseKnowledgeBundle(
            course_id=str(course_meta["course_id"]),
            course_code=_optional_str(course_meta.get("course_code")),
            course_title=_optional_str(course_meta.get("course_title")),
            concepts=concepts,
            relationships=relationships,
        )


class InMemoryCourseKnowledgeRepository:
    """Test double that returns a preloaded bundle for one or more courses."""

    def __init__(self, bundles: dict[str, CourseKnowledgeBundle]):
        self._bundles = bundles

    def get_course_knowledge(self, course_id: str) -> CourseKnowledgeBundle:
        if not isinstance(course_id, str) or not course_id.strip():
            raise UnknownCourseError(course_id if isinstance(course_id, str) else "")
        key = course_id.strip()
        bundle = self._bundles.get(key)
        if bundle is None:
            raise UnknownCourseError(key)
        return bundle


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
