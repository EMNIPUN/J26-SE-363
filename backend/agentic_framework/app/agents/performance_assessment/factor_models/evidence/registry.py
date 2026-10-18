"""Loads each factor package's cleaning module by path (the folders start with digits, so they cannot be imported by name).

    from evidence.registry import load_factors
    factors = load_factors()
    result = factors["effort"].featurize(evidence)
"""

import importlib.util
from pathlib import Path

FM = Path(__file__).resolve().parents[1]
FOLDERS = {
    "effort": "01_effort", "consistency": "02_consistency", "rf": "03_requirement_fulfillment",
    "collab": "04_collaboration", "tc": "05_task_complexity", "bp": "06_behavioral_pattern", "ko": "07_code_ownership",
}


def load_factors(names=None):
    out = {}
    for name in names or FOLDERS:
        spec = importlib.util.spec_from_file_location(f"cleaning_{FOLDERS[name]}", FM / FOLDERS[name] / "cleaning.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        out[name] = module
    return out


def featurize_all(evidence, factors):
    """Run every factor's featurize on one evidence dict. Returns (merged features, removed summary, warnings)."""
    features, removed, warnings = {}, {}, []
    for name, module in factors.items():
        if not hasattr(module, "featurize"):
            continue
        result = module.featurize(evidence)
        features.update(result["features"])
        removed.update(result.get("removed") or {})
        warnings += [f"{name}: {w}" for w in result.get("warnings", [])]
    return features, removed, warnings
