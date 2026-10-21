"""Production entry point of the Collaboration factor (looked up by ``com_agent/factor_bridge.py``: ``factor_models/04_collaboration/evaluate.py``).

``evaluate(payload, context)`` takes the raw evidence (``evidence/1``) for one student and sprint, or a payload holding it under ``"evidence"``, and returns the
standard factor result ``{factor, score, interval, features, removed, versions, warnings}``. When the score is not available (the team showed no review
activity) it raises ``NotEnoughEvidence`` with a readable message: the bridge then applies its fallback (status ``fallback_applied``) and fusion redistributes
the weight instead of treating the student as low. See PROTOCOL.md.

Until the agent's ingestion hands over raw evidence (ARCHITECTURE.md, section 9), the agent still sends feature payloads; ``async_evaluate`` passes those to the
existing simulator, so adding this file changes nothing for the agent today and the real tool takes over by itself once evidence is supplied.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_score = _load("collab_score", "score.py")
NotEnoughEvidence = _score.NotEnoughEvidence


def _as_evidence(payload):
    """The evidence dict when the payload is (or holds) raw evidence/1, else None."""
    if isinstance(payload, dict):
        for candidate in (payload, payload.get("evidence")):
            if isinstance(candidate, dict) and candidate.get("schema") == "evidence/1":
                return candidate
    return None


def evaluate(payload, context=None):
    evidence = _as_evidence(payload)
    if evidence is None:
        raise ValueError("collaboration: the payload is not evidence/1")
    result = _score.assess(evidence)
    if result["score"] is None:
        raise NotEnoughEvidence("; ".join(w for w in result["warnings"] if w.startswith("not available")) or "collaboration score not available")
    return result


async def async_evaluate(payload, context=None):
    if _as_evidence(payload) is not None:
        return evaluate(payload, context)
    ctx = context or {}
    mode = ctx.get("simulation_mode") or os.getenv("FACTOR_SIMULATION_MODE", "quick")
    duration = 0.01 if "pytest" in sys.modules else None
    sim = _load("collab_simulate", "simulate.py")
    return await sim.async_simulate(payload=payload, mode=mode, duration_seconds=duration)
