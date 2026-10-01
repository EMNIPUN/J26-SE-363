"""Tests for lecturer review node (T5.9 & PLAN.md Section 9 Node 10)."""

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

    # Lecturer conducts interview and adjusts score upwards to 0.78
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

    # Lecturer reviews and approves score as-is
    resume_payload = {
        "override_score": None,
        "reason": "Reviewed and confirmed legitimate work pattern.",
        "lecturer_id": "LEC-002",
    }

    updates = await lecturer_review_node(state, mock_resume_value=resume_payload)

    assert updates["current_step"] == "lecturer_review_completed"
    assert updates["lecturer_reviewed"] is True
    assert updates["lecturer_override_score"] is None
    # Score was not overridden
    assert "final_score" not in updates or updates.get("final_score") is None or updates.get("final_score") == state["final_score"]
    assert updates["lecturer_id"] == "LEC-002"
