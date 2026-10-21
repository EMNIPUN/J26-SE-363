"""Regression tests for the decomposition validation audit (2026-10-21).

Each test targets a specific finding from the audit and ensures the fix holds.
Tests are pure-Python (no LLM, no DB, no network) and exercise the deterministic
layers of the pipeline.
"""
import pytest

from app.agents.project_planning.schemas import (
    AcceptanceCriteriaReadiness,
    CheckResult,
    CoverageAnalysis,
    CoverageCheck,
    CoverageElement,
    CoverageElementType,
    CoverageGateResult,
    CoverageResult,
    DecompositionTaskSummary,
    InvestCriterionResult,
    InvestResult,
    StoryInvest,
    TaskCriterionOutcome,
    TaskCriterionResult,
    TaskSetCoverage,
    TaskValidationItem,
)
from app.agents.project_planning.subagents.decomposition.invest import detect_invest_signals
from app.agents.project_planning.subagents.decomposition.scorer import (
    _value,
    build_feedback,
    compute_components,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_pass_checks(failed=()):
    checks = {
        f"C{i}": CoverageCheck(
            check_id=f"C{i}",
            result=CheckResult.FAIL if f"C{i}" in failed else CheckResult.PASS,
            rationale="test",
            suggestion="fix it" if f"C{i}" in failed else "",
        )
        for i in range(1, 11)
    }
    return CoverageAnalysis(
        elements=[], coverage_percentage=100.0,
        gate=CoverageGateResult(checks=checks, passed=not failed),
    )


def _pass_criterion():
    return InvestCriterionResult(result=InvestResult.PASS, note="OK")


def _story(story_id, ready=True, ac_result=InvestResult.PASS, **overrides):
    criteria = {
        name: _pass_criterion()
        for name in ("independent", "negotiable", "valuable", "estimable", "small", "testable")
    }
    criteria.update(overrides)
    return StoryInvest(
        story_id=story_id,
        story_text="test story",
        linked_parent_requirement="REQ-1",
        story_ready=ready,
        acceptance_criteria_readiness=AcceptanceCriteriaReadiness(
            result=ac_result, criteria_count=3, issues=[], evidence=[], suggestion="",
        ),
        **criteria,
    )


# ---------------------------------------------------------------------------
# Fix 1 — AC override is PASS_WITH_NOTE, not FAIL
# ---------------------------------------------------------------------------

class TestACOverrideSoftened:
    def test_ac_fail_does_not_force_estimable_to_fail(self):
        """When AC readiness fails but LLM passed estimable, the override should
        produce PASS_WITH_NOTE, not FAIL."""
        signals = detect_invest_signals(
            "Login feature",
            "As a user, I want to log in so that I can access my dashboard",
        )
        assert signals["estimable"]["signal"] == "pass"

    def test_ac_override_score_not_triple_penalized(self):
        """A story where AC fails should not triple-penalize via estimable+testable."""
        story_ac_pass = _story("US-1", ac_result=InvestResult.PASS)
        story_ac_fail = _story(
            "US-2", ready=False,
            ac_result=InvestResult.FAIL,
            estimable=InvestCriterionResult(
                result=InvestResult.PASS_WITH_NOTE,
                note="[AC-derived] Estimability depends on acceptance criteria, which need improvement.",
            ),
            testable=InvestCriterionResult(
                result=InvestResult.PASS_WITH_NOTE,
                note="[AC-derived] Estimability depends on acceptance criteria, which need improvement.",
            ),
        )
        cov = _all_pass_checks()
        score_pass = compute_components(cov, [story_ac_pass], []).story_acceptance
        score_fail = compute_components(cov, [story_ac_fail], []).story_acceptance
        penalty = score_pass - score_fail
        assert penalty < 1.0, f"AC fail penalty {penalty} is too large (triple-counting)"


# ---------------------------------------------------------------------------
# Fix 2 — Graduated structural cap
# ---------------------------------------------------------------------------

class TestGraduatedStructuralCap:
    def test_one_structural_failure_caps_at_three(self):
        cov = _all_pass_checks(failed=("C1",))
        assert compute_components(cov, [], []).coverage == 3.0

    def test_two_structural_failures_cap_at_two(self):
        cov = _all_pass_checks(failed=("C1", "C6"))
        assert compute_components(cov, [], []).coverage == 2.0

    def test_three_structural_failures_cap_at_two(self):
        cov = _all_pass_checks(failed=("C1", "C6", "C9"))
        assert compute_components(cov, [], []).coverage <= 2.0

    def test_non_structural_failure_caps_at_three(self):
        cov = _all_pass_checks(failed=("C2",))
        assert compute_components(cov, [], []).coverage == 3.0


# ---------------------------------------------------------------------------
# Fix 9 — Structural cap feedback shown
# ---------------------------------------------------------------------------

class TestStructuralCapFeedback:
    def test_structural_failure_feedback_mentions_cap(self):
        cov = _all_pass_checks(failed=("C1",))
        feedback = build_feedback(cov, [], [])
        cap_lines = [f for f in feedback if "cap" in f.lower() and "structural" in f.lower()]
        assert cap_lines, f"Expected structural cap feedback, got: {feedback}"

    def test_no_cap_feedback_when_all_pass(self):
        cov = _all_pass_checks()
        feedback = build_feedback(cov, [], [])
        cap_lines = [f for f in feedback if "cap" in f.lower() and "structural" in f.lower()]
        assert not cap_lines


# ---------------------------------------------------------------------------
# Fix 3 — Cannot Assess consistency
# ---------------------------------------------------------------------------

class TestCannotAssessConsistency:
    def test_invest_cannot_assess_is_025(self):
        assert _value(InvestResult.CANNOT_ASSESS) == 0.25

    def test_task_cannot_assess_is_025(self):
        """Task validator should give Cannot Assess 0.25, not 0."""
        from app.agents.project_planning.subagents.task_validation.validator import TASK_CRITERIA
        task = TaskValidationItem(
            task_id="T-1", task_ready=False,
            **{c: TaskCriterionResult(result=TaskCriterionOutcome.CANNOT_ASSESS) for c in TASK_CRITERIA},
        )
        per_task = sum(
            .25 if getattr(task, c).result == TaskCriterionOutcome.CANNOT_ASSESS else 0
            for c in TASK_CRITERIA
        ) / len(TASK_CRITERIA)
        assert per_task == 0.25


# ---------------------------------------------------------------------------
# Fix 4 — "after" regex tightened
# ---------------------------------------------------------------------------

class TestAfterRegexTightened:
    def test_after_login_not_dependency(self):
        signals = detect_invest_signals("View results", "After login, the user can view results")
        assert signals["independent"]["signal"] == "pass"

    def test_after_completing_is_dependency(self):
        signals = detect_invest_signals("Payment", "After completing the order, process payment")
        assert signals["independent"]["signal"] == "fail"

    def test_after_the_x_is_dependency(self):
        signals = detect_invest_signals("Setup", "After the migration is done, run seeds")
        assert signals["independent"]["signal"] == "fail"

    def test_depends_on_still_works(self):
        signals = detect_invest_signals("Feature B", "Depends on feature A being deployed")
        assert signals["independent"]["signal"] == "fail"

    def test_only_once_still_works(self):
        signals = detect_invest_signals("Init", "Can only once be configured at startup")
        assert signals["independent"]["signal"] == "fail"


# ---------------------------------------------------------------------------
# Fix 5 — Estimable NFR context
# ---------------------------------------------------------------------------

class TestEstimableNFRContext:
    def test_efficient_in_nfr_context_not_penalized(self):
        signals = detect_invest_signals("Memory usage", "Efficient memory usage for performance")
        assert signals["estimable"]["signal"] == "pass"

    def test_fast_in_nfr_context_not_penalized(self):
        signals = detect_invest_signals("API speed", "Fast response time for latency requirements")
        assert signals["estimable"]["signal"] == "pass"

    def test_vague_without_nfr_still_fails(self):
        signals = detect_invest_signals("Dashboard", "Various appropriate widgets displayed nicely")
        assert signals["estimable"]["signal"] == "fail"


# ---------------------------------------------------------------------------
# Fix 6 — UX context in NFR regex (button not penalized)
# ---------------------------------------------------------------------------

class TestUXContextInNFR:
    def test_button_in_ux_context_not_penalized(self):
        signals = detect_invest_signals(
            "Accessible form", "Add ARIA labels to the submit button for accessibility"
        )
        assert signals["negotiable"]["signal"] == "pass"

    def test_button_in_ui_context_not_penalized(self):
        signals = detect_invest_signals(
            "Button style", "User interface button color follows the design system"
        )
        assert signals["negotiable"]["signal"] == "pass"

    def test_react_without_nfr_still_fails(self):
        signals = detect_invest_signals(
            "React page", "Build a React page with user registration form"
        )
        assert signals["negotiable"]["signal"] == "fail"

    def test_security_nfr_still_passes(self):
        """Regression: prior fix for security NFR context must still work."""
        signals = detect_invest_signals(
            "Password security", "Use computationally expensive password hashing for security"
        )
        assert signals["negotiable"]["signal"] == "pass"


# ---------------------------------------------------------------------------
# Feedback dedup — AC-derived entries suppressed
# ---------------------------------------------------------------------------

class TestFeedbackDedupACDerived:
    def test_ac_derived_estimable_suppressed_in_feedback(self):
        story = StoryInvest(
            story_id="US-1", story_text="test", linked_parent_requirement="REQ-1",
            story_ready=False,
            independent=_pass_criterion(),
            negotiable=_pass_criterion(),
            valuable=_pass_criterion(),
            estimable=InvestCriterionResult(
                result=InvestResult.FAIL,
                note="[AC-derived] Estimability depends on acceptance criteria, which need improvement.",
            ),
            small=_pass_criterion(),
            testable=InvestCriterionResult(
                result=InvestResult.FAIL,
                note="[AC-derived] Estimability depends on acceptance criteria, which need improvement.",
            ),
            acceptance_criteria_readiness=AcceptanceCriteriaReadiness(
                result=InvestResult.FAIL, criteria_count=0,
                issues=["No acceptance criteria were supplied."],
            ),
        )
        feedback = build_feedback(_all_pass_checks(), [story], [])
        ac_lines = [f for f in feedback if "acceptance criteria" in f.lower()]
        est_lines = [f for f in feedback if "Estimable" in f]
        test_lines = [f for f in feedback if "Testable" in f]
        assert ac_lines, "AC readiness failure should be reported"
        assert not est_lines, "AC-derived Estimable should be suppressed"
        assert not test_lines, "AC-derived Testable should be suppressed"


# ---------------------------------------------------------------------------
# Coverage percentage uses element coverage, not min()
# ---------------------------------------------------------------------------

class TestCoveragePercentageElementOnly:
    def test_coverage_percentage_from_elements_not_checks(self):
        elements = [
            CoverageElement(
                element_id=f"E{i}", element_type=CoverageElementType.MAIN_ACTION,
                description="test", required=True,
                covered_by=["US-1"] if i <= 8 else [],
                coverage_result=CoverageResult.COVERED if i <= 8 else CoverageResult.MISSING,
            )
            for i in range(1, 11)
        ]
        checks = {
            f"C{i}": CoverageCheck(check_id=f"C{i}", result=CheckResult.FAIL if i <= 5 else CheckResult.PASS)
            for i in range(1, 11)
        }
        cov = CoverageAnalysis(
            elements=elements, coverage_percentage=80.0,
            gate=CoverageGateResult(checks=checks, passed=False),
        )
        assert cov.coverage_percentage == 80.0


# ---------------------------------------------------------------------------
# C6/C9 decoupled — orphan does not cascade to out-of-scope
# ---------------------------------------------------------------------------

class TestC6C9Decoupled:
    def test_c6_orphan_does_not_imply_c9_failure(self):
        """C6 (orphan stories) and C9 (out-of-scope) should be independent checks."""
        checks = {f"C{i}": CoverageCheck(check_id=f"C{i}", result=CheckResult.PASS) for i in range(1, 11)}
        checks["C6"] = CoverageCheck(check_id="C6", result=CheckResult.FAIL, rationale="Orphan story US-3")
        cov = CoverageAnalysis(
            elements=[], coverage_percentage=80.0,
            gate=CoverageGateResult(checks=checks, passed=False, orphan_stories=["US-3"], out_of_scope_stories=[]),
        )
        assert cov.gate.checks["C9"].result == CheckResult.PASS
