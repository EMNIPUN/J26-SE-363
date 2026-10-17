"""Tests for AST quiz generator and await quiz response node (T5.3 & PLAN.md Section 12.2).

Improvements over original:
- Added empty string response test → raw_score = 0.0
- Added short response under extension cap (len <= 20 < cap → fusion = min(score, cap))
- Added direct ownership_score injection path test
- Existing tests preserved with improved assertions
"""

import pytest
from app.agents.performance_assessment.com_agent.state import ActiveVerificationState
from app.agents.performance_assessment.com_agent.nodes.active_quiz_node import (
    ast_quiz_generator_node,
    await_quiz_response_node,
    evaluate_ownership_tool,
)
from app.agents.performance_assessment.com_agent.config.settings_loader import settings


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
    """Student submits a good answer within the initial 48h window → no cap applied."""
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
    output = updates["factor_scores"]["code_ownership"]
    assert output.score == 0.85
    assert output.features["score_was_capped"] is False


@pytest.mark.asyncio
async def test_await_quiz_response_empty_string_scores_zero():
    """Empty response (len == 0) must yield ko_raw_score = 0.0."""
    state = {
        "active_verification": ActiveVerificationState(
            target_code_snippet="def foo(): pass",
            generated_question="Explain foo",
            is_extended=False,
        )
    }

    updates = await await_quiz_response_node(
        state,
        mock_resume_value={"student_response": ""},
    )

    assert updates["current_step"] == "quiz_evaluated"
    assert updates["ko_raw_score"] == 0.0
    assert updates["ko_fusion_score"] == 0.0
    output = updates["factor_scores"]["code_ownership"]
    assert output.score == 0.0
    assert output.features["score_was_capped"] is False


@pytest.mark.asyncio
async def test_await_quiz_response_first_timeout_triggers_extension():
    """Student misses initial 48h deadline → extension granted, quiz re-opens."""
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
async def test_await_quiz_response_extension_good_answer_score_is_capped():
    """Good answer in extension window: raw=0.85 but fusion is capped at ceiling."""
    cap = settings.quiz_timeout.capped_score_ceiling  # read from config, not hardcoded

    state = {
        "active_verification": ActiveVerificationState(
            target_code_snippet="def foo(): pass",
            generated_question="Explain foo",
            is_extended=True,
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
    assert updates["ko_fusion_score"] == pytest.approx(cap, abs=1e-6)
    output = updates["factor_scores"]["code_ownership"]
    assert output.score == pytest.approx(cap, abs=1e-6)
    assert output.features["score_was_capped"] is True
    assert output.features["ko_raw_score"] == 0.85
    assert output.features["ko_fusion_score"] == pytest.approx(cap, abs=1e-6)


@pytest.mark.asyncio
async def test_await_quiz_response_extension_short_answer_score_not_artificially_capped():
    """Short answer in extension: raw score is low (0.0), cap doesn't inflate it.

    A score of 0.0 is already below the cap ceiling — fusion_score must equal raw (0.0),
    not be raised to the cap. The cap is a ceiling, not a floor.
    """
    state = {
        "active_verification": ActiveVerificationState(
            target_code_snippet="def foo(): pass",
            generated_question="Explain foo",
            is_extended=True,
        )
    }

    updates = await await_quiz_response_node(
        state,
        mock_resume_value={"student_response": ""},
    )

    assert updates["current_step"] == "quiz_evaluated"
    raw = updates["ko_raw_score"]
    fusion = updates["ko_fusion_score"]
    cap = settings.quiz_timeout.capped_score_ceiling
    # fusion = min(raw, cap); if raw < cap, fusion equals raw
    assert fusion == pytest.approx(min(raw, cap), abs=1e-6)


@pytest.mark.asyncio
async def test_await_quiz_response_double_timeout_fails_to_zero():
    """Student misses both initial and extension windows → KO = 0."""
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
async def test_evaluate_ownership_tool_direct_injection():
    """Direct ownership_score injection (mock/override path) bypasses scoring formula."""
    state = {
        "active_verification": ActiveVerificationState(
            generated_question="Explain JWT exp",
            ownership_score=0.65,   # direct injection — must be used verbatim
            is_extended=False,
        )
    }

    updates = await evaluate_ownership_tool(state)
    assert updates["current_step"] == "ownership_evaluated"
    assert updates["ko_raw_score"] == 0.65
    # Not extended → no cap
    assert updates["ko_fusion_score"] == 0.65
    output = updates["factor_scores"]["code_ownership"]
    assert output.score == 0.65
    assert output.features["score_was_capped"] is False


@pytest.mark.asyncio
async def test_evaluate_ownership_tool_extended_caps_result():
    """evaluate_ownership_tool: extended + good answer → fusion capped."""
    cap = settings.quiz_timeout.capped_score_ceiling

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
    assert updates["ko_fusion_score"] == pytest.approx(cap, abs=1e-6)
    output = updates["factor_scores"]["code_ownership"]
    assert output.score == pytest.approx(cap, abs=1e-6)
    assert output.features["ko_raw_score"] == 0.85
