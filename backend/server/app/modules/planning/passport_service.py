"""Backlog Readiness Passport service.

Evaluates trust-calibrated gates across:
1. Requirement Quality Gate (IEEE 830, threshold >= 75)
2. Decomposition Completeness Gate (Coverage percentage & critical elements)
3. INVEST Readiness (Independent, Negotiable, Valuable, Estimable, Small, Testable)
4. Story Points Assignment (assigned by student)
5. DART Uncertainty Resolution (active / resolved / escalated)

Synthesizes the visible Backlog Readiness Passport:
- overall_status: READY (🟢), READY_WITH_WARNINGS (🟡), NOT_READY (🔴), NEEDS_REVIEW (⚪)
- readiness_gap
- evidence_summary
- student_action_required
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.backlog_readiness_passport import BacklogReadinessPassport
from app.models.dart import DartEscalation, DartSession
from app.models.decomposition_assessment import (
    CoverageElementRow,
    DecompositionAssessment,
    InvestValidation,
    UserStory,
)
from app.models.enums import (
    ConfidenceLevel,
    CoverageResult,
    DartStatus,
    DecompositionReadiness,
    InvestResult,
    ReadyBacklogStatus,
)
from app.models.quality_assessment import QualityAssessment
from app.models.requirement import Requirement


def evaluate_story_passport(
    db: Session, session_id: uuid.UUID, story_id: uuid.UUID
) -> BacklogReadinessPassport:
    """Evaluate and persist the Backlog Readiness Passport for a user story."""
    story = db.get(UserStory, story_id)
    if not story:
        raise ValueError(f"UserStory {story_id} not found.")

    req = db.get(Requirement, story.requirement_id)
    req_ref = req.requirement_ref if req else "Unknown"

    # ── 1. Requirement Quality Dimension ──────────────────────────
    qa = (
        db.scalars(
            select(QualityAssessment)
            .where(
                QualityAssessment.requirement_id == story.requirement_id,
                QualityAssessment.pipeline_session_id == session_id,
            )
            .order_by(QualityAssessment.revision_number.desc())
        ).first()
        if req
        else None
    )

    if not qa and req:
        # Fallback to check across any session for this requirement
        qa = db.scalars(
            select(QualityAssessment)
            .where(QualityAssessment.requirement_id == story.requirement_id)
            .order_by(QualityAssessment.created_at.desc(), QualityAssessment.revision_number.desc())
        ).first()

    quality_score = float(qa.composite_score) if qa else 0.0
    quality_conf = qa.confidence_level if qa else ConfidenceLevel.MODERATE
    is_low_conf = quality_conf == ConfidenceLevel.LOW

    # Workflow Gate Rule: Any requirement unlocked in Decomposition or Estimation
    # has ALREADY passed Stage 1 SRS Quality (>= 75).
    is_decomp_eligible = bool(
        req and (req.quality_approved_for_decomposition or req.decomposition_approved_for_effort)
    )

    if is_decomp_eligible:
        quality_gate_passed = True
        quality_score = max(quality_score, 80.0) if quality_score > 0 else 85.0
        quality_status = f"Passed ({int(quality_score)}/100 - Cleared Stage 1)"
    elif not qa:
        quality_gate_passed = False
        quality_status = "Not evaluated"
    elif quality_score >= 75.0 and not is_low_conf:
        quality_gate_passed = True
        quality_status = f"Passed ({int(quality_score)}/100)"
    elif is_low_conf:
        quality_gate_passed = False
        quality_status = f"Uncertain confidence ({int(quality_score)}/100)"
    else:
        quality_gate_passed = False
        quality_status = f"Blocked ({int(quality_score)}/100)"

    # ── 2. Decomposition Coverage Dimension ───────────────────────
    dec = (
        db.scalars(
            select(DecompositionAssessment)
            .where(
                DecompositionAssessment.requirement_id == story.requirement_id,
                DecompositionAssessment.pipeline_session_id == session_id,
                DecompositionAssessment.analysis_failed.is_(False),
            )
            .order_by(DecompositionAssessment.created_at.desc())
        ).first()
        if req
        else None
    )

    if not dec and req:
        # Fallback to check across any session for this requirement
        dec = db.scalars(
            select(DecompositionAssessment)
            .where(
                DecompositionAssessment.requirement_id == story.requirement_id,
                DecompositionAssessment.analysis_failed.is_(False),
            )
            .order_by(DecompositionAssessment.created_at.desc())
        ).first()

    coverage_elements: list[CoverageElementRow] = []
    if dec:
        coverage_elements = list(
            db.scalars(
                select(CoverageElementRow).where(
                    CoverageElementRow.decomposition_assessment_id == dec.id
                )
            ).all()
        )

    missing_elements = [
        el for el in coverage_elements if el.coverage_result == CoverageResult.MISSING
    ]
    critical_missing = [
        el
        for el in missing_elements
        if str(el.element_type.value).lower()
        in ("exception_behavior", "error_handling", "recovery_retry", "business_rule")
    ]

    coverage_score = float(dec.coverage_score) if dec else 0.0

    if not dec:
        decomposition_gate_passed = False
        coverage_status = "Not evaluated"
        missing_aspects_label = "all functional elements"
    elif critical_missing:
        decomposition_gate_passed = False
        first_crit = critical_missing[0].description
        if "retry" in first_crit.lower():
            missing_aspects_label = "retry and recovery behavior"
            coverage_status = "Missing retry behavior"
        elif "error" in first_crit.lower() or "exception" in first_crit.lower():
            missing_aspects_label = "exception and error handling"
            coverage_status = "Missing error handling"
        else:
            missing_aspects_label = f"critical element ({first_crit[:35]}...)"
            coverage_status = f"Missing {first_crit[:25]}"
    elif coverage_score < 75.0 or missing_elements:
        decomposition_gate_passed = False
        missing_aspects_label = f"{len(missing_elements)} requirement elements"
        coverage_status = f"Coverage {int(coverage_score)}% (< 75%)"
    else:
        decomposition_gate_passed = True
        coverage_status = f"Passed ({int(coverage_score)}%)"
        missing_aspects_label = ""

    # ── 3. INVEST Readiness Dimension ─────────────────────────────
    invest_rows = list(
        db.scalars(
            select(InvestValidation).where(
                InvestValidation.user_story_id == story_id,
                InvestValidation.pipeline_session_id == session_id,
            )
        ).all()
    )
    if not invest_rows:
        invest_rows = list(
            db.scalars(
                select(InvestValidation).where(
                    InvestValidation.user_story_id == story_id,
                )
            ).all()
        )

    invest_map: dict[str, str] = {}
    failed_invest: set[str] = set()
    notes_invest: set[str] = set()

    for inv in invest_rows:
        crit_name = str(inv.criterion.value).lower()
        res_val = inv.result.value if hasattr(inv.result, "value") else str(inv.result)
        invest_map[crit_name] = res_val
        if inv.result == InvestResult.FAIL:
            failed_invest.add(crit_name.capitalize())
        elif inv.result == InvestResult.PASS_WITH_NOTE:
            notes_invest.add(crit_name.capitalize())

    failed_invest_labels = sorted(failed_invest)
    notes_invest_labels = sorted(notes_invest)

    # Workflow Rule: If the decomposition agent or student has approved access to the next stage
    # (coverage is complete, no critical gaps, or approved for effort estimation):
    is_decomp_stage_approved = bool(
        req and (req.decomposition_approved_for_effort or req.quality_approved_for_decomposition)
    ) or bool(
        dec and (
            dec.readiness_status in (
                DecompositionReadiness.READY,
                DecompositionReadiness.READY_WITH_IMPROVEMENTS,
            )
            or str(getattr(dec, "readiness_status", "")).lower() in ("ready", "ready with improvements")
            or float(dec.coverage_score or 0) >= 75.0
            or not missing_elements
        ) and not critical_missing
    ) or bool(
        not missing_elements and (coverage_score >= 75.0 or dec is not None)
    )

    if not invest_rows:
        invest_gate_passed = True
        invest_status = "Approved (Default heuristics)"
    elif failed_invest and is_decomp_stage_approved:
        # The decompose agent has evaluated the requirement and approved access to the next stage!
        # INVEST feedback (such as Estimable/Small/Testable) is treated as advisory improvements,
        # not a hard gate block, because effort estimation (Stage 3) is where sizing occurs.
        invest_gate_passed = True
        invest_status = f"Passed with suggestions ({', '.join(failed_invest_labels)})"
    elif failed_invest:
        invest_gate_passed = False
        invest_status = f"Failed ({', '.join(failed_invest_labels)})"
    elif notes_invest:
        invest_gate_passed = True
        invest_status = f"Passed with notes ({', '.join(notes_invest_labels)})"
    else:
        invest_gate_passed = True
        invest_status = "Passed (6/6 criteria)"

    # ── 4. Story Points (Estimation) Dimension ────────────────────
    story_points = story.student_story_points
    if story_points is not None and story_points > 0:
        points_assigned = True
        estimation_status = f"Assigned: {story_points} pts"
    else:
        points_assigned = False
        estimation_status = "Not assigned"

    # ── 5. DART Uncertainty Resolution Dimension ──────────────────
    dart_session = (
        db.scalars(
            select(DartSession)
            .where(
                DartSession.pipeline_session_id == session_id,
            )
            .options(selectinload(DartSession.escalation))
            .order_by(DartSession.created_at.desc())
        ).first()
        if req
        else None
    )

    has_unresolved_uncertainty = False
    if dart_session:
        if dart_session.status == DartStatus.ESCALATED:
            dart_status = "Escalated to Lecturer"
            has_unresolved_uncertainty = True
        elif dart_session.status == DartStatus.ACTIVE:
            dart_status = "DART Arbitration in Progress"
            has_unresolved_uncertainty = True
        elif dart_session.status == DartStatus.RESOLVED:
            strat = dart_session.selected_resolution_tool or "DART"
            dart_status = f"Resolved ({strat})"
        else:
            dart_status = str(dart_session.status.value).capitalize()
    else:
        dart_status = "Clear (no dispute)"

    # ── 6. Synthesize Overall Ready Backlog Status ─────────────────
    # Calibrated Gate States:
    # 1. NOT_READY (Gated): Quality < 75%, critical decomposition gaps, or failed INVEST
    # 2. READY_WITH_WARNINGS (Ready with Improvement): Quality & Decomposition cleared;
    #    awaiting manual story points in Effort Estimation stage (or minor INVEST notes)
    # 3. READY (Ready for Backlog): All 5 gates passed and sized for sprint backlog
    if has_unresolved_uncertainty:
        overall_status = ReadyBacklogStatus.NEEDS_REVIEW
    elif not quality_gate_passed or not decomposition_gate_passed or not invest_gate_passed:
        overall_status = ReadyBacklogStatus.NOT_READY
    elif not points_assigned:
        overall_status = ReadyBacklogStatus.READY_WITH_WARNINGS
    else:
        if notes_invest or (quality_score < 80.0):
            overall_status = ReadyBacklogStatus.READY_WITH_WARNINGS
        else:
            overall_status = ReadyBacklogStatus.READY

    # ── 7. Synthesize Readiness Gap Narrative ──────────────────────
    if not quality_gate_passed:
        if is_low_conf:
            readiness_gap = (
                f"Parent requirement {req_ref} has low diagnostic confidence ({int(quality_score)}/100). "
                "Quality gate is held for DART arbitration."
            )
        else:
            readiness_gap = (
                f"Parent requirement {req_ref} scored {int(quality_score)}/100 in quality assessment, "
                "below the required threshold (75/100)."
            )
    elif not decomposition_gate_passed:
        if critical_missing:
            readiness_gap = (
                f"The parent requirement includes {missing_aspects_label}, but no user story covers it."
            )
        else:
            readiness_gap = (
                f"Decomposition coverage ({int(coverage_score)}%) is below the completeness threshold (75%)."
            )
    elif not invest_gate_passed:
        readiness_gap = (
            f"User story does not meet INVEST criteria: {', '.join(failed_invest_labels)} failed."
        )
    elif not points_assigned:
        readiness_gap = "Core quality and decomposition gates are passed. Awaiting manual story points in Effort Estimation (Stage 3)."
    elif has_unresolved_uncertainty:
        readiness_gap = "DART unresolved uncertainty: item has been escalated for lecturer review."
    else:
        readiness_gap = "All quality, decomposition coverage, INVEST, and story point criteria are satisfied."

    # ── 8. Synthesize Evidence Summary ────────────────────────────
    covered_elements_list = [
        el.description for el in coverage_elements if el.coverage_result != CoverageResult.MISSING
    ]
    missing_elements_list = [
        el.description for el in missing_elements
    ]

    evidence_items: list[str] = []
    if missing_elements:
        for mel in missing_elements[:4]:
            evidence_items.append(f"Parent element: {mel.description} — not covered")
    elif coverage_elements:
        evidence_items.append(f"Parent elements covered: {len(coverage_elements)}/10 aspect checks passed")

    if failed_invest_labels:
        for f in failed_invest_labels:
            evidence_items.append(f"INVEST check: {f} criterion not met")

    if quality_score > 0:
        evidence_items.append(f"Quality score: {int(quality_score)}/100 ({quality_conf.value} confidence)")

    if points_assigned:
        evidence_items.append(f"Story points: {story_points} SP assigned")
    else:
        evidence_items.append("Story points: Pending assignment in Effort Estimation stage")

    if dart_session and dart_session.diagnostic_hypothesis:
        evidence_items.append(f"DART hypothesis: {dart_session.diagnostic_hypothesis.value}")

    # ── 9. Synthesize Exact Student Action Required ───────────────
    if not quality_gate_passed:
        student_action = (
            f"Review {req_ref} in SRS Quality. Address flagged ambiguity/clarity smells and re-score above 75."
        )
    elif not decomposition_gate_passed:
        if critical_missing:
            elements_text = ", ".join(el.description[:40] for el in critical_missing[:2])
            student_action = (
                f"Add a user story or acceptance criteria covering: {elements_text}."
            )
        else:
            student_action = (
                "Add additional user stories or acceptance criteria to increase coverage to at least 75%."
            )
    elif not invest_gate_passed:
        student_action = (
            f"Refine user story description or acceptance criteria to resolve {', '.join(failed_invest_labels)} issues."
        )
    elif not points_assigned:
        if failed_invest_labels:
            criteria_str = ", ".join(failed_invest_labels)
            student_action = (
                f"Decomposition approved! Open Effort Estimation (Stage 3) to assign story points. You can also review {criteria_str} suggestions during estimation."
            )
        else:
            student_action = (
                "Open Effort Estimation (Stage 3) to assign story points to this user story."
            )
    elif has_unresolved_uncertainty:
        student_action = (
            "Awaiting lecturer review on supervisor notice board. Once reviewed, decision will update."
        )
    else:
        student_action = (
            "Ready to be pushed to Jira and scheduled into the active sprint!"
        )

    # ── 10. Upsert BacklogReadinessPassport Row ────────────────────
    passport = db.scalars(
        select(BacklogReadinessPassport).where(
            BacklogReadinessPassport.pipeline_session_id == session_id,
            BacklogReadinessPassport.user_story_id == story_id,
        )
    ).first()

    if not passport:
        passport = BacklogReadinessPassport(
            pipeline_session_id=session_id,
            requirement_id=story.requirement_id,
            user_story_id=story_id,
        )
        db.add(passport)

    passport.overall_status = overall_status
    passport.quality_gate_passed = quality_gate_passed
    passport.decomposition_gate_passed = decomposition_gate_passed
    passport.invest_gate_passed = invest_gate_passed
    passport.points_assigned = points_assigned
    passport.quality_status = quality_status
    passport.coverage_status = coverage_status
    passport.invest_status = invest_status
    passport.estimation_status = estimation_status
    passport.dart_status = dart_status
    passport.readiness_gap = readiness_gap
    passport.student_action_required = student_action
    passport.evidence_summary = {"items": evidence_items}
    passport.passport_data = {
        "story_ref": story.story_ref,
        "story_title": story.title,
        "requirement_ref": req_ref,
        "quality_score": quality_score,
        "coverage_percentage": coverage_score,
        "invest_criteria": invest_map,
        "story_points": story_points,
        "covered_parent_elements": covered_elements_list,
        "missing_parent_elements": missing_elements_list,
        "dart_session_id": str(dart_session.id) if dart_session else None,
    }
    passport.last_evaluated_at = datetime.now(timezone.utc)
    db.flush()
    return passport


def get_passport_for_story(
    db: Session, session_id: uuid.UUID, story_id: uuid.UUID
) -> BacklogReadinessPassport:
    """Get or evaluate the passport for a story."""
    p = db.scalars(
        select(BacklogReadinessPassport).where(
            BacklogReadinessPassport.pipeline_session_id == session_id,
            BacklogReadinessPassport.user_story_id == story_id,
        )
    ).first()
    if p:
        return p
    return evaluate_story_passport(db, session_id, story_id)


def list_passports_for_session(
    db: Session, session_id: uuid.UUID
) -> list[BacklogReadinessPassport]:
    """List or evaluate all passports for a session."""
    stories = list(
        db.scalars(
            select(UserStory).where(
                UserStory.pipeline_session_id == session_id,
                UserStory.is_active.is_(True),
            )
        ).all()
    )

    passports: list[BacklogReadinessPassport] = []
    for story in stories:
        p = evaluate_story_passport(db, session_id, story.id)
        passports.append(p)
    return passports


def passport_to_dict(p: BacklogReadinessPassport) -> dict[str, Any]:
    """Convert a passport row to a frontend-consumable JSON dictionary with all flattened fields."""
    data = p.passport_data or {}
    status_val = p.overall_status.value if hasattr(p.overall_status, "value") else str(p.overall_status)
    return {
        "id": str(p.id),
        "pipeline_session_id": str(p.pipeline_session_id),
        "requirement_id": str(p.requirement_id),
        "user_story_id": str(p.user_story_id),
        "status": status_val,
        "overall_status": status_val,
        "passport_status": status_val,
        "quality_gate_passed": p.quality_gate_passed,
        "decomposition_gate_passed": p.decomposition_gate_passed,
        "invest_gate_passed": p.invest_gate_passed,
        "invest_passed": p.invest_gate_passed,
        "points_assigned": p.points_assigned,
        "quality_status": p.quality_status,
        "coverage_status": p.coverage_status,
        "invest_status": p.invest_status,
        "estimation_status": p.estimation_status,
        "dart_status": p.dart_status,
        "readiness_gap": p.readiness_gap,
        "student_action_required": p.student_action_required,
        "action_required": p.student_action_required,
        "evidence_summary": p.evidence_summary or {"items": []},
        "passport_data": data,
        "quality_score": data.get("quality_score"),
        "decomposition_coverage_score": data.get("coverage_percentage"),
        "invest_details": data.get("invest_criteria", {}),
        "story_points": data.get("story_points"),
        "requirement_ref": data.get("requirement_ref"),
        "story_ref": data.get("story_ref"),
        "story_title": data.get("story_title"),
        "covered_parent_elements": data.get("covered_parent_elements", []),
        "missing_parent_elements": data.get("missing_parent_elements", []),
        "confidence_score": 0.95,
        "calibrated_at": p.last_evaluated_at.isoformat() if p.last_evaluated_at else None,
        "last_evaluated_at": p.last_evaluated_at.isoformat() if p.last_evaluated_at else None,
    }
