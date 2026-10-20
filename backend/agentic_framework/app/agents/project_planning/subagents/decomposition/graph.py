"""Evidence-based decomposition orchestration with selective retrieval."""
from __future__ import annotations
import asyncio
import logging
from app.agents.project_planning.knowledge import query_patterns
from app.agents.project_planning.schemas import AnalyzeDecompositionInput, CoverageAnalysis, DecompositionTaskSummary, InvestGateResult, StoryInvest
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
    story_ids_to_analyze = set(payload.options.story_ids_to_analyze)
    # An omitted list preserves the original behaviour for callers that do
    # not yet support incremental decomposition.
    if not story_ids_to_analyze:
        story_ids_to_analyze = {story["id"] for story in stories}
    stories_to_analyze = [
        story for story in stories if story["id"] in story_ids_to_analyze
    ]

    cached_invest = {}
    for raw in payload.options.cached_story_results:
        try:
            result = StoryInvest.model_validate(raw)
            cached_invest[result.story_id] = result
        except (TypeError, ValueError):
            logger.warning("Ignoring malformed cached INVEST result")
    cached_tasks = {}
    for raw in payload.options.cached_task_summaries:
        try:
            result = DecompositionTaskSummary.model_validate(raw)
            cached_tasks[result.story_id] = result
        except (TypeError, ValueError):
            logger.warning("Ignoring malformed cached task summary")

    coverage, fresh_invest, fresh_tasks = await asyncio.gather(
        analyze_coverage(payload.requirement.id, payload.requirement.text, stories),
        validate_invest(payload.requirement.id, stories_to_analyze),
        validate_task_sets(payload.requirement.text, stories_to_analyze),
    )
    fresh_invest_by_story = {result.story_id: result for result in fresh_invest}
    fresh_tasks_by_story = {result.story_id: result for result in fresh_tasks}
    # Keep every story in the aggregate score, but only invoke the per-story
    # AI validators for added or edited stories.
    invest = [
        fresh_invest_by_story.get(story["id"]) or cached_invest.get(story["id"])
        for story in stories
    ]
    task_summaries = [
        fresh_tasks_by_story.get(story["id"]) or cached_tasks.get(story["id"])
        for story in stories
    ]
    # A missing cache entry must be evaluated rather than silently omitted.
    missing_ids = {
        story["id"]
        for story, invest_result, task_result in zip(stories, invest, task_summaries)
        if invest_result is None or task_result is None
    }
    if missing_ids:
        logger.warning("Missing cached story analysis for %s; evaluating it", sorted(missing_ids))
        fallback_stories = [story for story in stories if story["id"] in missing_ids]
        fallback_invest, fallback_tasks = await asyncio.gather(
            validate_invest(payload.requirement.id, fallback_stories),
            validate_task_sets(payload.requirement.text, fallback_stories),
        )
        fresh_invest_by_story.update({result.story_id: result for result in fallback_invest})
        fresh_tasks_by_story.update({result.story_id: result for result in fallback_tasks})
        invest = [
            fresh_invest_by_story.get(story["id"]) or cached_invest[story["id"]]
            for story in stories
        ]
        task_summaries = [
            fresh_tasks_by_story.get(story["id"]) or cached_tasks[story["id"]]
            for story in stories
        ]

    tools = ["coverage_analyzer", "deterministic_scorer"]
    if stories_to_analyze:
        tools.extend(["invest_validator", "task_validator_batch"])
    if cached_invest or cached_tasks:
        tools.append("cached_story_analysis")
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
        story_ids_to_analyze = set(payload.options.story_ids_to_analyze) or {story["id"] for story in stories}
        stories_to_analyze = [story for story in stories if story["id"] in story_ids_to_analyze]
        fresh_invest, fresh_tasks = await asyncio.gather(
            validate_invest(payload.requirement.id, stories_to_analyze),
            validate_task_sets(payload.requirement.text, stories_to_analyze),
        )
        cached_invest = {}
        for raw in payload.options.cached_story_results:
            try:
                result = StoryInvest.model_validate(raw)
                cached_invest[result.story_id] = result
            except (TypeError, ValueError):
                logger.warning("Ignoring malformed cached INVEST result")
        cached_tasks = {}
        for raw in payload.options.cached_task_summaries:
            try:
                result = DecompositionTaskSummary.model_validate(raw)
                cached_tasks[result.story_id] = result
            except (TypeError, ValueError):
                logger.warning("Ignoring malformed cached task summary")
        fresh_invest_by_story = {result.story_id: result for result in fresh_invest}
        fresh_tasks_by_story = {result.story_id: result for result in fresh_tasks}
        missing_ids = {
            story["id"]
            for story in stories
            if (
                story["id"] not in fresh_invest_by_story and story["id"] not in cached_invest
            ) or (
                story["id"] not in fresh_tasks_by_story and story["id"] not in cached_tasks
            )
        }
        if missing_ids:
            fallback_stories = [story for story in stories if story["id"] in missing_ids]
            fallback_invest, fallback_tasks = await asyncio.gather(
                validate_invest(payload.requirement.id, fallback_stories),
                validate_task_sets(payload.requirement.text, fallback_stories),
            )
            fresh_invest_by_story.update({result.story_id: result for result in fallback_invest})
            fresh_tasks_by_story.update({result.story_id: result for result in fallback_tasks})
        invest = [fresh_invest_by_story.get(story["id"]) or cached_invest[story["id"]] for story in stories]
        tasks = [fresh_tasks_by_story.get(story["id"]) or cached_tasks[story["id"]] for story in stories]
        readiness, reason = _advisory_readiness(coverage, invest, tasks)
        return build_result(payload.requirement.id, coverage, invest, _invest_gate(invest), tasks, readiness, reason, [], ["coverage_analyzer", "invest_validator", "task_validator_batch", "deterministic_scorer"])
