"""Deterministic mathematical fusion calculator for com_agent.

Strictly aligned with:
- BOARD.md T3.1 (T3.1.1 - T3.1.4)
- PLAN.md Section 9 Node 8 (Deterministic Fusion Formula)
- Zero LLM calls. Pure deterministic mathematics.
"""

from typing import Dict, Any, Tuple, List, Union
from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.policies.fallback_policies import (
    redistribute_weights,
)


def compute_additive_score(
    factor_scores: Dict[str, Union[FactorOutput, Dict[str, Any]]],
    weights: Dict[str, float],
) -> Tuple[float, Dict[str, Any]]:
    """Compute weighted additive score across active factors.

    - Uses capped ko_fusion_score for code_ownership if present in features.
    - Automatically redistributes weights if any factor has status 'fallback_applied' or is missing.
    - Validates sum(effective_weights) == 1.0.
    - Produces a comprehensive, reproducible calculation audit trail.

    Returns:
        (additive_score, audit_trail)
    """
    failed_factors: List[str] = []

    # 1. Detect failed or fallback factors
    for factor_name, weight in weights.items():
        if factor_name not in factor_scores:
            failed_factors.append(factor_name)
            continue

        f_output = factor_scores[factor_name]
        status = (
            getattr(f_output, "status", None)
            if hasattr(f_output, "status")
            else f_output.get("status") if isinstance(f_output, dict) else None
        )
        score = (
            getattr(f_output, "score", None)
            if hasattr(f_output, "score")
            else f_output.get("score") if isinstance(f_output, dict) else None
        )

        if status == "fallback_applied" or score is None:
            failed_factors.append(factor_name)

    # 2. Redistribute weights if any factors failed
    effective_weights = redistribute_weights(weights, failed_factors)

    # 3. Validate sum of effective weights
    weights_sum = sum(effective_weights.values())
    if effective_weights and abs(weights_sum - 1.0) > 1e-5:
        raise ValueError(
            f"Effective weights must sum to 1.0 after redistribution, got {weights_sum}"
        )

    # 4. Compute weighted contributions
    steps: Dict[str, Dict[str, Any]] = {}
    additive_score = 0.0

    for factor_name, eff_weight in effective_weights.items():
        f_val = factor_scores[factor_name]

        # Extract factor score (handling code_ownership capped score in features)
        if factor_name == "code_ownership":
            features = (
                getattr(f_val, "features", {})
                if hasattr(f_val, "features")
                else f_val.get("features", {}) if isinstance(f_val, dict) else {}
            )
            # Use ko_fusion_score if present, otherwise factor score
            raw_score = features.get("ko_fusion_score")
            if raw_score is None:
                raw_score = (
                    getattr(f_val, "score", 0.0)
                    if hasattr(f_val, "score")
                    else f_val.get("score", 0.0) if isinstance(f_val, dict) else float(f_val)
                )
            score = float(raw_score)
        else:
            score = float(
                getattr(f_val, "score", 0.0)
                if hasattr(f_val, "score")
                else f_val.get("score", 0.0) if isinstance(f_val, dict) else float(f_val)
            )

        contribution = eff_weight * score
        additive_score += contribution

        steps[factor_name] = {
            "original_weight": weights.get(factor_name, eff_weight),
            "effective_weight": eff_weight,
            "factor_score": score,
            "weighted_contribution": contribution,
        }

    additive_score = round(additive_score, 4)

    audit_trail: Dict[str, Any] = {
        "original_weights": weights,
        "effective_weights": effective_weights,
        "failed_factors": failed_factors,
        "weights_sum": round(weights_sum, 6),
        "steps": steps,
        "additive_score": additive_score,
    }

    return additive_score, audit_trail


def apply_behavioral_modifier(additive_score: float, bp_modifier: float) -> float:
    """Compute final performance score S = bp_modifier * additive_score, clamped to [0.0, 1.0]."""
    raw_final = bp_modifier * additive_score
    clamped = max(0.0, min(1.0, raw_final))
    return round(clamped, 4)


def build_radar_chart_data(
    factor_scores: Dict[str, Union[FactorOutput, Dict[str, Any], float]]
) -> Dict[str, float]:
    """Extract normalized factor scores dictionary for UI radar chart rendering."""
    radar_data: Dict[str, float] = {}

    for factor_name, val in factor_scores.items():
        if hasattr(val, "score"):
            score = getattr(val, "score")
        elif isinstance(val, dict):
            score = val.get("score", 0.0)
        else:
            score = float(val)

        radar_data[factor_name] = round(float(score), 4)

    return radar_data
