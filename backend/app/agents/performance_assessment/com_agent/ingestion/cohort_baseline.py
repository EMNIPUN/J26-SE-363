"""Cohort rolling average baseline calculator for cross-sprint normalization.

Strictly aligned with:
- BOARD.md T2.5 (T2.5.1 - T2.5.4)
- PLAN.md Section 12.4 & Section 12.8
- state.py CohortBaseline Pydantic model
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from app.agents.performance_assessment.com_agent.state import CohortBaseline


def compute_current_sprint_raw_baseline(
    commits_by_student: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute per-metric mean and standard deviation across all students for the current sprint.

    Supports either:
    1. commits_by_student: Dict[student_id, List[CommitDict]]
    2. metrics_by_student: Dict[student_id, Dict[metric_name, float/int]]

    Metrics extracted from commit lists:
    - cc: commit count
    - loc_net: net lines of code (additions - deletions)
    - loc_add: total additions
    - loc_del: total deletions
    - fc: total files modified
    """
    if not commits_by_student:
        return {
            "metric_means": {},
            "metric_stds": {},
            "student_count": 0,
        }

    student_metrics: Dict[str, Dict[str, float]] = {}

    for student_id, data in commits_by_student.items():
        if isinstance(data, list):
            # List of commits
            cc = float(len(data))
            loc_add = 0.0
            loc_del = 0.0
            fc = 0.0
            for c in data:
                stats = c.get("stats") or {}
                loc_add += float(stats.get("additions", 0))
                loc_del += float(stats.get("deletions", 0))
                files = c.get("files") or []
                fc += float(len(files))
            loc_net = loc_add - loc_del
            student_metrics[student_id] = {
                "cc": cc,
                "loc_net": loc_net,
                "loc_add": loc_add,
                "loc_del": loc_del,
                "fc": fc,
            }
        elif isinstance(data, dict):
            # Pre-aggregated metric dictionary
            student_metrics[student_id] = {
                k: float(v) for k, v in data.items() if isinstance(v, (int, float))
            }
        else:
            student_metrics[student_id] = {}

    student_count = len(student_metrics)
    if student_count == 0:
        return {
            "metric_means": {},
            "metric_stds": {},
            "student_count": 0,
        }

    # Discover all metrics across students
    all_metrics = set()
    for m in student_metrics.values():
        all_metrics.update(m.keys())

    means: Dict[str, float] = {}
    stds: Dict[str, float] = {}

    for metric in sorted(all_metrics):
        values = [student_metrics[s].get(metric, 0.0) for s in student_metrics]
        mean_val = sum(values) / student_count
        means[metric] = round(mean_val, 4)

        if student_count <= 1:
            stds[metric] = 0.0
        else:
            variance = sum((x - mean_val) ** 2 for x in values) / student_count
            stds[metric] = round(math.sqrt(variance), 4)

    return {
        "metric_means": means,
        "metric_stds": stds,
        "student_count": student_count,
    }


def load_historical_baselines(store: Any, team_id: str) -> List[Dict[str, Any]]:
    """Query LangGraph Store or dev in-memory dictionary for historical sprint baselines.

    Queries namespace/key at ("cohort", team_id, "sprint_baselines").
    Returns [] on Sprint 1 (when no historical data exists yet).
    """
    if store is None:
        return []

    # Case 1: Plain python dictionary (dev mode)
    if isinstance(store, dict):
        key_tuple = ("cohort", team_id, "sprint_baselines")
        if key_tuple in store:
            val = store[key_tuple]
            return val if isinstance(val, list) else val.get("baselines", [])
        str_key = f"cohort:{team_id}:sprint_baselines"
        if str_key in store:
            val = store[str_key]
            return val if isinstance(val, list) else val.get("baselines", [])
        return []

    # Case 2: LangGraph BaseStore object with .get(namespace, key)
    if hasattr(store, "get"):
        try:
            # Try namespace=("cohort", team_id), key="sprint_baselines"
            item = store.get(("cohort", team_id), "sprint_baselines")
            if item is not None:
                val = getattr(item, "value", item)
                if isinstance(val, dict):
                    return val.get("baselines", [])
                if isinstance(val, list):
                    return val
        except TypeError:
            pass

        try:
            # Try single key
            item = store.get(("cohort", team_id, "sprint_baselines"))
            if item is not None:
                val = getattr(item, "value", item)
                if isinstance(val, dict):
                    return val.get("baselines", [])
                if isinstance(val, list):
                    return val
        except Exception:
            pass

    return []


def compute_rolling_average_baseline(
    historical: List[Dict[str, Any]], current: Dict[str, Any]
) -> CohortBaseline:
    """Compute rolling average baseline statistics across all N+1 sprints.

    Sets sprint_count_used = len(historical) + 1.
    """
    all_sprints = list(historical) + [current]
    sprint_count_used = len(all_sprints)

    all_metrics = set()
    for s in all_sprints:
        all_metrics.update(s.get("metric_means", {}).keys())

    rolling_means: Dict[str, float] = {}
    rolling_stds: Dict[str, float] = {}

    for metric in sorted(all_metrics):
        mean_vals = [s.get("metric_means", {}).get(metric, 0.0) for s in all_sprints]
        std_vals = [s.get("metric_stds", {}).get(metric, 0.0) for s in all_sprints]

        rolling_means[metric] = round(sum(mean_vals) / sprint_count_used, 4)
        rolling_stds[metric] = round(sum(std_vals) / sprint_count_used, 4)

    return CohortBaseline(
        metric_means=rolling_means,
        metric_stds=rolling_stds,
        student_count=current.get("student_count", 0),
        sprint_count_used=sprint_count_used,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


def save_sprint_baseline(
    store: Any, team_id: str, sprint_id: str, raw_baseline: Dict[str, Any]
) -> None:
    """Persist the current sprint raw baseline to the store.

    In development, store is typically a plain dict.
    In production, store is a LangGraph BaseStore instance.
    """
    if store is None:
        return

    entry = {
        "sprint_id": sprint_id,
        "metric_means": raw_baseline.get("metric_means", {}),
        "metric_stds": raw_baseline.get("metric_stds", {}),
        "student_count": raw_baseline.get("student_count", 0),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    # Case 1: Plain python dict
    if isinstance(store, dict):
        key = ("cohort", team_id, "sprint_baselines")
        existing = store.get(key, [])
        # Replace if existing sprint_id, else append
        updated = [b for b in existing if b.get("sprint_id") != sprint_id]
        updated.append(entry)
        store[key] = updated
        return

    # Case 2: LangGraph BaseStore with put(namespace, key, value)
    if hasattr(store, "put"):
        existing_item = None
        try:
            existing_item = store.get(("cohort", team_id), "sprint_baselines")
        except Exception:
            pass

        existing_list = []
        if existing_item:
            val = getattr(existing_item, "value", existing_item)
            if isinstance(val, dict):
                existing_list = val.get("baselines", [])
            elif isinstance(val, list):
                existing_list = val

        updated = [b for b in existing_list if b.get("sprint_id") != sprint_id]
        updated.append(entry)
        store.put(("cohort", team_id), "sprint_baselines", {"baselines": updated})
