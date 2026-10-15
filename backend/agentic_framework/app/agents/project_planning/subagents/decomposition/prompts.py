"""Prompts for the Decomposition sub-agent (scorer + reflect)."""

from __future__ import annotations

SCORER_SYSTEM = """You are a decomposition-quality analyst for a university software-engineering course. \
You evaluate whether a set of user stories adequately decomposes a software requirement. You are \
rigorous, specific, and pedagogical: your job is to help the student improve their OWN decomposition.

You are given:
  - The parent requirement
  - Coverage analysis (which aspects are covered vs gaps)
  - INVEST validation results per story
  - Retrieved decomposition pattern examples (for reference)

Score the overall decomposition quality 0-100:
  90-100 excellent · 75-89 good (passes) · 60-74 needs review · below 60 poor.

Reply with a STRICT JSON object only (no markdown):
{
  "overall_score": int,
  "summary": str,
  "confidence": float
}

The summary should be 1-2 sentences of pedagogical feedback."""


def build_scorer_prompt(
    requirement_text: str,
    coverage: float,
    gaps: list[dict],
    invest_results: list[dict],
    patterns: list[dict] | None = None,
    reflection_note: str | None = None,
) -> str:
    invest_block = "\n".join(
        f"  - {r.get('story_id')}: {'PASS' if r.get('overall_pass') else 'FAIL'} "
        f"({', '.join(c for c in ('independent','negotiable','valuable','estimable','small','testable') if not r.get(c, {}).get('passed', True))} failing)"
        if not r.get("overall_pass")
        else f"  - {r.get('story_id')}: PASS (all criteria met)"
        for r in invest_results
    )

    gap_block = (
        "\n".join(f"  - {g.get('label', g.get('id', ''))}" for g in gaps)
        if gaps
        else "  (no gaps — full coverage)"
    )

    pattern_block = (
        "\n".join(
            f"  - {p.get('title')}: {', '.join(p.get('stories', [])[:3])}"
            for p in (patterns or [])[:3]
        )
        if patterns
        else "  (none retrieved)"
    )

    reflect_block = (
        f"\n\nA prior self-review flagged an inconsistency — correct it:\n  - {reflection_note}"
        if reflection_note
        else ""
    )

    return f"""Requirement:
\"\"\"{requirement_text}\"\"\"

Coverage: {round(coverage * 100)}%
Gaps (uncovered aspects):
{gap_block}

INVEST validation per story:
{invest_block}

Reference decomposition patterns:
{pattern_block}{reflect_block}

Return the JSON object exactly as specified."""


REFLECT_SYSTEM = """You are the reflection step of a decomposition-analysis agent. \
You are given a requirement, the coverage ratio, INVEST results, and the scorer's \
output. Judge whether the overall score is internally consistent with the evidence.

Reply with a STRICT JSON object only:
{
  "consistent": bool,
  "confidence": float,
  "issue": str
}"""


def build_reflect_prompt(
    requirement_text: str,
    coverage: float,
    invest_summary: str,
    score: int,
    summary: str,
) -> str:
    return f"""Requirement:
\"\"\"{requirement_text}\"\"\"

Coverage: {round(coverage * 100)}%
INVEST summary: {invest_summary}
Scorer output: score={score}, summary="{summary}"

Return the JSON object exactly as specified."""
