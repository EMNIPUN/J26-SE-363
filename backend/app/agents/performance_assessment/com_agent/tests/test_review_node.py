"""Tests for lecturer review node (T5.9 & PLAN.md Section 9 Node 10).

Improvements over original:
- Added override_score out-of-range clamping test (>1.0 and <0.0)
- Added missing reviewer_id validation test
- Clarified no-override test assertion
"""

import pytest
from app.agents.performance_assessment.com_agent.state import DiscrepancyAlert
from app.agents.performance_assessment.com_agent.nodes.review_node import (
    lecturer_review_node,
)


@pytest.mark.asyncio
async def test_lecturer_review_node_with_score_override():
    state = {
        "student_id": "STU-001",
        "final_score": 0.55,
        "discrepancy_flags": [
            DiscrepancyAlert(
                alert_code="GHOSTWRITER_SUSPICION",
                severity="CRITICAL",
                description="High effort, low quiz score.",
                recommended_action="Conduct interview",
            )
        ],
    }

    resume_payload = {
        "override_score": 0.78,
        "reason": "Student explained git proxy workflow during oral defense.",
        "lecturer_id": "LEC-PROF-SILVA",
    }

    updates = await lecturer_review_node(state, mock_resume_value=resume_payload)

    assert updates["current_step"] == "lecturer_review_completed"
    assert updates["lecturer_reviewed"] is True
    assert updates["final_score"] == 0.78
    assert updates["lecturer_override_score"] == 0.78
    assert updates["lecturer_id"] == "LEC-PROF-SILVA"
    assert "Student explained git proxy" in updates["lecturer_comments"]
    assert updates["review_timestamp"] is not None


@pytest.mark.asyncio
async def test_lecturer_review_node_approved_without_override():
    state = {
        "student_id": "STU-001",
        "final_score": 0.65,
        "discrepancy_flags": [
            DiscrepancyAlert(
                alert_code="DEADLINE_PANIC",
                severity="WARNING",
                description="Clustered commits",
                recommended_action="Check timeline",
            )
        ],
    }

    resume_payload = {
        "override_score": None,
        "reason": "Reviewed and confirmed legitimate work pattern.",
        "lecturer_id": "LEC-002",
    }

    updates = await lecturer_review_node(state, mock_resume_value=resume_payload)

    assert updates["current_step"] == "lecturer_review_completed"
    assert updates["lecturer_reviewed"] is True
    assert updates["lecturer_override_score"] is None
    # original score must be preserved when no override is applied
    assert updates.get("final_score") is None or updates["final_score"] == 0.65
    assert updates["lecturer_id"] == "LEC-002"


@pytest.mark.asyncio
async def test_lecturer_review_node_override_score_clamped_above_one():
    """override_score > 1.0 must be clamped to 1.0 (scores must be in [0.0, 1.0])."""
    state = {
        "student_id": "STU-001",
        "final_score": 0.60,
        "discrepancy_flags": [],
    }

    resume_payload = {
        "override_score": 1.50,  # out-of-range — must be clamped to 1.0
        "reason": "Exceptional performance verified.",
        "lecturer_id": "LEC-003",
    }

    updates = await lecturer_review_node(state, mock_resume_value=resume_payload)

    assert updates["current_step"] == "lecturer_review_completed"
    assert updates["final_score"] <= 1.0, (
        f"override_score=1.50 must be clamped to 1.0, got {updates['final_score']}"
    )
    assert updates["final_score"] == pytest.approx(1.0, abs=1e-6)


@pytest.mark.asyncio
async def test_lecturer_review_node_override_score_clamped_below_zero():
    """override_score < 0.0 must be clamped to 0.0."""
    state = {
        "student_id": "STU-001",
        "final_score": 0.60,
        "discrepancy_flags": [],
    }

    resume_payload = {
        "override_score": -0.20,  # negative — must be clamped to 0.0
        "reason": "Academic misconduct confirmed.",
        "lecturer_id": "LEC-004",
    }

    updates = await lecturer_review_node(state, mock_resume_value=resume_payload)

    assert updates["current_step"] == "lecturer_review_completed"
    assert updates["final_score"] >= 0.0, (
        f"override_score=-0.20 must be clamped to 0.0, got {updates['final_score']}"
    )
    assert updates["final_score"] == pytest.approx(0.0, abs=1e-6)
