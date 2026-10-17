"""The decomposition sub-agent's two-level mandatory pass/fail gate.

Unlike the Quality sub-agent's single scoring-threshold gate (orchestrator/gates.py,
unchanged and still used by Quality), decomposition completion is never decided by
a single LLM percentage:

  1. Coverage Gate  — passes only when all of C1-C10 pass.
  2. INVEST Gate    — runs only after coverage passes; every story must be ready
                       (all 6 criteria Pass or Pass with note).

Both gates are evaluated in code from the structured check/story results, never
by the LLM.
"""

from __future__ import annotations

from app.agents.project_planning.schemas import (
    CoverageGateResult,
    DecompositionGateStatus,
    InvestGateResult,
)


def evaluate_decomposition_gate(
    coverage_gate: CoverageGateResult,
    invest_gate: InvestGateResult,
    needs_review: bool,
    needs_review_reason: str | None,
) -> tuple[DecompositionGateStatus, str | None]:
    """Return (gate_status, needs_review_reason).

    NEEDS_REVIEW only applies when coverage is otherwise complete — if coverage
    itself fails there's nothing ambiguous to review, only concrete gaps to fix,
    so that case is INCOMPLETE regardless of a needs_review flag.
    """
    if coverage_gate.passed and needs_review:
        return DecompositionGateStatus.NEEDS_REVIEW, needs_review_reason
    if coverage_gate.passed and invest_gate.all_stories_ready:
        return DecompositionGateStatus.COMPLETE, None
    return DecompositionGateStatus.INCOMPLETE, None
