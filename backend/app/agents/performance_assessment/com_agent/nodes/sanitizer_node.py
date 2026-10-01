"""PII redaction and restoration nodes for com_agent.

Strictly aligned with:
- BOARD.md T5.11 (T5.11.1 - T5.11.2)
- PLAN.md Section 7.1 (PII Redaction & Sanitization)
- PLAN.md Section 9 Nodes 12 & 14
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


async def pii_redaction_sanitizer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """T5.11.1: Node 12 — PII Redaction and Anonymization.

    Builds an in-memory substitution map replacing real names, student IDs,
    and private email addresses with synthetic placeholders ([STUDENT_A], [STUDENT_ID], [REDACTED_EMAIL_X]).
    Ensures third-party LLMs receive zero sensitive personally identifiable information.
    """
    real_name = state.get("student_name", "")
    real_id = state.get("student_id", "")
    real_username = state.get("student_github_username", "")
    emails: List[str] = state.get("student_git_emails") or []

    substitution_map: Dict[str, str] = {}

    if real_name:
        substitution_map["[STUDENT_A]"] = real_name
    if real_id:
        substitution_map["[STUDENT_ID]"] = real_id
    if real_username:
        substitution_map["[STUDENT_GH_USER]"] = real_username

    for i, email in enumerate(emails, start=1):
        placeholder = f"[REDACTED_EMAIL_{i}]"
        substitution_map[placeholder] = email

    return {
        "pii_substitution_map": substitution_map,
        "current_step": "pii_redacted",
    }


async def pii_restore_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """T5.11.2: Node 14 — PII Restoration.

    Reverses the substitution map on generated markdown reports (instructor_report_markdown
    and student_feedback_markdown) before final presentation and database persistence.
    Clears the transient pii_substitution_map.
    """
    substitution_map = state.get("pii_substitution_map", {})
    instructor_report = state.get("instructor_report_markdown")
    student_feedback = state.get("student_feedback_markdown")

    if instructor_report and substitution_map:
        for placeholder, original in substitution_map.items():
            instructor_report = instructor_report.replace(placeholder, original)

    if student_feedback and substitution_map:
        for placeholder, original in substitution_map.items():
            student_feedback = student_feedback.replace(placeholder, original)

    return {
        "instructor_report_markdown": instructor_report,
        "student_feedback_markdown": student_feedback,
        "pii_substitution_map": {},
        "current_step": "pii_restored",
    }
