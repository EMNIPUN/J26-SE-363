import uuid
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from shared.contracts import UserRole
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.planning import ALLOWED_FIBONACCI_POINTS, EstimateIn
from app.core.security import CurrentUser, get_current_user
from app.database.base import Base
from app.database.session import get_db, get_session_factory
from app.main import app
from app.models.decomposition_assessment import UserStory
from app.models.effort_estimation import StudentEffortEstimate
from app.models.sprint_backlog import SprintBacklogItem
from app.models.enums import Priority, StoryStatus
from app.models.group import Group, GroupMember
from app.models.pipeline_session import PipelineSession
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.user import User
from app.modules.planning import estimation_service


def test_estimate_in_validation_valid_fibonacci():
    for pt in [1, 2, 3, 5, 8, 13]:
        est = EstimateIn(story_ref="US-01", story_points=pt)
        assert est.story_points == pt

    # Test alias support
    est_alias = EstimateIn(story_ref="US-01", estimated_story_points=8, estimation_basis="Complex")
    assert est_alias.story_points == 8
    assert est_alias.basis == "Complex"


def test_estimate_in_validation_invalid_points():
    invalid_points = [0, 4, 6, 7, 9, 10, 21, -5]
    for pt in invalid_points:
        with pytest.raises(ValidationError):
            EstimateIn(story_ref="US-01", story_points=pt)


def test_save_and_update_student_estimate_in_db():
    session_factory = get_session_factory()
    db = session_factory()
    try:
        # Create a test requirement and user story
        user = User(
            id=uuid.uuid4(),
            keycloak_sub=f"test-sub-{uuid.uuid4()}",
            role=UserRole.STUDENT,
            name="Test Student",
        )
        db.add(user)
        db.flush()

        group = Group(id=uuid.uuid4(), code=f"GRP-{uuid.uuid4().hex[:6]}", name="Test Group")
        db.add(group)
        db.flush()

        project = Project(
            id=uuid.uuid4(),
            group_id=group.id,
            created_by_id=user.id,
            title="Test Project",
        )
        db.add(project)
        db.flush()

        pipe_session = PipelineSession(
            id=uuid.uuid4(),
            project_id=project.id,
            group_id=group.id,
            initiated_by=user.id,
        )
        db.add(pipe_session)
        db.flush()

        req = Requirement(
            id=uuid.uuid4(),
            project_id=project.id,
            group_id=group.id,
            pipeline_session_id=pipe_session.id,
            requirement_ref="FR-TEST",
            requirement_text="The system shall provide authentication.",
        )
        db.add(req)
        db.flush()

        story = UserStory(
            id=uuid.uuid4(),
            requirement_id=req.id,
            pipeline_session_id=pipe_session.id,
            story_ref=f"US-{uuid.uuid4().hex[:6].upper()}",
            title="As a user I want to log in",
            description="Login feature with password",
            acceptance_criteria=["Given valid password, when submit, then login succeeds"],
            status=StoryStatus.DRAFT,
            priority=Priority.HIGH,
        )
        db.add(story)
        db.flush()

        # 1. Save estimate for the story
        row = estimation_service.save_student_estimate(
            db=db,
            story_id=story.id,
            session_id=pipe_session.id,
            user_id=user.id,
            story_points=5,
            hours=10.0,
            basis="Database + auth library integration",
        )
        db.commit()

        assert row.estimated_story_points == 5
        assert row.user_story_id == story.id

        # Verify UserStory model was updated
        db.refresh(story)
        assert story.student_story_points == 5
        assert story.status == StoryStatus.ESTIMATED

        # 2. Verify list_estimates and estimate_to_dict serialization
        estimates = estimation_service.list_estimates(db, pipe_session.id)
        assert len(estimates) >= 1
        matching_est = next(e for e in estimates if e.user_story_id == story.id)
        est_dict = estimation_service.estimate_to_dict(matching_est)
        assert est_dict["story_ref"] == story.story_ref
        assert est_dict["story_points"] == 5
        assert est_dict["confirmed"] is True

        # 3. Update the estimate to 8 points
        updated_row = estimation_service.save_student_estimate(
            db=db,
            story_id=story.id,
            session_id=pipe_session.id,
            user_id=user.id,
            story_points=8,
            hours=16.0,
            basis="Updated scope complexity",
        )
        db.commit()

        assert updated_row.id == row.id  # Same record updated, not duplicated
        assert updated_row.estimated_story_points == 8

        db.refresh(story)
        assert story.student_story_points == 8
        assert story.status == StoryStatus.ESTIMATED

        # Clean up
        db.execute(StudentEffortEstimate.__table__.delete().where(StudentEffortEstimate.user_story_id == story.id))
        db.execute(UserStory.__table__.delete().where(UserStory.id == story.id))
        db.execute(Requirement.__table__.delete().where(Requirement.id == req.id))
        db.execute(PipelineSession.__table__.delete().where(PipelineSession.id == pipe_session.id))
        db.execute(Project.__table__.delete().where(Project.id == project.id))
        db.execute(Group.__table__.delete().where(Group.id == group.id))
        db.execute(User.__table__.delete().where(User.id == user.id))
        db.commit()
    finally:
        db.close()


