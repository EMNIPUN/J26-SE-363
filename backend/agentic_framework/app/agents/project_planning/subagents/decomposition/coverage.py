"""coverage_analyzer tool — extract the coverage-element matrix from the parent
requirement and evaluate the coverage-gate checks (C1-C10).

C1 (parent linkage), C6 (no orphan stories) and C9 (no out-of-scope behavior) are
computed deterministically in Python from the coverage matrix the LLM returns;
C2-C5/C7/C8 are judgment calls made in the SAME LLM pass (splitting them into
separate calls would add cost/latency with no extra grounding, since they all
reason over the same matrix).
"""

from __future__ import annotations

import logging

from app.agents.project_planning.llm import get_llm_client
from app.agents.project_planning.schemas import (
    CheckResult,
    CoverageAnalysis,
    CoverageCheck,
    CoverageElement,
    CoverageElementType,
    CoverageGateResult,
    CoverageResult,
)

logger = logging.getLogger(__name__)

_JUDGMENT_CHECKS = ("C2", "C3", "C4", "C5", "C7", "C8", "C10")
_ALL_CHECKS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10")
_ELEMENT_TYPES = ", ".join(t.value for t in CoverageElementType)

_COVERAGE_SYSTEM = f"""You are a requirements-decomposition analyst for a university \
software-engineering course. You evaluate whether a student's user stories cover a \
parent software requirement — you do NOT rewrite the student's stories.

Step 1 — Extract coverage elements from the parent requirement using this taxonomy: \
{_ELEMENT_TYPES}. A requirement typically has 3-10 elements. Each element is one \
discrete, testable piece of the requirement (an actor, a trigger, a precondition, \
the main action, an input, an output, a business rule, a constraint, a permission \
rule, an exception/error/recovery behavior, or a quality constraint).

Step 2 — For each element, decide which student stories (by story_id) cover it, by \
reading each story's title, user story description, and acceptance criteria. An element is "Covered" only if \
at least one story clearly addresses it; otherwise it is "Missing". An element may be \
covered by more than one story.

Step 3 — Using the coverage matrix you just built, evaluate these checks and give a \
rationale with evidence (element_ids and/or story_ids) for every result. When a check \
Fails, also give a concrete "suggestion": one sentence telling the student exactly what \
to add or change, with a short concrete example (not just "add more detail") — this \
feedback is shown directly to the student to help them improve, not to block them:
  - C2 functional_coverage: every functional behavior in the requirement is represented in at least one story.
  - C3 data_coverage: all required inputs, outputs, data fields and data rules are covered.
  - C4 condition_coverage: all triggers, preconditions, business rules, constraints and permissions are covered.
  - C5 exception_coverage: all defined error, failure, alternative, boundary and recovery behaviors are covered.
  - C7 no_duplicate_scope: stories do not substantially overlap or repeat the same behavior (list any overlapping element_ids in duplicate_elements).
  - C8 no_scope_loss: no necessary part of the requirement was omitted.
  - C10 acceptance_traceability: every material story behavior has at least one specific,
    relevant, and verifiable acceptance criterion. Fail for missing or vague criteria.

Step 4 — List any story_id that introduces behavior unrelated to this requirement in \
out_of_scope_stories.

Step 5 — Set needs_review=true ONLY when you cannot reliably judge coverage because \
the requirement references an external document, business rule, or domain constraint \
that is not available to you — give needs_review_reason. Do not use needs_review for \
ordinary missing coverage; that is a normal Fail, not a review case.

Reply with a STRICT JSON object only (no markdown):
{{
  "elements": [
    {{"element_id": "E1", "element_type": "<one of the taxonomy types>", "description": "...",
      "required": true, "covered_by": ["US-1"], "coverage_result": "Covered"|"Missing", "evidence": "..."}}
  ],
  "checks": {{
    "C2": {{"result": "Pass"|"Fail", "rationale": "...", "evidence": ["E1"], "suggestion": "..."}},
    "C3": {{"result": "Pass"|"Fail", "rationale": "...", "evidence": [], "suggestion": "..."}},
    "C4": {{"result": "Pass"|"Fail", "rationale": "...", "evidence": [], "suggestion": "..."}},
    "C5": {{"result": "Pass"|"Fail", "rationale": "...", "evidence": [], "suggestion": "..."}},
    "C7": {{"result": "Pass"|"Fail", "rationale": "...", "evidence": [], "suggestion": "..."}},
    "C8": {{"result": "Pass"|"Fail", "rationale": "...", "evidence": [], "suggestion": "..."}},
    "C10": {{"result": "Pass"|"Fail", "rationale": "...", "evidence": ["US-1"], "suggestion": "..."}}
  }},
  "duplicate_elements": ["E3"],
  "out_of_scope_stories": ["US-4"],
  "needs_review": false,
  "needs_review_reason": null
}}
"suggestion" is only required when result is "Fail"; use "" when Pass."""


