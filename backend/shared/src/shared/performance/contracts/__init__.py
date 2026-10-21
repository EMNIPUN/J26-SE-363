"""Versioned JSON Schemas for performance-assessment API payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_NAMES = (
    "meta",
    "team_overview",
    "team_development",
    "team_runs",
    "reviews",
    "review_form",
    "team_setup",
    "student_report",
    "student_history",
    "student_questions",
    "graph",
    "run",
    "run_events",
    "method",
    "my_reports",
    "my_quizzes",
)


def schema_path(name: str) -> Path:
    """Return the checked-in schema path for a payload name."""
    if name not in SCHEMA_NAMES:
        raise KeyError(f"Unknown performance contract: {name}")
    return Path(__file__).with_name(f"{name}.json")


def load_schema(name: str) -> dict[str, Any]:
    """Load one performance contract without requiring a JSON-schema package."""
    with schema_path(name).open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    if not isinstance(schema, dict):
        raise ValueError(f"Performance contract {name!r} must be a JSON object")
    return schema


__all__ = ["SCHEMA_NAMES", "load_schema", "schema_path"]
