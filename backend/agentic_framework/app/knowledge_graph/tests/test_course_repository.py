"""Unit tests for Neo4j course repository with mocked query execution."""

from __future__ import annotations

import pytest

from app.knowledge_graph.course_repository import Neo4jCourseKnowledgeRepository
from app.knowledge_graph.errors import UnknownCourseError


def test_neo4j_repository_assembles_course_scoped_concepts(monkeypatch):
    rows_by_query = {
        "exists": [
            {
                "course_id": "course-1",
                "course_code": "SE3020",
                "course_title": "Secure Web",
            }
        ],
        "concepts": [
            {
                "course_id": "course-1",
                "course_code": "SE3020",
                "course_title": "Secure Web",
                "concept_id": "c1",
                "concept_name": "Auth",
                "concept_code": "AUTH",
                "module_id": "m1",
                "module_title": "Security",
                "topic_id": "t1",
                "topic_title": "Auth topic",
                "lessons": [{"lesson_id": "l1", "title": "Intro"}],
            },
            {
                "course_id": "course-1",
                "course_code": "SE3020",
                "course_title": "Secure Web",
                "concept_id": "c2",
                "concept_name": None,
                "concept_code": None,
                "module_id": None,
                "module_title": None,
                "topic_id": None,
                "topic_title": None,
                "lessons": [],
            },
        ],
        "rels": [
            {
                "from_concept_id": "c1",
                "to_concept_id": "c2",
                "relationship_type": "PREREQUISITE_OF",
            }
        ],
    }

    def fake_run(cypher, parameters=None, cfg=None):
        if "RETURN c.id AS course_id, c.code AS course_code" in cypher and "HAS_MODULE" not in cypher:
            return rows_by_query["exists"]
        if "HAS_CONCEPT" in cypher and "PREREQUISITE_OF" not in cypher:
            assert parameters["course_id"] == "course-1"
            return rows_by_query["concepts"]
        return rows_by_query["rels"]

    monkeypatch.setattr(
        "app.knowledge_graph.course_repository.run_read_query",
        fake_run,
    )

    repo = Neo4jCourseKnowledgeRepository()
    bundle = repo.get_course_knowledge("course-1")

    assert bundle.course_id == "course-1"
    assert len(bundle.concepts) == 2
    assert bundle.concepts[0].lessons[0].lesson_id == "l1"
    assert bundle.concepts[0].prerequisite_concept_ids == ["c2"]
    assert bundle.concepts[1].concept_name is None


def test_neo4j_repository_unknown_course(monkeypatch):
    monkeypatch.setattr(
        "app.knowledge_graph.course_repository.run_read_query",
        lambda *args, **kwargs: [],
    )
    repo = Neo4jCourseKnowledgeRepository()
    with pytest.raises(UnknownCourseError):
        repo.get_course_knowledge("missing")
