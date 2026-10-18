"""invest_validator tool — rule-based signals + LLM judgment for a 4-state
per-criterion INVEST readiness verdict (Pass / Pass with note / Fail / Cannot Assess).

A story is ready for effort estimation only if all 6 criteria are Pass or
Pass with note (computed in Python from the LLM's per-criterion verdicts, never
trusted directly from the LLM, so the gate stays consistent with the rubric).
"""

from __future__ import annotations

import logging
import re

from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.schemas import (
    INVEST_CRITERIA,
    InvestCriterionResult,
    InvestResult,
    StoryInvest,
)

logger = logging.getLogger(__name__)

_DEPENDENCY_RE = re.compile(r"\b(after|once|depends on|requires that|only once|prerequisite)\b", re.IGNORECASE)
_IMPLEMENTATION_RE = re.compile(r"\b(api|endpoint|database|sql|react|button color|css|json payload|http)\b", re.IGNORECASE)
_ROLE_GOAL_RE = re.compile(r"as\s+(a|an|the)\s+.+i\s+want", re.IGNORECASE)
_BENEFIT_RE = re.compile(r"(so\s+that|in\s+order\s+to)\s+\S+", re.IGNORECASE)
_AMBIGUOUS_RE = re.compile(
    r"\b(various|some|several|many|few|appropriate|adequate|fast|efficient|user-friendly|easy|nice|good)\b", re.IGNORECASE
)


def detect_invest_signals(title: str, description: str) -> dict[str, dict]:
    """Deterministic rule-based signals for each INVEST criterion, fed to the LLM
    as evidence (and used directly as the LLM-unavailable fallback)."""
    combined = f"{title} {description}"

    independent = (
        {"signal": "fail", "note": "Wording implies dependency on another story."}
        if _DEPENDENCY_RE.search(combined)
        else {"signal": "pass", "note": "No hard dependency language found."}
    )

    negotiable = (
        {"signal": "fail", "note": "Locks in an implementation detail instead of describing the outcome."}
        if _IMPLEMENTATION_RE.search(combined)
        else {"signal": "pass", "note": "Describes the outcome, not a fixed implementation."}
    )

    has_role = bool(_ROLE_GOAL_RE.search(title))
    has_benefit = bool(_BENEFIT_RE.search(combined))
    valuable = (
        {"signal": "pass", "note": "States who wants this and why."}
        if has_role and has_benefit
        else {"signal": "fail", "note": "Missing a clear role/goal or a stated benefit."}
    )

    ambiguous = _AMBIGUOUS_RE.findall(combined)
    estimable = (
        {"signal": "fail", "note": f"Vague wording makes this hard to size: {', '.join(set(ambiguous))}."}
        if ambiguous
        else {"signal": "pass", "note": "Concrete enough to size with reasonable confidence."}
    )

    too_long = len(title) > 140 or bool(re.search(r"\band\b.*\band\b", title, re.IGNORECASE))
    small = (
        {"signal": "fail", "note": "Reads like more than one concern — consider splitting."}
        if too_long
        else {"signal": "pass", "note": "Scoped to a single unit of work."}
    )

    has_observable_outcome = bool(re.search(r"\b(can|able to|view|receive|create|update|delete|submit|display|store|send|access|download|upload|validate)\b", combined, re.IGNORECASE))
    testable = (
        {"signal": "pass", "note": "The story describes an observable behavior that can be verified."}
        if len(description.strip()) >= 20 and has_observable_outcome
        else {"signal": "fail", "note": "Describe a concrete, observable outcome so the story can be verified."}
    )

    return {
        "independent": independent,
        "negotiable": negotiable,
        "valuable": valuable,
        "estimable": estimable,
        "small": small,
        "testable": testable,
    }