def _unavailable_analysis(reason: str) -> CoverageAnalysis:
    """Deterministic, safe-to-fail state: never falsely reports completion."""
    checks = {
        cid: CoverageCheck(check_id=cid, result=CheckResult.FAIL, rationale=reason)
        for cid in _ALL_CHECKS
    }
    return CoverageAnalysis(
        elements=[],
        coverage_percentage=0.0,
        gate=CoverageGateResult(checks=checks, passed=False),
        needs_review=False,
        analysis_failed=True,
        failure_reason=reason,
    )


async def analyze_coverage(
    requirement_id: str,
    requirement_text: str,
    stories: list[dict],
) -> CoverageAnalysis:
    """Extract the coverage matrix and evaluate the coverage-gate checks (C1-C10)."""
    client = get_llm_client()
    story_ids = [s.get("id", "") for s in stories]

    if not client.configured:
        return _unavailable_analysis("LLM unavailable — coverage could not be assessed.")

    story_block = "\n".join(
        f'- {s.get("id")}: "{s.get("title", "")}" | Description: "{s.get("description", "")}" '
        f'| Acceptance criteria: {"; ".join(s.get("acceptance_criteria") or []) or "(none)"}'
        for s in stories
    )
    user_prompt = (
        f'Parent requirement (id={requirement_id}):\n"""{requirement_text}"""\n\n'
        f"Student stories:\n{story_block or '(no stories submitted)'}\n\n"
        "Return the JSON object exactly as specified."
    )

    try:
        raw = await client.complete_json(_COVERAGE_SYSTEM, user_prompt, max_tokens=1800)
    except Exception:
        logger.exception("coverage_analyzer LLM call failed for %s", requirement_id)
        return _unavailable_analysis("Coverage analysis failed — please re-run analysis.")

    elements: list[CoverageElement] = []
    for idx, el in enumerate(raw.get("elements", []) or []):
        try:
            element_type = CoverageElementType(el.get("element_type"))
        except ValueError:
            element_type = CoverageElementType.MAIN_ACTION
        covered_by = [sid for sid in el.get("covered_by", []) or [] if sid in story_ids]
        elements.append(
            CoverageElement(
                element_id=str(el.get("element_id") or f"E{idx + 1}"),
                element_type=element_type,
                description=str(el.get("description", "")),
                required=bool(el.get("required", True)),
                covered_by=covered_by,
                coverage_result=(
                    CoverageResult.COVERED if covered_by else CoverageResult.MISSING
                ),
                evidence=str(el.get("evidence", "")),
            )
        )

    required_elements = [e for e in elements if e.required] or elements
    covered_count = sum(
        1 for e in required_elements if e.coverage_result == CoverageResult.COVERED
    )
    coverage_percentage = round(
        (covered_count / len(required_elements) * 100) if required_elements else 0.0, 2
    )

    duplicate_elements = [str(x) for x in (raw.get("duplicate_elements") or [])]
    llm_out_of_scope = {
        str(x) for x in (raw.get("out_of_scope_stories") or []) if str(x) in story_ids
    }

    # C1 — parent linkage (deterministic, structural).
    unlinked = [
        s.get("id", "") for s in stories
        if s.get("linked_parent_requirement") != requirement_id
    ]
    checks: dict[str, CoverageCheck] = {
        "C1": CoverageCheck(
            check_id="C1",
            result=CheckResult.FAIL if unlinked else CheckResult.PASS,
            rationale=(
                f"Story(ies) not linked to {requirement_id}: {', '.join(unlinked)}"
                if unlinked
                else "Every story links to the parent requirement."
            ),
            evidence=unlinked,
            suggestion=(
                f"Set each story's parent requirement to {requirement_id} "
                f"(currently missing on {', '.join(unlinked)})."
                if unlinked
                else ""
            ),
        )
    }

    # C2-C5/C7/C8/C10 — LLM judgment over the shared coverage matrix.
    checks_raw = raw.get("checks", {}) or {}
    for check_id in _JUDGMENT_CHECKS:
        c = checks_raw.get(check_id, {}) or {}
        try:
            result = CheckResult(c.get("result", "Fail"))
        except ValueError:
            result = CheckResult.FAIL
        checks[check_id] = CoverageCheck(
            check_id=check_id,
            result=result,
            rationale=str(c.get("rationale", "")),
            evidence=[str(x) for x in (c.get("evidence") or [])],
            suggestion=str(c.get("suggestion", "")) if result == CheckResult.FAIL else "",
        )

    # C6 — no orphan stories (deterministic): every story must cover >=1 element.
    covering_story_ids = {sid for e in elements for sid in e.covered_by}
    orphan_stories = [sid for sid in story_ids if sid not in covering_story_ids]
    checks["C6"] = CoverageCheck(
        check_id="C6",
        result=CheckResult.FAIL if orphan_stories else CheckResult.PASS,
        rationale=(
            f"Orphan stor{'y' if len(orphan_stories) == 1 else 'ies'} with no "
            f"linked coverage element: {', '.join(orphan_stories)}"
            if orphan_stories
            else "Every story traces back to the parent requirement via at least one element."
        ),
        evidence=orphan_stories,
        suggestion=(
            f"Revise {', '.join(orphan_stories)} so its title/description "
            "clearly maps to a specific behavior in the parent requirement "
            "(e.g. the trigger, action, or output it names)."
            if orphan_stories
            else ""
        ),
    )

    # C10 is evaluated above because it needs the acceptance-criteria text;
    # C1/C6 still deterministically enforce structural traceability.

    # C9 — no out-of-scope behavior: cross-check the LLM's judgment against the
    # Python-computed orphan set. A disagreement is treated as Fail and both
    # signals are surfaced — never silently resolved in either direction.
    out_of_scope_signal = sorted(set(orphan_stories) | llm_out_of_scope)
    checks["C9"] = CoverageCheck(
        check_id="C9",
        result=CheckResult.FAIL if out_of_scope_signal else CheckResult.PASS,
        rationale=(
            "Potential out-of-scope or unlinked "
            f"stor{'y' if len(out_of_scope_signal) == 1 else 'ies'}: "
            f"{', '.join(out_of_scope_signal)}"
            if out_of_scope_signal
            else "No out-of-scope behavior detected."
        ),
        evidence=out_of_scope_signal,
        suggestion=(
            f"Check whether {', '.join(out_of_scope_signal)} actually belongs "
            "to this requirement, or move it under the requirement it really "
            "describes."
            if out_of_scope_signal
            else ""
        ),
    )

    gate_passed = all(c.result == CheckResult.PASS for c in checks.values())

    return CoverageAnalysis(
        elements=elements,
        coverage_percentage=coverage_percentage,
        gate=CoverageGateResult(
            checks=checks,
            passed=gate_passed,
            duplicate_elements=duplicate_elements,
            orphan_stories=orphan_stories,
            out_of_scope_stories=sorted(llm_out_of_scope),
        ),
        needs_review=bool(raw.get("needs_review", False)),
        needs_review_reason=raw.get("needs_review_reason"),
    )
