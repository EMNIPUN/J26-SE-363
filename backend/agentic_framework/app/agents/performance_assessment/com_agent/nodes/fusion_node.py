"""Deterministic mathematical fusion node for com_agent.

Strictly aligned with:
- BOARD.md T5.7 (T5.7.1 - T5.7.4)
- PLAN.md Section 9 Node 8 (Deterministic Fusion Formula)
- Zero LLM calls. Pure deterministic mathematics.
"""

import logging
from typing import Dict, Any
from app.agents.performance_assessment.com_agent.fusion_engine.calculator import (
    compute_additive_score,
    apply_behavioral_modifier,
    build_radar_chart_data,
)
from app.agents.performance_assessment.com_agent.fusion_engine.weights_config import (
    get_weights_as_dict,
)

logger = logging.getLogger(__name__)


async def deterministic_fusion_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """T5.7: Node 8 — Deterministic Fusion Node.

    Computes S = BP_modifier * (sum(w_i * F_i)), builds radar chart data,
    and logs the reproducible calculation audit trail.
    """
    weights = state.get("weights_used") or get_weights_as_dict()
    factor_scores = state.get("factor_scores", {})
    bp_modifier = float(state.get("behavioral_modifier", 1.00))

    # 1. T5.7.1: Compute weighted additive score and audit trail
    additive_score, audit_trail = compute_additive_score(factor_scores, weights)

    # 2. T5.7.2: Apply behavioral modifier with [0.0, 1.0] clamping
    final_score = apply_behavioral_modifier(additive_score, bp_modifier)

    # 3. T5.7.3: Generate radar chart data
    radar_data = build_radar_chart_data(factor_scores)

    # 4. T5.7.4: Return state update
    return {
        "additive_score": additive_score,
        "final_score": final_score,
        "calculation_audit_trail": audit_trail,
        "radar_chart_data": radar_data,
        "current_step": "fusion_complete",
    }
