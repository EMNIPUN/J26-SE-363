"""Unit and integration tests for agent execution triggers and lifecycle (Phase 7 & T8.1).

Strictly aligned with:
- BOARD.md Phase 7 (T7.1.1 - T7.1.4, T7.2.1 - T7.2.2)
- BOARD.md Phase 8 (T8.1.1 - T8.1.7)
- PLAN.md Section 2 (The Four Execution Triggers)
"""

import pytest
from app.agents.performance_assessment.agent import (
    trigger_sprint_end,
    submit_quiz_response,
    trigger_on_demand,
    submit_lecturer_review,
    get_assessment_status,
    reset_default_graph,
)
from app.agents.performance_assessment.com_agent.graph import (
    build_com_agent_graph,
    build_initial_state,
    make_thread_config,
    Command,
)
from app.agents.performance_assessment.com_agent.state import (
    DiscrepancyAlert,
    FactorOutput,
)


@pytest.fixture(autouse=True)
def clean_graph():
    reset_default_graph()
    yield
    reset_default_graph()


@pytest.mark.asyncio
async def test_t8_1_1_trigger_1_pause_at_quiz_interrupt():
    """T8.1.1: Trigger 1 -> all 5 passive factors complete -> thread paused at quiz interrupt."""
    graph = build_com_agent_graph()
    thread_ids = await trigger_sprint_end("sprint-02", ["STU-001"], graph=graph)
    assert len(thread_ids) == 1
    thread_id = thread_ids[0]
    assert thread_id == "sprint_sprint-02_student_STU-001"

    status = get_assessment_status(thread_id, graph=graph)
    assert status is not None
    assert status["current_step"] == "quiz_generated"
    # All 5 passive factors present
    for factor in ["effort", "consistency", "requirement_fulfillment", "collaboration", "task_complexity"]:
        assert factor in status["factor_scores"]
    assert status["active_verification"].generated_question is not None


@pytest.mark.asyncio
async def test_t8_1_2_trigger_2_submission_within_window():
    """T8.1.2: Trigger 2 within initial window -> KO scored normally -> fusion runs -> final_score in state."""
    graph = build_com_agent_graph()
    thread_ids = await trigger_sprint_end("sprint-02", ["STU-001"], graph=graph)
    thread_id = thread_ids[0]

    resp_status = await submit_quiz_response(
        thread_id,
        "The JWT token expiration claim is verified before granting access to protected routes.",
        graph=graph,
    )
    assert resp_status == "evaluation_complete"

    status = get_assessment_status(thread_id, graph=graph)
    assert status["current_step"] == "export_complete"
    assert status["final_score"] > 0.0
    assert status["final_score"] <= 1.0
    assert status["active_verification"].is_extended is False
    assert status["active_verification"].ownership_score is not None


@pytest.mark.asyncio
async def test_t8_1_3_trigger_2_extended_window_caps_score():
    """T8.1.3: Trigger 2 after initial window but within extension -> ko_fusion_score <= capped_score_ceiling; quiz_is_extended == True."""
    graph = build_com_agent_graph()
    cfg = make_thread_config("sprint-02", "STU-001")
    thread_id = cfg["configurable"]["thread_id"]

    # Start graph to quiz_generated
    await trigger_sprint_end("sprint-02", ["STU-001"], graph=graph)

    # First event: Timeout signal
    resume_timeout = Command(resume={"timeout": True})
    state_after_timeout = await graph.ainvoke(resume_timeout, config=cfg)
    assert state_after_timeout["current_step"] == "quiz_extended_waiting"
    assert state_after_timeout["quiz_is_extended"] is True

    # Second event: Student submits during extension window
    resp_status = await submit_quiz_response(
        thread_id,
        "The session handler validates the HMAC signature on the payload.",
        graph=graph,
    )
    assert resp_status == "evaluation_complete"

    status = get_assessment_status(thread_id, graph=graph)
    assert status["current_step"] == "export_complete"
    assert status["quiz_is_extended"] is True
    # Verify score capping at 0.50
    ko_output = status["factor_scores"].get("code_ownership")
    assert ko_output is not None
    assert ko_output.score <= 0.50
    assert ko_output.features.get("ko_fusion_score") <= 0.50


@pytest.mark.asyncio
async def test_t8_1_4_both_windows_expired_double_timeout():
    """T8.1.4: Both windows expired -> ko_fusion_score == 0.0; quiz_is_double_timed_out == True."""
    graph = build_com_agent_graph()
    cfg = make_thread_config("sprint-02", "STU-001")
    thread_id = cfg["configurable"]["thread_id"]

    await trigger_sprint_end("sprint-02", ["STU-001"], graph=graph)

    # Timeout 1: Enter extension
    resume_timeout_1 = Command(resume={"timeout": True})
    await graph.ainvoke(resume_timeout_1, config=cfg)

    # Timeout 2: Missed extension
    resume_timeout_2 = Command(resume={"timeout": True})
    final_state = await graph.ainvoke(resume_timeout_2, config=cfg)

    assert final_state["quiz_is_double_timed_out"] is True
    ko_output = final_state["factor_scores"].get("code_ownership")
    assert ko_output is not None
    assert ko_output.score == 0.0

    # High effort (>0.75) + zero ownership (0.0) triggers ghostwriter alert -> lecturer review
    if final_state.get("requires_human_review"):
        assert final_state["current_step"] == "discrepancy_checked"
        rev_status = await submit_lecturer_review(
            thread_id,
            override_score=0.0,
            reason="Confirmed double timeout with student",
            graph=graph,
        )
        assert rev_status == "finalized"
        final_state = get_assessment_status(thread_id, graph=graph)

    assert final_state["current_step"] == "export_complete"


