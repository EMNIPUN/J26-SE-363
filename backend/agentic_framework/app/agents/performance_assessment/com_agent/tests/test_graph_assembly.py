"""Tests for StateGraph construction and execution lifecycle (Phase 6)."""

import pytest
from app.agents.performance_assessment.com_agent.graph import (
    build_com_agent_graph,
    make_thread_config,
    build_initial_state,
    Command,
)


def test_make_thread_config():
    cfg = make_thread_config(sprint_id="sprint-02", student_id="STU-001")
    assert cfg["configurable"]["thread_id"] == "sprint_sprint-02_student_STU-001"


def test_build_initial_state():
    ctx = {
        "student_id": "STU-001",
        "student_name": "Alice Perera",
        "student_github_username": "alice-perera",
    }
    state = build_initial_state(ctx)
    assert state["student_id"] == "STU-001"
    assert state["student_name"] == "Alice Perera"
    assert state["github_api_call_count"] == 0
    assert state["github_sandbox_mode"] is False
    assert state["errors"] == []
    assert state["current_step"] == "initialized"


@pytest.mark.asyncio
async def test_graph_trigger_1_pause_at_quiz_interrupt():
    # Trigger 1: automated sprint deadline trigger
    graph = build_com_agent_graph()
    initial_state = build_initial_state({
        "student_id": "STU-001",
        "sprint_id": "sprint-02",
        "repo_url": "https://github.com/org/project-repo",
    })
    config = make_thread_config("sprint-02", "STU-001")

    # First invocation: runs validation, passive factors in parallel, AST question generation, then pauses
    state = await graph.ainvoke(initial_state, config=config)

    assert state["current_step"] == "quiz_generated"
    assert "effort" in state["factor_scores"]
    assert "consistency" in state["factor_scores"]
    assert state["active_verification"].generated_question is not None


@pytest.mark.asyncio
async def test_graph_trigger_2_resume_to_completion():
    # Trigger 1: Start and pause
    graph = build_com_agent_graph()
    initial_state = build_initial_state({
        "student_id": "STU-001",
        "sprint_id": "sprint-02",
        "repo_url": "https://github.com/org/project-repo",
    })
    config = make_thread_config("sprint-02", "STU-001")
    await graph.ainvoke(initial_state, config=config)

    # Trigger 2: Student submits quiz response
    resume_cmd = Command(
        resume={
            "student_response": "The exp claim specifies token expiration timestamp to prevent replay attacks."
        }
    )

    final_state = await graph.ainvoke(resume_cmd, config=config)

    assert final_state["current_step"] == "export_complete"
    assert final_state["final_score"] > 0.0
    assert final_state["final_score"] <= 1.0
    assert final_state["behavioral_persona"] is not None
    assert final_state["instructor_report_markdown"] is not None
    assert final_state["student_feedback_markdown"] is not None
    # Verify PII restoration completed
    assert "Alice Perera" in final_state["instructor_report_markdown"]


def test_router_discrepancy_node():
    from app.agents.performance_assessment.com_agent.graph import router_discrepancy_node
    assert router_discrepancy_node({"requires_human_review": True}) == "lecturer_review_node"
    assert router_discrepancy_node({"requires_human_review": False}) == "load_cross_sprint_memory_node"
    assert router_discrepancy_node({}) == "load_cross_sprint_memory_node"


@pytest.mark.asyncio
async def test_graph_trigger_3_lecturer_review_workflow():
    from app.agents.performance_assessment.agent import trigger_sprint_end, submit_quiz_response
    graph = build_com_agent_graph()
    config = make_thread_config("sprint-02", "STU-002")

    await trigger_sprint_end("sprint-02", ["STU-002"], graph=graph)
    await submit_quiz_response("sprint_sprint-02_student_STU-002", "idk", graph=graph)

    # Resume with lecturer review input
    resume_cmd = Command(
        resume={
            "lecturer_id": "LEC-007",
            "override_score": 0.85,
            "comments": "Reviewed commits manually. Effort is satisfactory.",
        }
    )

    final_state = await graph.ainvoke(resume_cmd, config=config)
    assert final_state["current_step"] == "export_complete"
    assert final_state["lecturer_reviewed"] is True
    assert final_state["lecturer_id"] == "LEC-007"
    assert final_state["final_score"] == 0.85
    assert final_state["lecturer_comments"] == "Reviewed commits manually. Effort is satisfactory."

