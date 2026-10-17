"""Typed errors for Neo4j course knowledge graph access."""


class KnowledgeGraphError(Exception):
    """Base error for knowledge-graph operations."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class KnowledgeGraphConfigError(KnowledgeGraphError):
    """Neo4j settings are missing or invalid."""

    def __init__(self, message: str):
        super().__init__("neo4j_not_configured", message)


class KnowledgeGraphQueryError(KnowledgeGraphError):
    """A Neo4j query failed or returned an unexpected shape."""

    def __init__(self, message: str):
        super().__init__("neo4j_query_failed", message)


class UnknownCourseError(KnowledgeGraphError):
    """No Course node exists for the given course id."""

    def __init__(self, course_id: str):
        super().__init__(
            "unknown_course",
            f"No course exists for course_id={course_id!r}.",
        )
        self.course_id = course_id
