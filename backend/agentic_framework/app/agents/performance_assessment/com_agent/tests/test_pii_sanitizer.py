"""Tests for PII redaction and restoration nodes (T5.11 & PLAN.md Section 7.1)."""

import pytest
from app.agents.performance_assessment.com_agent.nodes.sanitizer_node import (
    pii_redaction_sanitizer_node,
    pii_restore_node,
)


@pytest.mark.asyncio
async def test_pii_redaction_and_restoration_cycle():
    state = {
        "student_name": "Alice Perera",
        "student_id": "STU-001",
        "student_github_username": "alice-perera",
        "student_git_emails": ["alice@student.sliit.lk", "alice.p@gmail.com"],
    }

    # 1. Redact
    redact_updates = await pii_redaction_sanitizer_node(state)
    assert redact_updates["current_step"] == "pii_redacted"
    sub_map = redact_updates["pii_substitution_map"]
    assert sub_map["[STUDENT_A]"] == "Alice Perera"
    assert sub_map["[STUDENT_ID]"] == "STU-001"
    assert sub_map["[STUDENT_GH_USER]"] == "alice-perera"
    assert "[REDACTED_EMAIL_1]" in sub_map
    assert "[REDACTED_EMAIL_2]" in sub_map

    # 2. Simulate LLM generating reports using anonymized placeholders
    state_with_reports = {
        "pii_substitution_map": sub_map,
        "instructor_report_markdown": (
            "# Performance Assessment for [STUDENT_A] ([STUDENT_ID])\n"
            "Commits were authored under account [STUDENT_GH_USER]."
        ),
        "student_feedback_markdown": (
            "Dear [STUDENT_A],\n"
            "You performed admirably during this sprint. Keep up the great work!"
        ),
    }

    # 3. Restore
    restore_updates = await pii_restore_node(state_with_reports)
    assert restore_updates["current_step"] == "pii_restored"
    assert restore_updates["pii_substitution_map"] == {}

    inst_report = restore_updates["instructor_report_markdown"]
    assert "Alice Perera" in inst_report
    assert "STU-001" in inst_report
    assert "alice-perera" in inst_report
    assert "[STUDENT_A]" not in inst_report
    assert "[STUDENT_ID]" not in inst_report

    stu_report = restore_updates["student_feedback_markdown"]
    assert "Dear Alice Perera," in stu_report
    assert "[STUDENT_A]" not in stu_report


@pytest.mark.asyncio
async def test_pii_anonymization_in_rendered_prompts():
    """T8.5.1 & T8.5.2: student_name absent from LLM-bound fields, [STUDENT_A] present."""
    from app.agents.performance_assessment.com_agent.nodes.explanation_node import generate_explanation_node

    captured_prompts = []

    def mock_llm(system_prompt, user_prompt, model_config):
        captured_prompts.append((system_prompt, user_prompt))
        return "# Anonymized Assessment for [STUDENT_A]"

    state = {
        "student_name": "Alice Perera",
        "student_id": "STU-001",
        "sprint_id": "sprint-02",
        "factor_scores": {},
        "final_score": 0.85,
    }

    res = await generate_explanation_node(state, llm_callable=mock_llm)
    assert len(captured_prompts) == 2

    for sys_p, usr_p in captured_prompts:
        # Real name must be completely absent from both prompts
        assert "Alice Perera" not in sys_p
        assert "Alice Perera" not in usr_p
        # Anonymized placeholder [STUDENT_A] must be present in user prompt
        assert "[STUDENT_A]" in usr_p

