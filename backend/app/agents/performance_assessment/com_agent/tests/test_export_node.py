"""Tests for export results node (T5.13 & PLAN.md Section 9 Node 16 & Section 12.3)."""

import json
import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput
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

    with open(feed_file, "r", encoding="utf-8") as f:
        feed_data = json.load(f)
    assert feed_data["student_id"] == "STU-001"
    assert feed_data["final_score"] == 0.86
    # Student portal JSON must NOT contain instructor dossier
    assert "instructor_report_markdown" not in feed_data
    assert "student_feedback_markdown" in feed_data
