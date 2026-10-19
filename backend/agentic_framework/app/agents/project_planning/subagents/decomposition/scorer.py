"""Transparent evidence-based decomposition scoring and formal advisory gate."""
from __future__ import annotations

from app.agents.project_planning.schemas import (CheckResult, CoverageAnalysis, DecompositionGateStatus, DecompositionReadiness, DecompositionResult, DecompositionScoreComponents, DecompositionTaskSummary, InvestGateResult, InvestResult, QualityBand, StoryInvest)

_INVEST = ("independent", "negotiable", "valuable", "estimable", "small", "testable")
_STRUCTURAL = {"C1", "C6", "C7", "C8", "C9"}

def _value(result: InvestResult) -> float:
    return 1.0 if result == InvestResult.PASS else .75 if result == InvestResult.PASS_WITH_NOTE else 0.0

def quality_band(score: float) -> QualityBand:
    if score >= 3.5: return QualityBand.EXCELLENT
    if score >= 2.5: return QualityBand.GOOD
    if score >= 1.5: return QualityBand.MODERATE
    if score >= .5: return QualityBand.POOR
    return QualityBand.VERY_POOR

def compute_components(coverage: CoverageAnalysis, stories: list[StoryInvest], tasks: list[DecompositionTaskSummary]) -> DecompositionScoreComponents:
    checks = list(coverage.gate.checks.values())
    coverage_score = sum(c.result == CheckResult.PASS for c in checks) / max(len(checks), 1) * 4
    failures = {c.check_id for c in checks if c.result == CheckResult.FAIL}
    coverage_score = min(coverage_score, 2.0 if failures & _STRUCTURAL else 3.0) if failures else coverage_score
    story_score = sum((sum(_value(getattr(s, c).result) for c in _INVEST) + _value(s.acceptance_criteria_readiness.result)) / 7 for s in stories) / max(len(stories), 1) * 4
    task_score = sum(t.quality_score / 4 for t in tasks) / max(len(tasks), 1) * 4
    return DecompositionScoreComponents(coverage=round(coverage_score, 2), story_acceptance=round(story_score, 2), task_quality=round(task_score, 2))

def formal_status(coverage: CoverageAnalysis, stories: list[StoryInvest], tasks: list[DecompositionTaskSummary]) -> DecompositionGateStatus:
    if coverage.analysis_failed or coverage.needs_review or any(t.analysis_failed for t in tasks): return DecompositionGateStatus.NEEDS_REVIEW
    if not coverage.gate.passed or not stories or not all(s.story_ready for s in stories) or len(tasks) != len(stories) or not all(t.ready for t in tasks): return DecompositionGateStatus.INCOMPLETE
    return DecompositionGateStatus.COMPLETE

def build_feedback(coverage: CoverageAnalysis, stories: list[StoryInvest], tasks: list[DecompositionTaskSummary]) -> list[str]:
    feedback = []
    for c in sorted(coverage.gate.checks.values(), key=lambda x: x.check_id):
        if c.result == CheckResult.FAIL: feedback.append(f"{c.check_id}: {c.rationale}" + (f" → {c.suggestion}" if c.suggestion else ""))
    for s in stories:
        if s.acceptance_criteria_readiness.result not in (InvestResult.PASS, InvestResult.PASS_WITH_NOTE): feedback.append(f"{s.story_id} acceptance criteria: " + "; ".join(s.acceptance_criteria_readiness.issues or [s.acceptance_criteria_readiness.suggestion]))
        for c in _INVEST:
            criterion = getattr(s, c)
            if criterion.result in (InvestResult.FAIL, InvestResult.CANNOT_ASSESS): feedback.append(f"{s.story_id} {c.title()}: {criterion.note}")
    for t in tasks:
        if not t.tasks: feedback.append(f"{t.story_id} tasks: Add concrete implementation tasks; this story currently has none.")
        feedback.extend(f"{t.story_id} tasks: add work for {work}." for work in t.coverage.missing_work_items)
    return feedback or ["All coverage, story, acceptance-criteria, and task checks passed."]

def build_result(requirement_ref: str, coverage: CoverageAnalysis, stories: list[StoryInvest], invest_gate: InvestGateResult, tasks: list[DecompositionTaskSummary], readiness: DecompositionReadiness, readiness_reason: str, patterns: list[dict], tools_used: list[str], improvement_plan: list[dict] | None = None) -> DecompositionResult:
    components = compute_components(coverage, stories, tasks)
    score = 0.0 if coverage.analysis_failed else round(.4 * components.coverage + .4 * components.story_acceptance + .2 * components.task_quality, 2)
    status = formal_status(coverage, stories, tasks)
    return DecompositionResult(requirement_ref=requirement_ref, coverage=coverage, stories=stories, invest_gate=invest_gate, task_summaries=tasks, score_components=components, decomposition_quality_score=score, quality_band=quality_band(score), readiness=readiness, readiness_reason=readiness_reason, gate_status=status, needs_review_reason=coverage.needs_review_reason, student_feedback=build_feedback(coverage, stories, tasks), improvement_plan=improvement_plan or [], patterns=patterns, tools_used=tools_used, confidence=0.0 if coverage.analysis_failed else 1.0, dart_triggered=status == DecompositionGateStatus.NEEDS_REVIEW, analysis_failed=coverage.analysis_failed, failure_reason=coverage.failure_reason, retrieval={"patterns": patterns})
