"""Tests for AST quiz generator and await quiz response node (T5.3 & PLAN.md Section 12.2).

Improvements over original:
- Added empty string response test → raw_score = 0.0
- Added short response under extension cap (len <= 20 < cap → fusion = min(score, cap))
- Added direct ownership_score injection path test
- Existing tests preserved with improved assertions
"""

import pytest
from app.agents.performance_assessment.com_agent.state import ActiveVerificationState, FactorOutput
from app.agents.performance_assessment.com_agent.policies.fallback_policies import get_fallback_for_factor
from app.agents.performance_assessment.com_agent.nodes import active_quiz_node as node
from app.agents.performance_assessment.com_agent.nodes.active_quiz_node import (
    ast_quiz_generator_node,
    await_quiz_response_node,
    evaluate_ownership_tool,
)
from app.agents.performance_assessment.com_agent.config.settings_loader import settings


SEEN = []


@pytest.fixture(autouse=True)
def stub_scorer(monkeypatch):
    """The answer rating lives in factor_models/07_code_ownership (needs torch and a trained head); these tests check the node's flow, so the rating is stubbed."""
    SEEN.clear()

    async def fake(factor_name, payload=None, context=None, **kw):
        SEEN.append(payload)
        return FactorOutput(score=0.85, features={"ko_raw_score": 0.85}, status="completed")

    monkeypatch.setattr(node, "evaluate_factor", fake)


PY_FILE = """def split_total(items, discount):
    if discount < 0:
        raise ValueError('discount must not be negative')
    total = 0
    for item in items:
        if item['qty'] <= 0:
            continue
        total += item['price'] * item['qty']
    total = total - total * discount
    return round(total, 2)
"""


@pytest.mark.asyncio
async def test_generator_uses_the_ownership_package_when_source_files_are_given():
    updates = await ast_quiz_generator_node({"ownership_files": [{"path": "shop/cart.py", "text": PY_FILE}], "student_id": "STU-001", "sprint_id": "T01-S1"})
    av = updates["active_verification"]
    assert av.file_path == "shop/cart.py"
    assert av.ast_metadata["name"] == "split_total" and av.ast_metadata["language"] == "python"
    assert "split_total" in av.generated_question
    assert av.ast_metadata["reference_criteria"] and av.ast_metadata["facts"]["guards"]
    again = await ast_quiz_generator_node({"ownership_files": [{"path": "shop/cart.py", "text": PY_FILE}], "student_id": "STU-001", "sprint_id": "T01-S1"})
    assert again["active_verification"].generated_question == av.generated_question  # same student and sprint, same question


@pytest.mark.asyncio
async def test_generator_without_source_files_keeps_the_placeholder_quiz():
    updates = await ast_quiz_generator_node({"ownership_files": [{"path": "notes.py", "text": "x = 1\n"}]})
    assert updates["active_verification"].file_path == "backend/app/auth.py"


@pytest.mark.asyncio
async def test_rating_request_carries_question_code_and_facts():
    av = ActiveVerificationState(target_code_snippet="def f(x):\n    return x", generated_question="What does f return?", file_path="a.py",
                                 ast_metadata={"facts": {"guards": []}, "language": "python"})
    await await_quiz_response_node({"active_verification": av}, mock_resume_value={"student_response": "It returns x unchanged."})
    sent = SEEN[0]
    assert sent["generated_question"] == "What does f return?" and sent["code_snippet"].startswith("def f") and sent["facts"] == {"guards": []}


@pytest.mark.asyncio
async def test_unavailable_scorer_gives_a_fallback_not_a_made_up_score(monkeypatch):
    async def unavailable(factor_name, payload=None, context=None, **kw):
        return get_fallback_for_factor(factor_name, "no trained head")

    monkeypatch.setattr(node, "evaluate_factor", unavailable)
    av = ActiveVerificationState(target_code_snippet="def f(x):\n    return x", generated_question="What does f return?")
    updates = await await_quiz_response_node({"active_verification": av}, mock_resume_value={"student_response": "It returns x unchanged."})
    assert updates["factor_scores"]["code_ownership"].status == "fallback_applied"
    assert updates["ko_raw_score"] is None
    again = await evaluate_ownership_tool({"active_verification": updates["active_verification"]})
    assert again["factor_scores"]["code_ownership"].status == "fallback_applied"


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
