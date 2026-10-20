"""Business logic coordinating SELVIA planning artifacts with Jira Software."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.decomposition_assessment import UserStory, UserStoryTask
from app.models.enums import Priority, TaskStatus
from app.models.pipeline_session import PipelineSession
from app.models.requirement import Requirement
from app.models.sprint import Sprint
from app.models.sprint_backlog import SprintBacklogItem
from app.modules.planning import (
    decomposition_service,
    estimation_service,
    requirement_service,
    sprint_backlog_service,
)
from app.modules.planning.jira_client import JiraClient, build_story_adf, text_to_adf

logger = logging.getLogger(__name__)


def _parse_jira_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _jira_sprint_id(fields: dict[str, Any]) -> int | None:
    raw = fields.get("sprint")
    sprints = raw if isinstance(raw, list) else [raw]
    for sprint in reversed(sprints):
        if isinstance(sprint, dict) and sprint.get("id") is not None:
            try:
                return int(sprint["id"])
            except (TypeError, ValueError):
                pass
    return None


def _jira_task_status(fields: dict[str, Any]) -> TaskStatus:
    status = fields.get("status") or {}
    name = str(status.get("name") or "").lower()
    category = str((status.get("statusCategory") or {}).get("key") or "").lower()
    if "block" in name or "imped" in name:
        return TaskStatus.BLOCKED
    if category == "done" or name in {"done", "closed", "resolved", "complete", "completed"}:
        return TaskStatus.DONE
    if category == "indeterminate" or "progress" in name or "review" in name:
        return TaskStatus.IN_PROGRESS
    return TaskStatus.TODO


def _jira_priority(fields: dict[str, Any], fallback: Priority) -> Priority:
    value = str((fields.get("priority") or {}).get("name") or "").lower()
    if value in {p.value for p in Priority}:
        return Priority(value)
    if "highest" in value or "critical" in value:
        return Priority.CRITICAL
    if "high" in value:
        return Priority.HIGH
    if "low" in value:
        return Priority.LOW
    if "medium" in value or "normal" in value:
        return Priority.MEDIUM
    return fallback


def _apply_jira_execution_fields(row: UserStory | UserStoryTask, issue: dict[str, Any], synced_at: datetime) -> None:
    fields = issue.get("fields") or {}
    status = fields.get("status") or {}
    assignee = fields.get("assignee") or {}
    row.jira_status = status.get("name") or None
    row.jira_assignee_display_name = assignee.get("displayName") or None
    row.jira_assignee_account_id = assignee.get("accountId") or None
    row.jira_sprint_id = _jira_sprint_id(fields)
    row.jira_updated_at = _parse_jira_datetime(fields.get("updated"))
    row.jira_last_synced_at = synced_at
    row.priority = _jira_priority(fields, row.priority)
    if isinstance(row, UserStoryTask):
        row.status = _jira_task_status(fields)


def get_jira_client(overrides: dict[str, Any] | None = None) -> JiraClient:
    """Instantiate a JiraClient from configuration or runtime overrides."""
    overrides = overrides or {}
    base_url = (overrides["base_url"] if "base_url" in overrides and overrides["base_url"] is not None else (settings.JIRA_BASE_URL or "")).strip()
    email = (overrides["email"] if "email" in overrides and overrides["email"] is not None else (settings.JIRA_EMAIL or "")).strip()
    api_token = (overrides["api_token"] if "api_token" in overrides and overrides["api_token"] is not None else (settings.JIRA_API_TOKEN or "")).strip()
    project_key = (overrides["project_key"] if "project_key" in overrides and overrides["project_key"] is not None else (settings.JIRA_PROJECT_KEY or "")).strip()
    board_id = overrides.get("board_id") or settings.JIRA_BOARD_ID
    story_points_field = overrides.get("story_points_field") or settings.JIRA_STORY_POINTS_FIELD

    if not base_url or not email or not api_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Jira credentials are not configured. Please set JIRA_BASE_URL, "
                "JIRA_EMAIL, and JIRA_API_TOKEN in backend/server/.env or provide them in the request."
            ),
        )

    return JiraClient(
        base_url=base_url,
        email=email,
        api_token=api_token,
        project_key=project_key or None,
        board_id=board_id,
        story_points_field=story_points_field,
    )


async def check_jira_status(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check whether Jira credentials are configured and connection succeeds."""
    overrides = overrides or {}
    base_url = (overrides["base_url"] if "base_url" in overrides and overrides["base_url"] is not None else (settings.JIRA_BASE_URL or "")).strip()
    email = (overrides["email"] if "email" in overrides and overrides["email"] is not None else (settings.JIRA_EMAIL or "")).strip()
    api_token = (overrides["api_token"] if "api_token" in overrides and overrides["api_token"] is not None else (settings.JIRA_API_TOKEN or "")).strip()
    project_key = (overrides["project_key"] if "project_key" in overrides and overrides["project_key"] is not None else (settings.JIRA_PROJECT_KEY or "")).strip()

    if not base_url or not email or not api_token:
        return {
            "configured": False,
            "connected": False,
            "message": "Jira integration is not configured. Add JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN to backend/server/.env.",
        }

    client = JiraClient(
        base_url=base_url,
        email=email,
        api_token=api_token,
        project_key=project_key or None,
    )
    try:
        conn = await client.test_connection()
        return {
            "configured": True,
            "connected": True,
            "base_url": base_url,
            "project_key": project_key,
            "user": conn.get("displayName"),
            "email": conn.get("emailAddress"),
        }
    except Exception as e:
        logger.warning("Jira connection check failed: %s", e)
        return {
            "configured": True,
            "connected": False,
            "base_url": base_url,
            "project_key": project_key,
            "error": str(e),
        }


