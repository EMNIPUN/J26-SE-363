"""Deterministic requirement 'smell' detector (the ``smell_detector`` tool).

MVP: regex/lexicon based — fast, deterministic, no model needed. It flags the
surface problems that the LLM dimension scorer then uses as grounded evidence
(so scores are justified, not guessed). Upgrade path: a spaCy pipeline for
proper passive-voice / POS detection (plan task 4) — this module's output shape
stays the same.
"""

from __future__ import annotations

import re

from app.agents.project_planning.schemas import Smell

# Vague, non-measurable terms (IEEE 830: unambiguous / verifiable).
VAGUE_TERMS = [
    "user-friendly", "user friendly", "easy to use", "intuitive", "fast", "quick",
    "efficient", "flexible", "robust", "scalable", "reliable", "secure", "simple",
    "seamless", "modern", "optimal", "appropriate", "adequate", "sufficient",
    "reasonable", "acceptable", "state-of-the-art", "high-quality", "good",
    "better", "best", "as needed", "as appropriate", "etc", "and so on",
]

# Weak / optional modal words (requirement is not binding).
WEAK_WORDS = ["may", "might", "could", "should", "can", "optionally", "if possible", "preferably"]

# Unbounded / absolute quantifiers (hard to verify).
UNBOUNDED = ["all", "every", "always", "never", "any", "none", "everyone", "everything"]

# Vague time/quantity without a number.
UNQUANTIFIED = ["quickly", "slowly", "soon", "periodically", "regularly", "frequently", "many", "few", "several", "some", "most", "minimal", "maximal"]


def _find(text: str, terms: list[str]) -> list[str]:
    hits: list[str] = []
    lowered = text.lower()
    for term in terms:
        # word-boundary match for single words; substring for phrases with spaces/hyphens
        pattern = rf"\b{re.escape(term)}\b" if " " not in term and "-" not in term else re.escape(term)
        if re.search(pattern, lowered):
            hits.append(term)
    return hits


def detect_smells(text: str) -> list[Smell]:
    smells: list[Smell] = []

    for term in _find(text, VAGUE_TERMS):
        smells.append(Smell(
            type="vague_term", span=term,
            suggestion=f"Replace '{term}' with a specific, measurable criterion.",
        ))
    for term in _find(text, WEAK_WORDS):
        smells.append(Smell(
            type="weak_word", span=term,
            suggestion=f"'{term}' is optional/non-binding; use 'shall' for a firm requirement.",
        ))
    for term in _find(text, UNBOUNDED):
        smells.append(Smell(
            type="unbounded_quantifier", span=term,
            suggestion=f"'{term}' is absolute and hard to verify; bound the scope explicitly.",
        ))
    for term in _find(text, UNQUANTIFIED):
        smells.append(Smell(
            type="unquantified", span=term,
            suggestion=f"Quantify '{term}' with a number/threshold (e.g. 'within 2 seconds').",
        ))

    # Passive-voice heuristic: 'shall be <past-participle>' without 'by <actor>'.
    if re.search(r"\b(is|are|be|been|being)\s+\w+ed\b", text.lower()) and " by " not in text.lower():
        smells.append(Smell(
            type="passive_voice", span="",
            suggestion="Passive voice hides the actor; state who performs the action.",
        ))

    # No clear subject/obligation verb at all.
    if not re.search(r"\b(shall|must|will|should)\b", text.lower()):
        smells.append(Smell(
            type="no_obligation", span="",
            suggestion="Use an obligation verb ('shall') so the requirement is testable.",
        ))

    return smells
