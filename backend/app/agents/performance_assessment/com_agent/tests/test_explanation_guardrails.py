"""Tests for explanation generation node and guardrails (T5.12 & PLAN.md Section 9 Node 13)."""

import pytest
from app.agents.performance_assessment.com_agent.state import FactorOutput, DiscrepancyAlert
from app.agents.performance_assessment.com_agent.nodes.explanation_node import (
    generate_explanation_node,
)


@pytest.fixture
def mock_assessment_state():
    return {
        "student_name": "Alice Perera",
        "student_id": "STU-001",
        "sprint_id": "sprint-02",
        "final_score": 0.86,
        "behavioral_persona": "Consistent Builder",
        "behavioral_modifier": 1.10,
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
async def test_generate_explanation_node_default_synthesis(mock_assessment_state):
    updates = await generate_explanation_node(mock_assessment_state)

    assert updates["current_step"] == "explanation_generated"
    assert "instructor_report_markdown" in updates
    assert "student_feedback_markdown" in updates

    dossier = updates["instructor_report_markdown"]
    feedback = updates["student_feedback_markdown"]

    # Must preserve anonymization placeholders for PII sanitizer to restore later
    assert "[STUDENT_A]" in dossier
    assert "[STUDENT_ID]" in dossier
    assert "Alice Perera" not in dossier  # Anonymized before LLM / synthesizer
    assert "0.86" in dossier  # Score accuracy
    assert "Consistent Builder" in dossier

    assert "[STUDENT_A]" in feedback
    assert "0.86" in feedback
    assert "Alice Perera" not in feedback


@pytest.mark.asyncio
async def test_generate_explanation_node_with_custom_llm_callable(mock_assessment_state):
    calls = []

    def mock_llm(sys_prompt: str, usr_prompt: str, params: dict) -> str:
        calls.append((sys_prompt, usr_prompt, params))
        return f"Synthesized Response for {params.get('max_tokens')}"

    updates = await generate_explanation_node(mock_assessment_state, llm_callable=mock_llm)

    assert len(calls) == 2  # Once for dossier, once for student feedback
    # First call: instructor dossier (temp 0.15, max tokens 1500)
    assert calls[0][2]["temperature"] == 0.15
    assert calls[0][2]["max_tokens"] == 1500

    # Second call: student feedback (temp 0.30, max tokens 1000)
    assert calls[1][2]["temperature"] == 0.30
    assert calls[1][2]["max_tokens"] == 1000

    assert "Synthesized Response for 1500" in updates["instructor_report_markdown"]
    assert "Synthesized Response for 1000" in updates["student_feedback_markdown"]


@pytest.mark.asyncio
async def test_explanation_guardrails_constraints_and_trace_isolation(mock_assessment_state):
    """T8.8.1 - T8.8.4: Verify exact score, constraints in system prompt, and evidence trace isolation."""
    calls = []

    def capturing_llm(sys_prompt: str, usr_prompt: str, params: dict) -> str:
        calls.append((sys_prompt, usr_prompt))
        return f"# Report\nFinal Score: 0.86\nFeedback content without trace data."

    updates = await generate_explanation_node(mock_assessment_state, llm_callable=capturing_llm)

    # T8.8.1: Exact final_score appears verbatim
    dossier = updates["instructor_report_markdown"]
    assert "0.86" in dossier

    # T8.8.3: strict_constraints guardrail text present in rendered system prompt
    dossier_sys, feedback_sys = calls[0][0], calls[1][0]
    assert ("MANDATORY CONSTRAINTS:" in dossier_sys or "RULES:" in dossier_sys)
    assert ("STRICTLY FORBIDDEN:" in dossier_sys or "RULES:" in feedback_sys)

    # T8.8.4: student_feedback_markdown contains no raw evidence trace data
    feedback = updates["student_feedback_markdown"]
    for prohibited in ["sha", "stats", "deletions", "additions", "commit_history", "evidence_traces"]:
        assert prohibited not in feedback.lower()

