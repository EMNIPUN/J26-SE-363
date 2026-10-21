"""The factors as tools: one call per factor through the factor bridge, with the result turned into a plain dict the graph, the store and the audit all use.

    {"factor", "score" (None unless completed), "status": completed | not_available | fallback, "interval", "warnings", "versions", "features", "provisional", "removed", "tasks", "model"}

"not_available" means the factor itself says it cannot be scored (for example Collaboration when nobody in the team reviewed): fusion shares its weight, nobody is marked down.
"fallback" means something failed; the audit treats it as a problem to look at. A factor's score is only ever produced by the factor package; nothing in the agent invents or edits one.
"""
from app.agents.performance_assessment.com_agent import factor_bridge

PASSIVE_FACTORS = ("effort", "consistency", "requirement_fulfillment", "collaboration", "task_complexity")
ALL_FACTORS = PASSIVE_FACTORS + ("code_ownership", "behavioral_pattern")


def _as_result(name, out) -> dict:
    feats = dict(out.features or {})
    meta = feats.pop("_result", {})
    failure = feats.pop("failure_kind", None)
    if out.status == "completed":
        status, score = "completed", float(out.score)
    else:
        status, score = ("not_available" if failure == "not_available" else "fallback"), None
    warnings = list(meta.get("warnings", []))
    if status != "completed" and out.error_message:
        warnings.append(out.error_message)
    return {"factor": name, "score": score, "status": status, "interval": meta.get("interval"), "warnings": warnings, "versions": meta.get("versions", {}), "features": feats,
            "provisional": bool(meta.get("provisional", False)), "removed": meta.get("removed", {}), "tasks": meta.get("tasks"), "model": meta.get("model")}


async def run_factor(name: str, evidence: dict, *, patches_ref: str | None = None, context: dict | None = None) -> dict:
    """Run one of the five factors that read evidence. ``context`` carries the language-model client and progress callback for Requirement Fulfillment."""
    payload = {"evidence": evidence, "patches_ref": patches_ref} if name == "requirement_fulfillment" else evidence
    out = await factor_bridge.evaluate_factor(name, payload, context=context or {})
    return _as_result(name, out)


def behavioral_signals(results: dict) -> dict:
    """The inputs of the Behavioral Pattern rules from the other factors' results; a factor that is not completed is passed as None (never as 0)."""
    def score(n):
        r = results.get(n)
        return r["score"] if r and r["status"] == "completed" else None

    cons = (results.get("consistency") or {}).get("features", {})
    bimodal = cons.get("C_bimodal") if cons.get("C_bimodal") in (0, 1, True, False) else None
    late = None if cons.get("C_no_activity") in (1, True) or cons.get("C_DC") is None else float(cons["C_DC"])
    return {"effort": score("effort"), "consistency": score("consistency"), "collaboration": score("collaboration"), "is_bimodal": None if bimodal is None else int(bool(bimodal)), "late_churn": late}


def run_behavioral(results: dict, provisional: bool = False) -> dict:
    """Behavioral Pattern from the other factors' results. During a sprint it is a tendency: reported, with ``applied`` False, so no modifier reaches the mark."""
    signals = behavioral_signals(results)
    resolved = factor_bridge._resolve_factor_module("behavioral_pattern")
    if not resolved or not hasattr(resolved[0], "classify"):
        return {"factor": "behavioral_pattern", "status": "fallback", "persona": "Unclassified", "modifier": 1.0, "applied": False, "warnings": ["the Behavioral Pattern package could not be loaded"],
                "signals": signals, "rationale": ""}
    r = resolved[0].classify(signals)
    return {"factor": "behavioral_pattern", "status": "completed", "persona": r["persona"], "modifier": r["score_modifier"], "applied": not provisional and r["persona"] != "Unclassified",
            "rationale": r["rationale"], "strength": r.get("strength"), "near_threshold": r.get("near_threshold"), "untestable_rules": r.get("untestable_rules", {}), "evidence": r.get("evidence"),
            "warnings": r.get("warnings", []), "thresholds": r.get("thresholds"), "signals": signals, "provisional": provisional}
