"""task_validator tool — ONE LLM call that judges every task on four criteria
(relevance, scope, actionability, duplication) AND whether the task set as a
whole covers the story's main work, in the same structured response.

A single combined call (not a per-criterion or per-task loop, and not a
separate coverage pass) keeps this sub-agent at the same quota discipline
established for decomposition (see decomposition/scorer.py's module
docstring) — task validation has no separate taxonomy-extraction phase, so
one pass over the story + task list is enough context for both judgments.
"""

from __future__ import annotations

import logging
import re

from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.schemas import (
    TASK_CRITERIA,
    TaskCriterionOutcome,
    TaskCriterionResult,
    TaskSetCoverage,
    TaskValidationItem,
)

logger = logging.getLogger(__name__)

_VAGUE_TITLE_RE = re.compile(
    r"^(do|fix|handle|work on|improve|update|misc|stuff|todo)\b", re.IGNORECASE
)


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()


def detect_task_signals(tasks: list[dict]) -> dict[str, dict]:
    """Deterministic rule-based signals per task, fed to the LLM as evidence
    (and used directly as the LLM-unavailable fallback). Flags obviously
    vague titles and exact/near-duplicate titles among the submitted tasks."""
    normalized = [_normalize_title(t.get("title", "")) for t in tasks]
    counts: dict[str, int] = {}
    for n in normalized:
        if n:
            counts[n] = counts.get(n, 0) + 1

    signals: dict[str, dict] = {}
    for task, norm in zip(tasks, normalized, strict=True):
        tid = task.get("id", "")
        title = task.get("title", "")
        description = task.get("description", "")

        too_vague = len(title.strip()) < 6 or bool(_VAGUE_TITLE_RE.match(title.strip()))
        actionability = (
            {"signal": "fail", "note": "Title is too short or generic to act on — name a concrete action."}
            if too_vague
            else {"signal": "pass", "note": "Title names a concrete action."}
        )

        is_duplicate = norm and counts.get(norm, 0) > 1
        duplication = (
            {"signal": "fail", "note": "Matches another task's title almost exactly."}
            if is_duplicate
            else {"signal": "pass", "note": "No exact/near-duplicate title found among the submitted tasks."}
        )

        signals[tid] = {
            "relevance": {"signal": "pass", "note": "No rule-based signal available — relies on LLM judgment."},
            "scope": {"signal": "pass", "note": "No rule-based signal available — relies on LLM judgment."},
            "actionability": actionability,
            "duplication": duplication,
        }
        del description  # not used by the deterministic signals, kept for symmetry with invest.py's shape
    return signals


_TASK_VALIDATION_SYSTEM = """You are a task-breakdown validator for a university \
software-engineering course. You are given a user story and the development tasks a \
student wrote to implement it. You do NOT rewrite the student's tasks. Evaluate EACH \
task independently against four criteria, each with one of four results:
  - "Pass": fully satisfied.
  - "Needs Improvement": a minor issue you can name, but not disqualifying.
  - "Fail": not satisfied.
  - "Cannot Assess": you cannot determine the result from the available information.

Rubric (pass rule -> fail example):
  - Relevance: the task is actually needed to implement this story (and, when given, fits \
the parent requirement) -> fails on a task unrelated to the story's goal.
  - Scope: the task stays within the story's boundaries, not someone else's story or a \
different feature -> fails on a task that clearly belongs to unrelated functionality.
  - Actionability: the task names a concrete, startable unit of work a developer could pick \
up -> fails on a vague title like "Fix stuff" or "Handle edge cases" with no specifics.
  - Duplication: the task is not a near-duplicate of another task in the same list -> fails \
when two tasks describe the same work in different words (name the other task_id).

Then, looking at the task list AS A WHOLE, judge whether it covers the story's main \
work: identify any clearly missing piece of work the story needs that no task addresses \
(e.g. the story implies validation, an error case, or a UI step with no corresponding \
task). List each as a short, concrete phrase in missing_work_items (empty list if none). \
Give coverage_percentage as your estimate (0-100) of how much of the story's necessary \
work the task list addresses.

You are given each task (title + description) and deterministic rule signals already \
detected for it (actionability/duplication only - judge relevance and scope yourself). \
Use the signals as evidence but apply your own judgment.

Reply with a STRICT JSON object only (no markdown):
{
  "tasks": {
    "<task_id>": {
      "relevance": {"result": "Pass"|"Needs Improvement"|"Fail"|"Cannot Assess", "note": str, "evidence": str},
      "scope": {"result": "Pass"|"Needs Improvement"|"Fail"|"Cannot Assess", "note": str, "evidence": str},
      "actionability": {"result": "Pass"|"Needs Improvement"|"Fail"|"Cannot Assess", "note": str, "evidence": str},
      "duplication": {"result": "Pass"|"Needs Improvement"|"Fail"|"Cannot Assess", "note": str, "evidence": str}
    }
  },
  "coverage_percentage": 0-100,
  "missing_work_items": ["..."]
}"""

