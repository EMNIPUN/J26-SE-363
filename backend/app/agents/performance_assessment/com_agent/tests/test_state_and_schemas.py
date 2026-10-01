"""Unit tests for Phase 1: State & Schema Layer."""

import pytest
from pydantic import ValidationError
from app.agents.performance_assessment.com_agent.state import FactorOutput

# --- T1.1.1: FactorOutput Tests ---

def test_factor_output_valid_instantiation():
    fo = FactorOutput(
        score=0.85,
        features={"cc": 12, "loc_net": 450},
        evidence_traces=[{"commit_sha": "a1b2c3d"}],
        status="completed"
    )
    assert fo.score == 0.85
    assert fo.features["cc"] == 12
    assert len(fo.evidence_traces) == 1
    assert fo.status == "completed"
    assert fo.error_message is None

def test_factor_output_score_boundary_validation():
    # Valid boundaries
    f_zero = FactorOutput(score=0.0)
    assert f_zero.score == 0.0

    f_one = FactorOutput(score=1.0)
    assert f_one.score == 1.0

    # Invalid boundaries
    with pytest.raises(ValidationError):
        FactorOutput(score=-0.01)

    with pytest.raises(ValidationError):
        FactorOutput(score=1.01)

def test_factor_output_status_literal_validation():
    for valid_status in ["completed", "missing", "fallback_applied"]:
        fo = FactorOutput(score=0.0, status=valid_status)
        assert fo.status == valid_status

    with pytest.raises(ValidationError):
        FactorOutput(score=0.5, status="invalid_status")

def test_factor_output_defaults():
    fo = FactorOutput(score=0.75)
    assert fo.features == {}
    assert fo.evidence_traces == []
    assert fo.status == "completed"
    assert fo.error_message is None

from app.agents.performance_assessment.com_agent.state import ActiveVerificationState

# --- T1.1.2: ActiveVerificationState Tests ---

def test_active_verification_defaults():
    av = ActiveVerificationState()
    assert av.target_code_snippet is None
    assert av.file_path is None
    assert av.line_range is None
    assert av.generated_question is None
    assert av.ast_metadata == {}
    assert av.student_response is None
    assert av.response_timestamp is None
    assert av.ownership_score is None
    assert av.is_timed_out is False
    assert av.is_extended is False
    assert av.quiz_extension_deadline is None
    assert av.is_double_timed_out is False

def test_active_verification_full_instantiation():
    av = ActiveVerificationState(
        target_code_snippet="def authenticate(user, pwd): pass",
        file_path="app/core/security.py",
        line_range=[10, 25],
        generated_question="Explain how the token is hashed and verified.",
        ast_metadata={"node_type": "FunctionDef", "complexity": 4},
        student_response="The function hashes password with bcrypt.",
        response_timestamp="2025-09-08T12:00:00Z",
        ownership_score=0.92,
        is_timed_out=True,
        is_extended=True,
        quiz_extension_deadline="2025-09-10T12:00:00Z",
        is_double_timed_out=False
    )
    assert av.target_code_snippet.startswith("def authenticate")
    assert av.ownership_score == 0.92
    assert av.is_extended is True
    assert av.quiz_extension_deadline == "2025-09-10T12:00:00Z"

def test_active_verification_ownership_score_bounds():
    # Valid
    av1 = ActiveVerificationState(ownership_score=0.0)
    assert av1.ownership_score == 0.0
    av2 = ActiveVerificationState(ownership_score=1.0)
    assert av2.ownership_score == 1.0

    # Invalid
    with pytest.raises(ValidationError):
        ActiveVerificationState(ownership_score=-0.05)
    with pytest.raises(ValidationError):
        ActiveVerificationState(ownership_score=1.05)

from app.agents.performance_assessment.com_agent.state import DiscrepancyAlert

# --- T1.1.3: DiscrepancyAlert Tests ---

