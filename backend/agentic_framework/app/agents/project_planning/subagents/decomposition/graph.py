"""Evidence-based decomposition orchestration with selective retrieval."""
from __future__ import annotations
import asyncio
import logging
from app.agents.project_planning.knowledge import query_patterns
from app.agents.project_planning.schemas import AnalyzeDecompositionInput, CoverageAnalysis, InvestGateResult, StoryInvest
from app.agents.project_planning.subagents.decomposition.coverage import analyze_coverage, _unavailable_analysis
from app.agents.project_planning.subagents.decomposition.gate import classify_readiness
from app.agents.project_planning.subagents.decomposition.invest import validate_invest
from app.agents.project_planning.subagents.decomposition.scorer import build_result, formal_status
from app.agents.project_planning.subagents.decomposition.feedback import synthesize_improvement_plan
from app.agents.project_planning.subagents.task_validation.validator import validate_task_sets

logger = logging.getLogger(__name__)
AGENT_TIMEOUT_SECONDS = 180.0

def _invest_gate(results: list[StoryInvest]) -> InvestGateResult:
    failed = [r.story_id for r in results if not r.story_ready]
    return InvestGateResult(all_stories_ready=not failed, failed_stories=failed)

def _needs_patterns(coverage, stories, tasks) -> bool:
    return coverage.needs_review or not coverage.gate.passed or any(not s.story_ready for s in stories) or any(not t.ready for t in tasks)

def _advisory_readiness(coverage, stories, tasks):
    # Existing readiness labels remain advisory, but task and AC failures are
    # visible as Needs Attention instead of being silently downgraded.
    readiness, reason = classify_readiness(coverage, stories)
    if any(not t.ready for t in tasks) and readiness.value != "Needs Attention":
        return type(readiness).READY_WITH_IMPROVEMENTS, "Story tasks need revision before this decomposition is fully complete; you may still continue."
    return readiness, reason

async def _run(payload: AnalyzeDecompositionInput):
    stories = [{"id": s.id, "title": s.title, "description": s.description, "acceptance_criteria": s.acceptance_criteria, "tasks": [t.model_dump() for t in s.tasks], "linked_parent_requirement": s.linked_parent_requirement or payload.requirement.id} for s in payload.stories]
    coverage, invest, task_summaries = await asyncio.gather(
        analyze_coverage(payload.requirement.id, payload.requirement.text, stories),
        validate_invest(payload.requirement.id, stories),
        validate_task_sets(payload.requirement.text, stories),
    )
    tools = ["coverage_analyzer", "invest_validator", "task_validator_batch", "deterministic_scorer"]
    patterns = []
    if _needs_patterns(coverage, invest, task_summaries):
        try:
            patterns = await asyncio.to_thread(query_patterns, payload.requirement.text, 3)
            tools.append("pattern_retriever")
        except Exception:
            logger.exception("pattern retrieval failed for %s", payload.requirement.id)
    readiness, reason = _advisory_readiness(coverage, invest, task_summaries)
    improvement_plan = []
    if formal_status(coverage, invest, task_summaries).value != "COMPLETE":
        try:
            improvement_plan = await synthesize_improvement_plan({
                "coverage_checks": [c.model_dump() for c in coverage.gate.checks.values()],
                "stories": [s.model_dump() for s in invest],
                "tasks": [t.model_dump() for t in task_summaries],
                "patterns": patterns,
            })
            if improvement_plan: tools.append("feedback_synthesizer")
        except Exception:
            logger.exception("feedback synthesis failed for %s", payload.requirement.id)
    return build_result(payload.requirement.id, coverage, invest, _invest_gate(invest), task_summaries, readiness, reason, patterns, tools, improvement_plan)

async def run_decomposition_agent(payload: AnalyzeDecompositionInput):
    try:
        return await asyncio.wait_for(_run(payload), timeout=AGENT_TIMEOUT_SECONDS)
    except Exception:
        logger.exception("Decomposition analysis failed for %s", payload.requirement.id)
        stories = [{"id": s.id, "title": s.title, "description": s.description, "acceptance_criteria": s.acceptance_criteria, "tasks": [t.model_dump() for t in s.tasks], "linked_parent_requirement": s.linked_parent_requirement or payload.requirement.id} for s in payload.stories]
        coverage = _unavailable_analysis("Decomposition analysis failed — please re-run analysis.")
        invest = await validate_invest(payload.requirement.id, stories)
        tasks = await validate_task_sets(payload.requirement.text, stories)
        readiness, reason = _advisory_readiness(coverage, invest, tasks)
        return build_result(payload.requirement.id, coverage, invest, _invest_gate(invest), tasks, readiness, reason, [], ["coverage_analyzer", "invest_validator", "task_validator_batch", "deterministic_scorer"])