_INVEST_SYSTEM = """You are an INVEST criteria validator for user stories in a software-engineering \
course. You will be given MULTIPLE stories in one request — evaluate EACH one independently against the \
six INVEST criteria. You are rigorous and pedagogical. Each criterion gets one of four results:
  - "Pass": fully satisfied.
  - "Pass with note": satisfied, but you see a minor improvement opportunity.
  - "Fail": not satisfied.
  - "Cannot Assess": you cannot determine the result from the available information.

Rubric (pass rule -> fail example):
  - Independent: the story can be implemented without requiring another unfinished story, except an \
explicitly declared and justified dependency -> fails on "After US-3 is finished, implement this" or an \
unclear dependency.
  - Negotiable: the story describes an outcome or need, not a fixed technical design -> fails on "Use \
MySQL triggers to update the inventory table".
  - Valuable: the story identifies a user, stakeholder, or system value -> fails on "As a developer, I \
want to create a database table" with no user value.
  - Estimable: the title and user story description contain enough information for a reasonable estimate -> \
fails on unclear scope or undefined rules.
  - Small: the story represents one coherent unit of work -> fails on a story covering registration, \
login, password reset, and profile management all at once.
  - Testable: the story description states observable behavior with a clear, verifiable outcome -> fails on \
"The system should work well". Do not require acceptance criteria; they are intentionally absent.

You are given each story (title + user story description) and deterministic rule signals already detected \
for it. Use these signals as evidence but apply your own judgment — rules can have false positives/negatives.

Reply with a STRICT JSON object only (no markdown), one entry per story_id exactly as given:
{
  "<story_id>": {
    "independent": {"result": "Pass"|"Pass with note"|"Fail"|"Cannot Assess", "note": str, "evidence": str},
    "negotiable": {"result": "Pass"|"Pass with note"|"Fail"|"Cannot Assess", "note": str, "evidence": str},
    "valuable": {"result": "Pass"|"Pass with note"|"Fail"|"Cannot Assess", "note": str, "evidence": str},
    "estimable": {"result": "Pass"|"Pass with note"|"Fail"|"Cannot Assess", "note": str, "evidence": str},
    "small": {"result": "Pass"|"Pass with note"|"Fail"|"Cannot Assess", "note": str, "evidence": str},
    "testable": {"result": "Pass"|"Pass with note"|"Fail"|"Cannot Assess", "note": str, "evidence": str}
  }
}"""

_READY_RESULTS = (InvestResult.PASS, InvestResult.PASS_WITH_NOTE)


def _from_signal(signal: dict) -> InvestCriterionResult:
    return InvestCriterionResult(
        result=InvestResult.PASS if signal["signal"] == "pass" else InvestResult.FAIL,
        note=signal["note"],
    )


async def validate_invest(
    requirement_id: str, stories: list[dict]
) -> list[StoryInvest]:
    """Run INVEST validation on ALL stories in ONE LLM call (not one call per
    story — each requirement.analyze_decomposition run already makes a
    coverage_analyzer call, so a per-story loop here was the dominant source
    of API quota usage). Falls back to rule signals only when the LLM is
    unavailable or fails (never invents Pass with note / Cannot Assess
    without LLM judgment, since those require nuance a regex can't provide)."""
    if not stories:
        return []

    signals_by_story = {
        s.get("id", ""): detect_invest_signals(s.get("title", ""), s.get("description", ""))
        for s in stories
    }

    client = get_llm_client()
    llm_results: dict = {}
    if client.configured:
        try:
            story_block = "\n\n".join(
                f'Story {s.get("id")}:\n'
                f'  Title: "{s.get("title", "")}"\n'
                f'  User story description: "{s.get("description", "")}"\n'
                f"  Rule signals: "
                + "; ".join(f"{k}={v['signal']}" for k, v in signals_by_story[s.get("id", "")].items())
                for s in stories
            )
            user_prompt = (
                f"Stories to evaluate:\n\n{story_block}\n\n"
                "Return the JSON object exactly as specified, with one entry per story_id."
            )
            # A compact per-criterion verdict is sufficient for the UI. Keep
            # one batched request small to reduce provider load and latency.
            max_tokens = min(1800, max(600, 260 * len(stories)))
            llm_results = await client.complete_json(_INVEST_SYSTEM, user_prompt, max_tokens=max_tokens)
        except Exception:
            logger.exception(
                "LLM INVEST validation failed for batch of %d stories; using rules", len(stories)
            )
            llm_results = {}

    results: list[StoryInvest] = []
    for story in stories:
        sid = story.get("id", "")
        title = story.get("title", "")
        description = story.get("description", "")
        signals = signals_by_story[sid]
        story_llm = llm_results.get(sid) if isinstance(llm_results, dict) else None

        criteria: dict[str, InvestCriterionResult] = {}
        if story_llm:
            for c in INVEST_CRITERIA:
                raw = story_llm.get(c, {}) or {}
                try:
                    result = InvestResult(raw.get("result"))
                except ValueError:
                    result = _from_signal(signals[c]).result
                criteria[c] = InvestCriterionResult(
                    result=result,
                    note=str(raw.get("note", signals[c]["note"])),
                    evidence=str(raw.get("evidence", "")),
                )
        else:
            criteria = {c: _from_signal(signals[c]) for c in INVEST_CRITERIA}

        story_ready = all(criteria[c].result in _READY_RESULTS for c in INVEST_CRITERIA)
        results.append(
            StoryInvest(
                story_id=sid,
                story_text=f"{title} {description}".strip(),
                linked_parent_requirement=story.get("linked_parent_requirement", requirement_id),
                story_ready=story_ready,
                **criteria,
            )
        )

    return results
