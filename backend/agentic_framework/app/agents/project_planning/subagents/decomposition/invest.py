"""invest_validator tool — rule-based signals + LLM judgment for INVEST criteria.

Mirrors the frontend mock's deterministic regex signals (decompositionEngine.js)
and grounds an LLM call to produce per-story 6-criterion verdicts.
"""

from __future__ import annotations

import logging
import re

from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.schemas import (
    INVEST_CRITERIA,
    InvestCriterion,
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


def detect_invest_signals(title: str, ac: str) -> dict[str, dict]:
    """Deterministic rule-based signals for each INVEST criterion."""
    combined = f"{title} {ac}"

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

    testable = (
        {"signal": "pass", "note": "Acceptance criteria gives a concrete condition to verify."}
        if len(ac.strip()) >= 20
        else {"signal": "fail", "note": "Acceptance criteria is missing or too brief to verify."}
    )

    return {
        "independent": independent,
        "negotiable": negotiable,
        "valuable": valuable,
        "estimable": estimable,
        "small": small,
        "testable": testable,
    }


_INVEST_SYSTEM = """You are an INVEST criteria validator for user stories in a software-engineering course. \
You evaluate ONE user story against the six INVEST criteria (Independent, Negotiable, Valuable, Estimable, \
Small, Testable). You are rigorous and pedagogical.

You are given the story (title + acceptance criteria) and deterministic rule signals already detected. Use \
these signals as evidence but apply your own judgment — rules can have false positives/negatives.

Reply with a STRICT JSON object only (no markdown):
{
  "independent": {"passed": bool, "note": str},
  "negotiable": {"passed": bool, "note": str},
  "valuable": {"passed": bool, "note": str},
  "estimable": {"passed": bool, "note": str},
  "small": {"passed": bool, "note": str},
  "testable": {"passed": bool, "note": str}
}"""


async def validate_invest(stories: list[dict]) -> list[StoryInvest]:
    """Run INVEST validation on a list of stories. Uses LLM when available, falls back to rules."""
    client = get_llm_client()
    results: list[StoryInvest] = []

    for story in stories:
        sid = story.get("id", "")
        title = story.get("title", "")
        ac = story.get("acceptance_criteria", "")
        signals = detect_invest_signals(title, ac)

        if client.configured:
            try:
                signal_block = "\n".join(f"  - {k}: {v['signal']} — {v['note']}" for k, v in signals.items())
                user_prompt = (
                    f'Story title: """{title}"""\n'
                    f'Acceptance criteria: """{ac}"""\n\n'
                    f"Rule-based signals (use as evidence):\n{signal_block}\n\n"
                    "Return the JSON object exactly as specified."
                )
                llm_result = await client.complete_json(_INVEST_SYSTEM, user_prompt, max_tokens=600)
                criteria = {}
                for c in INVEST_CRITERIA:
                    raw = llm_result.get(c, {})
                    criteria[c] = InvestCriterion(
                        passed=bool(raw.get("passed", signals[c]["signal"] == "pass")),
                        note=str(raw.get("note", signals[c]["note"])),
                    )
                overall = all(criteria[c].passed for c in INVEST_CRITERIA)
                results.append(StoryInvest(story_id=sid, overall_pass=overall, **criteria))
                continue
            except Exception:
                logger.exception("LLM INVEST validation failed for %s; using rules", sid)

        criteria = {}
        for c in INVEST_CRITERIA:
            criteria[c] = InvestCriterion(
                passed=signals[c]["signal"] == "pass",
                note=signals[c]["note"],
            )
        overall = all(criteria[c].passed for c in INVEST_CRITERIA)
        results.append(StoryInvest(story_id=sid, overall_pass=overall, **criteria))

    return results