def test_discrepancy_alert_valid_codes_and_severities():
    valid_codes = ["GHOSTWRITER_SUSPICION", "DEADLINE_PANIC", "FREE_RIDER", "UNRECORDED_WORK"]
    valid_severities = ["INFO", "WARNING", "CRITICAL"]

    for code in valid_codes:
        for sev in valid_severities:
            alert = DiscrepancyAlert(
                alert_code=code,
                severity=sev,
                description=f"Testing {code} with {sev}",
                recommended_action="Inspect student submissions"
            )
            assert alert.alert_code == code
            assert alert.severity == sev

def test_discrepancy_alert_invalid_code_fails():
    with pytest.raises(ValidationError):
        DiscrepancyAlert(
            alert_code="UNKNOWN_ANOMALY",
            severity="WARNING",
            description="desc",
            recommended_action="action"
        )

def test_discrepancy_alert_invalid_severity_fails():
    with pytest.raises(ValidationError):
        DiscrepancyAlert(
            alert_code="GHOSTWRITER_SUSPICION",
            severity="HIGH",  # Invalid - must be INFO, WARNING, or CRITICAL
            description="desc",
            recommended_action="action"
        )

from app.agents.performance_assessment.com_agent.state import CohortBaseline

# --- T1.1.4: CohortBaseline Tests ---

def test_cohort_baseline_defaults():
    cb = CohortBaseline()
    assert cb.metric_means == {}
    assert cb.metric_stds == {}
    assert cb.student_count == 0
    assert cb.sprint_count_used == 1
    assert isinstance(cb.computed_at, str)
    assert len(cb.computed_at) > 10

def test_cohort_baseline_full_instantiation():
    cb = CohortBaseline(
        metric_means={"cc": 14.5, "loc_net": 350.0, "fc": 6.2},
        metric_stds={"cc": 3.8, "loc_net": 95.0, "fc": 2.1},
        student_count=20,
        sprint_count_used=3,
        computed_at="2025-09-14T23:59:59Z"
    )
    assert cb.metric_means["cc"] == 14.5
    assert cb.metric_stds["loc_net"] == 95.0
    assert cb.student_count == 20
    assert cb.sprint_count_used == 3
    assert cb.computed_at == "2025-09-14T23:59:59Z"

import operator
from typing import get_type_hints
from app.agents.performance_assessment.com_agent.state import AssessmentState

# --- T1.2: AssessmentState TypedDict Tests ---

def test_assessment_state_annotations_completeness():
    hints = get_type_hints(AssessmentState, include_extras=True)

    # 1. Project & Student Context
    for f in ["student_id", "student_name", "student_github_username", "student_git_emails", "team_id", "sprint_id", "repo_url", "sprint_start", "sprint_end", "assigned_tasks", "cohort_baselines"]:
        assert f in hints, f"Missing context field: {f}"

    # 2. Raw Evidence
    for f in ["commit_history", "pull_requests", "review_comments", "scrum_status_history"]:
        assert f in hints, f"Missing evidence field: {f}"

    # 3. Factor scores reducer
    assert "factor_scores" in hints
    # Verify reducer annotation contains operator.ior
    annotated_args = getattr(hints["factor_scores"], "__metadata__", ())
    assert operator.ior in annotated_args, "factor_scores must have operator.ior reducer"

    # 4. Active Verification
    assert "active_verification" in hints

    # 5. Behavioral & Fusion
    for f in ["behavioral_persona", "behavioral_modifier", "weights_used", "additive_score", "final_score", "calculation_audit_trail"]:
        assert f in hints, f"Missing fusion field: {f}"

    # 6. Discrepancy & HITL
    for f in ["discrepancy_flags", "requires_human_review", "lecturer_reviewed", "lecturer_id", "lecturer_override_score", "lecturer_comments", "review_timestamp"]:
        assert f in hints, f"Missing discrepancy/HITL field: {f}"

    # 7. Memory & PII
    for f in ["historical_trajectory", "pii_substitution_map"]:
        assert f in hints, f"Missing memory/PII field: {f}"

    # 8. Explanations & Metadata
    for f in ["instructor_report_markdown", "student_feedback_markdown", "radar_chart_data", "current_step", "errors"]:
        assert f in hints, f"Missing explanation/metadata field: {f}"

    # 9. Timeout fields (PLAN.md §12.2)
    for f in ["ko_raw_score", "ko_fusion_score", "quiz_is_extended", "quiz_is_double_timed_out", "quiz_extension_deadline"]:
        assert f in hints, f"Missing timeout field: {f}"

    # 10. GitHub API Tracking fields (PLAN.md §12.7)
    for f in ["github_api_call_count", "github_sandbox_mode"]:
        assert f in hints, f"Missing GitHub tracking field: {f}"

