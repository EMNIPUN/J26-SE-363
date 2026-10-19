from app.agents.project_planning.schemas import (
    CheckResult, CoverageAnalysis, CoverageCheck, CoverageGateResult,
    DecompositionGateStatus, DecompositionTaskSummary, InvestCriterionResult,
    InvestResult, StoryInvest, TaskSetCoverage,
)
from app.agents.project_planning.subagents.decomposition.scorer import (
    compute_components, formal_status, quality_band,
)


def _coverage(failed=()):
    checks = {f"C{i}": CoverageCheck(check_id=f"C{i}", result=CheckResult.FAIL if f"C{i}" in failed else CheckResult.PASS) for i in range(1, 11)}
    return CoverageAnalysis(gate=CoverageGateResult(checks=checks, passed=not failed))


def test_structural_coverage_failure_caps_component_at_two():
    assert compute_components(_coverage(("C1",)), [], []).coverage == 2.0


def test_non_structural_coverage_failure_caps_component_at_three():
    assert compute_components(_coverage(("C2",)), [], []).coverage == 3.0


def test_complete_requires_ready_story_and_tasks():
    story = StoryInvest(
        story_id="US-1", story_ready=True,
        **{name: InvestCriterionResult(result=InvestResult.PASS) for name in ("independent", "negotiable", "valuable", "estimable", "small", "testable")},
        acceptance_criteria_readiness={"result": "Pass"},
    )
    tasks = [DecompositionTaskSummary(story_id="US-1", ready=True, quality_score=4, coverage=TaskSetCoverage())]
    assert formal_status(_coverage(), [story], tasks) == DecompositionGateStatus.COMPLETE
    assert formal_status(_coverage(), [story], []) == DecompositionGateStatus.INCOMPLETE


def test_documented_quality_bands():
    assert quality_band(3.5).value == "Excellent"
    assert quality_band(2.5).value == "Good"
    assert quality_band(1.5).value == "Moderate"
    assert quality_band(.5).value == "Poor"
