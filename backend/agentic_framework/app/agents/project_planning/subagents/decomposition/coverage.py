"""coverage_analyzer tool — extract requirement aspects and match against stories.

Uses the LLM to extract what a complete decomposition should cover (aspects),
then MiniLM cosine similarity to match each aspect against the student's stories.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agents.project_planning.knowledge.similarity import aspect_coverage
from app.agents.project_planning.llm import get_llm_client

logger = logging.getLogger(__name__)

_ASPECT_SYSTEM = """You are a requirements analyst. Given a software requirement, extract the \
distinct functional aspects (capabilities/concerns) that a complete set of user stories should \
cover. Each aspect is one testable piece of functionality.

Reply with a STRICT JSON object only (no markdown):
{
  "aspects": [
    {"id": "aspect-1", "label": "short description of the aspect"},
    {"id": "aspect-2", "label": "short description of the aspect"}
  ]
}

Extract 2-6 aspects. Be specific and concrete — each aspect should map to roughly one user story."""


async def analyze_coverage(
    requirement_text: str,
    stories: list[dict],
    similarity_threshold: float = 0.45,
) -> dict[str, Any]:
    """Extract aspects from the requirement and match against stories via SBERT."""
    client = get_llm_client()
    story_texts = [f"{s.get('title', '')} {s.get('acceptance_criteria', '')}" for s in stories]

    aspects_raw: list[dict] = []
    if client.configured:
        try:
            result = await client.complete_json(
                _ASPECT_SYSTEM,
                f'Requirement:\n"""{requirement_text}"""\n\nReturn the JSON object.',
                max_tokens=600,
            )
            aspects_raw = result.get("aspects", [])
        except Exception:
            logger.exception("LLM aspect extraction failed; using fallback")

    if not aspects_raw:
        aspects_raw = [{"id": "aspect-1", "label": requirement_text[:100]}]

    aspect_results = await asyncio.to_thread(
        aspect_coverage, aspects_raw, story_texts, similarity_threshold
    )

    covered = [a for a in aspect_results if a["covered"]]
    gaps = [a for a in aspect_results if not a["covered"]]
    coverage_ratio = len(covered) / len(aspect_results) if aspect_results else 0.0

    return {
        "coverage": round(coverage_ratio, 3),
        "aspects": aspect_results,
        "covered": covered,
        "gaps": gaps,
    }
