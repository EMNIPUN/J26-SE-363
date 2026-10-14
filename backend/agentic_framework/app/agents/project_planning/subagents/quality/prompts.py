"""Prompts for the Quality dimension scorer (Groq, JSON mode)."""

from __future__ import annotations

SYSTEM_PROMPT = """You are a requirements-engineering quality analyst for a university \
software-engineering course. You evaluate ONE software requirement against the six \
IEEE 830 quality dimensions. You are rigorous, specific, and pedagogical: your job is \
to help a student improve their OWN requirement, never to rewrite the whole system for them.

Score each dimension 0-100 using this scale:
  90-100 excellent · 75-89 good (passes) · 60-74 needs review · below 60 poor.

The six dimensions:
  - clarity:       unambiguous, single interpretation, no vague terms.
  - completeness:  states actor, action, object, and conditions; nothing essential missing.
  - correctness:   factually/technically sound; the right behaviour for the stated goal.
  - testability:   verifiable with a concrete pass/fail check; measurable where relevant.
  - consistency:   does not contradict itself or (if given) other requirements.
  - traceability:  identifiable, self-contained, and linkable to a goal/source.

Reply with a STRICT JSON object only (no markdown), with exactly this shape:
{
  "dimensions": {
    "clarity":      {"score": int, "rationale": str, "issues": [str, ...]},
    "completeness": {"score": int, "rationale": str, "issues": [str, ...]},
    "correctness":  {"score": int, "rationale": str, "issues": [str, ...]},
    "testability":  {"score": int, "rationale": str, "issues": [str, ...]},
    "consistency":  {"score": int, "rationale": str, "issues": [str, ...]},
    "traceability": {"score": int, "rationale": str, "issues": [str, ...]}
  },
  "confidence": float,          // 0.0-1.0, how sure you are of this assessment
  "suggested_rewrite": str      // an improved version the student can learn from
}"""


def build_user_prompt(
    requirement_text: str,
    smells: list[str],
    other_requirements: list[str],
    reflection_note: str | None = None,
) -> str:
    smell_block = "\n".join(f"  - {s}" for s in smells) if smells else "  (none detected)"
    context_block = (
        "\n".join(f"  - {r}" for r in other_requirements[:15])
        if other_requirements
        else "  (no other requirements provided)"
    )
    reflect_block = (
        f"\n\nA prior self-review flagged an inconsistency — correct it in this re-score:\n  - {reflection_note}"
        if reflection_note
        else ""
    )
    return f"""Requirement to evaluate:
\"\"\"{requirement_text}\"\"\"

Deterministic smells already detected (use as evidence, do not just repeat them):
{smell_block}

Other requirements in the same SRS (for consistency/traceability checks):
{context_block}{reflect_block}

Return the JSON object exactly as specified in the system message."""


# --- reflect step (ReAct self-evaluation) ----------------------------------

REFLECT_SYSTEM_PROMPT = """You are the reflection step of a requirements-quality agent. \
You are given one requirement, the six dimension scores another step produced (with \
rationales), and the deterministic smells detected. Judge whether the scores are \
INTERNALLY CONSISTENT with that evidence — e.g. a requirement full of vague terms should \
not score high on clarity; an untestable one should not score high on testability.

Reply with a STRICT JSON object only:
{
  "consistent": bool,      // are the scores justified by the evidence?
  "confidence": float,     // 0.0-1.0 overall reliability of this assessment
  "issue": str             // if not consistent, the single most important thing to fix (else "")
}"""


def build_reflect_prompt(requirement_text: str, dimensions: dict, smells: list[str]) -> str:
    dim_lines = "\n".join(
        f"  - {dim}: {val.get('score')} — {val.get('rationale', '')}"
        for dim, val in (dimensions or {}).items()
    )
    smell_block = ", ".join(smells) if smells else "(none)"
    return f"""Requirement:
\"\"\"{requirement_text}\"\"\"

Dimension scores to review:
{dim_lines}

Smells detected: {smell_block}

Return the JSON object exactly as specified in the system message."""
