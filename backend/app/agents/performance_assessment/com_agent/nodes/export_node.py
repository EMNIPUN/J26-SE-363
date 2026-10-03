"""Assessment result persistence and export node for com_agent.

Strictly aligned with:
- BOARD.md T5.13 (T5.13.1)
- PLAN.md Section 9 Node 16 (export_results_node)
- PLAN.md Section 12.3 (Output API Schema Contracts)
- schemas.py (AssessmentResultSchema, StudentFeedbackSchema, FactorScoreOutput)
"""

import json
import logging
import pathlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.agents.performance_assessment.schemas import (
    AssessmentResultSchema,
    StudentFeedbackSchema,
    FactorScoreOutput,
)
from app.agents.performance_assessment.com_agent.config.settings_loader import IS_DEV_MODE

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = (
    pathlib.Path(__file__).resolve().parent.parent / "mock_context" / "output"
)

FACTOR_LABELS = {
    "effort": "Effort & Volume",
    "consistency": "Temporal Consistency",
    "requirement_fulfillment": "Requirement Fulfillment",
    "collaboration": "Peer Collaboration",
    "task_complexity": "Task Complexity",
    "code_ownership": "Code Ownership & Comprehension",
}


def _build_factor_score_outputs(
    factor_scores: Dict[str, Any]
) -> Dict[str, FactorScoreOutput]:
    outputs: Dict[str, FactorScoreOutput] = {}
    for name, f_val in factor_scores.items():
        score = float(
            getattr(f_val, "score", 0.0)
            if hasattr(f_val, "score")
            else f_val.get("score", 0.0) if isinstance(f_val, dict) else f_val
        )
        status = (
            getattr(f_val, "status", "completed")
            if hasattr(f_val, "status")
            else f_val.get("status", "completed") if isinstance(f_val, dict) else "completed"
        )
        if status not in ["completed", "fallback_applied", "missing"]:
            status = "completed"

        traces = (
            getattr(f_val, "evidence_traces", [])
            if hasattr(f_val, "evidence_traces")
            else f_val.get("evidence_traces", []) if isinstance(f_val, dict) else []
        )
        summary = (
            f"Assessed {len(traces)} primary evidence traces."
            if traces
            else "Standard metric evaluation completed."
        )

        outputs[name] = FactorScoreOutput(
            score=round(max(0.0, min(1.0, score)), 4),
            label=FACTOR_LABELS.get(name, name.replace("_", " ").title()),
            evidence_summary=summary,
            status=status,
        )
    return outputs


async def export_results_node(
    state: Dict[str, Any],
    output_dir: Optional[pathlib.Path] = None,
    is_dev: Optional[bool] = None,
) -> Dict[str, Any]:
    """T5.13.1: Node 16 — Assessment Result Export and Persistence.

    - Validates state against strongly-typed AssessmentResultSchema and StudentFeedbackSchema.
    - Serializes output contracts to JSON files in mock_context/output/ during dev mode.
    - Sets current_step = 'export_complete'.
    """
    if is_dev is None:
        is_dev = IS_DEV_MODE

    student_id = state.get("student_id") or "STU-UNKNOWN"
    student_name = state.get("student_name") or "Unknown Student"
    team_id = state.get("team_id") or "TEAM-UNKNOWN"
    sprint_id = state.get("sprint_id") or "sprint-01"

    final_score = float(state.get("final_score", 0.0) or 0.0)
    final_score = round(max(0.0, min(1.0, final_score)), 4)
    final_percentage = round(final_score * 100.0, 2)

    additive_score = float(state.get("additive_score", final_score) or final_score)
    additive_score = round(max(0.0, min(1.0, additive_score)), 4)

    bp_modifier = float(state.get("behavioral_modifier", 1.00) or 1.00)
    bp_modifier = round(max(0.80, min(1.20, bp_modifier)), 4)

    persona = state.get("behavioral_persona") or "Balanced Contributor"
    radar_data = state.get("radar_chart_data") or {}
    inst_report = state.get("instructor_report_markdown") or "# Instructor Dossier"
    stu_report = state.get("student_feedback_markdown") or "# Student Feedback"

    override_score = state.get("lecturer_override_score")
    has_override = override_score is not None

    flags_raw = state.get("discrepancy_flags", [])
    flags_serialized = [
        f.model_dump() if hasattr(f, "model_dump") else f for f in flags_raw
    ]

    factor_score_outputs = _build_factor_score_outputs(state.get("factor_scores", {}))

    # 1. Instantiate and validate Lecturer Dossier Contract
    assessment_result = AssessmentResultSchema(
        student_id=student_id,
        student_name=student_name,
        team_id=team_id,
        sprint_id=sprint_id,
        assessed_at=datetime.now(timezone.utc),
        factor_scores=factor_score_outputs,
        additive_score=additive_score,
        behavioral_modifier=bp_modifier,
        final_score=final_score,
        final_score_percentage=final_percentage,
        behavioral_persona=persona,
        instructor_report_markdown=inst_report,
        student_feedback_markdown=stu_report,
        radar_chart_data=radar_data,
        lecturer_override_applied=has_override,
        lecturer_override_score=override_score,
        lecturer_comments=state.get("lecturer_comments"),
        calculation_audit_trail=state.get("calculation_audit_trail", {}),
        discrepancy_flags=flags_serialized,
        historical_trajectory=state.get("historical_trajectory", []),
    )

    # 2. Instantiate and validate Student Portal Contract (Sanitized, no instructor dossier)
    student_feedback = StudentFeedbackSchema(
        student_id=student_id,
        sprint_id=sprint_id,
        final_score=final_score,
        final_score_percentage=final_percentage,
        behavioral_persona=persona,
        radar_chart_data=radar_data,
        student_feedback_markdown=stu_report,
        historical_trajectory=state.get("historical_trajectory", []),
    )

    # 3. In dev mode, write to mock_context/output/
    if is_dev:
        target_dir = output_dir or DEFAULT_OUTPUT_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        res_path = target_dir / f"assessment_result_{student_id}_{sprint_id}.json"
        with open(res_path, "w", encoding="utf-8") as f:
            f.write(assessment_result.model_dump_json(indent=2))

        feed_path = target_dir / f"student_feedback_{student_id}_{sprint_id}.json"
        with open(feed_path, "w", encoding="utf-8") as f:
            f.write(student_feedback.model_dump_json(indent=2))

    return {
        "assessment_result": assessment_result.model_dump(),
        "student_feedback": student_feedback.model_dump(),
        "current_step": "export_complete",
    }