async def clear_jira_keys(db: Session, session_id: uuid.UUID) -> dict[str, Any]:
    """Reset all Jira keys for requirements, stories, tasks, and sprints in the session,
    allowing a clean fresh push to Jira.
    """
    requirements = requirement_service.list_requirements(db, session_id)
    for req in requirements:
        req.jira_epic_key = None

    stories = decomposition_service.list_stories(db, session_id)
    for story in stories:
        story.jira_issue_key = None
        for task in (story.tasks or []):
            task.jira_subtask_key = None

    sprint = db.query(Sprint).order_by(Sprint.created_at.desc()).first()
    if sprint:
        sprint.jira_sprint_id = None

    db.commit()
    return {
        "ok": True,
        "message": "All Jira keys have been cleared from database. You can now re-push cleanly to Jira.",
    }


async def sync_backlog_to_jira(
    db: Session,
    session_id: uuid.UUID,
    client: JiraClient,
    force_resync: bool = False,
    story_refs: list[str] | None = None,
    story_points: dict[str, int | float] | None = None,
) -> dict[str, Any]:
    """Push validated requirements (Epics), user stories (Stories with Story Points),
    and tasks (Sub-tasks) into the Jira project backlog.
    Only pushes active product backlog user stories (or story_refs if specified).
    """
    if force_resync:
        await clear_jira_keys(db, session_id)

    # 1. Fetch user stories and determine candidate stories
    all_stories = decomposition_service.list_stories(db, session_id)
    estimates = estimation_service.list_estimates(db, session_id)
    estimates_by_story_id = {est.user_story_id: est for est in estimates}

    if story_refs:
        ref_set = set(story_refs)
        candidate_stories = [s for s in all_stories if s.story_ref in ref_set or str(s.id) in ref_set]
    else:
        # Default: candidate stories that have points, estimates, or are marked for backlog
        candidate_stories = [
            s for s in all_stories
            if s.id in estimates_by_story_id
            or s.student_story_points is not None
            or (hasattr(s, "status") and s.status in ("in_backlog", "estimated"))
        ]

    # Filter candidates through Backlog Readiness Passport: only ready items can be pushed to Jira
    from app.modules.planning.passport_service import get_passport_for_story
    stories = []
    blocked_stories = []
    for s in candidate_stories:
        passport = get_passport_for_story(db, session_id, s.id)
        status_val = passport.overall_status.value if hasattr(passport.overall_status, "value") else str(passport.overall_status)
        if status_val in ("ready", "ready_with_warnings"):
            stories.append(s)
        else:
            blocked_stories.append({
                "story_ref": s.story_ref,
                "title": s.title,
                "status": status_val,
                "readiness_gap": passport.readiness_gap,
                "student_action_required": passport.student_action_required,
            })

    # 2. Fetch requirements and only create Epics for requirements that have active backlog stories
    all_requirements = requirement_service.list_requirements(db, session_id)
    needed_req_ids = {s.requirement_id for s in stories if s.requirement_id}
    requirements = [r for r in all_requirements if r.id in needed_req_ids]

    epics_created = 0
    epic_key_by_req_id: dict[uuid.UUID, str] = {}

    for req in requirements:
        # Check if existing Jira Epic was deleted in Jira
        if req.jira_epic_key:
            if not await client.issue_exists(req.jira_epic_key):
                req.jira_epic_key = None
                db.commit()

        if req.jira_epic_key:
            epic_key_by_req_id[req.id] = req.jira_epic_key
            continue
        try:
            summary = f"[{req.requirement_ref}] {req.requirement_text[:120]}"
            desc_adf = text_to_adf(
                f"Requirement: {req.requirement_ref}\n"
                f"Category: {req.requirement_category.value}\n\n"
                f"{req.requirement_text}"
            )
            created = await client.create_epic(
                summary=summary,
                description_adf=desc_adf,
                req_ref=req.requirement_ref,
            )
            key = created.get("key")
            if key:
                req.jira_epic_key = key
                epic_key_by_req_id[req.id] = key
                epics_created += 1
                db.commit()
        except Exception as e:
            logger.warning("Could not create Epic for %s: %s", req.requirement_ref, e)

    stories_synced = 0
    subtasks_created = 0
    synced_issues: list[dict[str, Any]] = []
    status_warnings: list[str] = []

    for story in stories:
        est = estimates_by_story_id.get(story.id)
        custom_pts = None
        if story_points:
            custom_pts = story_points.get(story.story_ref) or story_points.get(str(story.id))

        points = (
            custom_pts
            if custom_pts is not None
            else (
                est.estimated_story_points
                if est
                else (story.student_story_points or 3)
            )
        )
        hours = float(est.estimated_hours) if est and est.estimated_hours else None
        basis = est.estimation_basis if est else None

        parent_epic_key = epic_key_by_req_id.get(story.requirement_id) or (
            getattr(story.user_story, "requirement", None).jira_epic_key
            if hasattr(story, "user_story") and getattr(story.user_story, "requirement", None)
            else None
        )

        desc_adf = build_story_adf(
            as_a=story.as_a,
            i_want=story.i_want,
            so_that=story.so_that,
            description=story.description,
            acceptance_criteria=story.acceptance_criteria,
            story_points=points,
            hours=hours,
            estimation_basis=basis,
        )

        # Create or reuse Story
        story_key = story.jira_issue_key
        # Check if existing key was deleted in Jira
        if story_key:
            if not await client.issue_exists(story_key):
                story.jira_issue_key = None
                story_key = None
                db.commit()

        if not story_key:
            try:
                created = await client.create_story(
                    summary=f"[{story.story_ref}] {story.title}",
                    description_adf=desc_adf,
                    story_points=points,
                    priority=story.priority.value if hasattr(story.priority, "value") else str(story.priority),
                    parent_epic_key=parent_epic_key,
                    story_ref=story.story_ref,
                )
                story_key = created.get("key")
                if story_key:
                    story.jira_issue_key = story_key
                    created_now = not bool(created.get("_selvia_reused"))
                    if created_now:
                        stories_synced += 1
                    db.commit()
                    # Jira projects can be configured to create issues directly
                    # in In Progress.  A backlog export must never start work;
                    # change only brand-new issues, never linked/reused ones.
                    if created_now:
                        try:
                            await client.ensure_issue_in_todo(story_key)
                        except Exception as exc:
                            warning = (
                                f"{story_key} was created, but Jira could not move it to To Do: {exc}"
                            )
                            logger.warning(warning)
                            status_warnings.append(warning)
            except Exception as e:
                logger.error("Failed to sync story %s to Jira: %s", story.story_ref, e)
                continue

        synced_issues.append({
            "story_ref": story.story_ref,
            "title": story.title,
            "jira_key": story_key,
            "points": points,
            "jira_url": f"{client.base_url}/browse/{story_key}" if story_key else None,
        })

        # Create subtasks if story has decomposed tasks
        if story_key and story.tasks:
            for task in story.tasks:
                if task.jira_subtask_key:
                    if not await client.issue_exists(task.jira_subtask_key):
                        task.jira_subtask_key = None
                        db.commit()

                if not task.jira_subtask_key:
                    try:
                        sub_created = await client.create_subtask(
                            parent_issue_key=story_key,
                            summary=task.title,
                            description_adf=text_to_adf(task.description or task.title),
                            priority=task.priority.value if hasattr(task.priority, "value") else "Medium",
                        )
                        task.jira_subtask_key = sub_created.get("key")
                        created_now = not bool(sub_created.get("_selvia_reused"))
                        if created_now:
                            subtasks_created += 1
                        db.commit()
                        if task.jira_subtask_key and created_now:
                            try:
                                await client.ensure_issue_in_todo(task.jira_subtask_key)
                            except Exception as exc:
                                warning = (
                                    f"{task.jira_subtask_key} was created, but Jira could not move it to To Do: {exc}"
                                )
                                logger.warning(warning)
                                status_warnings.append(warning)
                    except Exception as e:
                        logger.warning("Could not create subtask '%s': %s", task.title, e)

    db.commit()

    return {
        "ok": True,
        "epics_created": epics_created,
        "stories_synced": stories_synced,
        "subtasks_created": subtasks_created,
        "total_stories": len(stories),
        "issues": synced_issues,
        "jira_base_url": client.base_url,
        "status_warnings": status_warnings,
        "blocked_stories": blocked_stories,
    }


