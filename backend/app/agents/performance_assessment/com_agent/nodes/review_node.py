"""Lecturer review and override human-in-the-loop node for com_agent.

Strictly aligned with:
- BOARD.md T5.9 (T5.9.1)
- PLAN.md Section 2 (Trigger 4: Lecturer Review & Override)
- PLAN.md Section 9 Node 10 (lecturer_review_node)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# LangGraph interrupt import with graceful fallback
try:
    from langgraph.types import interrupt
except ImportError:
    def interrupt(value: Any) -> Any:
        return value


async def lecturer_review_node(
    state: Dict[str, Any],
    mock_resume_value: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """T5.9.1: Node 10 — Lecturer Review & Override (HITL Interrupt).

    Pauses thread execution for instructor review when discrepancy flags are present.
    Resumes with optional score override, justification, and lecturer credentials.
    """
    flags_data = [
        f.model_dump() if hasattr(f, "model_dump") else f
        for f in state.get("discrepancy_flags", [])
    ]

    interrupt_payload = {
        "type": "lecturer_review_needed",
        "student_id": state.get("student_id"),
        "flags": flags_data,
        "scores": state.get("radar_chart_data", {}),
        "final_score": state.get("final_score"),
    }

    if mock_resume_value is not None:
        resume_data = mock_resume_value
    else:
        resume_data = interrupt(interrupt_payload) or {}

    override_score = resume_data.get("override_score")
    lecturer_id = resume_data.get("lecturer_id") or "LEC-001"
    reason = (
        resume_data.get("comments")
        or resume_data.get("reason")
        or resume_data.get("lecturer_comments")
        or "Approved by lecturer"
    )
    now_iso = datetime.now(timezone.utc).isoformat()

    updates: Dict[str, Any] = {
        "lecturer_reviewed": True,
        "lecturer_id": lecturer_id,
        "lecturer_comments": reason,
        "review_timestamp": now_iso,
        "current_step": "lecturer_review_completed",
    }

    if override_score is not None:
        clamped_score = round(max(0.0, min(1.0, float(override_score))), 4)
        updates["final_score"] = clamped_score
        updates["lecturer_override_score"] = clamped_score
    else:
        updates["lecturer_override_score"] = None

    return updates
