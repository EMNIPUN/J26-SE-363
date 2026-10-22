import pytest
from pydantic import ValidationError
from shared.contracts import (
    AgentRequest,
    ProjectContext,
    SelviaContext,
    SprintContext,
    StudentContext,
    TaskContext,
)

from app.agents.adaptive_tutor.context import (
    ContextBuildError,
    build_student_project_context,
)
from app.agents.adaptive_tutor.context.provider import SprintDataProviderError
from app.agents.adaptive_tutor.tests.fixtures.sprint_data import (
    CAMPUS_SPRINT_DATASET,
    CAMPUS_SPRINT_SNAPSHOT,
    COURSE_ID,
    PEER_STUDENT_ID,
    PROJECT_ID,
    SPRINT_ID,
    STUDENT_ID,
    make_fixture_sprint_provider,
)


def _request(**overrides) -> AgentRequest:
    fields = {
        "action": "tutor.sprint_guidance",
        "student_id": STUDENT_ID,
        "project_id": PROJECT_ID,
        "sprint_id": SPRINT_ID,
    }
    fields.update(overrides)
    return AgentRequest(**fields)


def test_stu001_receives_assigned_sprint_tasks():
    context = build_student_project_context(_request(), CAMPUS_SPRINT_SNAPSHOT)

    assert context.student_id == STUDENT_ID
    assert context.project_id == PROJECT_ID
    assert context.sprint_id == SPRINT_ID
    assert [task.task_id for task in context.assigned_tasks] == [
        "task-s1-initial-repo",
        "task-s1-architecture",
        "task-s1-lifecycle-apis",
        "task-s1-common-models",
    ]


def test_peer_student_has_no_assigned_tasks():
    context = build_student_project_context(
        _request(student_id=PEER_STUDENT_ID),
        CAMPUS_SPRINT_SNAPSHOT,
    )

    assert context.assigned_tasks == []


def test_nested_dataset_exposes_project_sprint_and_students():
    assert CAMPUS_SPRINT_DATASET.project.project_id == PROJECT_ID
    assert CAMPUS_SPRINT_DATASET.project.course_id == COURSE_ID
    assert CAMPUS_SPRINT_DATASET.project.technology_stack == [
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
    ]
    assert CAMPUS_SPRINT_SNAPSHOT.course_id == CAMPUS_SPRINT_DATASET.project.course_id
    assert CAMPUS_SPRINT_DATASET.sprint.goal is not None
    assert [student.student_id for student in CAMPUS_SPRINT_DATASET.students] == [
        STUDENT_ID,
        PEER_STUDENT_ID,
        "STU-003",
        "STU-004",
    ]


def test_snapshot_inherits_sprint_id_on_tasks():
    assert all(task.sprint_id == SPRINT_ID for task in CAMPUS_SPRINT_SNAPSHOT.tasks)


def test_missing_student_id_is_rejected():
    request = _request(student_id=None)

    with pytest.raises(ContextBuildError) as exc_info:
        build_student_project_context(request, CAMPUS_SPRINT_SNAPSHOT)

    assert exc_info.value.code == "missing_student_id"


def test_blank_student_id_is_rejected():
    with pytest.raises(ContextBuildError) as exc_info:
        build_student_project_context(_request(student_id="   "), CAMPUS_SPRINT_SNAPSHOT)

    assert exc_info.value.code == "missing_student_id"


def test_project_id_mismatch_is_rejected():
    with pytest.raises(ContextBuildError) as exc_info:
        build_student_project_context(
            _request(project_id="P-OTHER"),
            CAMPUS_SPRINT_SNAPSHOT,
        )

    assert exc_info.value.code == "project_id_mismatch"


def test_sprint_id_mismatch_is_rejected():
    with pytest.raises(ContextBuildError) as exc_info:
        build_student_project_context(
            _request(sprint_id="sprint-99"),
            CAMPUS_SPRINT_SNAPSHOT,
        )

    assert exc_info.value.code == "sprint_id_mismatch"


def test_conflicting_nested_context_ids_are_rejected_by_shared_rules():
    with pytest.raises(ValidationError, match="student_id"):
        AgentRequest(
            action="tutor.sprint_guidance",
            student_id=STUDENT_ID,
            project_id=PROJECT_ID,
            sprint_id=SPRINT_ID,
            context=SelviaContext(student=StudentContext(student_id="STU-002")),
        )


def test_conflicting_nested_task_id_is_rejected_by_shared_rules():
    with pytest.raises(ValidationError, match="task_id"):
        AgentRequest(
            action="tutor.sprint_guidance",
            student_id=STUDENT_ID,
            project_id=PROJECT_ID,
            sprint_id=SPRINT_ID,
            task_id="task-jwt",
            context=SelviaContext(task=TaskContext(task_id="task-profile")),
        )


def test_task_metadata_from_nested_dataset_is_preserved():
    context = build_student_project_context(_request(), CAMPUS_SPRINT_SNAPSHOT)
    repo_task = next(
        task for task in context.assigned_tasks if task.task_id == "task-s1-initial-repo"
    )

    assert repo_task.description is not None
    assert repo_task.priority == "high"
    assert repo_task.story_points == 2
    assert repo_task.labels == ["backend", "infrastructure"]
    assert repo_task.acceptance_criteria is not None


def test_unknown_project_sprint_is_rejected_by_fixture_provider():
    provider = make_fixture_sprint_provider()

    with pytest.raises(SprintDataProviderError) as exc_info:
        provider.get_sprint_snapshot("P-UNKNOWN", SPRINT_ID)

    assert exc_info.value.code == "unknown_sprint"


def test_valid_sprint_with_no_tasks_for_student_returns_empty_list():
    context = build_student_project_context(
        _request(student_id="STU-999"),
        CAMPUS_SPRINT_SNAPSHOT,
    )

    assert context.student_id == "STU-999"
    assert context.assigned_tasks == []


def test_optional_snapshot_metadata_is_not_fabricated():
    context = build_student_project_context(
        _request(
            context=SelviaContext(
                student=StudentContext(student_id=STUDENT_ID),
                project=ProjectContext(
                    project_id=PROJECT_ID,
                    title="Ethical Tourism Certification System Backend",
                ),
                sprint=SprintContext(
                    sprint_id=SPRINT_ID,
                    name="Foundation and Backend Architecture",
                ),
            )
        ),
        CAMPUS_SPRINT_SNAPSHOT,
    )

    assert context.group_id is None
    assert context.project_title == "Ethical Tourism Certification System Backend"
    assert context.project_description == (
        "Node.js/Express backend for ethical tourism hotel certification: "
        "JWT auth, certification applications, audit workflows, public search/"
        "discovery, and certificate lifecycle management."
    )
    assert context.sprint_goal == (
        "Establish the Express/Mongo feature-module architecture, shared "
        "common utilities, and initial certificate lifecycle API surface."
    )
    assert context.sprint_status == "completed"
    repo_task = next(
        task for task in context.assigned_tasks if task.task_id == "task-s1-initial-repo"
    )
    assert repo_task.description is not None
