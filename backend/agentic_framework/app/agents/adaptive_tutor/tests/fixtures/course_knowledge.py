"""In-memory Neo4j course knowledge fixtures for Required Knowledge tests."""

from app.knowledge_graph.models import (
    ConceptRecord,
    ConceptRelationship,
    CourseKnowledgeBundle,
    LessonRecord,
)

COURSE_ID = "b5a46382-0d6a-4035-a924-0f5efa654796"
OTHER_COURSE_ID = "course-other-999"

AUTH_CONCEPT_ID = "6e1db9cc-f661-44d6-84c8-65f1020ae24a"
JWT_CONCEPT_ID = "concept-jwt-fixture"
REST_CONCEPT_ID = "concept-rest-fixture"
UNRELATED_CONCEPT_ID = "concept-unrelated-db"


def make_course_bundle() -> CourseKnowledgeBundle:
    return CourseKnowledgeBundle(
        course_id=COURSE_ID,
        course_code="SE3020",
        course_title="Software Engineering and Secure Web Development",
        concepts=[
            ConceptRecord(
                concept_id=AUTH_CONCEPT_ID,
                concept_name="Web Authentication Fundamentals",
                concept_code="SE3020-AUTH",
                module_id="mod-auth",
                module_title="Web Application Security and Authentication",
                topic_id="topic-auth",
                topic_title="Authentication Fundamentals",
                lessons=[
                    LessonRecord(
                        lesson_id="lesson-auth-intro",
                        title="Introduction to Web Authentication",
                    )
                ],
                prerequisite_concept_ids=[REST_CONCEPT_ID],
                related_concept_ids=[JWT_CONCEPT_ID],
            ),
            ConceptRecord(
                concept_id=JWT_CONCEPT_ID,
                concept_name="JWT Access Tokens",
                concept_code="SE3020-JWT",
                module_id="mod-auth",
                module_title="Web Application Security and Authentication",
                topic_id="topic-jwt",
                topic_title="Token-based Authentication",
                lessons=[
                    LessonRecord(
                        lesson_id="lesson-jwt",
                        title="Signing and validating JWT access tokens",
                    )
                ],
                prerequisite_concept_ids=[AUTH_CONCEPT_ID],
            ),
            ConceptRecord(
                concept_id=REST_CONCEPT_ID,
                concept_name="REST API Basics",
                concept_code="SE3020-REST",
                module_title="API Design",
                topic_title="REST Resources",
                lessons=[],
            ),
            ConceptRecord(
                concept_id=UNRELATED_CONCEPT_ID,
                concept_name="Relational Database Normalisation",
                concept_code="SE3020-DB",
                module_title="Data Persistence",
                topic_title="Normalisation",
                lessons=[],
            ),
            ConceptRecord(
                concept_id="concept-missing-description",
                concept_name=None,
                concept_code=None,
                module_title=None,
                topic_title=None,
                lessons=[],
            ),
        ],
        relationships=[
            ConceptRelationship(
                from_concept_id=AUTH_CONCEPT_ID,
                to_concept_id=REST_CONCEPT_ID,
                relationship_type="PREREQUISITE_OF",
            ),
            ConceptRelationship(
                from_concept_id=JWT_CONCEPT_ID,
                to_concept_id=AUTH_CONCEPT_ID,
                relationship_type="REQUIRES",
            ),
            ConceptRelationship(
                from_concept_id=AUTH_CONCEPT_ID,
                to_concept_id=JWT_CONCEPT_ID,
                relationship_type="RELATED_TO",
            ),
        ],
    )


def make_empty_course_bundle() -> CourseKnowledgeBundle:
    return CourseKnowledgeBundle(
        course_id=COURSE_ID,
        course_code="SE3020",
        course_title="Software Engineering and Secure Web Development",
        concepts=[],
        relationships=[],
    )


OTHER_COURSE_BUNDLE = CourseKnowledgeBundle(
    course_id=OTHER_COURSE_ID,
    course_code="OTHER",
    course_title="Unrelated Course",
    concepts=[
        ConceptRecord(
            concept_id="other-course-concept",
            concept_name="Other Course Only Concept",
            concept_code="OTHER-1",
        )
    ],
)
