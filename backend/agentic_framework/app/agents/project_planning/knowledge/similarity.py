"""cross_req_checker — semantic similarity across the SRS (SBERT/MiniLM + cosine).

Uses ChromaDB's default all-MiniLM-L6-v2 (384-d) embedding to find other
requirements that are near-duplicates of, or overlap with, the one being scored.
High similarity to another requirement is evidence for the consistency and
traceability dimensions (possible duplication, contradiction or overlap).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np


@lru_cache(maxsize=1)
def _embedder():
    from chromadb.utils import embedding_functions

    return embedding_functions.DefaultEmbeddingFunction()


def cross_req_check(
    req_text: str,
    other_texts: list[str],
    threshold: float = 0.78,
    top: int = 3,
) -> list[dict[str, Any]]:
    """Return the most similar other requirements above ``threshold`` cosine."""
    others = [t for t in dict.fromkeys(other_texts) if t and t != req_text]
    if not others:
        return []

    vectors = np.asarray(_embedder()([req_text, *others]), dtype=float)
    query = vectors[0]
    rest = vectors[1:]
    query /= np.linalg.norm(query) + 1e-9
    rest /= np.linalg.norm(rest, axis=1, keepdims=True) + 1e-9
    sims = rest @ query

    ranked = sorted(zip(sims.tolist(), others), reverse=True)
    return [
        {"text": text, "similarity": round(float(sim), 3)}
        for sim, text in ranked[:top]
        if sim >= threshold
    ]
