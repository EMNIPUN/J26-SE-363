"""Context and evidence validation node for com_agent.

Strictly aligned with:
- BOARD.md T5.1 (T5.1.1 - T5.1.6)
- PLAN.md Section 9 Node 1 & Section 12.1
"""

import json
import logging
import pathlib
from typing import Dict, Any, List, Optional
from app.agents.performance_assessment.com_agent.config.settings_loader import IS_DEV_MODE
from app.agents.performance_assessment.com_agent.ingestion.cohort_baseline import (
    load_historical_baselines,
    compute_rolling_average_baseline,
)
from app.agents.performance_assessment.com_agent.state import AssessmentState, CohortBaseline

logger = logging.getLogger(__name__)

MOCK_CONTEXT_FILE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "mock_context"
    / "student_context.json"
)

REQUIRED_FIELDS = [
    "student_id",
    "student_github_username",
    "team_id",
    "sprint_id",
    "repo_url",
    "assigned_tasks",
]


async def validate_context_node(
    state: Dict[str, Any],
    store: Optional[Any] = None,
    is_dev: Optional[bool] = None,
    mock_file: Optional[pathlib.Path] = None,
) -> Dict[str, Any]:
    """Validate student identity, repository context, task assignments, and baseline.

    In dev mode, loads default student identity from mock_context/student_context.json
    if not already fully populated in state.
    """
    if is_dev is None:
        is_dev = IS_DEV_MODE

    errors: List[str] = list(state.get("errors", []))
    updates: Dict[str, Any] = {}

    # 1. T5.1.1: In dev mode, fill missing context from student_context.json
    if is_dev:
        ctx_path = mock_file or MOCK_CONTEXT_FILE
        if ctx_path.exists():
            try:
                with open(ctx_path, "r", encoding="utf-8") as f:
                    file_ctx = json.load(f)
                for k, v in file_ctx.items():
                    if state.get(k) is None:
                        updates[k] = v


            except Exception as e:
                errors.append(f"Failed to load mock student context: {e}")

    merged = {**state, **updates}

    # 2. T5.1.2: Validate required fields
    for field in REQUIRED_FIELDS:
        val = merged.get(field)
        if val is None or (isinstance(val, (str, list)) and len(val) == 0):
            errors.append(f"Missing or empty required field: '{field}'")

    # 3. T5.1.3: Validate student_git_emails
    emails = merged.get("student_git_emails")
    if not emails or not isinstance(emails, list) or len(emails) == 0:
        errors.append("Validation error: 'student_git_emails' must be a non-empty list")
    elif not all(isinstance(e, str) and "@" in e for e in emails):
        errors.append("Validation error: 'student_git_emails' must contain valid email addresses")

    # 4. T5.1.4: Verify local clone directory in production mode
    team_id = merged.get("team_id")
    if not is_dev and team_id:
        clone_dir = pathlib.Path(f"/repos/{team_id}")
        if not clone_dir.exists():
            errors.append(f"Local clone directory does not exist: {clone_dir}")

    # 5. T5.1.6: If errors occurred, fail fast
    if errors:
        return {
            **updates,
            "errors": errors,
            "current_step": "validation_failed",
        }

    # 6. T5.1.5: Compute or load rolling cohort baseline
    historical = load_historical_baselines(store, team_id=team_id or "UNKNOWN")
    # Current sprint raw baseline fallback if not already in state
    current_raw = merged.get("cohort_raw_current") or {
        "metric_means": {"cc": 10.0, "loc_net": 250.0, "fc": 4.0},
        "metric_stds": {"cc": 2.5, "loc_net": 60.0, "fc": 1.5},
        "student_count": 4,
    }
    baseline_obj = compute_rolling_average_baseline(historical, current_raw)
    updates["cohort_baselines"] = baseline_obj.model_dump()
    updates["current_step"] = "context_validated"
    updates["errors"] = []

    return updates
