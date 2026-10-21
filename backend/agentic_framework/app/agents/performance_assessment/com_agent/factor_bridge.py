"""Factor Model Bridge and Dispatcher.

Strictly decouples the LangGraph agent from the concrete factor model implementations:
- Agent nodes and tools invoke `evaluate_factor()` through this bridge.
- The agent NEVER directly imports or executes `simulate.py` or factor model files.
- Dynamic Resolution Order:
    1. Production Model (`factor_models/<dir>/evaluate.py`, `predict.py`, or `model.py`)
    2. Factor Simulator (`factor_models/<dir>/simulate.py`)
    3. Safe Heuristic Fallback Policy
- When `simulate.py` is removed after the real ML model is trained, the agent
  seamlessly switches to the production model with ZERO changes to agent code.
"""

import os
import sys
import logging
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from app.agents.performance_assessment.com_agent.state import FactorOutput
from app.agents.performance_assessment.com_agent.policies.fallback_policies import (
    get_fallback_for_factor,
)

logger = logging.getLogger(__name__)

FACTOR_DIR_MAP = {
    "effort": "01_effort",
    "consistency": "02_consistency",
    "requirement_fulfillment": "03_requirement_fulfillment",
    "collaboration": "04_collaboration",
    "task_complexity": "05_task_complexity",
    "behavioral_pattern": "06_behavioral_pattern",
    "code_ownership": "07_code_ownership",
}

_LOADED_MODULES_CACHE: Dict[str, Any] = {}


def _get_factor_models_root() -> Path:
    """Locate the factor_models directory."""
    # This file is in com_agent/, parent is performance_assessment/
    return Path(__file__).resolve().parent.parent / "factor_models"


