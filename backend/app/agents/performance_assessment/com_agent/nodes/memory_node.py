"""Cross-sprint memory load and update nodes for com_agent.

Strictly aligned with:
- BOARD.md T5.10 (T5.10.1 - T5.10.2)
- PLAN.md Section 7.3 (Two-Tier Memory Management)
- PLAN.md Section 9 Nodes 11 & 15
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.agents.performance_assessment.com_agent.ingestion.cohort_baseline import (
    save_sprint_baseline,
)

logger = logging.getLogger(__name__)


async def load_cross_sprint_memory_node(
    state: Dict[str, Any], store: Optional[Any] = None
) -> Dict[str, Any]:
    """T5.10.1: Node 11 — Load Cross-Sprint Student Trajectory.

    Queries LangGraph long-term Store under ("students", student_id, "sprint_history").
    Returns empty list on Sprint 1.
    """
    student_id = state.get("student_id")
    trajectory: List[Dict[str, Any]] = []

    if store is not None and student_id:
        # Case 1: Dict store
        if isinstance(store, dict):
            key = ("students", student_id, "sprint_history")
            trajectory = store.get(key, [])
        # Case 2: LangGraph BaseStore
        elif hasattr(store, "get"):
            try:
                item = store.get(("students", student_id), "sprint_history")
                if item:
                    val = getattr(item, "value", item)
                    trajectory = val.get("history", []) if isinstance(val, dict) else val
            except Exception as e:
                logger.warning(f"Failed to query store for student trajectory: {e}")

    return {
        "historical_trajectory": trajectory,
        "current_step": "cross_sprint_memory_loaded",
    }


async def update_cross_sprint_memory_node(
    state: Dict[str, Any], store: Optional[Any] = None
) -> Dict[str, Any]:
    """T5.10.2: Node 15 — Persist Assessment Results & Update Cohort Memory.

    Appends student sprint performance snapshot into long-term Store,
    and invokes save_sprint_baseline to persist the team cohort metrics.
    """
    student_id = state.get("student_id")
    sprint_id = state.get("sprint_id")
    team_id = state.get("team_id", "DEFAULT_TEAM")

    snapshot = {
        "sprint_id": sprint_id,
        "final_score": state.get("final_score"),
        "additive_score": state.get("additive_score"),
        "behavioral_persona": state.get("behavioral_persona"),
        "behavioral_modifier": state.get("behavioral_modifier"),
        "discrepancy_count": len(state.get("discrepancy_flags", [])),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    if store is not None and student_id:
        # Case 1: Dict store
        if isinstance(store, dict):
            key = ("students", student_id, "sprint_history")
            history = store.get(key, [])
            updated = [h for h in history if h.get("sprint_id") != sprint_id]
            updated.append(snapshot)
            store[key] = updated
        # Case 2: LangGraph BaseStore
        elif hasattr(store, "put"):
            try:
                existing_item = store.get(("students", student_id), "sprint_history")
                existing_list = []
                if existing_item:
                    val = getattr(existing_item, "value", existing_item)
                    existing_list = val.get("history", []) if isinstance(val, dict) else val
                updated = [h for h in existing_list if h.get("sprint_id") != sprint_id]
                updated.append(snapshot)
                store.put(("students", student_id), "sprint_history", {"history": updated})
            except Exception as e:
                logger.warning(f"Failed to persist student history to store: {e}")

    # Persist cohort baseline for this sprint
    current_raw = state.get("cohort_raw_current") or {
        "metric_means": {"cc": 10.0, "loc_net": 250.0},
        "metric_stds": {"cc": 2.5, "loc_net": 60.0},
        "student_count": 4,
    }
    save_sprint_baseline(store, team_id=team_id, sprint_id=sprint_id or "sprint-01", raw_baseline=current_raw)

    return {
        "current_step": "cross_sprint_memory_updated",
    }
