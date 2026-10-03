"""Effort Factor Simulator (Factor 1).

Grounded in PROPOSAL.md Section 3.1.2:
- Measures: Observable work investment from GitHub and Scrum.
- Feature vector: X_E = [CC, LOC_net, FC, CT, RD]
    - CC: Commit count
    - LOC_net: Net human lines of code changed (excluding dependencies)
    - FC: Files changed
    - CT: Completed assigned tasks
    - RD: Review participation / comments
- Standardized via cohort z-scores: z = (x - mu) / sigma
- Model: Ridge regression form:
    E = b + w1*z_CC + w2*z_LOC + w3*z_FC + w4*z_CT + w5*z_RD
- Clips score between 0.0 and 1.0.
- Applies deduction if third-party dependencies were committed.

Supports dual-tier simulation:
- quick: ~0.5s (unit tests, rapid development)
- hard: 300s (5 min, configurable) to verify thread persistence in LangGraph checkpointer.
"""

import sys
import json
import time
import asyncio
import logging
import argparse
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default cohort reference baselines (mean, std)
COHORT_BASELINES = {
    "CC": {"mean": 12.0, "std": 5.0},
    "LOC_net": {"mean": 250.0, "std": 120.0},
    "FC": {"mean": 8.0, "std": 4.0},
    "CT": {"mean": 3.0, "std": 1.5},
    "RD": {"mean": 4.0, "std": 2.5},
}

# Ridge regression weights from research baseline
RIDGE_WEIGHTS = {
    "intercept": 0.50,
    "w_CC": 0.08,
    "w_LOC": 0.14,
    "w_FC": 0.06,
    "w_CT": 0.12,
    "w_RD": 0.05,
}

QUICK_DELAY_SECONDS = 0.5
HARD_DELAY_SECONDS = 300.0  # 5 minutes


def _compute_z_score(val: float, metric: str) -> float:
    base = COHORT_BASELINES.get(metric, {"mean": 1.0, "std": 1.0})
    std = base["std"] if base["std"] > 0 else 1.0
    return (val - base["mean"]) / std


def calculate_effort_score(features: Dict[str, Any], has_committed_dependencies: bool = False) -> Dict[str, Any]:
    cc = float(features.get("CC", 10))
    loc = float(features.get("LOC_net", 200))
    fc = float(features.get("FC", 6))
    ct = float(features.get("CT", 2))
    rd = float(features.get("RD", 3))

    z_cc = _compute_z_score(cc, "CC")
    z_loc = _compute_z_score(loc, "LOC_net")
    z_fc = _compute_z_score(fc, "FC")
    z_ct = _compute_z_score(ct, "CT")
    z_rd = _compute_z_score(rd, "RD")

    raw_score = (
        RIDGE_WEIGHTS["intercept"]
        + RIDGE_WEIGHTS["w_CC"] * z_cc
        + RIDGE_WEIGHTS["w_LOC"] * z_loc
        + RIDGE_WEIGHTS["w_FC"] * z_fc
        + RIDGE_WEIGHTS["w_CT"] * z_ct
        + RIDGE_WEIGHTS["w_RD"] * z_rd
    )

    penalty = 0.0
    if has_committed_dependencies:
        # Research rule: committing vendor / node_modules penalizes net effort integrity
        penalty = 0.15
        raw_score -= penalty

    score = round(max(0.0, min(1.0, raw_score)), 4)

    return {
        "score": score,
        "features": {
            "CC": cc,
            "LOC_net": loc,
            "FC": fc,
            "CT": ct,
            "RD": rd,
        },
        "z_scores": {
            "z_CC": round(z_cc, 4),
            "z_LOC": round(z_loc, 4),
            "z_FC": round(z_fc, 4),
            "z_CT": round(z_ct, 4),
            "z_RD": round(z_rd, 4),
        },
        "penalty_applied": penalty,
        "has_committed_dependencies": has_committed_dependencies,
        "model": "RidgeRegression",
        "status": "completed",
    }


async def async_simulate(
    payload: Optional[Dict[str, Any]] = None,
    mode: str = "quick",
    duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Asynchronously simulate Effort Factor calculation with configurable delay."""
    delay = duration_seconds if duration_seconds is not None else (
        HARD_DELAY_SECONDS if mode == "hard" else QUICK_DELAY_SECONDS
    )

    start_time = time.time()
    logger.info(f"[EffortSimulator] Starting {mode} simulation (planned duration: {delay:.1f}s)...")

    # Non-blocking async sleep with periodic heartbeat
    elapsed = 0.0
    step = min(5.0, delay) if delay > 0 else 0
    while elapsed < delay:
        wait_chunk = min(step, delay - elapsed)
        await asyncio.sleep(wait_chunk)
        elapsed = time.time() - start_time
        if delay >= 10.0 and int(elapsed) % 30 == 0:
            logger.info(f"[EffortSimulator] In progress... {elapsed:.1f}s / {delay:.1f}s elapsed.")

    features = (payload or {}).get("features", {})
    if not features:
        # Default representative student payload
        features = {
            "CC": (payload or {}).get("commits_count", 14),
            "LOC_net": (payload or {}).get("net_human_loc", 320),
            "FC": (payload or {}).get("files_changed", 9),
            "CT": (payload or {}).get("completed_tasks", 3),
            "RD": (payload or {}).get("reviews_count", 5),
        }

    has_deps = bool((payload or {}).get("has_committed_dependencies", False))
    result = calculate_effort_score(features, has_committed_dependencies=has_deps)
    result["execution_time_seconds"] = round(time.time() - start_time, 3)
    result["mode"] = mode
    return result


def simulate(
    payload: Optional[Dict[str, Any]] = None,
    mode: str = "quick",
    duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Synchronous entry point."""
    return asyncio.run(async_simulate(payload=payload, mode=mode, duration_seconds=duration_seconds))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Factor 1: Effort")
    parser.add_argument("--mode", choices=["quick", "hard"], default="quick", help="Simulation tier")
    parser.add_argument("--duration", type=float, default=None, help="Custom sleep duration in seconds")
    parser.add_argument("--input", type=str, default=None, help="Path to input JSON payload")
    args = parser.parse_args()

    input_payload = None
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            input_payload = json.load(f)

    res = simulate(payload=input_payload, mode=args.mode, duration_seconds=args.duration)
    print(json.dumps(res, indent=2))
