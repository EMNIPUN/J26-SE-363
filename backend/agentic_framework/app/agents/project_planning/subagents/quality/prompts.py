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


def build_user_prompt(requirement_text: str, smells: list[str], other_requirements: list[str]) -> str:
    smell_block = "\n".join(f"  - {s}" for s in smells) if smells else "  (none detected)"
    context_block = (
        "\n".join(f"  - {r}" for r in other_requirements[:15])
        if other_requirements
        else "  (no other requirements provided)"
    )
    return f"""Requirement to evaluate:
\"\"\"{requirement_text}\"\"\"

Deterministic smells already detected (use as evidence, do not just repeat them):
{smell_block}

Other requirements in the same SRS (for consistency/traceability checks):
{context_block}

Return the JSON object exactly as specified in the system message."""
