import uuid
import pytest
from fastapi.testclient import TestClient
from shared.contracts import UserRole

from app.core.security import CurrentUser, get_current_user
from app.database.session import get_session_factory
from app.main import app
from app.models.backlog_readiness_passport import BacklogReadinessPassport
from app.models.decomposition_assessment import (
    CoverageElementRow,
    DecompositionAssessment,
    InvestValidation,
    UserStory,
)
from app.models.enums import (
    ConfidenceLevel,
    CoverageElementType,
    CoverageResult,
    DecompositionReadiness,
    InvestCriterion,
    InvestResult,
    Priority,
    QualityBand,
    QualityDimension,
    ReadyBacklogStatus,
    SessionStatus,
    StoryStatus,
)
from app.models.group import Group, GroupMember
from app.models.pipeline_session import PipelineSession
from app.models.project import Project
from app.models.quality_assessment import QualityAssessment, QualityDimensionScore
from app.models.requirement import Requirement
from app.models.user import User
from app.modules.planning import passport_service


def test_passport_lifecycle_from_unready_to_ready():
    """Verify that a story transitions through the trust-calibrated passport:
    1. Unready when quality gate < 75.
    2. Unready when quality passes but decomposition misses retry behavior.
    3. Unready when decomposition passes but story points are not assigned.
    4. Ready once all gates pass and story points are assigned.
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        user = User(
            id=uuid.uuid4(),
            keycloak_sub=f"sub-{uuid.uuid4()}",
            role=UserRole.STUDENT,
            name="Passport Test Student",
        )
        db.add(user)
        db.flush()

        group_code = f"T{uuid.uuid4().hex[:6].upper()}"
        group = Group(id=uuid.uuid4(), code=group_code, name="Passport Group")
        db.add(group)
        db.flush()

        db.add(GroupMember(group_id=group.id, user_id=user.id))
        db.flush()

        proj = Project(
            id=uuid.uuid4(),
            group_id=group.id,
            created_by_id=user.id,
            title="Passport Test Project",
        )
        db.add(proj)
        db.flush()

        sess = PipelineSession(
            id=uuid.uuid4(),
            project_id=proj.id,
            group_id=group.id,
            initiated_by=user.id,
            status=SessionStatus.ACTIVE,
        )
        db.add(sess)
        db.flush()

        req = Requirement(
            id=uuid.uuid4(),
            project_id=proj.id,
            group_id=group.id,
            pipeline_session_id=sess.id,
            requirement_ref="FR-ORD-014",
            requirement_text="The system shall notify user on order status and retry delivery notification after 24 hours.",
        )
        db.add(req)
        db.flush()

        story_ref = f"US-ORD-{uuid.uuid4().hex[:6].upper()}"
        story = UserStory(
            id=uuid.uuid4(),
            requirement_id=req.id,
            pipeline_session_id=sess.id,
            story_ref=story_ref,
            title="Order Status Notification",
            description="As a customer, I want notification so that I know status.",
            status=StoryStatus.DRAFT,
            priority=Priority.HIGH,
        )
        db.add(story)
        db.flush()

        # Step 1: No assessments -> Not Ready
        p1 = passport_service.evaluate_story_passport(db, sess.id, story.id)
        assert p1.overall_status == ReadyBacklogStatus.NOT_READY
        assert p1.quality_gate_passed is False
        assert "not evaluated" in p1.quality_status.lower()

        # Add passing quality assessment (82/100)
        qa = QualityAssessment(
            id=uuid.uuid4(),
            requirement_id=req.id,
            pipeline_session_id=sess.id,
            revision_number=1,
            requirement_text_snapshot=req.requirement_text,
            composite_score=82.0,
            confidence_level=ConfidenceLevel.HIGH,
        )
        db.add(qa)
        db.flush()

        # Step 2: Quality passed, but Decomposition missing retry behavior -> Not Ready
        dec = DecompositionAssessment(
            id=uuid.uuid4(),
            requirement_id=req.id,
            pipeline_session_id=sess.id,
            readiness_status=DecompositionReadiness.NEEDS_ATTENTION,
            decomposition_quality_score=2.5,
            quality_band=QualityBand.MODERATE,
            coverage_score=60.0,
            confidence_level=ConfidenceLevel.HIGH,
        )
        db.add(dec)
        db.flush()

        missing_retry = CoverageElementRow(
            id=uuid.uuid4(),
            decomposition_assessment_id=dec.id,
            element_type=CoverageElementType.RECOVERY_RETRY,
            description="Retry notification after 24 hours",
            coverage_result=CoverageResult.MISSING,
        )
        db.add(missing_retry)
        db.flush()

        p2 = passport_service.evaluate_story_passport(db, sess.id, story.id)
        assert p2.overall_status == ReadyBacklogStatus.NOT_READY
        assert p2.quality_gate_passed is True
        assert p2.decomposition_gate_passed is False
        assert "retry" in p2.coverage_status.lower()
        assert "retry" in p2.readiness_gap.lower()
        assert "retry" in p2.student_action_required.lower()

        # Step 3: Fix coverage and add INVEST validations, but no story points yet
        missing_retry.coverage_result = CoverageResult.COVERED
        dec.coverage_score = 90.0
        db.flush()

        for crit in [
            InvestCriterion.INDEPENDENT,
            InvestCriterion.NEGOTIABLE,
            InvestCriterion.VALUABLE,
            InvestCriterion.ESTIMABLE,
            InvestCriterion.SMALL,
            InvestCriterion.TESTABLE,
        ]:
            db.add(
                InvestValidation(
                    decomposition_assessment_id=dec.id,
                    user_story_id=story.id,
                    pipeline_session_id=sess.id,
                    criterion=crit,
                    result=InvestResult.PASS,
                    is_satisfied=True,
                )
            )
        db.flush()

        p3 = passport_service.evaluate_story_passport(db, sess.id, story.id)
        assert p3.overall_status == ReadyBacklogStatus.READY_WITH_WARNINGS
        assert p3.quality_gate_passed is True
        assert p3.decomposition_gate_passed is True
        assert p3.invest_gate_passed is True
        assert p3.points_assigned is False
        assert "story points" in p3.readiness_gap.lower()

        # Step 4: Assign story points -> Transitions to READY!
        story.student_story_points = 5
        db.flush()

        p4 = passport_service.evaluate_story_passport(db, sess.id, story.id)
        assert p4.overall_status == ReadyBacklogStatus.READY
        assert p4.quality_gate_passed is True
        assert p4.decomposition_gate_passed is True
        assert p4.invest_gate_passed is True
        assert p4.points_assigned is True
        assert "5 pts" in p4.estimation_status
        assert "satisfied" in p4.readiness_gap.lower()
        db.commit()

        # Step 5: Test API endpoints using TestClient
        mock_current_user = CurrentUser(
            user_id=user.keycloak_sub,
            username="passportstudent",
            role=UserRole.STUDENT,
            roles=["student"],
        )
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        client = TestClient(app)
        try:
            headers = {"X-Team-Id": group.code}
            resp = client.get("/api/v1/planning/passports", headers=headers)
            assert resp.status_code == 200
            passports = resp.json()["passports"]
            assert len(passports) >= 1
            matched = next(p for p in passports if p["user_story_id"] == str(story.id))
            assert matched["overall_status"] == "ready"
            assert matched["quality_gate_passed"] is True
            assert matched["decomposition_gate_passed"] is True
            assert matched["invest_gate_passed"] is True
            assert matched["points_assigned"] is True

            # Test single passport endpoint
            resp_single = client.get(f"/api/v1/planning/passports/{story.story_ref}", headers=headers)
            assert resp_single.status_code == 200
            single_p = resp_single.json()["passport"]
            assert single_p["overall_status"] == "ready"
            assert single_p["estimation_status"] == "Assigned: 5 pts"
        finally:
            app.dependency_overrides.clear()
    finally:
        db.close()
        db_clean = session_factory()
        try:
            db_clean.execute(BacklogReadinessPassport.__table__.delete().where(BacklogReadinessPassport.pipeline_session_id == sess.id))
            db_clean.execute(InvestValidation.__table__.delete().where(InvestValidation.pipeline_session_id == sess.id))
            db_clean.execute(CoverageElementRow.__table__.delete().where(CoverageElementRow.decomposition_assessment_id == dec.id))
            db_clean.execute(DecompositionAssessment.__table__.delete().where(DecompositionAssessment.pipeline_session_id == sess.id))
            db_clean.execute(QualityAssessment.__table__.delete().where(QualityAssessment.pipeline_session_id == sess.id))
            db_clean.execute(UserStory.__table__.delete().where(UserStory.pipeline_session_id == sess.id))
            db_clean.execute(Requirement.__table__.delete().where(Requirement.pipeline_session_id == sess.id))
            db_clean.execute(PipelineSession.__table__.delete().where(PipelineSession.id == sess.id))
            db_clean.execute(Project.__table__.delete().where(Project.id == proj.id))
            db_clean.execute(GroupMember.__table__.delete().where(GroupMember.group_id == group.id))
            db_clean.execute(Group.__table__.delete().where(Group.id == group.id))
            db_clean.execute(User.__table__.delete().where(User.id == user.id))
            db_clean.commit()
        except Exception:
            db_clean.rollback()
        finally:
            db_clean.close()
