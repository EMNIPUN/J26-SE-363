"""Production entry point of the Behavioral Pattern factor (looked up by ``com_agent/factor_bridge.py``: ``factor_models/06_behavioral_pattern/evaluate.py``).

The agent's behavioral node passes the other factors' scores and gets the pattern and the score modifier back; all rules live in ``rules.py`` (thresholds in
``thresholds.json``), none in the agent. ``classify`` is the name the bridge looks for. A score that is missing (the factor was not available or fell back) is passed as ``None``
and is never replaced by a typical value.

    classify({"effort": .., "consistency": .., "collaboration": .. or None, "is_bimodal": 0/1 or None, "late_churn": 0..1 or None}) -> {persona, score_modifier, rationale, ...}

``late_churn`` is the Consistency package's late-churn share (``C_DC``); pass ``None`` when the student had no activity or the value is not available.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_rules = _load("bp_rules", "rules.py")


def classify(factor_scores, context=None):
    fs = factor_scores or {}
    th = None
    name = (context or {}).get("bp_thresholds") if isinstance(context, dict) else None
    if name:
        th = _rules.load_thresholds(name)
    return _rules.classify({"E": fs.get("effort"), "C": fs.get("consistency"), "Co": fs.get("collaboration")}, fs.get("is_bimodal"), th, fs.get("late_churn"))


def evaluate(payload, context=None):
    """Same as ``classify``; accepts the scores directly or under ``factor_scores``."""
    return classify(payload.get("factor_scores", payload), context)
