"""Behavioral Pattern Factor Simulator (Factor 6).

Grounded in PROPOSAL.md Section 3.1.7:
- Measures: Contributor typology identified through cross-factor performance.
- Not a trained regression model; a rule-based classifier evaluating 5 literature-backed patterns:
    1. Consistent deep contributor: Effort > 0.70 and Consistency > 0.70 -> modifier: 1.15
    2. Last-minute rusher: Effort > 0.70 and Consistency < 0.30 -> modifier: 0.92
    3. Reviewer or coordinator: Effort < 0.40 and Collaboration > 0.70 -> modifier: 1.02
    4. Burst worker: Effort > 0.70 and Activity variability bimodal -> modifier: 0.98
    5. Free rider: Effort < 0.30 and Collaboration < 0.30 -> modifier: 0.82
    - Fallback: Balanced contributor -> modifier: 1.00
- Multiplier is applied to the final composite score to reward proactive teamwork or penalize free-riding.

Supports dual-tier simulation:
- quick: ~0.3s (unit tests, rapid development)
- hard: 60s (1 min, configurable) to verify thread persistence in LangGraph checkpointer.
"""

import sys
import json
import time
import asyncio
import logging
import argparse
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

QUICK_DELAY_SECONDS = 0.3
HARD_DELAY_SECONDS = 60.0  # 1 minute


def classify_behavioral_pattern(factor_scores: Dict[str, float]) -> Dict[str, Any]:
    e = float(factor_scores.get("effort", 0.75))
    c = float(factor_scores.get("consistency", 0.70))
    co = float(factor_scores.get("collaboration", 0.65))
    ko = float(factor_scores.get("code_ownership", 0.80))
    rf = float(factor_scores.get("requirement_fulfillment", 0.75))

    # Evaluate canonical rules in priority order
    if e > 0.70 and c > 0.70:
        persona = "Consistent deep contributor"
        modifier = 1.15
        rationale = "Demonstrates steady, high-volume contributions across the entire sprint duration."
    elif e > 0.70 and c < 0.30:
        persona = "Last-minute rusher"
        modifier = 0.92
        rationale = "Heavy commit volume concentrated almost entirely at sprint deadlines."
    elif e < 0.40 and co > 0.70:
        persona = "Reviewer or coordinator"
        modifier = 1.02
        rationale = "Focuses heavily on code reviews, discussion, and coordinating teammates rather than raw coding."
    elif e < 0.30 and co < 0.30:
        persona = "Free rider"
        modifier = 0.82
        rationale = "Critically low observable coding effort combined with negligible collaboration."
    elif e > 0.70 and factor_scores.get("is_bimodal", False):
        persona = "Burst worker"
        modifier = 0.98
        rationale = "High overall work delivered in irregular, disconnected bursts."
    else:
        persona = "Balanced contributor"
        modifier = 1.00
        rationale = "Normal, well-distributed contributions meeting course baseline expectations."

    return {
        "persona": persona,
        "score_modifier": modifier,
        "rationale": rationale,
        "pattern_features": {
            "effort": e,
            "consistency": c,
            "collaboration": co,
            "code_ownership": ko,
            "requirement_fulfillment": rf,
        },
        "model": "RuleBasedTypologyClassifier",
        "status": "completed",
    }


async def async_simulate(
    payload: Optional[Dict[str, Any]] = None,
    mode: str = "quick",
    duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Asynchronously simulate Behavioral Pattern classification with configurable delay."""
    delay = duration_seconds if duration_seconds is not None else (
        HARD_DELAY_SECONDS if mode == "hard" else QUICK_DELAY_SECONDS
    )

    start_time = time.time()
    logger.info(f"[BehavioralSimulator] Starting {mode} simulation (planned duration: {delay:.1f}s)...")

    elapsed = 0.0
    step = min(5.0, delay) if delay > 0 else 0
    while elapsed < delay:
        wait_chunk = min(step, delay - elapsed)
        await asyncio.sleep(wait_chunk)
        elapsed = time.time() - start_time
        if delay >= 10.0 and int(elapsed) % 30 == 0:
            logger.info(f"[BehavioralSimulator] In progress... {elapsed:.1f}s / {delay:.1f}s elapsed.")

    factor_scores = (payload or {}).get("factor_scores", {})
    if not factor_scores:
        factor_scores = {
            "effort": (payload or {}).get("effort_score", 0.78),
            "consistency": (payload or {}).get("consistency_score", 0.72),
            "collaboration": (payload or {}).get("collaboration_score", 0.68),
            "code_ownership": (payload or {}).get("ownership_score", 0.82),
            "requirement_fulfillment": (payload or {}).get("rf_score", 0.75),
        }

    result = classify_behavioral_pattern(factor_scores)
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
    parser = argparse.ArgumentParser(description="Simulate Factor 6: Behavioral Pattern")
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
