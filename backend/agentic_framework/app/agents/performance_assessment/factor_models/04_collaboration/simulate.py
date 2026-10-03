"""Collaboration Factor Simulator (Factor 4).

Grounded in PROPOSAL.md Section 3.1.5:
- Measures: Substantive peer review, issue discussion, and active team coordination.
- Feature vector: X_Co = [PRC_depth, IC_depth, MC, PCount, CCount, IR]
    - PRC_depth: Substantiveness of PR review comments (scored 0-1 via sentence encoder)
    - IC_depth: Substantiveness of issue discussion comments (scored 0-1)
    - MC: Meaningful mentions and teammate replies
    - PCount: Reviewed pull requests count
    - CCount: Authored comments count
    - IR: Interaction response and resolution rate
- Model: Pretrained sentence encoder + regression head:
    Co = clip(b + w1*PRC_depth + w2*IC_depth + w3*MC + w4*PCount + w5*CCount + w6*IR, 0.0, 1.0)
- Distinguishes high-volume superficial chatter from genuinely substantive technical critique.

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
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

REGRESSION_WEIGHTS = {
    "intercept": 0.10,
    "w_PRC_depth": 0.30,
    "w_IC_depth": 0.20,
    "w_MC": 0.15,
    "w_PCount": 0.10,
    "w_CCount": 0.10,
    "w_IR": 0.15,
}

QUICK_DELAY_SECONDS = 1.0
HARD_DELAY_SECONDS = 300.0  # 5 minutes


def calculate_collaboration_score(features: Dict[str, Any]) -> Dict[str, Any]:
    prc_depth = float(features.get("PRC_depth", 0.75))
    ic_depth = float(features.get("IC_depth", 0.70))
    mc = float(features.get("MC", 4))
    pcount = float(features.get("PCount", 3))
    ccount = float(features.get("CCount", 6))
    ir = float(features.get("IR", 0.85))

    # Normalize counts against expected sprint norms
    norm_mc = min(1.0, mc / 5.0)
    norm_pcount = min(1.0, pcount / 4.0)
    norm_ccount = min(1.0, ccount / 8.0)
    ir_bounded = max(0.0, min(1.0, ir))

    raw_score = (
        REGRESSION_WEIGHTS["intercept"]
        + REGRESSION_WEIGHTS["w_PRC_depth"] * prc_depth
        + REGRESSION_WEIGHTS["w_IC_depth"] * ic_depth
        + REGRESSION_WEIGHTS["w_MC"] * norm_mc
        + REGRESSION_WEIGHTS["w_PCount"] * norm_pcount
        + REGRESSION_WEIGHTS["w_CCount"] * norm_ccount
        + REGRESSION_WEIGHTS["w_IR"] * ir_bounded
    )

    score = round(max(0.0, min(1.0, raw_score)), 4)
    avg_substantiveness = round((prc_depth + ic_depth) / 2.0, 4)

    return {
        "score": score,
        "features": {
            "PRC_depth": round(prc_depth, 4),
            "IC_depth": round(ic_depth, 4),
            "MC": mc,
            "PCount": pcount,
            "CCount": ccount,
            "IR": round(ir_bounded, 4),
        },
        "substantiveness_rating": avg_substantiveness,
        "is_active_reviewer": pcount >= 2 and prc_depth >= 0.60,
        "model": "SentenceEncoder_RegressionHead",
        "status": "completed",
    }


async def async_simulate(
    payload: Optional[Dict[str, Any]] = None,
    mode: str = "quick",
    duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Asynchronously simulate Collaboration Factor calculation with configurable delay."""
    delay = duration_seconds if duration_seconds is not None else (
        HARD_DELAY_SECONDS if mode == "hard" else QUICK_DELAY_SECONDS
    )

    start_time = time.time()
    logger.info(f"[CollaborationSimulator] Starting {mode} simulation (planned duration: {delay:.1f}s)...")

    elapsed = 0.0
    step = min(5.0, delay) if delay > 0 else 0
    while elapsed < delay:
        wait_chunk = min(step, delay - elapsed)
        await asyncio.sleep(wait_chunk)
        elapsed = time.time() - start_time
        if delay >= 10.0 and int(elapsed) % 30 == 0:
            logger.info(f"[CollaborationSimulator] In progress... {elapsed:.1f}s / {delay:.1f}s elapsed.")

    features = (payload or {}).get("features", {})
    if not features:
        review_comments = (payload or {}).get("review_comments", [])
        issue_comments = (payload or {}).get("issue_comments", [])
        features = {
            "PRC_depth": 0.78 if review_comments else 0.40,
            "IC_depth": 0.72 if issue_comments else 0.45,
            "MC": len(review_comments) + len(issue_comments),
            "PCount": (payload or {}).get("pr_reviews_authored", 3),
            "CCount": len(review_comments) + len(issue_comments),
            "IR": 0.85,
        }

    result = calculate_collaboration_score(features)
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
    parser = argparse.ArgumentParser(description="Simulate Factor 4: Collaboration")
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
