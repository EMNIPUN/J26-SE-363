"""Public schemas and API response contracts for individual student performance assessment.

Strictly aligned with:
- PLAN.md Section 12.3 (Output API Schema — Assessment Result Contract)
- Functional Requirements FR8, FR14, NFR8
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class FactorScoreOutput(BaseModel):
    """Public representation of an individual factor evaluation result."""
    model_config = ConfigDict(frozen=True)

    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score in [0.0, 1.0]")
    label: str = Field(..., description="Human-readable factor title (e.g. 'Effort', 'Consistency')")
    evidence_summary: str = Field(..., description="Synthesized evidence statement explaining the score basis")
    status: Literal["completed", "fallback_applied", "missing"] = Field(
        default="completed", description="Factor execution status"
    )


class AssessmentResultSchema(BaseModel):
    """Final, comprehensive assessment contract written to database and consumed by Lecturer Dashboard."""
    model_config = ConfigDict(frozen=True)

    # 1. Identity & Context
    student_id: str = Field(..., description="Unique student identifier")
    student_name: str = Field(..., description="Student full name (PII restored)")
    team_id: str = Field(..., description="Team/Project identifier")
    sprint_id: str = Field(..., description="Sprint identifier (e.g. 'sprint-02')")
    assessed_at: datetime = Field(..., description="Timestamp when assessment was finalized")

    # 2. Mathematical Scores
    factor_scores: Dict[str, FactorScoreOutput] = Field(
        ..., description="Mapping of factor keys (effort, consistency, etc.) to factor score outputs"
    )
    additive_score: float = Field(..., ge=0.0, le=1.0, description="Weighted additive sum before behavioral modifier")
    behavioral_modifier: float = Field(..., ge=0.80, le=1.20, description="Empirical modifier based on contributor archetype")
    final_score: float = Field(..., ge=0.0, le=1.0, description="Final mathematical score S in [0.0, 1.0]")
    final_score_percentage: float = Field(..., ge=0.0, le=100.0, description="Final score S scaled to percentage (0 - 100)")
    behavioral_persona: str = Field(..., description="Contributor archetype (e.g. 'Steady Contributor', 'Deadline Rusher')")

    # 3. Transparent Explanations (PII-Restored)
    instructor_report_markdown: str = Field(..., description="Formal comprehensive markdown assessment dossier for instructors")
    student_feedback_markdown: str = Field(..., description="Constructive, pedagogical feedback for student development")

    # 4. Visualizations
    radar_chart_data: Dict[str, float] = Field(..., description="Key-value mapping of factor dimensions for UI radar chart")

    # 5. Auditing & Human Overrides
    lecturer_override_applied: bool = Field(default=False, description="True if an instructor manually overrode the score")
    lecturer_override_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Overridden score value if applied")
    lecturer_comments: Optional[str] = Field(default=None, description="Instructor review or override justification notes")
    calculation_audit_trail: Dict[str, Any] = Field(
        default_factory=dict, description="Verifiable mathematical breakdown of weights, raw factors, and modifiers used"
    )
    discrepancy_flags: List[Dict[str, Any]] = Field(
        default_factory=list, description="Automated quality alert items (Ghostwriter, Deadline Panic, Free Rider, etc.)"
    )

    # 6. Historical Trajectory
    historical_trajectory: List[Dict[str, Any]] = Field(
        default_factory=list, description="Prior sprint scores and archetypes for longitudinal comparison"
    )


class StudentFeedbackSchema(BaseModel):
    """Sanitized student-facing feedback contract exposed via Student Portal."""
    model_config = ConfigDict(frozen=True)

    student_id: str = Field(..., description="Unique student identifier")
    sprint_id: str = Field(..., description="Sprint identifier")
    final_score: float = Field(..., ge=0.0, le=1.0, description="Final individual contribution score")
    final_score_percentage: float = Field(..., ge=0.0, le=100.0, description="Contribution score expressed as percentage")
    behavioral_persona: str = Field(..., description="Contributor archetype title")
    radar_chart_data: Dict[str, float] = Field(..., description="Dimension breakdown for student visualization")
    student_feedback_markdown: str = Field(..., description="Constructive, formative recommendations for agile improvement")
    historical_trajectory: List[Dict[str, Any]] = Field(
        default_factory=list, description="Progress trajectory across previous sprints"
    )


__all__ = [
    "FactorScoreOutput",
    "AssessmentResultSchema",
    "StudentFeedbackSchema",
]