_READY_RESULTS = (TaskCriterionOutcome.PASS, TaskCriterionOutcome.NEEDS_IMPROVEMENT)


def _from_signal(signal: dict) -> TaskCriterionResult:
    return TaskCriterionResult(
        result=TaskCriterionOutcome.PASS if signal["signal"] == "pass" else TaskCriterionOutcome.FAIL,
        note=signal["note"],
    )


async def validate_tasks(
    story_ref: str, story_text: str, requirement_text: str, tasks: list[dict]
) -> tuple[list[TaskValidationItem], TaskSetCoverage, bool, str | None]:
    """Validate every task in ONE LLM call, covering both per-task criteria and
    set-level coverage. Falls back to rule signals + a conservative 0%
    coverage estimate when the LLM is unavailable or fails (never invents a
    passing coverage estimate without LLM judgment).

    Returns (items, coverage, analysis_failed, failure_reason) - callers must
    check analysis_failed before treating the coverage/items as a real
    finding, same guarantee as decomposition's CoverageAnalysis.analysis_failed."""
    if not tasks:
        return [], TaskSetCoverage(coverage_percentage=0.0, missing_work_items=[]), False, None

    signals_by_task = detect_task_signals(tasks)

    client = get_llm_client()
    raw: dict = {}
    llm_failed = False
    failure_reason: str | None = None
    if not client.configured:
        llm_failed = True
        failure_reason = "LLM unavailable — task validation could not be assessed."
    else:
        try:
            task_block = "\n\n".join(
                f'Task {t.get("id")}:\n'
                f'  Title: "{t.get("title", "")}"\n'
                f'  Description: "{t.get("description", "")}"\n'
                f"  Rule signals: "
                + "; ".join(
                    f"{k}={v['signal']}"
                    for k, v in signals_by_task[t.get("id", "")].items()
                    if k in ("actionability", "duplication")
                )
                for t in tasks
            )
            user_prompt = (
                f'User story ({story_ref}): "{story_text}"\n\n'
                + (f'Parent requirement context: "{requirement_text}"\n\n' if requirement_text else "")
                + f"Tasks to evaluate:\n\n{task_block}\n\n"
                "Return the JSON object exactly as specified."
            )
            max_tokens = min(3000, max(800, 300 * len(tasks)))
            raw = await client.complete_json(_TASK_VALIDATION_SYSTEM, user_prompt, max_tokens=max_tokens)
        except Exception:
            logger.exception(
                "LLM task validation failed for story %s (%d tasks); using rules", story_ref, len(tasks)
            )
            raw = {}
            llm_failed = True
            failure_reason = "Task validation failed — please re-run validation."

    llm_tasks = raw.get("tasks") if isinstance(raw, dict) else None
    llm_tasks = llm_tasks if isinstance(llm_tasks, dict) else {}

    results: list[TaskValidationItem] = []
    for task in tasks:
        tid = task.get("id", "")
        signals = signals_by_task[tid]
        task_llm = llm_tasks.get(tid)

        criteria: dict[str, TaskCriterionResult] = {}
        if task_llm:
            for c in TASK_CRITERIA:
                c_raw = task_llm.get(c, {}) or {}
                try:
                    result = TaskCriterionOutcome(c_raw.get("result"))
                except ValueError:
                    result = _from_signal(signals[c]).result
                criteria[c] = TaskCriterionResult(
                    result=result,
                    note=str(c_raw.get("note", signals[c]["note"])),
                    evidence=str(c_raw.get("evidence", "")),
                )
        else:
            criteria = {c: _from_signal(signals[c]) for c in TASK_CRITERIA}

        task_ready = all(criteria[c].result in _READY_RESULTS for c in TASK_CRITERIA)
        results.append(
            TaskValidationItem(task_id=tid, task_ready=task_ready, **criteria)
        )

    if llm_tasks:
        coverage_percentage = max(0.0, min(100.0, float(raw.get("coverage_percentage", 0.0) or 0.0)))
        missing_work_items = [str(x) for x in (raw.get("missing_work_items") or [])]
    else:
        # LLM unavailable/failed - never invent a passing coverage estimate.
        llm_failed = True
        failure_reason = failure_reason or "Task validation could not be completed."
        coverage_percentage = 0.0
        missing_work_items = []

    return (
        results,
        TaskSetCoverage(coverage_percentage=coverage_percentage, missing_work_items=missing_work_items),
        llm_failed,
        failure_reason,
    )
