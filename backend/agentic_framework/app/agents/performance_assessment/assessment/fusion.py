"""The final mark: S = BP_modifier * sum(w_k * factor_k), on the factors that exist, with the weights of missing ones shared out (plain arithmetic, no language model).

Uses the project's fusion engine (com_agent/fusion_engine) so the formula has one implementation. A factor that is "not available" or failed is left out and its weight shared in proportion;
a factor still pending (Code Ownership before the student has answered the quiz) is treated the same way and listed as pending, so the mark is provisional until it arrives.
The band is conservative: it adds up the factors' own bands with the same weights, as if their errors all went the same way.
"""
from app.agents.performance_assessment.com_agent.fusion_engine.calculator import apply_behavioral_modifier, compute_additive_score
from app.agents.performance_assessment.com_agent.fusion_engine.weights_config import get_weights_as_dict

DEFAULT_BAND = 0.2  # half-width assumed for a factor that gave no band of its own


def fuse(results: dict, behavioral: dict | None = None, weights: dict | None = None) -> dict:
    weights = weights or get_weights_as_dict()
    inputs, pending = {}, []
    for name in weights:
        r = results.get(name)
        if r is None or r.get("status") == "pending":
            pending.append(name)
            continue
        inputs[name] = {"score": r["score"], "status": "completed" if r["status"] == "completed" and r["score"] is not None else "fallback_applied"}
    if not any(v["status"] == "completed" for v in inputs.values()):
        return {"mark": None, "mark_interval": None, "additive": None, "modifier": 1.0, "effective_weights": {}, "failed_factors": sorted(set(weights) - set(inputs)) + [n for n, v in inputs.items() if v["status"] != "completed"],
                "pending": pending, "steps": {}, "behavioral": behavioral, "note": "no factor could be scored"}
    additive, audit = compute_additive_score(inputs, weights)
    modifier = float(behavioral["modifier"]) if behavioral and behavioral.get("applied") else 1.0
    final = apply_behavioral_modifier(additive, modifier)
    lo = hi = 0.0
    for name, w in audit["effective_weights"].items():
        r = results[name]
        band = r.get("interval") or [max(0.0, r["score"] - DEFAULT_BAND), min(1.0, r["score"] + DEFAULT_BAND)]
        lo += w * band[0]
        hi += w * band[1]
    return {"mark": round(100 * final, 2), "mark_interval": [round(100 * max(0.0, min(1.0, lo * modifier)), 2), round(100 * max(0.0, min(1.0, hi * modifier)), 2)], "additive": additive, "modifier": modifier,
            "effective_weights": audit["effective_weights"], "failed_factors": audit["failed_factors"], "pending": pending, "steps": audit["steps"], "behavioral": behavioral,
            "weights_version": "weights_config.yaml"}
