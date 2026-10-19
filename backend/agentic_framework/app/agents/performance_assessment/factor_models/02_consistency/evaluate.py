"""Production entry point of the consistency factor (looked up by com_agent/factor_bridge.py).

evaluate(payload) takes raw evidence (evidence/1, optionally with "as_of" for a provisional result during the sprint) or {"features": {...}} with this factor's own feature names, and
returns the standard result {factor, score, interval, features, removed, versions, warnings, provisional}. The model is a ridge card (model/consistency_model.json, written by
ml_lib/fit_production.py) evaluated without scikit-learn; see PRODUCTION_MODEL.md for how it was chosen and what it does not show.
Until the agent hands over evidence, payloads in an older format go to simulate.py exactly as before.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from evidence import linear_model as _lm  # noqa: E402

NotEnoughEvidence = _lm.NotEnoughEvidence
CARD = HERE / "model" / "consistency_model.json"
MIN_DAYS = 5  # days of the sprint that must have passed before a provisional score is given


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_clean = _load("consistency_cleaning_prod", "cleaning.py")


def evaluate(payload, context=None):
    return _lm.evaluate(CARD, _clean, payload, context, min_days=MIN_DAYS, factor="consistency")


def _usable(payload):
    if isinstance(payload, dict) and payload.get("schema") == "evidence/1":
        return True
    return isinstance(payload, dict) and _lm.covers(CARD, payload.get("features"))


async def async_evaluate(payload, context=None):
    if _usable(payload):
        return evaluate(payload, context)
    ctx = context or {}
    mode = ctx.get("simulation_mode") or os.getenv("FACTOR_SIMULATION_MODE", "quick")
    duration = 0.01 if "pytest" in sys.modules else None
    sim = _load("consistency_simulate", "simulate.py")
    return await sim.async_simulate(payload=payload, mode=mode, duration_seconds=duration)
