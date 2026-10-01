"""Tests for AST quiz generator and await quiz response node (T5.3 & PLAN.md Section 12.2)."""

import pytest
from app.agents.performance_assessment.com_agent.state import ActiveVerificationState
from app.agents.performance_assessment.com_agent.nodes.active_quiz_node import (
    ast_quiz_generator_node,
    await_quiz_response_node,
)


@pytest.mark.asyncio
async def test_ast_quiz_generator_node():
    state = {}
    updates = await ast_quiz_generator_node(state)

    assert updates["current_step"] == "quiz_generated"
    assert "active_verification" in updates
    av = updates["active_verification"]
    assert isinstance(av, ActiveVerificationState)
    assert av.target_code_snippet is not None
    assert av.generated_question is not None
    assert av.file_path == "backend/app/auth.py"
    assert av.line_range == [45, 52]
    assert "cyclomatic_complexity" in av.ast_metadata


@pytest.mark.asyncio
async def test_await_quiz_response_normal_on_time():
    # Student submits within first 48h
    state = {
        "active_verification": ActiveVerificationState(
            target_code_snippet="def foo(): pass",
            generated_question="Explain foo",
            is_extended=False,
        )
    }

    updates = await await_quiz_response_node(
        state,
        mock_resume_value={
            "student_response": "The function foo generates session authentication tokens using HMAC-SHA256."
        },
    )

    assert updates["current_step"] == "quiz_evaluated"
    assert updates["ko_raw_score"] == 0.85
    assert updates["ko_fusion_score"] == 0.85
    assert "code_ownership" in updates["factor_scores"]
    output = updates["factor_scores"]["code_ownership"]
    assert output.score == 0.85
    assert output.features["score_was_capped"] is False


@pytest.mark.asyncio
async def test_await_quiz_response_first_timeout_triggers_extension():
    # Student misses initial 48h deadline
    state = {
        "active_verification": ActiveVerificationState(
            target_code_snippet="def foo(): pass",
            generated_question="Explain foo",
            is_extended=False,
        )
    }

    updates = await await_quiz_response_node(
        state,
        mock_resume_value={"timeout": True},
    )

    assert updates["current_step"] == "quiz_extended_waiting"
    assert updates["quiz_is_extended"] is True
    assert updates["quiz_extension_deadline"] is not None
    av = updates["active_verification"]
    assert av.is_timed_out is True
    assert av.is_extended is True


@pytest.mark.asyncio
async def test_await_quiz_response_extension_submission_score_is_capped():
    # Student submits during 48h extension window
    state = {
        "active_verification": ActiveVerificationState(
            target_code_snippet="def foo(): pass",
            generated_question="Explain foo",
            is_extended=True,  # In extension
        )
    }

    updates = await await_quiz_response_node(
        state,
        mock_resume_value={
            "student_response": "Comprehensive explanation of token claims and expiration logic in JWT."
        },
    )

    assert updates["current_step"] == "quiz_evaluated"
    assert updates["ko_raw_score"] == 0.85
    # Capped at 0.50 (settings.quiz_timeout.capped_score_ceiling)
    assert updates["ko_fusion_score"] == 0.50
    output = updates["factor_scores"]["code_ownership"]
    assert output.score == 0.50
    assert output.features["score_was_capped"] is True
    assert output.features["ko_raw_score"] == 0.85
    assert output.features["ko_fusion_score"] == 0.50


@pytest.mark.asyncio
async def test_await_quiz_response_double_timeout_fails_to_zero():
    # Student misses both initial and extension deadlines
    state = {
        "active_verification": ActiveVerificationState(
            target_code_snippet="def foo(): pass",
            generated_question="Explain foo",
            is_extended=True,
        )
    }

    updates = await await_quiz_response_node(
        state,
        mock_resume_value={"timeout": True},
    )

    assert updates["current_step"] == "quiz_evaluated"
    assert updates["quiz_is_double_timed_out"] is True
    assert updates["ko_raw_score"] == 0.0
    assert updates["ko_fusion_score"] == 0.0
    output = updates["factor_scores"]["code_ownership"]
    assert output.score == 0.0
    assert output.features["is_double_timed_out"] is True


@pytest.mark.asyncio
async def test_evaluate_ownership_tool_node_direct_call():
    from app.agents.performance_assessment.com_agent.nodes.active_quiz_node import (
        evaluate_ownership_tool,
    )

    state = {
        "active_verification": ActiveVerificationState(
            generated_question="Explain JWT exp",
            student_response="The exp claim specifies expiration Unix timestamp preventing replay attacks.",
            is_extended=True,
        )
    }

    updates = await evaluate_ownership_tool(state)
    assert updates["current_step"] == "ownership_evaluated"
    assert updates["ko_raw_score"] == 0.85
    assert updates["ko_fusion_score"] == 0.50  # Capped due to extension
    output = updates["factor_scores"]["code_ownership"]
    assert output.score == 0.50
    assert output.features["ko_raw_score"] == 0.85

