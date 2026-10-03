"""
Tutor Agent Tasks (Teammate C) — registered with Procrastinate.

Queue: "tutor"
Task names:
  - tutor.generate_guidance
  - tutor.explain_code_concept
  - tutor.recommend_learning_topics
"""

import logging
from typing import Any
from shared.queue import app

logger = logging.getLogger(__name__)


@app.task(name="tutor.generate_guidance", queue="tutor")
async def generate_guidance(payload: dict[str, Any]) -> dict[str, Any]:
    """Generate interactive pedagogical guidance based on student code queries."""
    student_id = payload.get("student_id")
    question = payload.get("question")
    logger.info(f"[tutor] generate_guidance for student={student_id}")

    return {
        "student_id": student_id,
        "question": question,
        "tutor_response": (
            "To resolve the merge conflict in Git, consider rebasing your feature branch onto main "
            "and resolving conflicts hunk-by-hunk rather than creating a messy merge commit."
        ),
        "suggested_followups": [
            "How do I abort a rebase?",
            "What is the difference between git merge and git rebase?",
        ],
        "status": "COMPLETED",
    }


@app.task(name="tutor.explain_code_concept", queue="tutor")
async def explain_code_concept(payload: dict[str, Any]) -> dict[str, Any]:
    """Explain a specific code snippet or design pattern to a student."""
    concept = payload.get("concept", "Dependency Injection")
    logger.info(f"[tutor] explain_code_concept: {concept}")

    return {
        "concept": concept,
        "explanation": f"In software engineering, {concept} allows decoupling object creation from behavior.",
        "difficulty_level": "INTERMEDIATE",
        "status": "COMPLETED",
    }


@app.task(name="tutor.recommend_learning_topics", queue="tutor")
async def recommend_learning_topics(payload: dict[str, Any]) -> dict[str, Any]:
    """Analyze student factor deficiencies and recommend remedial learning modules."""
    student_id = payload.get("student_id")
    logger.info(f"[tutor] recommend_learning_topics for student={student_id}")

    return {
        "student_id": student_id,
        "recommended_modules": [
            {"title": "Unit Testing Best Practices with Pytest", "priority": "HIGH"},
            {"title": "Git Feature Branch Workflow", "priority": "MEDIUM"},
        ],
        "status": "COMPLETED",
    }
