"""Build validated Student & Project Context from an AgentRequest and sprint snapshot.

The builder is pure: callers load the snapshot via a SprintDataProvider first.
"""

from shared.contracts import AgentRequest

from app.agents.adaptive_tutor.schemas import (
    SprintSnapshot,
    SprintTask,
    StudentProjectContext,
)


class ContextBuildError(ValueError):
    """Raised when Student & Project Context cannot be built from the request."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def build_student_project_context(
    request: AgentRequest,
    snapshot: SprintSnapshot,
) -> StudentProjectContext:
    """Validate request scope against a sprint snapshot and return assigned tasks only."""
    student_id = _require_scope_id(request.student_id, "student_id", "missing_student_id")
    project_id = _require_scope_id(request.project_id, "project_id", "missing_project_id")
    sprint_id = _require_scope_id(request.sprint_id, "sprint_id", "missing_sprint_id")

    _reject_nested_conflicts(request, student_id, project_id, sprint_id)
    _reject_snapshot_mismatch(snapshot, project_id, sprint_id)

    assigned_tasks = _assigned_tasks_for_student(snapshot, student_id, sprint_id)

    return StudentProjectContext(
        student_id=student_id,
        project_id=project_id,
        project_title=snapshot.project_title,
        group_id=request.group_id,
        sprint_id=sprint_id,
        sprint_name=snapshot.sprint_name,
        sprint_number=snapshot.sprint_number,
        start_date=snapshot.start_date,
        end_date=snapshot.end_date,
        assigned_tasks=assigned_tasks,
    )


def _require_scope_id(value: str | None, field_name: str, code: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ContextBuildError(
            code,
            f"{field_name} is required for the sprint-start tutoring workflow.",
        )
    return value.strip()


def _reject_nested_conflicts(
    request: AgentRequest,
    student_id: str,
    project_id: str,
    sprint_id: str,
) -> None:
    context = request.context
    _reject_entity_id_conflict(
        getattr(context.student, "student_id", None) if context.student else None,
        student_id,
        "student_id",
    )
    _reject_entity_id_conflict(
        getattr(context.project, "project_id", None) if context.project else None,
        project_id,
        "project_id",
    )
    _reject_entity_id_conflict(
        getattr(context.sprint, "sprint_id", None) if context.sprint else None,
        sprint_id,
        "sprint_id",
    )
    if request.task_id is not None and context.task is not None:
        _reject_entity_id_conflict(context.task.task_id, request.task_id, "task_id")


def _reject_entity_id_conflict(
    nested_id: str | None,
    flat_id: str,
    field_name: str,
) -> None:
    if nested_id is None:
        return
    if nested_id != flat_id:
        raise ContextBuildError(
            "context_id_mismatch",
            f"{field_name} on the request does not match nested SelviaContext.",
        )


def _reject_snapshot_mismatch(
    snapshot: SprintSnapshot,
    project_id: str,
    sprint_id: str,
) -> None:
    if snapshot.project_id != project_id:
        raise ContextBuildError(
            "project_id_mismatch",
            "request.project_id does not match the sprint snapshot project.",
        )
    if snapshot.sprint_id != sprint_id:
        raise ContextBuildError(
            "sprint_id_mismatch",
            "request.sprint_id does not match the sprint snapshot sprint.",
        )


def _assigned_tasks_for_student(
    snapshot: SprintSnapshot,
    student_id: str,
    sprint_id: str,
) -> list[SprintTask]:
    assigned: list[SprintTask] = []
    for task in snapshot.tasks:
        if task.sprint_id != sprint_id:
            continue
        if student_id not in task.assignee_ids:
            continue
        assigned.append(task)
    return assigned
