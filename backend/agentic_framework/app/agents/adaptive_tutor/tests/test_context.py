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
    CAMPUS_SPRINT_SNAPSHOT,
    PROJECT_ID,
    SPRINT_ID,
    make_fixture_sprint_provider,
)


def _request(**overrides) -> AgentRequest:
    fields = {
        "action": "tutor.sprint_guidance",
        "student_id": "STU-001",
        "project_id": PROJECT_ID,
        "sprint_id": SPRINT_ID,
    }
    fields.update(overrides)
    return AgentRequest(**fields)


def test_stu001_receives_two_assigned_tasks():
    context = build_student_project_context(_request(), CAMPUS_SPRINT_SNAPSHOT)

    assert context.student_id == "STU-001"
    assert context.project_id == PROJECT_ID
    assert context.sprint_id == SPRINT_ID
    assert [task.task_id for task in context.assigned_tasks] == [
        "task-jwt",
        "task-profile",
    ]


def test_stu002_tasks_are_excluded_for_stu001():
    context = build_student_project_context(_request(), CAMPUS_SPRINT_SNAPSHOT)

    assert "task-dashboard" not in {task.task_id for task in context.assigned_tasks}


def test_unassigned_tasks_are_excluded():
    context = build_student_project_context(_request(), CAMPUS_SPRINT_SNAPSHOT)

    assert "task-unassigned" not in {task.task_id for task in context.assigned_tasks}


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
            student_id="STU-001",
            project_id=PROJECT_ID,
            sprint_id=SPRINT_ID,
            context=SelviaContext(student=StudentContext(student_id="STU-002")),
        )


def test_conflicting_nested_task_id_is_rejected_by_shared_rules():
    with pytest.raises(ValidationError, match="task_id"):
        AgentRequest(
            action="tutor.sprint_guidance",
            student_id="STU-001",
            project_id=PROJECT_ID,
            sprint_id=SPRINT_ID,
            task_id="task-jwt",
            context=SelviaContext(task=TaskContext(task_id="task-profile")),
        )


def test_missing_optional_task_description_is_preserved():
    context = build_student_project_context(_request(), CAMPUS_SPRINT_SNAPSHOT)
    jwt_task = next(task for task in context.assigned_tasks if task.task_id == "task-jwt")

    assert jwt_task.description is None
    assert jwt_task.requirements is not None


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
                student=StudentContext(student_id="STU-001"),
                project=ProjectContext(project_id=PROJECT_ID, title="SELVIA Campus Portal (sample)"),
                sprint=SprintContext(sprint_id=SPRINT_ID, name="Sprint 2 — Access control"),
            )
        ),
        CAMPUS_SPRINT_SNAPSHOT,
    )

    assert context.group_id is None
    assert context.project_title == "SELVIA Campus Portal (sample)"
    profile = next(task for task in context.assigned_tasks if task.task_id == "task-profile")
    assert profile.description is not None