@pytest.mark.asyncio
async def test_t8_1_5_critical_discrepancy_pauses_at_lecturer_review():
    """T8.1.5: CRITICAL discrepancy injected -> thread pauses at lecturer_review_node."""
    graph = build_com_agent_graph()
    cfg = make_thread_config("sprint-02", "STU-001")
    thread_id = cfg["configurable"]["thread_id"]

    await trigger_sprint_end("sprint-02", ["STU-001"], graph=graph)

    # Simulate high effort but low ownership (Ghostwriter suspicion triggers CRITICAL discrepancy)
    # Very short low-quality quiz response gives raw score 0.40
    # In student_context.json, effort is high (story points = 13, 2 completed)
    # To directly verify discrepancy pause, simulate state with critical flag
    saved = get_assessment_status(thread_id, graph=graph) or {}
    saved_updates = {
        "requires_human_review": True,
        "discrepancy_flags": [
            DiscrepancyAlert(
                alert_code="GHOSTWRITER_SUSPICION",
                severity="CRITICAL",
                description="High effort with low ownership detected",
                recommended_action="Conduct oral viva",
            )
        ],
    }
    if hasattr(graph, "update_state"):
        graph.update_state(cfg, saved_updates)
    else:
        saved.update(saved_updates)
        graph.checkpointer.put(cfg, saved)

    # Resume quiz
    resp_status = await submit_quiz_response(thread_id, "Very brief text", graph=graph)
    assert resp_status == "pending_lecturer_review"

    status = get_assessment_status(thread_id, graph=graph)
    assert status["requires_human_review"] is True


@pytest.mark.asyncio
async def test_t8_1_6_trigger_4_with_override_score():
    """T8.1.6: Trigger 4 with override_score=0.45 -> final_score == 0.45; lecturer_reviewed == True."""
    graph = build_com_agent_graph()
    cfg = make_thread_config("sprint-02", "STU-001")
    thread_id = cfg["configurable"]["thread_id"]

    await trigger_sprint_end("sprint-02", ["STU-001"], graph=graph)
    resp_status = await submit_quiz_response(thread_id, "idk", graph=graph)
    assert resp_status == "pending_lecturer_review"

    result = await submit_lecturer_review(
        thread_id,
        override_score=0.45,
        reason="Confirmed via oral viva that third party contributed",
        lecturer_id="LEC-009",
        graph=graph,
    )
    assert result == "finalized"

    status = get_assessment_status(thread_id, graph=graph)
    assert status["current_step"] == "export_complete"
    assert status["final_score"] == 0.45
    assert status["lecturer_reviewed"] is True
    assert status["lecturer_id"] == "LEC-009"


@pytest.mark.asyncio
async def test_t8_1_7_trigger_4_with_none_override_preserves_score():
    """T8.1.7: Trigger 4 with override_score=None -> original final_score preserved."""
    graph = build_com_agent_graph()
    cfg = make_thread_config("sprint-02", "STU-001")
    thread_id = cfg["configurable"]["thread_id"]

    await trigger_sprint_end("sprint-02", ["STU-001"], graph=graph)
    resp_status = await submit_quiz_response(thread_id, "idk", graph=graph)
    assert resp_status == "pending_lecturer_review"

    status_before = get_assessment_status(thread_id, graph=graph)
    orig_score = status_before["final_score"]

    result = await submit_lecturer_review(
        thread_id,
        override_score=None,
        reason="Inspected git history. Effort verified satisfactory.",
        lecturer_id="LEC-001",
        graph=graph,
    )
    assert result == "finalized"

    status = get_assessment_status(thread_id, graph=graph)
    assert status["final_score"] == orig_score
    assert status["lecturer_reviewed"] is True


@pytest.mark.asyncio
async def test_trigger_3_on_demand_execution():
    """T7.1.3: Trigger 3 on-demand execution returns thread ID."""
    graph = build_com_agent_graph()
    thread_id = await trigger_on_demand("sprint-03", "STU-001", graph=graph)
    assert thread_id == "sprint_sprint-03_student_STU-001"

    status = get_assessment_status(thread_id, graph=graph)
    assert status["current_step"] == "quiz_generated"


def test_t7_2_schemas_importable():
    """T7.2.1 & T7.2.2: Schemas importable and exported correctly."""
    from app.agents.performance_assessment import (
        AssessmentResultSchema,
        StudentFeedbackSchema,
        FactorScoreOutput,
    )
    assert AssessmentResultSchema is not None
    assert StudentFeedbackSchema is not None
    assert FactorScoreOutput is not None
