"""
Performance Assessment Tasks — registered with the Procrastinate job queue.

Each function decorated with @app.task is a trigger point the server can enqueue.
The worker process (agentic_framework/worker.py) picks these up and runs them.

Queue: "performance"
Task names:
  - performance.assess_student
  - performance.parse_rubric
  - performance.generate_ownership_quiz
  - performance.ingest_git_commits
"""

import logging
from typing import Any

from shared.queue import app

logger = logging.getLogger(__name__)


@app.task(name="performance.assess_student", queue="performance")
async def assess_student(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the full LangGraph multi-factor evaluation + AHP fusion pipeline.

    Expected payload keys:
        student_id  (str)  — e.g. "IT21098765"
        batch_id    (str)  — e.g. "2026-REG-Y4S1"
        sprint_id   (str)  — e.g. "sprint-2"
        repo_url    (str)  — GitHub repository URL (optional)
        rubric_id   (str)  — assessment rubric identifier (optional)
    """
    # Heavy imports stay inside the function so the server process never loads them
    # from app.agents.performance_assessment.agent import run_evaluation
    logger.info(f"[performance] assess_student started: student={payload.get('student_id')}")

    # --- YOUR REAL AGENT CODE GOES HERE ---
    # result = await run_evaluation(
    #     student_id=payload["student_id"],
    #     sprint_id=payload.get("sprint_id", "sprint-1"),
    # )
    # return result

    return {
        "student_id": payload.get("student_id"),
        "sprint_id": payload.get("sprint_id"),
        "final_score": 87.5,
        "factor_scores": {"effort": 88.0, "consistency": 85.0, "code_ownership": 90.0},
    }


@app.task(name="performance.parse_rubric", queue="performance")
async def parse_rubric(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse an uploaded rubric PDF/Word into structured criteria weights.

    Expected payload keys:
        project_id  (str)  — project identifier
        file_path   (str)  — path/URL to rubric file
    """
    logger.info(f"[performance] parse_rubric: project={payload.get('project_id')}")

    return {
        "project_id": payload.get("project_id"),
        "criteria": ["code_quality", "collaboration", "delivery", "problem_solving"],
        "weights": [0.30, 0.25, 0.25, 0.20],
    }


@app.task(name="performance.generate_ownership_quiz", queue="performance")
async def generate_ownership_quiz(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate code-ownership quiz questions for a student's ambiguous commits.

    Expected payload keys:
        student_id   (str)  — student identifier
        commit_hash  (str)  — Git commit hash to quiz on
    """
    logger.info(f"[performance] generate_ownership_quiz: student={payload.get('student_id')}")

    return {
        "student_id": payload.get("student_id"),
        "commit_hash": payload.get("commit_hash"),
        "questions": [
            {
                "question": "What does the function `calculate_score()` do in this commit?",
                "options": ["Calculates AHP weights", "Fetches GitHub data", "Renders a chart", "Sends an email"],
                "correct_index": 0,
            }
        ],
    }


@app.task(name="performance.ingest_git_commits", queue="performance")
async def ingest_git_commits(payload: dict[str, Any]) -> dict[str, Any]:
    """Sandbox-clone a repo and compute commit regularity + authorship metrics.

    Expected payload keys:
        student_id  (str)  — student identifier
        repo_url    (str)  — GitHub HTTPS clone URL
        branch      (str)  — branch name (default: "main")
    """
    logger.info(f"[performance] ingest_git_commits: student={payload.get('student_id')}")

    return {
        "student_id": payload.get("student_id"),
        "repo_url": payload.get("repo_url"),
        "total_commits": 47,
        "lines_added": 3821,
        "lines_deleted": 512,
        "commit_regularity_score": 92.0,
    }
