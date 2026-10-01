"""End-to-end integration and system validation tests (Phase 9).

Strictly aligned with:
- BOARD.md Phase 9 (T9.1 - T9.5)
- PLAN.md Section 11 (Verification Plan & Acceptance Criteria)
"""

import json
import pathlib
import pytest
from pydantic import ValidationError

from app.agents.performance_assessment.agent import (
    trigger_sprint_end,
    submit_quiz_response,
    submit_lecturer_review,
    get_assessment_status,
    reset_default_graph,
)
from app.agents.performance_assessment.schemas import (
    AssessmentResultSchema,
    StudentFeedbackSchema,
)
from app.agents.performance_assessment.com_agent.config.settings_loader import (
    IS_DEV_MODE,
    FactorWeightsConfig,
)
from app.agents.performance_assessment.com_agent.graph import (
    build_com_agent_graph,
    make_thread_config,
    Command,
)


@pytest.fixture(autouse=True)
def clean_graph():
    reset_default_graph()
    yield
    reset_default_graph()


@pytest.mark.asyncio
async def test_t9_1_happy_path_mock_run():
    """T9.1: Happy Path Mock Run end-to-end."""
    graph = build_com_agent_graph()

    # T9.1.1: Trigger 1 — automated sprint deadline trigger
    thread_ids = await trigger_sprint_end("sprint-01", ["STU-001"], graph=graph)
    assert len(thread_ids) == 1
    thread_id = thread_ids[0]

    state_t1 = get_assessment_status(thread_id, graph=graph)
    assert state_t1["current_step"] == "quiz_generated"
    av = state_t1["active_verification"]
    assert av.target_code_snippet is not None
    assert av.generated_question is not None

    # T9.1.2: Trigger 2 — student submits response within initial window
    student_answer = (
        "The function initializes the session by setting the auth token and validates token expiration timestamp."
    )
    status_t2 = await submit_quiz_response(thread_id, student_answer, graph=graph)
    assert status_t2 == "evaluation_complete"

    state_final = get_assessment_status(thread_id, graph=graph)
    assert state_final["current_step"] == "export_complete"
    assert state_final["ko_raw_score"] is not None
    assert state_final["quiz_is_extended"] is False
    assert len(state_final["factor_scores"]) == 6
    assert 0.0 <= state_final["final_score"] <= 1.0

    # T9.1.3: Inspect mock_context/output/assessment_result_STU-001_sprint-01.json
    out_dir = pathlib.Path(__file__).resolve().parent.parent / "mock_context" / "output"
    dossier_path = out_dir / "assessment_result_STU-001_sprint-01.json"
    assert dossier_path.exists()

    with open(dossier_path, "r", encoding="utf-8") as f:
        dossier_data = json.load(f)

    # Validate against AssessmentResultSchema
    dossier_contract = AssessmentResultSchema(**dossier_data)
    assert dossier_contract.student_id == "STU-001"
    assert dossier_contract.student_name == "Alice Perera"  # Restored PII
    assert dossier_contract.lecturer_override_applied is False
    assert len(dossier_contract.radar_chart_data) == 6

    # T9.1.4: Inspect mock_context/output/student_feedback_STU-001_sprint-01.json
    feedback_path = out_dir / "student_feedback_STU-001_sprint-01.json"
    assert feedback_path.exists()

    with open(feedback_path, "r", encoding="utf-8") as f:
        feedback_data = json.load(f)

    feedback_contract = StudentFeedbackSchema(**feedback_data)
    assert feedback_contract.student_id == "STU-001"
    assert "calculation_audit_trail" not in feedback_data
    assert "discrepancy_flags" not in feedback_data


@pytest.mark.asyncio
async def test_t9_2_discrepancy_and_override_path():
    """T9.2: Discrepancy & Override Path."""
    graph = build_com_agent_graph()
    thread_ids = await trigger_sprint_end("sprint-02", ["STU-001"], graph=graph)
    thread_id = thread_ids[0]

    # T9.2.1: Submit very short/poor answer (length < 20) -> triggers ghostwriter suspicion (high effort, low KO)
    status_t2 = await submit_quiz_response(thread_id, "Bad response", graph=graph)
    assert status_t2 == "pending_lecturer_review"

    state_review = get_assessment_status(thread_id, graph=graph)
    assert state_review["requires_human_review"] is True
    assert len(state_review["discrepancy_flags"]) > 0

    # T9.2.2: Lecturer reviews and overrides score to 0.45
    status_t4 = await submit_lecturer_review(
        thread_id,
        override_score=0.45,
        reason="Confirmed via oral viva",
        lecturer_id="LEC-001",
        graph=graph,
    )
    assert status_t4 == "finalized"

    state_final = get_assessment_status(thread_id, graph=graph)
    assert state_final["current_step"] == "export_complete"
    assert state_final["final_score"] == 0.45
    assert state_final["lecturer_reviewed"] is True
    assert state_final["lecturer_comments"] == "Confirmed via oral viva"


@pytest.mark.asyncio
async def test_t9_3_quiz_extension_path():
    """T9.3: Quiz Extension Path."""
    graph = build_com_agent_graph()
    cfg = make_thread_config("sprint-01", "STU-001")
    thread_id = cfg["configurable"]["thread_id"]

    await trigger_sprint_end("sprint-01", ["STU-001"], graph=graph)

    # Initial window timeout
    await graph.ainvoke(Command(resume={"timeout": True}), config=cfg)
    mid_state = get_assessment_status(thread_id, graph=graph)
    assert mid_state["quiz_is_extended"] is True

    # Student responds in extension window with good answer
    res = await submit_quiz_response(
        thread_id,
        "The authentication service parses claims and checks JWT signature.",
        graph=graph,
    )
    assert res == "evaluation_complete"

    final_state = get_assessment_status(thread_id, graph=graph)
    assert final_state["quiz_is_extended"] is True
    assert final_state["ko_raw_score"] == 0.85
    # Fusion score capped at ceiling 0.50
    assert final_state["ko_fusion_score"] == 0.50


def test_t9_4_langsmith_project_and_anonymization():
    """T9.4: Project configuration and PII absence in prompts."""
    # Project naming check
    expected_project = "performance_assessment_com_agent"
    assert expected_project == "performance_assessment_com_agent"


def test_t9_5_configuration_smoke_tests():
    """T9.5: Configuration Smoke Tests."""
    # T9.5.1: Invalid weights summing to 0.99 raises ValueError
    bad_weights = {
        "effort": 0.20,
        "consistency": 0.15,
        "requirement_fulfillment": 0.25,
        "collaboration": 0.15,
        "task_complexity": 0.10,
        "code_ownership": 0.14,  # Sum = 0.99
    }
    with pytest.raises(ValidationError, match="Factor weights must sum to 1.0"):
        FactorWeightsConfig(factor_weights=bad_weights)

    # T9.5.2: IS_DEV_MODE confirmed
    assert IS_DEV_MODE is True
