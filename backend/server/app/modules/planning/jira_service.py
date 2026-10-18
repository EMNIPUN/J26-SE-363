"""Business logic coordinating SELVIA planning artifacts with Jira Software."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.decomposition_assessment import UserStory, UserStoryTask
from app.models.requirement import Requirement
from app.models.sprint import Sprint
from app.modules.planning import (
    decomposition_service,
    estimation_service,
    requirement_service,
    sprint_backlog_service,
)
from app.modules.planning.jira_client import JiraClient, build_story_adf, text_to_adf

logger = logging.getLogger(__name__)


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

    # 1. Fetch user stories and determine which stories belong to the backlog
    all_stories = decomposition_service.list_stories(db, session_id)
    estimates = estimation_service.list_estimates(db, session_id)
    estimates_by_story_id = {est.user_story_id: est for est in estimates}

    if story_refs:
        ref_set = set(story_refs)
        stories = [s for s in all_stories if s.story_ref in ref_set or str(s.id) in ref_set]
    else:
        # Default: only sync stories that have an estimate, have points, or are confirmed in backlog
        stories = [
            s for s in all_stories
            if s.id in estimates_by_story_id
            or s.student_story_points is not None
            or (hasattr(s, "status") and s.status in ("in_backlog", "estimated"))
        ]

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
                    stories_synced += 1
                    db.commit()
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
                        subtasks_created += 1
                        db.commit()
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
