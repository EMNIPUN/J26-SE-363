"""Unit tests for ISO/IEC/IEEE 29148 requirement quality scoring method."""

from app.agents.project_planning.schemas import (
    GateAction,
    GateStatus,
    QualityBand,
    RequirementInput,
    Smell,
)
from app.agents.project_planning.subagents.quality.scorer import (
    build_result,
    heuristic_result,
)


def test_pdf_example_1_fully_satisfactory():
    """Example 1: REQ-PAY-021 (All 6 dimensions score 4) -> 4.0/4, 100%."""
    data = {
        "dimension_scores": {
            "clarity": 4,
            "completeness": 4,
            "testability": 4,
            "consistency": 4,
            "traceability": 4,
            "correctness": 4,
        },
        "applicability": {
            "clarity": "applicable",
            "completeness": "applicable",
            "testability": "applicable",
            "consistency": "applicable",
            "traceability": "applicable",
            "correctness": "applicable",
        },
        "evidence": {
            "clarity": "Actors, trigger, behavior, data, and exception behavior are explicit.",
            "completeness": "Normal and failure paths are included.",
            "testability": "Receipt fields and failure behavior can be verified.",
            "consistency": "No conflict is evident in the provided requirement set.",
            "traceability": "Source and test cases are linked.",
            "correctness": "Matches the referenced business rule.",
        },
        "confidence": 0.95,
    }
    result = build_result("REQ-PAY-021", [], data, threshold=75)
    assert result.overall_score_4 == 4.0
    assert result.overall_score == 100
    assert result.quality_band == QualityBand.EXCELLENT
    assert result.status == GateStatus.PASSED
    assert result.gate_action == GateAction.PASS
    assert len(result.applicable_dimensions) == 6
    assert len(result.cannot_assess_dimensions) == 0


def test_pdf_example_2_clear_but_incomplete_with_cannot_assess():
    """Example 2: REQ-USR-007 (Clarity 3, Completeness 1, Testability 2, Consistency 3, Traceability 1, Correctness C/A).
    Applicable dimensions = 5. Q = (3+1+2+3+1)/5 = 2.0/4 = 50%."""
    data = {
        "dimension_scores": {
            "clarity": 3,
            "completeness": 1,
            "testability": 2,
            "consistency": 3,
            "traceability": 1,
            "correctness": None,
        },
        "applicability": {
            "clarity": "applicable",
            "completeness": "applicable",
            "testability": "applicable",
            "consistency": "applicable",
            "traceability": "applicable",
            "correctness": "cannot_assess",
        },
        "evidence": {
            "clarity": "The main action is clear, although users and image constraints are broad.",
            "completeness": "File types, maximum size, image validation, storage, and error behavior are missing.",
            "testability": "Upload can be demonstrated, but acceptance limits are undefined.",
            "consistency": "No conflict is evident from the available context.",
            "traceability": "Requirement ID exists, but no source or downstream links are provided.",
            "correctness": "No stakeholder need or source requirement is available.",
        },
        "confidence": 0.85,
    }
    result = build_result("REQ-USR-007", [], data, threshold=75)
    assert result.overall_score_4 == 2.0
    assert result.overall_score == 50
    assert result.quality_band == QualityBand.MODERATE
    assert result.status == GateStatus.BLOCKED
    assert result.gate_action == GateAction.BLOCK
    assert "correctness" in result.cannot_assess_dimensions
    assert len(result.applicable_dimensions) == 5


def test_pdf_example_3_requirement_with_high_scores():
    """Example 3: REQ-SEC-009 (Scores 4, 3, 4, 4, 3, 4) -> Q = 22/6 = 3.67/4 = 92%."""
    data = {
        "dimension_scores": {
            "clarity": 4,
            "completeness": 3,
            "testability": 4,
            "consistency": 4,
            "traceability": 3,
            "correctness": 4,
        },
        "applicability": {d: "applicable" for d in ["clarity", "completeness", "testability", "consistency", "traceability", "correctness"]},
        "confidence": 0.90,
    }
    result = build_result("REQ-SEC-009", [], data, threshold=75)
    assert result.overall_score_4 == 3.67
    assert result.overall_score == 92
    assert result.quality_band == QualityBand.EXCELLENT
    assert result.status == GateStatus.PASSED


def test_pdf_example_4_correct_but_untestable():
    """Example 4: REQ-PRF-003 (Clarity 2, Completeness 1, Testability 0, Consistency 3, Traceability 1, Correctness C/A).
    Q = (2+1+0+3+1)/5 = 1.4/4 = 35%."""
    data = {
        "dimension_scores": {
            "clarity": 2,
            "completeness": 1,
            "testability": 0,
            "consistency": 3,
            "traceability": 1,
            "correctness": None,
        },
        "applicability": {
            "clarity": "applicable",
            "completeness": "applicable",
            "testability": "applicable",
            "consistency": "applicable",
            "traceability": "applicable",
            "correctness": "cannot_assess",
        },
        "confidence": 0.85,
    }
    result = build_result("REQ-PRF-003", [], data, threshold=75)
    assert result.overall_score_4 == 1.4
    assert result.overall_score == 35
    assert result.quality_band == QualityBand.POOR
    assert result.status == GateStatus.BLOCKED


def test_pdf_example_5_missing_traceability():
    """Example 5: REQ-INV-012 (Clarity 4, Completeness 3, Testability 4, Consistency 4, Traceability 0, Correctness 4).
    Q = 19/6 = 3.17/4 = 79%."""
    data = {
        "dimension_scores": {
            "clarity": 4,
            "completeness": 3,
            "testability": 4,
            "consistency": 4,
            "traceability": 0,
            "correctness": 4,
        },
        "applicability": {d: "applicable" for d in ["clarity", "completeness", "testability", "consistency", "traceability", "correctness"]},
        "confidence": 0.90,
    }
    result = build_result("REQ-INV-012", [], data, threshold=75)
    assert result.overall_score_4 == 3.17
    assert result.overall_score == 79
    assert result.quality_band == QualityBand.GOOD
    assert result.status == GateStatus.PASSED


def test_heuristic_fallback_distinguishes_quality():
    """Verify heuristic fallback gives high score to complete requirements and low score to vague ones."""
    vague_text = "The app should be fast and user-friendly."
    smells = [
        Smell(type="vague_term", span="fast"),
        Smell(type="vague_term", span="user-friendly"),
        Smell(type="weak_word", span="should"),
    ]
    poor_result = heuristic_result("FR-01", smells, 75, req_text=vague_text)
    assert poor_result.overall_score < 50
    assert poor_result.quality_band in (QualityBand.POOR, QualityBand.MODERATE)
    assert poor_result.dimension_scores["clarity"].raw_score <= 1
    assert poor_result.dimension_scores["testability"].raw_score <= 1

    good_text = (
        "When a registered user submits a valid login request, the system shall authenticate "
        "the user within 2 seconds. If invalid, the system shall display an error message. "
        "Source: BR-AUTH-01. Test: TC-AUTH-001."
    )
    good_result = heuristic_result("FR-02", [], 75, req_text=good_text, other_texts=["Another requirement"])
    assert good_result.overall_score >= 85
    assert good_result.quality_band == QualityBand.EXCELLENT
    assert good_result.status == GateStatus.PASSED
