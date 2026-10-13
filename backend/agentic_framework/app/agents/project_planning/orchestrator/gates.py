"""Quality-gate rule, shared by the Quality and (later) Decomposition sub-agents.

Rule (PLAN.md, proposal FR-04):
    confidence < CONFIDENCE_THRESHOLD  -> DART (arbitrate; do not trust the score yet)
    overall_score >= threshold         -> PASS
    overall_score <  threshold         -> BLOCK (+ actionable feedback)
"""

from __future__ import annotations

from app.agents.project_planning.schemas import GateAction, GateStatus

CONFIDENCE_THRESHOLD = 0.6


def evaluate_gate(
    overall_score: int,
    confidence: float,
    threshold: int,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> tuple[GateStatus, GateAction, bool]:
    """Return (status, action, dart_triggered)."""
    if confidence < confidence_threshold:
        return GateStatus.NEEDS_REVIEW, GateAction.DART, True
    if overall_score >= threshold:
        return GateStatus.PASSED, GateAction.PASS, False
    return GateStatus.BLOCKED, GateAction.BLOCK, False
