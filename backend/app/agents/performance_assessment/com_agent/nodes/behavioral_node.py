"""Behavioral pattern classification node for com_agent.

Strictly aligned with:
- BOARD.md T5.6 (T5.6.1)
- PLAN.md Section 9 Node 7 (run_behavioral_pattern_node)
- User Constraint: Uses RAW uncapped code ownership (ko_raw_score), never capped score.
"""

import logging
from typing import Dict, Any, Tuple
from app.agents.performance_assessment.com_agent.state import FactorOutput

logger = logging.getLogger(__name__)


def classify_persona(signals: Dict[str, float]) -> Tuple[str, float]:
    """Classify student into one of 5 contributor archetypes.

    Returns:
        (persona_name, bp_modifier) where bp_modifier in [0.80, 1.20]
    """
    effort = signals.get("effort", 0.5)
    consistency = signals.get("consistency", 0.5)
    collaboration = signals.get("collaboration", 0.5)
    ko_raw = signals.get("ko_raw", 0.5)

    if effort >= 0.70 and consistency >= 0.60 and ko_raw >= 0.65:
        return "Consistent Builder", 1.10
    elif collaboration >= 0.70 and effort >= 0.45:
        return "Collaborative Harmonizer", 1.05
    elif effort >= 0.60 and consistency < 0.35:
        return "Deadline Rusher", 0.90
    elif effort < 0.30 and collaboration < 0.30:
        return "Disengaged Contributor", 0.85
    else:
        return "Balanced Contributor", 1.00


async def run_behavioral_pattern_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """T5.6.1: Node 7 — Behavioral Pattern Persona Classifier.

    Collects effort, consistency, collaboration, and RAW uncapped ko_raw_score.
    Determines contributor archetype and sets behavioral_modifier in [0.80, 1.20].
    """
    factor_scores: Dict[str, Any] = state.get("factor_scores", {})

    def _get_score(name: str) -> float:
        val = factor_scores.get(name)
        if val is None:
            return 0.5
        if hasattr(val, "score"):
            return float(getattr(val, "score"))
        if isinstance(val, dict):
            return float(val.get("score", 0.5))
        return float(val)

    effort = _get_score("effort")
    consistency = _get_score("consistency")
    collaboration = _get_score("collaboration")

    # Explicitly use RAW uncapped score per design specification
    ko_raw = state.get("ko_raw_score")
    if ko_raw is None:
        ko_val = factor_scores.get("code_ownership")
        if ko_val and hasattr(ko_val, "features"):
            ko_raw = ko_val.features.get("ko_raw_score")
        elif isinstance(ko_val, dict):
            ko_raw = ko_val.get("features", {}).get("ko_raw_score")
        if ko_raw is None:
            ko_raw = _get_score("code_ownership")

    ko_raw = float(ko_raw) if ko_raw is not None else 0.5

    signals = {
        "effort": effort,
        "consistency": consistency,
        "collaboration": collaboration,
        "ko_raw": ko_raw,
    }

    persona, modifier = classify_persona(signals)

    # Clamping guarantee [0.80, 1.20]
    modifier = max(0.80, min(1.20, float(modifier)))

    return {
        "behavioral_persona": persona,
        "behavioral_modifier": round(modifier, 4),
        "current_step": "behavioral_pattern_classified",
    }
