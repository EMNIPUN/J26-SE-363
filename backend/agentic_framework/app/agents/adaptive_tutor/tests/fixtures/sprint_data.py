"""Mock nested sprint dataset for Student & Project Context tests.

Replaceable later by a shared database or Project Planning provider.
This fixture is Sprint 1 of the Ethical Tourism Certification System backend.
"""

from datetime import date

from app.agents.adaptive_tutor.schemas import (
    FixtureStudent,
    ProjectInfo,
    SprintDataset,
    SprintInfo,
    SprintSnapshot,
    SprintTask,
)

# Sprint 01 — Foundation & Architecture (2026-02-08 → 2026-02-21)
ETCS_PROJECT_ID = "P-ETCS"
ETCS_COURSE_ID = "5f7a0677-a957-40dc-bbc7-ce130cf2aab0"
SPRINT_01_ID = "sprint-01"

STUDENT_NIPUN = "36841e50-ac3f-4bf2-952e-08eb4315becd"
STUDENT_SADEESHA = "STU-002"
STUDENT_CHATHUSH = "STU-003"
STUDENT_ERIC = "STU-004"

ETCS_STUDENTS = [
    FixtureStudent(student_id=STUDENT_NIPUN, name="Nipun Dhananjaya"),
    FixtureStudent(student_id=STUDENT_SADEESHA, name="Sadeesha Sathsara"),
    FixtureStudent(student_id=STUDENT_CHATHUSH, name="Chathush Vishmika"),
    FixtureStudent(student_id=STUDENT_ERIC, name="Croos Eric Devon"),
]

ETCS_PROJECT = ProjectInfo(
    project_id=ETCS_PROJECT_ID,
    project_name="Ethical Tourism Certification System Backend",
    course_id=ETCS_COURSE_ID,
    description=(
        "Node.js/Express backend for ethical tourism hotel certification: "
        "JWT auth, certification applications, audit workflows, public search/"
        "discovery, and certificate lifecycle management."
    ),
    technology_stack=[
        "Node.js",
        "Express",
        "MongoDB",
        "Mongoose",
        "JWT",
        "Swagger",
        "SerpAPI",
        "SendGrid",
        "Jest",
        "Vercel",
    ],
)

ETCS_SPRINT_01_DATASET = SprintDataset(
    project=ETCS_PROJECT,
    sprint=SprintInfo(
        sprint_id=SPRINT_01_ID,
        name="Foundation and Backend Architecture",
        goal=(
            "Establish the Express/Mongo feature-module architecture, shared "
            "common utilities, and initial certificate lifecycle API surface."
        ),
        start_date=date(2026, 2, 8),
        end_date=date(2026, 2, 21),
        status="completed",
    ),
    students=ETCS_STUDENTS,
    tasks=[
        SprintTask(
            task_id="task-s1-initial-repo",
            title="Initialize backend repository",
            description=(
                "Create the initial commit and repository baseline for the "
                "ethical tourism certification backend."
            ),
            status="done",
            priority="high",
            assignee_ids=[STUDENT_NIPUN],
            acceptance_criteria=[
                "Repository exists with initial commit",
                "Project can be cloned and opened by the team",
            ],
            labels=["backend", "infrastructure"],
            story_points=2,
        ),
        SprintTask(
            task_id="task-s1-architecture",
            title="Establish feature-based backend architecture",
            description=(
                "Scaffold core modules, common utilities, middleware patterns, "
                "and test infrastructure (Sadeesha: architecture commit 2026-02-08)."
            ),
            status="done",
            priority="high",
            assignee_ids=[STUDENT_NIPUN],
            acceptance_criteria=[
                "common/, modules/, and app entrypoints exist",
                "Shared utilities and middleware layout are in place",
                "Test infrastructure folder structure is ready",
            ],
            labels=["backend", "architecture"],
            story_points=8,
        ),
        SprintTask(
            task_id="task-s1-lifecycle-apis",
            title="Implement initial certificate lifecycle APIs",
            description=(
                "Deliver the first certificate lifecycle endpoints "
                "(Chathush: 'Implemented the lifecycle apis', 2026-02-17)."
            ),
            status="done",
            priority="high",
            assignee_ids=[STUDENT_NIPUN],
            acceptance_criteria=[
                "Lifecycle routes are mounted under /certification",
                "Basic issue/get certificate operations work",
            ],
            labels=["backend", "lifecycle"],
            story_points=5,
        ),
        SprintTask(
            task_id="task-s1-common-models",
            title="Define shared User and Hotel models",
            description=(
                "Place shared Mongoose models in common/models for use across "
                "certification, audit, and search modules."
            ),
            status="done",
            priority="medium",
            assignee_ids=[STUDENT_NIPUN],
            acceptance_criteria=[
                "User model supports Admin, Hotel Owner, Auditor, Tourist roles",
                "Hotel model is reusable across modules",
            ],
            labels=["backend", "models"],
            story_points=5,
        ),
    ],
)

ETCS_SPRINT_01_SNAPSHOT = SprintSnapshot.from_dataset(ETCS_SPRINT_01_DATASET)

# Names imported by the tutor, smoke scripts, and tests. They now refer to Sprint 1.
PROJECT_ID = ETCS_PROJECT_ID
SPRINT_ID = SPRINT_01_ID
COURSE_ID = ETCS_COURSE_ID
STUDENT_ID = STUDENT_NIPUN
PEER_STUDENT_ID = STUDENT_SADEESHA
CAMPUS_SPRINT_DATASET = ETCS_SPRINT_01_DATASET
CAMPUS_SPRINT_SNAPSHOT = ETCS_SPRINT_01_SNAPSHOT

SPRINT_SNAPSHOTS: dict[tuple[str, str], SprintSnapshot] = {
    (PROJECT_ID, SPRINT_ID): ETCS_SPRINT_01_SNAPSHOT,
}


def make_fixture_sprint_provider():
    """Wire the mock provider to the Sprint 1 fixture."""
    from app.agents.adaptive_tutor.context.provider import FixtureSprintDataProvider

    return FixtureSprintDataProvider(SPRINT_SNAPSHOTS)