def test_assessment_state_parallel_merge_behavior():
    scores1 = {"effort": FactorOutput(score=0.85)}
    scores2 = {"consistency": FactorOutput(score=0.72)}
    scores3 = {"collaboration": FactorOutput(score=0.90)}

    merged = operator.ior(scores1, scores2)
    merged = operator.ior(merged, scores3)

    assert set(merged.keys()) == {"effort", "consistency", "collaboration"}
    assert merged["effort"].score == 0.85
    assert merged["consistency"].score == 0.72
    assert merged["collaboration"].score == 0.90

from datetime import datetime, timezone
from app.agents.performance_assessment.schemas import (
    FactorScoreOutput,
    AssessmentResultSchema,
    StudentFeedbackSchema,
)

# --- T1.3: Public Output Schemas Tests ---

def test_factor_score_output_valid_and_frozen():
    fso = FactorScoreOutput(
        score=0.88,
        label="Effort",
        evidence_summary="15 commits, 450 lines added, 3 tasks touched",
        status="completed"
    )
    assert fso.score == 0.88
    assert fso.label == "Effort"

    # Test frozen immutability
    with pytest.raises(ValidationError):
        fso.score = 0.95

def test_assessment_result_schema_valid_and_frozen():
    f_effort = FactorScoreOutput(score=0.80, label="Effort", evidence_summary="Effort summary")
    f_consistency = FactorScoreOutput(score=0.75, label="Consistency", evidence_summary="Consistency summary")

    res = AssessmentResultSchema(
        student_id="STU-001",
        student_name="Alice Perera",
        team_id="TEAM-A",
        sprint_id="sprint-02",
        assessed_at=datetime.now(timezone.utc),
        factor_scores={"effort": f_effort, "consistency": f_consistency},
        additive_score=0.78,
        behavioral_modifier=1.05,
        final_score=0.819,
        final_score_percentage=81.9,
        behavioral_persona="Steady Contributor",
        instructor_report_markdown="# Instructor Dossier",
        student_feedback_markdown="### Great Work",
        radar_chart_data={"effort": 0.80, "consistency": 0.75},
        lecturer_override_applied=False,
        calculation_audit_trail={"effort_weighted": 0.16},
        discrepancy_flags=[],
        historical_trajectory=[]
    )
    assert res.student_id == "STU-001"
    assert res.final_score_percentage == 81.9

    # Test frozen immutability
    with pytest.raises(ValidationError):
        res.final_score = 0.90

def test_student_feedback_schema_sanitized_and_frozen():
    fb = StudentFeedbackSchema(
        student_id="STU-001",
        sprint_id="sprint-02",
        final_score=0.82,
        final_score_percentage=82.0,
        behavioral_persona="Steady Contributor",
        radar_chart_data={"effort": 0.80, "consistency": 0.75},
        student_feedback_markdown="### Formative Feedback",
        historical_trajectory=[]
    )
    assert fb.student_id == "STU-001"
    assert not hasattr(fb, "instructor_report_markdown"), "StudentFeedbackSchema must not have instructor_report_markdown"
    assert not hasattr(fb, "calculation_audit_trail"), "StudentFeedbackSchema must not have calculation_audit_trail"
    assert not hasattr(fb, "discrepancy_flags"), "StudentFeedbackSchema must not have discrepancy_flags"
    assert not hasattr(fb, "lecturer_comments"), "StudentFeedbackSchema must not have lecturer_comments"

    # Test frozen immutability
    with pytest.raises(ValidationError):
        fb.final_score = 0.90