def _resolve_factor_module(factor_name: str) -> Optional[Tuple[Any, str]]:
    """Dynamically resolves the factor model or simulator module without direct imports.

    Returns:
        (module, "production") or (module, "simulator") or None
    """
    folder_name = FACTOR_DIR_MAP.get(factor_name)
    if not folder_name:
        return None

    cache_key = f"factor_{factor_name}"
    if cache_key in _LOADED_MODULES_CACHE:
        return _LOADED_MODULES_CACHE[cache_key]

    factor_dir = _get_factor_models_root() / folder_name

    # 1. Check for production model entrypoints first
    for prod_name in ["evaluate.py", "predict.py", "model.py"]:
        prod_path = factor_dir / prod_name
        if prod_path.exists():
            try:
                spec = importlib.util.spec_from_file_location(f"prod_{folder_name}", prod_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                logger.info(f"Loaded production factor model for '{factor_name}' from {prod_path.name}")
                _LOADED_MODULES_CACHE[cache_key] = (mod, "production")
                return (mod, "production")
            except Exception as e:
                logger.warning(f"Failed to load production model from {prod_path}: {e}")

    # 2. Check for simulator entrypoint
    sim_path = factor_dir / "simulate.py"
    if sim_path.exists():
        try:
            spec = importlib.util.spec_from_file_location(f"sim_{folder_name}", sim_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _LOADED_MODULES_CACHE[cache_key] = (mod, "simulator")
            return (mod, "simulator")
        except Exception as e:
            logger.warning(f"Failed to load factor simulator from {sim_path}: {e}")

    return None


async def evaluate_factor(
    factor_name: str,
    payload: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    mode: Optional[str] = None,
    duration_seconds: Optional[float] = None,
) -> FactorOutput:
    """Main decoupled entry point for the agent to evaluate any factor.

    The agent passes extracted features/data; the bridge routes to either
    the production model or the simulator, returning a standardized FactorOutput.
    """
    ctx = context or {}
    sim_mode = mode or ctx.get("simulation_mode") or os.getenv("FACTOR_SIMULATION_MODE", "quick")

    # Fast test duration default under pytest if not explicitly specified
    if duration_seconds is None:
        env_dur = os.getenv("FACTOR_SIMULATION_DURATION")
        if env_dur:
            try:
                duration_seconds = float(env_dur)
            except ValueError:
                pass
        elif "pytest" in sys.modules:
            duration_seconds = 0.01

    resolved = _resolve_factor_module(factor_name)

    if not resolved:
        logger.warning(f"No factor module found for '{factor_name}', falling back to default heuristic.")
        return get_fallback_for_factor(factor_name, "No factor implementation or simulator found")

    mod, tier = resolved

    try:
        if tier == "production":
            # Production model execution
            if hasattr(mod, "async_evaluate"):
                raw_res = await mod.async_evaluate(payload, context=ctx)
            elif hasattr(mod, "evaluate"):
                raw_res = mod.evaluate(payload, context=ctx)
            elif hasattr(mod, "predict"):
                raw_res = mod.predict(payload)
            else:
                raise AttributeError(f"Production model for {factor_name} has no evaluate/predict function")
        else:
            # Simulator execution
            if hasattr(mod, "async_simulate"):
                raw_res = await mod.async_simulate(
                    payload=payload,
                    mode=sim_mode,
                    duration_seconds=duration_seconds,
                )
            elif hasattr(mod, "simulate"):
                raw_res = mod.simulate(
                    payload=payload,
                    mode=sim_mode,
                    duration_seconds=duration_seconds,
                )
            else:
                raise AttributeError(f"Simulator for {factor_name} has no simulate function")

        # Normalize score and features into FactorOutput
        score = float(raw_res.get("score", 0.50))
        merged_features = dict(payload.get("features", {}))
        merged_features.update(raw_res.get("features", {}))

        # Copy any special diagnostic flags
        for k in ["procrastination_detected", "substantiveness_rating", "structural_impact_level", "traceability_rate"]:
            if k in raw_res:
                merged_features[k] = raw_res[k]
        # What a production factor reports besides the score (band, warnings, versions, what was removed, per-task detail); the graph's audit and explanation read it from here
        meta = {k: raw_res[k] for k in ("interval", "warnings", "versions", "removed", "provisional", "sprint_elapsed", "model", "tasks", "usage") if k in raw_res}
        if meta:
            merged_features["_result"] = meta

        evidence_traces = raw_res.get("evidence_traces", [])
        if not evidence_traces:
            evidence_traces = [
                {"factor": factor_name, "model": raw_res.get("model", tier), "score": score}
            ]

        return FactorOutput(
            score=round(max(0.0, min(1.0, score)), 4),
            features=merged_features,
            evidence_traces=evidence_traces,
            status="completed",
        )

    except Exception as e:
        # "not available" (the factor says it cannot be scored) is not the same as a failure: the graph and the lecturer see the difference
        kind = "not_available" if type(e).__name__ == "NotEnoughEvidence" else "error"
        (logger.info if kind == "not_available" else logger.error)(f"Factor '{factor_name}' via bridge: {kind}: {e}")
        out = get_fallback_for_factor(factor_name, str(e))
        out.features = {"failure_kind": kind}
        return out


async def generate_quiz_via_bridge(
    payload: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Bridge for Factor 7 phase 1: the Code Ownership package picks the student's code and builds the AST question.

    Returns the quiz dict, or None when the package has no ``generate_quiz`` (simulator only), found no function worth asking about, or failed;
    the quiz node then keeps its placeholder quiz.
    """
    resolved = _resolve_factor_module("code_ownership")
    if not resolved:
        return None
    mod, tier = resolved
    if tier != "production" or not hasattr(mod, "generate_quiz"):
        return None
    try:
        return mod.generate_quiz(payload, context=context or {})
    except Exception as e:
        logger.warning(f"Code Ownership quiz generation failed, keeping the placeholder quiz: {e}")
        return None


async def generate_quizzes_via_bridge(payload, context=None):
    resolved = _resolve_factor_module("code_ownership")
    if not resolved:
        return []
    mod, tier = resolved
    if tier != "production":
        return []
    try:
        if hasattr(mod, "generate_many"):
            return mod.generate_many(payload.get("files") or [], payload.get("student_id", ""), payload.get("sprint_id", ""), payload.get("count", 10))
        one = await generate_quiz_via_bridge(payload, context)
        return [one] if one else []
    except Exception as e:
        logger.warning("Code Ownership quiz batch generation failed: %s", e)
        return []
async def classify_persona_via_bridge(
    factor_scores: Dict[str, float],
    context: Optional[Dict[str, Any]] = None,
    mode: Optional[str] = None,
    duration_seconds: Optional[float] = None,
) -> Tuple[str, float, str]:
    """Bridge for Factor 6: Behavioral Pattern.

    Returns:
        (persona_name, score_modifier, rationale)
    """
    ctx = context or {}
    sim_mode = mode or ctx.get("simulation_mode") or os.getenv("FACTOR_SIMULATION_MODE", "quick")
    dur = duration_seconds if duration_seconds is not None else (0.01 if "pytest" in sys.modules else None)

    resolved = _resolve_factor_module("behavioral_pattern")
    if resolved:
        mod, tier = resolved
        try:
            if hasattr(mod, "async_simulate"):
                res = await mod.async_simulate(
                    payload={"factor_scores": factor_scores},
                    mode=sim_mode,
                    duration_seconds=dur,
                )
            elif hasattr(mod, "classify"):
                res = mod.classify(factor_scores)
            else:
                res = mod.simulate(payload={"factor_scores": factor_scores}, mode=sim_mode, duration_seconds=dur)

            persona = res.get("persona", "Balanced Contributor")
            modifier = float(res.get("score_modifier", 1.00))
            rationale = res.get("rationale", "Normal contribution pattern.")
            return persona, modifier, rationale
        except Exception as e:
            logger.warning(f"Behavioral pattern bridge fallback: {e}")

    # Neither the Behavioral Pattern package nor its simulator could be loaded: no pattern and no adjustment (the rules live in factor_models/06_behavioral_pattern)
    return "Unclassified", 1.00, "Behavioral Pattern rules unavailable: no adjustment applied."
