"""Requirement Fulfillment Factor Simulator (Factor 3).

Grounded in PROPOSAL.md Section 3.1.4:
- Measures: Satisfaction of assigned tasks and acceptance criteria (AC) via code diffs.
- Pipeline:
    1. Task Mapping: Links commits to assigned sprint tasks; flags untracked commits.
    2. LLM-Based Evaluation: Evaluates Task Description (TD_j), Acceptance Criteria (AC_j),
       and Code Diff (CD_j):
       RF_j = (R_j - 1) / 4  (rescaling 1-5 rubric to 0-1)
    3. Overall sprint fulfillment: RF = (1/m) * sum(RF_j)
- Traceability Rate: percentage of commits successfully mapped to Scrum tasks.

Supports dual-tier simulation:
- quick: ~2.0s (unit tests, rapid development)
- hard: 600s (10 min, configurable) to verify thread persistence in LangGraph checkpointer.
"""

import sys
import json
import time
import asyncio
import logging
import argparse
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

QUICK_DELAY_SECONDS = 2.0
HARD_DELAY_SECONDS = 600.0  # 10 minutes


def evaluate_task_fulfillment(tasks: List[Dict[str, Any]], commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not tasks:
        # Default placeholder task evaluations if none provided
        tasks = [
            {
                "task_id": "TASK-101",
                "title": "Implement JWT authentication filter",
                "story_points": 3,
                "status": "Done",
                "acceptance_criteria_met": True,
                "semantic_alignment_score": 0.90,
            },
            {
                "task_id": "TASK-104",
                "title": "Add role-based authorization guards",
                "story_points": 2,
                "status": "Done",
                "acceptance_criteria_met": True,
                "semantic_alignment_score": 0.85,
            },
        ]

    task_scores = []
    task_evaluations = []
    ac_met_count = 0

    for t in tasks:
        is_done = t.get("status") in ["Done", "Closed"]
        ac_met = bool(t.get("acceptance_criteria_met", is_done))
        if ac_met:
            ac_met_count += 1

        if "semantic_alignment_score" in t:
            semantic = float(t["semantic_alignment_score"])
        else:
            semantic = 1.0 if is_done else 0.0

        rubric_val = 1.0 + (semantic * 4.0)  # Map 0.0-1.0 to 1.0-5.0 rubric
        rf_j = round((rubric_val - 1.0) / 4.0, 4)

        task_scores.append(rf_j)
        task_evaluations.append({
            "task_id": t.get("task_id", "TASK-X"),
            "title": t.get("title", "Unnamed Task"),
            "story_points": t.get("story_points", 2),
            "status": t.get("status", "Done"),
            "acceptance_criteria_met": ac_met,
            "rubric_rating_1_to_5": round(rubric_val, 2),
            "rf_score": rf_j,
        })

    m = len(task_scores)
    overall_rf = round(sum(task_scores) / m if m > 0 else 0.5, 4)

    # Traceability calculation
    total_commits = len(commits) if commits else 8
    untracked_commits = max(0, int(total_commits * 0.15))  # ~15% untracked baseline
    traceability_rate = round(max(0.0, (total_commits - untracked_commits) / total_commits), 4) if total_commits > 0 else 1.0

    return {
        "score": overall_rf,
        "features": {
            "completed_tasks_count": sum(1 for t in tasks if t.get("status") == "Done"),
            "total_assigned_tasks": len(tasks),
            "acceptance_criteria_met_ratio": round(ac_met_count / len(tasks), 4) if tasks else 1.0,
            "untracked_commits_count": untracked_commits,
            "traceability_rate": traceability_rate,
        },
        "task_evaluations": task_evaluations,
        "traceability_rate": traceability_rate,
        "model": "LLM_SemanticEvaluation",
        "status": "completed",
    }


async def async_simulate(
    payload: Optional[Dict[str, Any]] = None,
    mode: str = "quick",
    duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Asynchronously simulate Requirement Fulfillment Factor calculation with configurable delay."""
    delay = duration_seconds if duration_seconds is not None else (
        HARD_DELAY_SECONDS if mode == "hard" else QUICK_DELAY_SECONDS
    )

    start_time = time.time()
    logger.info(f"[ReqFulfillmentSimulator] Starting {mode} simulation (planned duration: {delay:.1f}s)...")

    elapsed = 0.0
    step = min(10.0, delay) if delay > 0 else 0
    while elapsed < delay:
        wait_chunk = min(step, delay - elapsed)
        await asyncio.sleep(wait_chunk)
        elapsed = time.time() - start_time
        if delay >= 15.0 and int(elapsed) % 30 == 0:
            logger.info(f"[ReqFulfillmentSimulator] In progress... {elapsed:.1f}s / {delay:.1f}s elapsed.")

    tasks = (payload or {}).get("student_tasks", [])
    commits = (payload or {}).get("commits", [])

    result = evaluate_task_fulfillment(tasks, commits)
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
    parser = argparse.ArgumentParser(description="Simulate Factor 3: Requirement Fulfillment")
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
