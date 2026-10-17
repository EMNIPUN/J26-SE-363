"""Tests for export results node (T5.13 & PLAN.md Section 9 Node 16 & Section 12.3).

Improvements:
- Added test with lecturer override applied (verifying audit trail & override flags in export JSON).
- Added test with is_dev=False (verifying no files written to disk in production mode).
- Added strict verification that student_feedback excludes sensitive instructor fields (GDPR/grading audit isolation).
- Added fractional score percentage rounding verification.
"""

import json
import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput, DiscrepancyAlert
from app.agents.performance_assessment.com_agent.nodes.export_node import (
    export_results_node,
)


@pytest.fixture
def complete_assessment_state():
    return {
        "student_id": "STU-001",
        "student_name": "Alice Perera",
        "team_id": "TEAM-A",
        "sprint_id": "sprint-02",
        "final_score": 0.86,
        "additive_score": 0.78,
        "behavioral_modifier": 1.10,
        "behavioral_persona": "Consistent Builder",
        "instructor_report_markdown": "# Formal Instructor Assessment Dossier\n\nStudent performed exceptionally.",
        "student_feedback_markdown": "# Feedback for Alice\n\nGreat job on authentication module!",
        "radar_chart_data": {
            "effort": 0.80,
            "consistency": 0.70,
            "requirement_fulfillment": 0.90,
            "collaboration": 0.60,
            "task_complexity": 0.75,
            "code_ownership": 0.85,
        },
        "factor_scores": {
            "effort": FactorOutput(score=0.80),
            "consistency": FactorOutput(score=0.70),
            "requirement_fulfillment": FactorOutput(score=0.90),
            "collaboration": FactorOutput(score=0.60),
            "task_complexity": FactorOutput(score=0.75),
            "code_ownership": FactorOutput(score=0.85),
        },
        "discrepancy_flags": [],
        "historical_trajectory": [
            {"sprint_id": "sprint-01", "final_score": 0.75, "behavioral_persona": "Balanced Contributor"}
        ],
    }


@pytest.mark.asyncio
async def test_export_results_node_success(tmp_path, complete_assessment_state):
    updates = await export_results_node(
        complete_assessment_state, output_dir=tmp_path, is_dev=True
    )

    assert updates["current_step"] == "export_complete"
    assert "assessment_result" in updates
    assert "student_feedback" in updates

    # Verify files were generated in output_dir
    res_file = tmp_path / "assessment_result_STU-001_sprint-02.json"
    feed_file = tmp_path / "student_feedback_STU-001_sprint-02.json"

    assert res_file.exists(), f"Expected {res_file} to exist"
    assert feed_file.exists(), f"Expected {feed_file} to exist"

    with open(res_file, "r", encoding="utf-8") as f:
        res_data = json.load(f)
    assert res_data["student_id"] == "STU-001"
    assert res_data["final_score"] == 0.86
    assert res_data["final_score_percentage"] == 86.0
    assert "instructor_report_markdown" in res_data
    assert "factor_scores" in res_data
    assert res_data["factor_scores"]["effort"]["label"] == "Effort & Volume"
    assert res_data["lecturer_override_applied"] is False

    with open(feed_file, "r", encoding="utf-8") as f:
        feed_data = json.load(f)
    assert feed_data["student_id"] == "STU-001"
    assert feed_data["final_score"] == 0.86
    # Student portal JSON must NOT contain instructor dossier, discrepancies, or calculation audit trail
    assert "instructor_report_markdown" not in feed_data
    assert "calculation_audit_trail" not in feed_data
    assert "discrepancy_flags" not in feed_data
    assert "student_feedback_markdown" in feed_data


@pytest.mark.asyncio
async def test_export_results_node_with_lecturer_override(tmp_path, complete_assessment_state):
    """Lecturer override must be correctly reflected in exported contracts."""
    state = {
        **complete_assessment_state,
        "final_score": 0.92,
        "lecturer_reviewed": True,
        "lecturer_override_score": 0.92,
        "lecturer_comments": "Verified comprehensive understanding during oral review.",
        "discrepancy_flags": [
            DiscrepancyAlert(
                alert_code="GHOSTWRITER_SUSPICION",
                severity="CRITICAL",
                description="Initial discrepancy resolved by viva.",
                recommended_action="Conduct interview",
            )
        ],
    }

    updates = await export_results_node(state, output_dir=tmp_path, is_dev=True)

    res_data = updates["assessment_result"]
    assert res_data["lecturer_override_applied"] is True
    assert res_data["lecturer_override_score"] == 0.92
    assert res_data["final_score"] == 0.92
    assert res_data["final_score_percentage"] == 92.0
    assert res_data["lecturer_comments"] == "Verified comprehensive understanding during oral review."
    assert len(res_data["discrepancy_flags"]) == 1
    assert res_data["discrepancy_flags"][0]["alert_code"] == "GHOSTWRITER_SUSPICION"


@pytest.mark.asyncio
async def test_export_results_node_prod_mode_no_disk_write(tmp_path, complete_assessment_state):
    """In production mode (is_dev=False), export_results_node must not write files to disk."""
    updates = await export_results_node(
        complete_assessment_state, output_dir=tmp_path, is_dev=False
    )
    assert updates["current_step"] == "export_complete"
    # No files should have been created in output_dir
    files_created = list(tmp_path.glob("*.json"))
    assert files_created == [], f"Expected no files in prod mode, but found: {files_created}"


@pytest.mark.asyncio
async def test_export_results_score_percentage_rounding(tmp_path, complete_assessment_state):
    """Fractional scores must round percentage to 2 decimal places."""
    state = {**complete_assessment_state, "final_score": 0.833333}
    updates = await export_results_node(state, output_dir=tmp_path, is_dev=False)
    assert updates["assessment_result"]["final_score_percentage"] == 83.33
    assert updates["student_feedback"]["final_score_percentage"] == 83.33
