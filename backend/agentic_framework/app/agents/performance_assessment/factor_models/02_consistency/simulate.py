"""Consistency Factor Simulator (Factor 2).

Grounded in PROPOSAL.md Section 3.1.3:
- Measures: Spread of work over the sprint duration (steady vs. deadline rush).
- Feature vector: X_C = [AWR, 1 - DC, 1 - LI_norm, 1 - CV_norm]
    - AWR: Active Window Ratio (active days / sprint duration days)
    - DC: Deadline Concentration (proportion of work done in final 48h)
    - LI_norm: Normalised Longest Inactivity period (longest gap / total sprint duration)
    - CV_norm: Normalised Activity Variability (coefficient of variation of daily commit counts)
- Higher feature values represent higher consistency.
- Model: Ridge regression form:
    C = clip(b + w1*AWR + w2*(1-DC) + w3*(1-LI_norm) + w4*(1-CV_norm), 0.0, 1.0)
- Flags procrastination pattern if DC > 0.65 or AWR < 0.25.

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

RIDGE_WEIGHTS = {
    "intercept": 0.15,
    "w_AWR": 0.30,
    "w_no_DC": 0.25,
    "w_no_LI": 0.15,
    "w_no_CV": 0.15,
}

QUICK_DELAY_SECONDS = 0.5
HARD_DELAY_SECONDS = 300.0  # 5 minutes


def calculate_consistency_score(features: Dict[str, Any]) -> Dict[str, Any]:
    awr = float(features.get("AWR", 0.65))
    dc = float(features.get("DC", 0.30))
    li_norm = float(features.get("LI_norm", 0.25))
    cv_norm = float(features.get("CV_norm", 0.35))

    # Bound features between 0.0 and 1.0
    awr = max(0.0, min(1.0, awr))
    dc = max(0.0, min(1.0, dc))
    li_norm = max(0.0, min(1.0, li_norm))
    cv_norm = max(0.0, min(1.0, cv_norm))

    score_raw = (
        RIDGE_WEIGHTS["intercept"]
        + RIDGE_WEIGHTS["w_AWR"] * awr
        + RIDGE_WEIGHTS["w_no_DC"] * (1.0 - dc)
        + RIDGE_WEIGHTS["w_no_LI"] * (1.0 - li_norm)
        + RIDGE_WEIGHTS["w_no_CV"] * (1.0 - cv_norm)
    )

    score = round(max(0.0, min(1.0, score_raw)), 4)
    procrastination_detected = (dc > 0.65) or (awr < 0.25)

    return {
        "score": score,
        "features": {
            "AWR": round(awr, 4),
            "DC": round(dc, 4),
            "LI_norm": round(li_norm, 4),
            "CV_norm": round(cv_norm, 4),
        },
        "procrastination_detected": procrastination_detected,
        "steady_cadence": score >= 0.70,
        "model": "RidgeRegression",
        "status": "completed",
    }


async def async_simulate(
    payload: Optional[Dict[str, Any]] = None,
    mode: str = "quick",
    duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Asynchronously simulate Consistency Factor calculation with configurable delay."""
    delay = duration_seconds if duration_seconds is not None else (
        HARD_DELAY_SECONDS if mode == "hard" else QUICK_DELAY_SECONDS
    )

    start_time = time.time()
    logger.info(f"[ConsistencySimulator] Starting {mode} simulation (planned duration: {delay:.1f}s)...")

    elapsed = 0.0
    step = min(5.0, delay) if delay > 0 else 0
    while elapsed < delay:
        wait_chunk = min(step, delay - elapsed)
        await asyncio.sleep(wait_chunk)
        elapsed = time.time() - start_time
        if delay >= 10.0 and int(elapsed) % 30 == 0:
            logger.info(f"[ConsistencySimulator] In progress... {elapsed:.1f}s / {delay:.1f}s elapsed.")

    features = (payload or {}).get("features", {})
    if not features:
        active_days = (payload or {}).get("active_days_count", 8)
        sprint_days = (payload or {}).get("sprint_duration_days", 14)
        awr = active_days / sprint_days if sprint_days > 0 else 0.5
        features = {
            "AWR": awr,
            "DC": (payload or {}).get("deadline_concentration", 0.28),
            "LI_norm": (payload or {}).get("longest_inactivity_norm", 0.20),
            "CV_norm": (payload or {}).get("activity_variability_norm", 0.30),
        }

    result = calculate_consistency_score(features)
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
    parser = argparse.ArgumentParser(description="Simulate Factor 2: Consistency")
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