async def sync_sprint_to_jira(
    db: Session,
    session_id: uuid.UUID,
    client: JiraClient,
    sprint_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Create a Sprint on the Jira Scrum board and assign estimated backlog stories to it."""
    # Find sprint row
    sprint: Sprint | None = None
    if sprint_id:
        sprint = db.get(Sprint, sprint_id)
    if not sprint:
        sprint = db.query(Sprint).order_by(Sprint.created_at.desc()).first()

    sprint_name = f"Sprint {sprint.sprint_number}" if sprint else "Sprint 1"
    start_date = sprint.start_date.isoformat() if sprint and sprint.start_date else None
    end_date = sprint.end_date.isoformat() if sprint and sprint.end_date else None

    # Find board ID
    board_id = await client.discover_board_id()
    if not board_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Scrum Board found in Jira project. Please create a Scrum board in your Jira project first.",
        )

    # Create sprint in Jira
    created_sprint = await client.create_sprint(
        name=sprint_name,
        board_id=board_id,
        start_date_iso=start_date,
        end_date_iso=end_date,
        goal=f"Sprint planning generated from SELVIA pipeline session {session_id}",
    )
    jira_sprint_id = created_sprint.get("id")
    if sprint and jira_sprint_id:
        sprint.jira_sprint_id = jira_sprint_id

    # Collect all story keys for this session
    stories = decomposition_service.list_stories(db, session_id)
    issue_keys = [s.jira_issue_key for s in stories if s.jira_issue_key]

    moved = False
    if jira_sprint_id and issue_keys:
        moved = await client.move_issues_to_sprint(jira_sprint_id, issue_keys)

    db.commit()

    return {
        "ok": True,
        "jira_sprint_id": jira_sprint_id,
        "sprint_name": sprint_name,
        "issues_assigned": issue_keys,
        "moved": moved,
        "board_id": board_id,
        "jira_board_url": f"{client.base_url}/jira/software/projects/{client.project_key}/boards/{board_id}",
    }


def _sync_story_payload(story: UserStory) -> dict[str, Any]:
    return {
        "id": str(story.id),
        "story_ref": story.story_ref,
        "title": story.title,
        "jira_issue_key": story.jira_issue_key,
        "jira_status": story.jira_status,
        "priority": story.priority.value,
        "jira_assignee_display_name": story.jira_assignee_display_name,
        "jira_sprint_id": story.jira_sprint_id,
        "jira_updated_at": story.jira_updated_at.isoformat() if story.jira_updated_at else None,
        "jira_last_synced_at": story.jira_last_synced_at.isoformat() if story.jira_last_synced_at else None,
        "student_story_points": story.student_story_points,
    }


def _sync_task_payload(task: UserStoryTask, story: UserStory) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "story_ref": story.story_ref,
        "story_title": story.title,
        "title": task.title,
        "jira_subtask_key": task.jira_subtask_key,
        "jira_status": task.jira_status,
        "status": task.status.value,
        "priority": task.priority.value,
        "jira_assignee_display_name": task.jira_assignee_display_name,
        "jira_sprint_id": task.jira_sprint_id,
        "jira_updated_at": task.jira_updated_at.isoformat() if task.jira_updated_at else None,
        "jira_last_synced_at": task.jira_last_synced_at.isoformat() if task.jira_last_synced_at else None,
    }


async def fetch_linked_jira_execution(
    db: Session,
    session_id: uuid.UUID,
    client: JiraClient,
) -> dict[str, Any]:
    """Pull current Jira execution fields for linked backlog work only.

    The import is deliberately one-way and field-scoped: Jira controls delivery
    state/assignee/priority mirrors, while local planning lifecycle and content
    remain untouched. Each issue is handled independently so one deleted or
    inaccessible Jira item cannot discard successful updates from others.
    """
    now = datetime.now(UTC)
    stories = decomposition_service.list_stories(db, session_id)
    linked_stories = [story for story in stories if story.jira_issue_key]
    linked_tasks = [task for story in stories for task in (story.tasks or []) if task.jira_subtask_key]
    errors: list[dict[str, str]] = []
    issue_cache: dict[str, dict[str, Any]] = {}

    session = db.get(PipelineSession, session_id)
    linked_keys = {story.jira_issue_key for story in linked_stories} | {
        task.jira_subtask_key for task in linked_tasks
    }
    sprint_membership: dict[str, int] = {}
    sprint_payloads: list[dict[str, Any]] = []
    membership_loaded = False
    try:
        # Student-created Jira sprints are discovered from the Scrum board, not
        # from a local "create sprint" action. Jira is therefore authoritative
        # when a linked story is moved from a sprint back to the backlog.
        remote_sprints = await client.list_board_sprints()
        membership_loaded = True
        for remote_sprint in remote_sprints:
            remote_id = remote_sprint.get("id")
            if remote_id is None:
                continue
            try:
                remote_id = int(remote_id)
                remote_issues = await client.list_sprint_issues(remote_id)
            except Exception as exc:
                errors.append({"key": str(remote_id), "message": str(exc)})
                membership_loaded = False
                continue
            linked_count = 0
            for issue in remote_issues:
                key = issue.get("key")
                if key:
                    issue_cache[key] = issue
                if key in linked_keys:
                    sprint_membership[key] = remote_id
                    linked_count += 1
            if linked_count:
                sprint_payloads.append({
                    "jira_sprint_id": remote_id,
                    "name": remote_sprint.get("name") or f"Sprint {remote_id}",
                    "state": remote_sprint.get("state") or None,
                    "goal": remote_sprint.get("goal") or None,
                    "start_date": remote_sprint.get("startDate"),
                    "end_date": remote_sprint.get("endDate"),
                    "linked_items": linked_count,
                    "last_synced_at": now.isoformat(),
                })

        local_sprint_by_jira_id: dict[int, Sprint] = {}
        if session:
            local_sprints = db.query(Sprint).filter(Sprint.project_id == session.project_id).all()
            remote_by_id = {item["jira_sprint_id"]: item for item in sprint_payloads}
            for local_sprint in local_sprints:
                if local_sprint.jira_sprint_id:
                    local_sprint_by_jira_id[local_sprint.jira_sprint_id] = local_sprint
                    remote = remote_by_id.get(local_sprint.jira_sprint_id)
                    if remote:
                        local_sprint.jira_state = remote["state"]
                        local_sprint.jira_goal = remote["goal"]
                        local_sprint.jira_last_synced_at = now

            max_num = max([s.sprint_number for s in local_sprints], default=0)
            for item in sprint_payloads:
                jid = item["jira_sprint_id"]
                if jid not in local_sprint_by_jira_id:
                    max_num += 1
                    new_sp = Sprint(
                        project_id=session.project_id,
                        sprint_number=max_num,
                        jira_sprint_id=jid,
                        jira_state=item.get("state"),
                        jira_goal=item.get("goal"),
                        jira_last_synced_at=now,
                        status="active" if item.get("state") == "active" else "planning",
                    )
                    db.add(new_sp)
                    db.flush()
                    local_sprint_by_jira_id[jid] = new_sp
    except Exception as exc:
        errors.append({"key": "board-sprints", "message": str(exc)})

    async def resolve_issue(key: str) -> dict[str, Any] | None:
        if key in issue_cache:
            return issue_cache[key]
        try:
            issue_cache[key] = await client.get_issue(key)
            return issue_cache[key]
        except Exception as exc:
            errors.append({"key": key, "message": str(exc)})
            return None

    stories_updated = 0
    tasks_updated = 0
    for story in linked_stories:
        issue = await resolve_issue(story.jira_issue_key)
        if issue:
            _apply_jira_execution_fields(story, issue, now)
            if membership_loaded:
                story.jira_sprint_id = sprint_membership.get(story.jira_issue_key)

            # Sync with SprintBacklogItem so Kanban board and local queries reflect Jira
            backlog_item = db.query(SprintBacklogItem).filter(
                SprintBacklogItem.user_story_id == story.id,
                SprintBacklogItem.pipeline_session_id == session_id,
            ).first()
            if backlog_item:
                fields = issue.get("fields") or {}
                backlog_item.status = _jira_task_status(fields)
                if story.jira_sprint_id and story.jira_sprint_id in local_sprint_by_jira_id:
                    backlog_item.sprint_id = local_sprint_by_jira_id[story.jira_sprint_id].id

            stories_updated += 1

    for task in linked_tasks:
        issue = await resolve_issue(task.jira_subtask_key)
        if issue:
            _apply_jira_execution_fields(task, issue, now)
            if membership_loaded:
                task.jira_sprint_id = sprint_membership.get(
                    task.jira_subtask_key,
                    task.user_story.jira_sprint_id,
                )
            tasks_updated += 1

    # A partial Jira failure must keep previously mirrored values intact. Only
    # rows whose individual fetch succeeded were mutated above.
    completion_conflicts = [
        {
            "story_ref": story.story_ref,
            "jira_issue_key": story.jira_issue_key,
            "message": "Jira marks this story Done while one or more linked tasks are unfinished.",
            "open_tasks": [task.title for task in (story.tasks or []) if task.status != TaskStatus.DONE],
        }
        for story in linked_stories
        if _jira_task_status({"status": {"name": story.jira_status}}) == TaskStatus.DONE
        and any(task.status != TaskStatus.DONE for task in (story.tasks or []))
    ]
    db.commit()
    return {
        "ok": True,
        "fetched_at": now.isoformat(),
        "jira_base_url": client.base_url,
        "sprint": sprint_payloads[0] if sprint_payloads else None,
        "sprints": sprint_payloads,
        "stories_updated": stories_updated,
        "tasks_updated": tasks_updated,
        "linked_stories": len(linked_stories),
        "linked_tasks": len(linked_tasks),
        "unlinked_stories": len(stories) - len(linked_stories),
        "unlinked_tasks": sum(len(story.tasks or []) for story in stories) - len(linked_tasks),
        "errors": errors,
        "completion_conflicts": completion_conflicts,
        "stories": [_sync_story_payload(story) for story in linked_stories],
        "tasks": [_sync_task_payload(task, story) for story in stories for task in (story.tasks or []) if task.jira_subtask_key],
    }


async def transition_jira_issue(
    db: Session,
    session_id: uuid.UUID,
    client: JiraClient,
    issue_key: str,
    target_status: str,
    acceptance_criteria_confirmed: bool = False,
) -> dict[str, Any]:
    """Execute status transition on Jira issue and immediately reflect in local DB."""
    # Find matching story or task
    story = db.query(UserStory).filter(
        UserStory.jira_issue_key == issue_key,
        UserStory.pipeline_session_id == session_id,
    ).first()

    task = None
    if not story:
        task = db.query(UserStoryTask).filter(
            UserStoryTask.jira_subtask_key == issue_key,
        ).first()

    requested_status = _jira_task_status({"status": {"name": target_status}})
    if story and requested_status == TaskStatus.DONE:
        tasks = db.query(UserStoryTask).filter(UserStoryTask.user_story_id == story.id).all()
        incomplete: list[str] = []
        # Re-read each linked subtask from Jira before allowing a story
        # completion transition, so stale browser/local state cannot close a
        # parent while Jira still has unfinished work.
        for child in tasks:
            if not child.jira_subtask_key:
                incomplete.append(child.title)
                continue
            try:
                remote = await client.get_issue(child.jira_subtask_key)
            except Exception:
                incomplete.append(child.title)
                continue
            _apply_jira_execution_fields(child, remote, datetime.now(UTC))
            if child.status != TaskStatus.DONE:
                incomplete.append(child.title)
        if incomplete:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "The user story cannot be marked Done while tasks remain unfinished.",
                    "open_tasks": incomplete,
                },
            )
        if not story.acceptance_criteria or not acceptance_criteria_confirmed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Confirm the acceptance criteria and Definition of Done before completing this user story.",
                },
            )

    res = await client.transition_issue_by_status_name(issue_key, target_status)
    now = datetime.now(UTC)

    to_name = res.get("to_status") or target_status
    if story:
        story.jira_status = to_name
        story.jira_last_synced_at = now
        backlog_item = db.query(SprintBacklogItem).filter(
            SprintBacklogItem.user_story_id == story.id,
            SprintBacklogItem.pipeline_session_id == session_id,
        ).first()
        if backlog_item:
            backlog_item.status = _jira_task_status({"status": {"name": to_name}})
    elif task:
        task.jira_status = to_name
        task.status = _jira_task_status({"status": {"name": to_name}})
        task.jira_last_synced_at = now

    db.commit()
    return {
        "ok": True,
        "issue_key": issue_key,
        "target_status": target_status,
        "jira_status": to_name,
        "transition": res,
    }
