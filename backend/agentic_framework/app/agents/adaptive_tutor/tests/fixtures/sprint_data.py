"""Mock sprint snapshots for Student & Project Context tests.

Replaceable later by a shared database or Project Planning provider.
"""

from datetime import date

from app.agents.adaptive_tutor.schemas import SprintSnapshot, SprintTask

PROJECT_ID = "P-CAMPUS"
SPRINT_ID = "sprint-02"

CAMPUS_SPRINT_SNAPSHOT = SprintSnapshot(
    project_id=PROJECT_ID,
    project_title="SELVIA Campus Portal (sample)",
    sprint_id=SPRINT_ID,
    sprint_name="Sprint 2 — Access control",
    sprint_number=2,
    start_date=date(2026, 10, 1),
    end_date=date(2026, 10, 14),
    tasks=[
        SprintTask(
            task_id="task-jwt",
            title="Implement JWT authentication",
            sprint_id=SPRINT_ID,
            assignee_ids=["STU-001"],
            description=None,  # optional metadata intentionally missing
            requirements=[
                "Sign-in returns a signed JWT.",
                "Protected routes reject a missing or expired token.",
            ],
            acceptance_criteria=[
                "A valid token reaches a protected endpoint.",
                "An expired token returns 401.",
            ],
            concept_ids=["concept-rest", "concept-auth", "concept-jwt"],
            status="In progress",
        ),
        SprintTask(
            task_id="task-profile",
            title="Build the student profile API",
            sprint_id=SPRINT_ID,
            assignee_ids=["STU-001"],
            description=(
                "Expose the signed-in student profile after authentication, "
                "without returning secrets."
            ),
            requirements=[
                "GET /me returns the signed-in profile.",
                "The response never includes a password hash.",
            ],
            acceptance_criteria=[
                "The JSON matches the profile contract.",
                "Secrets are absent from the payload.",
            ],
            concept_ids=["concept-rest", "concept-resource"],
            status="Not started",
        ),
        SprintTask(
            task_id="task-dashboard",
            title="Student dashboard widgets",
            sprint_id=SPRINT_ID,
            assignee_ids=["STU-002"],
            description="Show sprint progress widgets for the signed-in student.",
            requirements=["Widgets load for enrolled students only."],
            acceptance_criteria=["Unauthenticated requests receive 401."],
            concept_ids=["concept-rest"],
            status="Not started",
        ),
        SprintTask(
            task_id="task-admin-roles",
            title="Lecturer role guards",
            sprint_id=SPRINT_ID,
            assignee_ids=["STU-003"],
            description="Restrict lecturer routes using a role claim.",
            requirements=["A student token cannot open lecturer routes."],
            acceptance_criteria=["Forbidden access returns 403."],
            concept_ids=["concept-authz"],
            status="Not started",
        ),
        SprintTask(
            task_id="task-unassigned",
            title="Spike: refresh-token rotation",
            sprint_id=SPRINT_ID,
            assignee_ids=[],
            description="Investigate refresh-token rotation options.",
            requirements=None,
            acceptance_criteria=None,
            concept_ids=None,
            status="Backlog",
        ),
    ],
)

SPRINT_SNAPSHOTS: dict[tuple[str, str], SprintSnapshot] = {
    (PROJECT_ID, SPRINT_ID): CAMPUS_SPRINT_SNAPSHOT,
}


def make_fixture_sprint_provider():
    """Wire the mock provider to the campus sprint fixtures."""
    from app.agents.adaptive_tutor.context.provider import FixtureSprintDataProvider

    return FixtureSprintDataProvider(SPRINT_SNAPSHOTS)
