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


def _normalize_resume_data(resume_data: Any) -> Dict[str, Any]:
    """Safely parse resume_data into a dictionary regardless of input type.

    Handles:
    - dict: returned as-is
    - bool: converted to approved/rejected comment
    - int / float: treated as override_score
    - JSON string: parsed to dict or primitive
    - numeric string: treated as override_score
    - string comment: treated as lecturer comments
    - None / empty: empty dict
    """
    if resume_data is None:
        return {}
    if isinstance(resume_data, dict):
        return resume_data
    if isinstance(resume_data, bool):
        return {"comments": "Approved by lecturer" if resume_data else "Review rejected by lecturer"}
    if isinstance(resume_data, (int, float)):
        return {"override_score": float(resume_data)}
    if isinstance(resume_data, str):
        trimmed = resume_data.strip()
        if not trimmed:
            return {}
        # Try JSON parsing
        try:
            import json
            parsed = json.loads(trimmed)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, bool):
                return {"comments": "Approved by lecturer" if parsed else "Review rejected by lecturer"}
            if isinstance(parsed, (int, float)):
                return {"override_score": float(parsed)}
        except Exception:
            pass
        # Try numeric string (e.g. "0.85")
        try:
            val = float(trimmed)
            return {"override_score": val}
        except ValueError:
            pass
        # Plain text comment/approval
        return {"comments": trimmed}
    if hasattr(resume_data, "model_dump"):
        return resume_data.model_dump()
    return {}


async def lecturer_review_node(
    state: Dict[str, Any],
    mock_resume_value: Optional[Any] = None,
) -> Dict[str, Any]:
    """T5.9.1: Node 10 — Lecturer Review & Override (HITL Interrupt).

    Pauses thread execution for instructor review when discrepancy flags are present.
    Resumes with optional score override, justification, and lecturer credentials.
    """
    raw_flags = state.get("discrepancy_flags") or []
    flags_data = [
        f.model_dump() if hasattr(f, "model_dump") else (dict(f) if isinstance(f, dict) else str(f))
        for f in raw_flags
    ]

    factor_scores_summary = {}
    for k, v in (state.get("factor_scores") or {}).items():
        if hasattr(v, "score"):
            factor_scores_summary[k] = v.score
        elif isinstance(v, dict):
            factor_scores_summary[k] = v.get("score")
        elif isinstance(v, (int, float)):
            factor_scores_summary[k] = float(v)

    interrupt_payload = {
        "type": "lecturer_review_needed",
        "student_id": state.get("student_id"),
        "flags": flags_data,
        "scores": factor_scores_summary or state.get("radar_chart_data") or {},
        "final_score": state.get("final_score"),
    }

    if mock_resume_value is not None:
        raw_resume = mock_resume_value
    else:
        raw_resume = interrupt(interrupt_payload)

    resume_data = _normalize_resume_data(raw_resume)

    override_score = (
        resume_data.get("override_score")
        if "override_score" in resume_data
        else (
            resume_data.get("score")
            if "score" in resume_data
            else (
                resume_data.get("override")
                if "override" in resume_data
                else resume_data.get("new_score")
            )
        )
    )

    lecturer_id = (
        resume_data.get("lecturer_id")
        or resume_data.get("reviewer_id")
        or resume_data.get("instructor_id")
        or "LEC-001"
    )
    reason = (
        resume_data.get("comments")
        or resume_data.get("comment")
        or resume_data.get("reason")
        or resume_data.get("lecturer_comments")
        or resume_data.get("justification")
        or resume_data.get("notes")
        or "Approved by lecturer"
    )
    now_iso = datetime.now(timezone.utc).isoformat()

    updates: Dict[str, Any] = {
        "lecturer_reviewed": True,
        "requires_human_review": False,
        "lecturer_id": lecturer_id,
        "lecturer_comments": reason,
        "review_timestamp": now_iso,
        "current_step": "lecturer_review_completed",
    }

    if override_score is not None:
        try:
            clamped_score = round(max(0.0, min(1.0, float(override_score))), 4)
            updates["final_score"] = clamped_score
            updates["lecturer_override_score"] = clamped_score
        except (ValueError, TypeError):
            updates["lecturer_override_score"] = None
    else:
        updates["lecturer_override_score"] = None

    return updates

