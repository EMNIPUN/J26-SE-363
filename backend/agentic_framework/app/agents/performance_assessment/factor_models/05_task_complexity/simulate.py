"""Task Complexity Factor Simulator (Factor 5).

Grounded in PROPOSAL.md Section 3.1.6:
- Measures: Technical and structural difficulty of assigned sprint responsibilities.
- Important: Computed from pre-existing dependency graph before work begins to avoid
  circular inflation by bloated implementations.
- Feature vector: X_TC = [SP, SC, FI, DR, CB]
    - SP: Story Points
    - SC: Subtask Count
    - FI: Files Involved / touched
    - DR: Dependency Reach (transitive fan-out across modules)
    - CB: Component Breadth (distinct subsystem interfaces crossed)
- Model: Ridge regression form:
    TC = clip(b + w1*norm(SP) + w2*norm(SC) + w3*norm(FI) + w4*norm(DR) + w5*norm(CB), 0.0, 1.0)
- Structural Impact Level: "low" | "medium" | "high"

Supports dual-tier simulation:
- quick: ~1.0s (unit tests, rapid development)
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
    "intercept": 0.12,
    "w_SP": 0.30,
    "w_SC": 0.15,
    "w_FI": 0.15,
    "w_DR": 0.20,
    "w_CB": 0.20,
}

QUICK_DELAY_SECONDS = 1.0
HARD_DELAY_SECONDS = 300.0  # 5 minutes


def calculate_task_complexity_score(features: Dict[str, Any]) -> Dict[str, Any]:
    sp = float(features.get("SP", 5))
    sc = float(features.get("SC", 3))
    fi = float(features.get("FI", 6))
    dr = float(features.get("DR", 4))
    cb = float(features.get("CB", 3))

    # Normalize against typical sprint thresholds
    norm_sp = min(1.0, sp / 8.0)
    norm_sc = min(1.0, sc / 5.0)
    norm_fi = min(1.0, fi / 10.0)
    norm_dr = min(1.0, dr / 8.0)
    norm_cb = min(1.0, cb / 5.0)

    raw_score = (
        RIDGE_WEIGHTS["intercept"]
        + RIDGE_WEIGHTS["w_SP"] * norm_sp
        + RIDGE_WEIGHTS["w_SC"] * norm_sc
        + RIDGE_WEIGHTS["w_FI"] * norm_fi
        + RIDGE_WEIGHTS["w_DR"] * norm_dr
        + RIDGE_WEIGHTS["w_CB"] * norm_cb
    )

    score = round(max(0.0, min(1.0, raw_score)), 4)

    # Qualitative classification
    if score >= 0.70:
        impact_level = "high"
    elif score >= 0.40:
        impact_level = "medium"
    else:
        impact_level = "low"

    return {
        "score": score,
        "features": {
            "SP": sp,
            "SC": sc,
            "FI": fi,
            "DR": dr,
            "CB": cb,
        },
        "structural_impact_level": impact_level,
        "architectural_crossings": cb,
        "model": "RidgeRegression_DependencyGraph",
        "status": "completed",
    }


async def async_simulate(
    payload: Optional[Dict[str, Any]] = None,
    mode: str = "quick",
    duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Asynchronously simulate Task Complexity Factor calculation with configurable delay."""
    delay = duration_seconds if duration_seconds is not None else (
        HARD_DELAY_SECONDS if mode == "hard" else QUICK_DELAY_SECONDS
    )

    start_time = time.time()
    logger.info(f"[ComplexitySimulator] Starting {mode} simulation (planned duration: {delay:.1f}s)...")

    elapsed = 0.0
    step = min(5.0, delay) if delay > 0 else 0
    while elapsed < delay:
        wait_chunk = min(step, delay - elapsed)
        await asyncio.sleep(wait_chunk)
        elapsed = time.time() - start_time
        if delay >= 10.0 and int(elapsed) % 30 == 0:
            logger.info(f"[ComplexitySimulator] In progress... {elapsed:.1f}s / {delay:.1f}s elapsed.")

    features = (payload or {}).get("features", {})
    if not features:
        features = {
            "SP": (payload or {}).get("total_story_points", 5),
            "SC": (payload or {}).get("subtask_count", 3),
            "FI": (payload or {}).get("files_involved", 7),
            "DR": (payload or {}).get("dependency_reach", 4),
            "CB": (payload or {}).get("component_breadth", 3),
        }

    result = calculate_task_complexity_score(features)
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
    parser = argparse.ArgumentParser(description="Simulate Factor 5: Task Complexity")
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
