"""Mock nested sprint datasets for Student & Project Context tests.

Replaceable later by a shared database or Project Planning provider.
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

PROJECT_ID = "P-CAMPUS"
SPRINT_ID = "sprint-02"

CAMPUS_SPRINT_DATASET = SprintDataset(
    project=ProjectInfo(
        project_id=PROJECT_ID,
        project_name="SELVIA Campus Portal",
        description="A campus portal for student services",
        technology_stack=["Python", "FastAPI", "React", "PostgreSQL"],
    ),
    sprint=SprintInfo(
        sprint_id=SPRINT_ID,
        name="Authentication and Profile Management",
        goal="Implement secure authentication and student profiles",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 19),
        status="active",
    ),
    students=[
        FixtureStudent(student_id="STU-001", name="Student One"),
        FixtureStudent(student_id="STU-002", name="Student Two"),
    ],
    tasks=[
        SprintTask(
            task_id="task-jwt",
            title="Implement JWT Authentication",
            description=(
                "Implement token-based authentication for protected REST API endpoints."
            ),
            status="in_progress",
            priority="high",
            assignee_ids=["STU-001"],
            acceptance_criteria=[
                "Valid credentials produce an access token",
                "Protected endpoints validate tokens",
                "Invalid or expired tokens are rejected",
            ],
            labels=["backend", "authentication"],
            story_points=5,
        ),
        SprintTask(
            task_id="task-profile",
            title="Implement Student Profile API",
            description=(
                "Allow authenticated students to retrieve and update their own profiles."
            ),
            status="todo",
            priority="medium",
            assignee_ids=["STU-001"],
            acceptance_criteria=[
                "Students can retrieve their own profiles",
                "Students can update permitted profile fields",
                "Students cannot modify other students' profiles",
            ],
            labels=["backend", "api"],
            story_points=3,
        ),
        SprintTask(
            task_id="task-dashboard",
            title="Implement Student Dashboard API",
            description=(
                "Return the student's assigned projects and sprint task progress."
            ),
            status="todo",
            priority="medium",
            assignee_ids=["STU-002"],
            acceptance_criteria=[
                "Return the authenticated student's tasks",
                "Include task completion status",
            ],
            labels=["backend", "dashboard"],
            story_points=3,
        ),
    ],
)

CAMPUS_SPRINT_SNAPSHOT = SprintSnapshot.from_dataset(CAMPUS_SPRINT_DATASET)

SPRINT_SNAPSHOTS: dict[tuple[str, str], SprintSnapshot] = {
    (PROJECT_ID, SPRINT_ID): CAMPUS_SPRINT_SNAPSHOT,
}


def make_fixture_sprint_provider():
    """Wire the mock provider to the campus sprint fixtures."""
    from app.agents.adaptive_tutor.context.provider import FixtureSprintDataProvider

    return FixtureSprintDataProvider(SPRINT_SNAPSHOTS)