def test_estimation_api_endpoints():
    session_factory = get_session_factory()
    db = session_factory()
    test_user_id = f"sub-{uuid.uuid4()}"
    test_group_code = f"T{uuid.uuid4().hex[:6].upper()}"

    # Provision user and session
    user_row = User(
        id=uuid.uuid4(),
        keycloak_sub=test_user_id,
        role=UserRole.STUDENT,
        name="API Test Student",
    )
    db.add(user_row)

    other_user_id = f"other-sub-{uuid.uuid4()}"
    other_user_row = User(
        id=uuid.uuid4(),
        keycloak_sub=other_user_id,
        role=UserRole.STUDENT,
        name="Other Student",
    )
    db.add(other_user_row)
    db.flush()

    group_row = Group(id=uuid.uuid4(), code=test_group_code, name="API Test Group")
    db.add(group_row)
    db.flush()

    db.add(GroupMember(group_id=group_row.id, user_id=user_row.id))
    db.flush()

    proj_row = Project(
        id=uuid.uuid4(),
        group_id=group_row.id,
        created_by_id=user_row.id,
        title="API Test Project",
    )
    db.add(proj_row)
    db.flush()

    sess_row = PipelineSession(
        id=uuid.uuid4(),
        project_id=proj_row.id,
        group_id=group_row.id,
        initiated_by=user_row.id,
    )
    db.add(sess_row)
    db.flush()

    req_row = Requirement(
        id=uuid.uuid4(),
        project_id=proj_row.id,
        group_id=group_row.id,
        pipeline_session_id=sess_row.id,
        requirement_ref="FR-API",
        requirement_text="API requirement",
    )
    db.add(req_row)
    db.flush()

    story_ref = f"US-API-{uuid.uuid4().hex[:4].upper()}"
    story_row = UserStory(
        id=uuid.uuid4(),
        requirement_id=req_row.id,
        pipeline_session_id=sess_row.id,
        story_ref=story_ref,
        title="API Story Title",
        description="Description of API Story",
        acceptance_criteria=["Criterion 1"],
        status=StoryStatus.DRAFT,
        priority=Priority.MEDIUM,
    )
    db.add(story_row)
    user_id_val = user_row.id
    other_user_id_val = other_user_row.id
    group_id_val = group_row.id
    proj_id_val = proj_row.id
    sess_id_val = sess_row.id
    req_id_val = req_row.id
    story_id_val = story_row.id
    db.commit()
    db.close()

    mock_current_user = CurrentUser(
        user_id=test_user_id,
        username="apitest",
        role=UserRole.STUDENT,
        roles=["student"],
    )

    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    client = TestClient(app)

    try:
        headers = {"X-Team-Id": test_group_code}

        # 1. Invalid point value should return 422
        resp = client.post(
            "/api/v1/planning/estimates",
            json={"story_ref": story_ref, "story_points": 4},
            headers=headers,
        )
        assert resp.status_code == 422

        # 2. Valid Fibonacci point (5 SP) should succeed
        resp = client.post(
            "/api/v1/planning/estimates",
            json={"story_ref": story_ref, "story_points": 5, "basis": "Initial estimate"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["estimate"]["story_points"] == 5
        assert data["estimate"]["story_ref"] == story_ref

        # 3. GET /planning/estimates should return the saved estimate
        resp = client.get("/api/v1/planning/estimates", headers=headers)
        assert resp.status_code == 200
        estimates = resp.json()["estimates"]
        matching = [e for e in estimates if e["story_ref"] == story_ref]
        assert len(matching) == 1
        assert matching[0]["estimated_story_points"] == 5

        # 4. GET /planning/stories should reflect student_story_points
        resp = client.get("/api/v1/planning/stories", headers=headers)
        assert resp.status_code == 200
        stories = resp.json()["stories"]
        matching_story = next((s for s in stories if s["story_ref"] == story_ref), None)
        assert matching_story is not None
        assert matching_story["student_story_points"] == 5
        assert matching_story["status"] == "estimated"

        # 5. Update the estimate to 13 SP
        resp = client.post(
            "/api/v1/planning/estimates",
            json={"story_ref": story_ref, "story_points": 13, "basis": "Re-evaluated to 13"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["estimate"]["story_points"] == 13

        # 6. Verify unauthorized student access is blocked (HTTP 403)
        mock_other_student = CurrentUser(
            user_id=other_user_id,
            username="otherstudent",
            role=UserRole.STUDENT,
            roles=["student"],
        )
        app.dependency_overrides[get_current_user] = lambda: mock_other_student
        resp = client.post(
            "/api/v1/planning/estimates",
            json={"story_ref": story_ref, "story_points": 3},
            headers=headers,
        )
        assert resp.status_code == 403

    finally:
        app.dependency_overrides.clear()
        # Clean up database records
        db_cleanup = session_factory()
        db_cleanup.execute(StudentEffortEstimate.__table__.delete().where(StudentEffortEstimate.user_story_id == story_id_val))
        db_cleanup.execute(UserStory.__table__.delete().where(UserStory.id == story_id_val))
        db_cleanup.execute(Requirement.__table__.delete().where(Requirement.id == req_id_val))
        db_cleanup.execute(PipelineSession.__table__.delete().where(PipelineSession.id == sess_id_val))
        db_cleanup.execute(Project.__table__.delete().where(Project.id == proj_id_val))
        db_cleanup.execute(GroupMember.__table__.delete().where(GroupMember.group_id == group_id_val))
        db_cleanup.execute(Group.__table__.delete().where(Group.id == group_id_val))
        db_cleanup.execute(User.__table__.delete().where(User.id == user_id_val))
        db_cleanup.execute(User.__table__.delete().where(User.id == other_user_id_val))
        db_cleanup.commit()
        db_cleanup.close()


def test_estimated_story_backlog_eligibility_and_persistence():
    """Verify that user stories with saved estimates are persisted and eligible for the sprint backlog."""
    session_factory = get_session_factory()
    db = session_factory()
    test_user_id = f"sub-{uuid.uuid4()}"
    test_group_code = f"T{uuid.uuid4().hex[:6].upper()}"

    user_row = User(
        id=uuid.uuid4(),
        keycloak_sub=test_user_id,
        role=UserRole.STUDENT,
        name="Backlog Student",
    )
    db.add(user_row)
    db.flush()

    group_row = Group(id=uuid.uuid4(), code=test_group_code, name="Backlog Test Group")
    db.add(group_row)
    db.flush()

    db.add(GroupMember(group_id=group_row.id, user_id=user_row.id))
    db.flush()

    proj_row = Project(
        id=uuid.uuid4(),
        group_id=group_row.id,
        created_by_id=user_row.id,
        title="Backlog Eligibility Project",
    )
    db.add(proj_row)
    db.flush()

    sess_row = PipelineSession(
        id=uuid.uuid4(),
        project_id=proj_row.id,
        group_id=group_row.id,
        initiated_by=user_row.id,
    )
    db.add(sess_row)
    db.flush()

    req_row = Requirement(
        id=uuid.uuid4(),
        project_id=proj_row.id,
        group_id=group_row.id,
        pipeline_session_id=sess_row.id,
        requirement_ref="FR-ELIGIBLE",
        requirement_text="Functional requirement for backlog eligibility.",
    )
    db.add(req_row)
    db.flush()

    story_ref = f"US-ELG-{uuid.uuid4().hex[:4].upper()}"
    story_row = UserStory(
        id=uuid.uuid4(),
        requirement_id=req_row.id,
        pipeline_session_id=sess_row.id,
        story_ref=story_ref,
        title="Eligible User Story Title",
        description="Story awaiting effort estimation",
        acceptance_criteria=["Criterion A", "Criterion B"],
        status=StoryStatus.DRAFT,
        priority=Priority.HIGH,
    )
    db.add(story_row)

    user_id_val = user_row.id
    group_id_val = group_row.id
    proj_id_val = proj_row.id
    sess_id_val = sess_row.id
    req_id_val = req_row.id
    story_id_val = story_row.id
    db.commit()
    db.close()

    mock_current_user = CurrentUser(
        user_id=test_user_id,
        username="backlogstudent",
        role=UserRole.STUDENT,
        roles=["student"],
    )

    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    client = TestClient(app)

    try:
        headers = {"X-Team-Id": test_group_code}

        # Step 1: Query stories before estimation — points should be None
        resp = client.get("/api/v1/planning/stories", headers=headers)
        assert resp.status_code == 200
        stories = resp.json()["stories"]
        story = next(s for s in stories if s["story_ref"] == story_ref)
        assert story["student_story_points"] is None
        assert story["status"] == "draft"

        # Step 2: Save estimate with Fibonacci points = 5
        resp = client.post(
            "/api/v1/planning/estimates",
            json={"story_ref": story_ref, "story_points": 5, "basis": "Sprint 1 priority feature"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["estimate"]["story_points"] == 5

        # Step 3: Verify story now has status='estimated' and student_story_points=5
        resp = client.get("/api/v1/planning/stories", headers=headers)
        assert resp.status_code == 200
        stories = resp.json()["stories"]
        story = next(s for s in stories if s["story_ref"] == story_ref)
        assert story["student_story_points"] == 5
        assert story["status"] == "estimated"

        # Step 4: Confirm estimate to send to sprint backlog
        resp = client.post(
            f"/api/v1/planning/estimates/{story_ref}/confirm",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Step 5: Verify story appears in sprint backlog with points=5
        resp = client.get("/api/v1/planning/backlog", headers=headers)
        assert resp.status_code == 200
        backlog_items = resp.json()["items"]
        backlog_item = next((item for item in backlog_items if item.get("story_ref") == story_ref), None)
        assert backlog_item is not None
        assert backlog_item["points"] == 5

        # Step 6: Verify updating the estimate updates the story points (Fibonacci 8)
        resp = client.post(
            "/api/v1/planning/estimates",
            json={"story_ref": story_ref, "story_points": 8, "basis": "Updated complexity"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["estimate"]["story_points"] == 8

        # Verify persisted in stories query
        resp = client.get("/api/v1/planning/stories", headers=headers)
        story = next(s for s in resp.json()["stories"] if s["story_ref"] == story_ref)
        assert story["student_story_points"] == 8

    finally:
        app.dependency_overrides.clear()
        db_cleanup = session_factory()
        db_cleanup.execute(SprintBacklogItem.__table__.delete().where(SprintBacklogItem.user_story_id == story_id_val))
        db_cleanup.execute(StudentEffortEstimate.__table__.delete().where(StudentEffortEstimate.user_story_id == story_id_val))
        db_cleanup.execute(UserStory.__table__.delete().where(UserStory.id == story_id_val))
        db_cleanup.execute(Requirement.__table__.delete().where(Requirement.id == req_id_val))
        db_cleanup.execute(PipelineSession.__table__.delete().where(PipelineSession.id == sess_id_val))
        db_cleanup.execute(Project.__table__.delete().where(Project.id == proj_id_val))
        db_cleanup.execute(GroupMember.__table__.delete().where(GroupMember.group_id == group_id_val))
        db_cleanup.execute(Group.__table__.delete().where(Group.id == group_id_val))
        db_cleanup.execute(User.__table__.delete().where(User.id == user_id_val))
        db_cleanup.commit()
        db_cleanup.close()

