"""Behavioral pattern classification node for com_agent.

Strictly aligned with:
- BOARD.md T5.6 (T5.6.1)
- PLAN.md Section 9 Node 7 (run_behavioral_pattern_node)

The node only gathers the inputs and writes the result into the state. The rules, the thresholds and the modifier live in ``factor_models/06_behavioral_pattern``
(``rules.py``, ``thresholds.json``) and are reached through the factor bridge; nothing about the patterns is decided here.

A score the agent could not compute (the factor fell back or is missing, for example Collaboration when nobody in the team reviewed in the sprint) is passed on as ``None``:
the rules that need it are then reported as not testable, never fed a typical value.
"""

import logging
from typing import Any, Dict, Optional

from app.agents.performance_assessment.com_agent.factor_bridge import classify_persona_via_bridge

logger = logging.getLogger(__name__)


def _score_or_none(factor_scores: Dict[str, Any], name: str) -> Optional[float]:
    """The factor's score, or None when it is absent or was not really computed (fallback / missing)."""
    val = factor_scores.get(name)
    if val is None:
        return None
    status = getattr(val, "status", None) if not isinstance(val, dict) else val.get("status")
    if status in ("fallback_applied", "missing"):
        return None
    score = getattr(val, "score", None) if not isinstance(val, (dict, int, float)) else (val.get("score") if isinstance(val, dict) else val)
    return None if score is None else float(score)


def _bimodal_flag(factor_scores: Dict[str, Any]) -> Optional[int]:
    val = factor_scores.get("consistency")
    feats = getattr(val, "features", None) if not isinstance(val, dict) else val.get("features")
    for key in ("C_bimodal", "is_bimodal", "bimodal"):
        if isinstance(feats, dict) and feats.get(key) in (0, 1, True, False):
            return int(bool(feats[key]))
    return None


def _late_churn(factor_scores: Dict[str, Any]) -> Optional[float]:
    """The Consistency package's late-churn share (C_DC), only for a student who had activity (no activity gives the worst value by construction)."""
    val = factor_scores.get("consistency")
    feats = getattr(val, "features", None) if not isinstance(val, dict) else val.get("features")
    if not isinstance(feats, dict) or feats.get("C_no_activity") in (1, True) or feats.get("C_DC") is None:
        return None
    return float(feats["C_DC"])


async def run_behavioral_pattern_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """T5.6.1: Node 7 — Behavioral Pattern classifier. Sets behavioral_persona and behavioral_modifier (within 0.80-1.20, enforced by the rules)."""
    factor_scores: Dict[str, Any] = state.get("factor_scores", {})
    signals = {
        "effort": _score_or_none(factor_scores, "effort"),
        "consistency": _score_or_none(factor_scores, "consistency"),
        "collaboration": _score_or_none(factor_scores, "collaboration"),
        "is_bimodal": _bimodal_flag(factor_scores),
        "late_churn": _late_churn(factor_scores),
    }
    persona, modifier, _rationale = await classify_persona_via_bridge(signals, context=state)
    return {
        "behavioral_persona": persona,
        "behavioral_modifier": round(max(0.80, min(1.20, float(modifier))), 4),
        "current_step": "behavioral_pattern_classified",
    }
