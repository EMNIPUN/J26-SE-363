"""Code Ownership Factor Simulator (Factor 7).

Grounded in PROPOSAL.md Section 3.1.8:
- Measures: Active comprehension verification of student's own authored code.
- Mechanism:
    1. Phase 1 (Generate): AST analysis extracts student-authored function candidates
       and generates a targeted comprehension question.
    2. Phase 2 (Evaluate): When the student submits their response, a pretrained
       code-text encoder (UniXcoder / CodeBERT) + regression head evaluates the answer:
       CO = A = (R - 1) / 4   (rescaling 1-5 rubric to 0-1)
- Caps score at 0.50 if submitted during the 48-hour extension window or after timeout.

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

QUICK_DELAY_SECONDS = 0.5
HARD_DELAY_SECONDS = 300.0  # 5 minutes


def generate_ownership_quiz(code_snippet: Optional[str] = None) -> Dict[str, Any]:
    """Phase 1: Generate comprehension question from AST candidate snippet."""
    snippet = code_snippet or (
        "def process_order(order_id: str, items: list, discount_rate: float) -> dict:\n"
        "    if not items:\n"
        "        raise ValueError('Order must contain at least one item')\n"
        "    subtotal = sum(item['price'] * item['qty'] for item in items)\n"
        "    tax = subtotal * 0.08\n"
        "    total = (subtotal - (subtotal * discount_rate)) + tax\n"
        "    return {'order_id': order_id, 'total': round(total, 2)}"
    )

    return {
        "function_name": "process_order",
        "code_snippet": snippet,
        "cyclomatic_complexity": 2,
        "token_count": 48,
        "generated_question": (
            "Explain how discount calculation affects the taxable base in process_order, "
            "and what happens if items is empty."
        ),
        "reference_criteria": [
            "Identifies ValueError raised on empty items list",
            "Explains subtotal discount deduction and subsequent tax addition",
        ],
        "status": "quiz_generated",
    }


def evaluate_ownership_response(
    student_response: Optional[str] = None,
    is_extension_period: bool = False,
    is_timeout: bool = False,
) -> Dict[str, Any]:
    """Phase 2: Evaluate student's submitted response."""
    if is_timeout:
        return {
            "score": 0.0,
            "features": {
                "comprehension_rating_1_to_5": 1.0,
                "cyclomatic_complexity": 2,
                "token_count": 48,
                "capped_applied": True,
                "timeout": True,
            },
            "eval_summary": "Zero score assigned due to quiz deadline expiration with no submission.",
            "model": "UniXcoder_ComprehensionRegressor",
            "status": "completed",
        }

    response = student_response or (
        "If the items list is empty, the function immediately raises a ValueError. "
        "Otherwise, it sums each item's price times quantity to get subtotal, computes tax, "
        "and calculates the total after applying discount_rate."
    )

    # Simulated semantic comprehension rubric score (1.0 to 5.0)
    words = response.split()
    if len(words) >= 8:
        rubric_rating = 4.40
    elif len(words) >= 4:
        rubric_rating = 3.00
    else:
        rubric_rating = 1.80
    raw_score = round((rubric_rating - 1.0) / 4.0, 4)

    capped = False
    final_score = raw_score
    if is_extension_period:
        capped = True
        final_score = min(0.50, raw_score)

    return {
        "score": final_score,
        "raw_score": raw_score,
        "features": {
            "ko_raw_score": raw_score,
            "ko_fusion_score": final_score,
            "comprehension_rating_1_to_5": rubric_rating,
            "cyclomatic_complexity": 2,
            "token_count": 48,
            "capped_applied": capped,
            "timeout": False,
        },
        "student_response_evaluated": response,
        "eval_summary": "Demonstrates strong understanding of branching logic, error conditions, and calculations.",
        "model": "UniXcoder_ComprehensionRegressor",
        "status": "completed",
    }


async def async_simulate(
    payload: Optional[Dict[str, Any]] = None,
    mode: str = "quick",
    duration_seconds: Optional[float] = None,
    phase: str = "auto",
) -> Dict[str, Any]:
    """Asynchronously simulate Code Ownership factor with configurable delay.

    phase options:
    - 'generate': Phase 1 AST extraction and quiz creation.
    - 'evaluate': Phase 2 submission grading.
    - 'auto': Complete simulation (generate + evaluate).
    """
    delay = duration_seconds if duration_seconds is not None else (
        HARD_DELAY_SECONDS if mode == "hard" else QUICK_DELAY_SECONDS
    )

    start_time = time.time()
    logger.info(f"[CodeOwnershipSimulator] Starting {mode} simulation (phase: {phase}, delay: {delay:.1f}s)...")

    elapsed = 0.0
    step = min(5.0, delay) if delay > 0 else 0
    while elapsed < delay:
        wait_chunk = min(step, delay - elapsed)
        await asyncio.sleep(wait_chunk)
        elapsed = time.time() - start_time
        if delay >= 10.0 and int(elapsed) % 30 == 0:
            logger.info(f"[CodeOwnershipSimulator] In progress... {elapsed:.1f}s / {delay:.1f}s elapsed.")

    if phase == "generate":
        quiz_data = generate_ownership_quiz(code_snippet=(payload or {}).get("code_snippet"))
        quiz_data["execution_time_seconds"] = round(time.time() - start_time, 3)
        quiz_data["mode"] = mode
        return quiz_data

    # For 'evaluate' or 'auto'
    is_ext = bool((payload or {}).get("is_extension_period", False))
    is_to = bool((payload or {}).get("is_timeout", False))
    resp = (payload or {}).get("student_response")

    result = evaluate_ownership_response(
        student_response=resp,
        is_extension_period=is_ext,
        is_timeout=is_to,
    )
    result["quiz_metadata"] = generate_ownership_quiz()
    result["execution_time_seconds"] = round(time.time() - start_time, 3)
    result["mode"] = mode
    return result


def simulate(
    payload: Optional[Dict[str, Any]] = None,
    mode: str = "quick",
    duration_seconds: Optional[float] = None,
    phase: str = "auto",
) -> Dict[str, Any]:
    """Synchronous entry point."""
    return asyncio.run(async_simulate(payload=payload, mode=mode, duration_seconds=duration_seconds, phase=phase))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Factor 7: Code Ownership")
    parser.add_argument("--mode", choices=["quick", "hard"], default="quick", help="Simulation tier")
    parser.add_argument("--phase", choices=["generate", "evaluate", "auto"], default="auto", help="Simulation phase")
    parser.add_argument("--duration", type=float, default=None, help="Custom sleep duration in seconds")
    parser.add_argument("--input", type=str, default=None, help="Path to input JSON payload")
    args = parser.parse_args()

    input_payload = None
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            input_payload = json.load(f)

    res = simulate(payload=input_payload, mode=args.mode, duration_seconds=args.duration, phase=args.phase)
    print(json.dumps(res, indent=2))
