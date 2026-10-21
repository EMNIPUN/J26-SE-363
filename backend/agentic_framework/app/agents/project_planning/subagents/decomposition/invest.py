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
    AcceptanceCriteriaReadiness,
    StoryInvest,
)

logger = logging.getLogger(__name__)

_DEPENDENCY_RE = re.compile(
    r"\b(depends on|requires that|only once|prerequisite|after\s+(?:completing|finishing|the\s+\w+\s+(?:is|has)))\b",
    re.IGNORECASE,
)
_IMPLEMENTATION_RE = re.compile(r"\b(api|endpoint|database|sql|react|button color|css|json payload|http)\b", re.IGNORECASE)
_ROLE_GOAL_RE = re.compile(r"as\s+(a|an|the)\s+.+i\s+want", re.IGNORECASE)
_BENEFIT_RE = re.compile(r"(so\s+that|in\s+order\s+to)\s+\S+", re.IGNORECASE)
_AMBIGUOUS_RE = re.compile(
    r"\b(various|some|several|many|few|appropriate|adequate|fast|efficient|user-friendly|easy|nice|good)\b", re.IGNORECASE
)
_NFR_CONTEXT_RE = re.compile(
    r"\b(security|secure|performance|compliance|encryption|encrypted|hashing|backup|"
    r"availability|latency|throughput|reliability|scalability|disaster recovery|failover|"
    r"response time|uptime|authentication|authorization|"
    r"accessibility|usability|user interface|ui|ux|wcag|aria|screen reader)\b",
    re.IGNORECASE,
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

    impl_match = _IMPLEMENTATION_RE.search(combined)
    nfr_context = _NFR_CONTEXT_RE.search(combined) if impl_match else None
    negotiable = (
        {"signal": "fail", "note": "Locks in an implementation detail instead of describing the outcome."}
        if impl_match and not nfr_context
        else {"signal": "pass", "note": (
            "Technical terms appear in a non-functional requirement context — not an implementation lock-in."
            if impl_match and nfr_context
            else "Describes the outcome, not a fixed implementation."
        )}
    )

    has_role = bool(_ROLE_GOAL_RE.search(combined))
    has_benefit = bool(_BENEFIT_RE.search(combined))
    valuable = (
        {"signal": "pass", "note": "States who wants this and why."}
        if has_role and has_benefit
        else {"signal": "fail", "note": "Missing a clear role/goal or a stated benefit."}
    )

    ambiguous = _AMBIGUOUS_RE.findall(combined)
    nfr_in_estimable = _NFR_CONTEXT_RE.search(combined) if ambiguous else None
    if ambiguous and not nfr_in_estimable:
        estimable = {"signal": "fail", "note": f"Vague wording makes this hard to size: {', '.join(set(ambiguous))}. Replace with measurable terms (e.g., 'within 3 seconds' instead of 'fast', 'at most 5 fields' instead of 'few')."}
    elif ambiguous and nfr_in_estimable:
        estimable = {"signal": "pass", "note": f"Vague terms ({', '.join(set(ambiguous))}) appear in an NFR context — consider adding measurable thresholds."}
    else:
        estimable = {"signal": "pass", "note": "Concrete enough to size with reasonable confidence."}

    too_long = len(title) > 140 or bool(re.search(r"\band\b.*\band\b", title, re.IGNORECASE))
    small = (
        {"signal": "fail", "note": "Reads like more than one concern — consider splitting."}
        if too_long
        else {"signal": "pass", "note": "Scoped to a single unit of work."}
    )

    has_observable_outcome = bool(re.search(r"\b(can|able to|view|receive|create|update|delete|submit|display|store|send|access|download|upload|validate)\b", combined, re.IGNORECASE))
    if len(description.strip()) >= 20 and has_observable_outcome:
        testable = {"signal": "pass", "note": "The story describes an observable behavior that can be verified."}
    elif len(description.strip()) < 20:
        testable = {"signal": "fail", "note": "Description is too brief — add at least one observable outcome (e.g., 'user can view…', 'system displays…', 'error message is shown')."}
    else:
        testable = {"signal": "fail", "note": "Name a specific observable outcome verb (e.g., 'user can view…', 'system displays…', 'data is stored…') so a tester can verify pass/fail."}

    return {
        "independent": independent,
        "negotiable": negotiable,
        "valuable": valuable,
        "estimable": estimable,
        "small": small,
        "testable": testable,
    }


def has_bounded_calculation_contract(acceptance_criteria: list[str]) -> bool:
    """Recognise a small, directly-testable calculation story.

    An LLM must not mistake normal valid-input, invalid-input, and rounding
    scenarios for separate product outcomes. This guardrail deliberately has a
    narrow shape: a named calculation with its inputs, a numeric oracle, and
    an observable result. Other story types remain subject to normal review.
    """
    text = " ".join(acceptance_criteria).lower()
    if not 2 <= len(acceptance_criteria) <= 7:
        return False

    has_calculation = bool(re.search(r"\b(calculate|calculation|formula)\b", text))
    has_named_inputs = sum(
        name in text
        for name in ("total_minutes", "maintenance_minutes", "unavailable_minutes")
    ) >= 2
    has_numeric_oracle = bool(re.search(r"\b\d+(?:[,.]\d+)?\s*%", text))
    has_observable_result = bool(re.search(r"\b(return|display|reject|validation error)\b", text))
    return has_calculation and has_named_inputs and has_numeric_oracle and has_observable_result


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
MySQL triggers to update the inventory table". A non-functional requirement specifying a security \
standard (e.g. "computationally expensive password hashing"), performance target, compliance rule, or \
availability constraint describes a legitimate need, not a fixed technical design. Fail Negotiable \
only when the story prescribes a specific library, framework, SQL dialect, or UI technology rather \
than describing a desired security/performance outcome.
  - Valuable: the story identifies a user, stakeholder, or system value -> fails on "As a developer, I \
want to create a database table" with no user value.
  - Estimable: the title, description, and acceptance criteria contain enough information for a reasonable estimate -> \
fails on unclear scope, undefined rules, or missing criteria. Do NOT require a student to specify an
internal architecture, monitoring vendor, database, or implementation task when the story gives a
bounded input, outcome, and business rule. A clearly stated calculation formula and named inputs are
normally enough to estimate a calculation story.
  - Small: the story represents one coherent unit of work -> fails on a story covering registration, \
Do NOT fail Small merely because acceptance criteria include normal success, boundary, and error
scenarios for the same outcome. Calculating, rounding, and returning one value is one coherent outcome;
collecting data, calculating it, displaying a dashboard, and sending alerts are separate outcomes.
  - Testable: the story and its acceptance criteria state observable behavior with a clear, verifiable outcome -> fails on \
"The system should work well" or criteria that cannot establish pass/fail. Multiple Given/When/Then
examples and a formula with named inputs make a story MORE testable, not less testable.

Also assess acceptance_criteria_readiness: criteria must be specific, observable, verifiable,
relevant to the story, and sufficient to test its material behavior.

Scope-calibration rules (apply these before assigning any Fail):
  1. First identify the story's PRIMARY user outcome. Evaluate the scope of that outcome, not the
     number of acceptance-criteria lines.
  2. Treat success, boundary, validation, error, permission, empty-result, formatting, rounding,
     and retry scenarios as tests of ONE outcome when they all support the same capability. They do
     not make a story non-small merely because there are several scenarios.
  3. Mark Small as Fail only when the story contains two or more independently usable outcomes that
     could be delivered separately. Examples: account registration PLUS sign-in; search PLUS saved
     favourites; calculate a report PLUS configure alerts. Do not fail because a single form validates
     input, a search handles no results, a calculation rejects invalid values, or a secure action has
     an authorization-denied case.
  4. Mark Estimable as Pass or Pass with note when the story gives a bounded behavior, the relevant
     inputs or preconditions, and a visible outcome or business rule. Do not require technical design
     details. This applies equally to functional, reporting, calculation, availability, security,
     performance, and usability requirements.
  5. Mark Testable and acceptance_criteria_readiness as Pass or Pass with note when a tester can set
     up the stated condition, perform the stated action, and observe the expected result. A concrete
     example, threshold, returned value, displayed state, error, or access decision is a valid oracle.
  6. A non-functional target is not automatically too large. Treat it as a small story when it is
     bounded to one measurable capability, timeframe, component, or decision; fail only if it mixes
     separate capabilities such as monitoring collection, calculation, dashboard display, alerting,
     and remediation in the same story.

Student-feedback rules:
  - Do not use generic statements such as "the criteria are complex" or "add more detail".
  - A failure must quote or precisely identify one missing or conflicting piece of information.
  - Give one smallest next step the student can complete. If the best action is to split the story,
    name the single outcome that should stay in this story and name the outcome that should move.
  - Never recommend splitting a story solely because it contains several acceptance scenarios. State
    the two independently valuable outcomes that justify a split; if you cannot name them, do not
    fail Small.
  - Never say that testing is unclear when the criteria already provide a setup, action, and observable
    expected result. If a testability gap remains, name the exact missing expected result or boundary.
  - Do not fail both acceptance-criteria readiness and Testable for the same well-defined scenario
    solely because it has more than one acceptance criterion.

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
    "testable": {"result": "Pass"|"Pass with note"|"Fail"|"Cannot Assess", "note": str, "evidence": str},
    "acceptance_criteria_readiness": {"result": "Pass"|"Pass with note"|"Fail"|"Cannot Assess", "issues": [str], "evidence": [str], "suggestion": str}
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
                f'  Acceptance criteria: {"; ".join(s.get("acceptance_criteria") or []) or "(none)"}\n'
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
            max_tokens = min(3000, max(600, 260 * len(stories)))
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

        ac_raw = (story_llm or {}).get("acceptance_criteria_readiness", {}) or {}
        try:
            ac_result = InvestResult(ac_raw.get("result"))
        except ValueError:
            # Conservative deterministic fallback: criteria are indispensable
            # for estimate/test readiness, but do not invent a passing result.
            ac_result = InvestResult.CANNOT_ASSESS if story.get("acceptance_criteria") else InvestResult.FAIL
        acceptance = AcceptanceCriteriaReadiness(
            result=ac_result,
            criteria_count=len(story.get("acceptance_criteria") or []),
            issues=[str(x) for x in (ac_raw.get("issues") or [])],
            evidence=[str(x) for x in (ac_raw.get("evidence") or [])],
            suggestion=str(ac_raw.get("suggestion", "")),
        )
        if not story_llm and not acceptance.issues:
            acceptance.issues = (["No acceptance criteria were supplied."] if not acceptance.criteria_count else ["Acceptance criteria could not be assessed because the LLM was unavailable."])
            acceptance.suggestion = "Add observable Given/When/Then or measurable pass/fail criteria for this story."

        # A calculation with named inputs, a numeric expected result, and
        # observable success/error behavior is estimable and testable. Its
        # validation and rounding scenarios are part of the same calculation
        # outcome, so they do not make the story too large.
        if has_bounded_calculation_contract(story.get("acceptance_criteria") or []):
            acceptance = AcceptanceCriteriaReadiness(
                result=InvestResult.PASS_WITH_NOTE,
                criteria_count=len(story.get("acceptance_criteria") or []),
                issues=[],
                evidence=["Named calculation inputs, expected numeric result, and observable success/error outcomes are present."],
                suggestion="Optionally use one complete Given/When/Then line per scenario for readability.",
            )
            for criterion in ("estimable", "small", "testable"):
                if criteria[criterion].result not in _READY_RESULTS:
                    criteria[criterion] = InvestCriterionResult(
                        result=InvestResult.PASS_WITH_NOTE,
                        note="The bounded calculation and its validation scenarios form one estimable, testable outcome.",
                        evidence="Inputs, formula, numeric expected result, and validation behavior are defined.",
                    )

        # Weak criteria directly make estimate and test confidence weak.
        # The "[AC-derived]" prefix lets build_feedback skip these when the AC
        # readiness failure is already reported, avoiding redundant feedback.
        if acceptance.result not in _READY_RESULTS:
            for criterion in ("estimable", "testable"):
                if criteria[criterion].result in _READY_RESULTS:
                    criteria[criterion] = InvestCriterionResult(
                        result=InvestResult.PASS_WITH_NOTE,
                        note="[AC-derived] Estimability depends on acceptance criteria, which need improvement.",
                        evidence="; ".join(acceptance.evidence),
                    )

        story_ready = all(criteria[c].result in _READY_RESULTS for c in INVEST_CRITERIA) and acceptance.result in _READY_RESULTS
        results.append(
            StoryInvest(
                story_id=sid,
                story_text=f"{title} {description}".strip(),
                linked_parent_requirement=story.get("linked_parent_requirement", requirement_id),
                story_ready=story_ready,
                acceptance_criteria_readiness=acceptance,
                **criteria,
            )
        )

    return results
