"""Semantic similarity utilities (shared embedder + cosine).

- ``cross_req_check``: find near-duplicate requirements across the SRS.
- ``aspect_coverage``: match extracted requirement aspects against story texts
  for the Decomposition agent's coverage_analyzer tool.

Uses the shared fastembed-based embedder from ``embeddings.py`` so that
similarity judgments are made with the same model as RAG retrieval.

.. note:: The ``threshold`` defaults (0.78 for cross-req, 0.45 for aspect
   coverage) were calibrated for MiniLM-L6-v2.  After upgrading to
   bge-small-en-v1.5 they **must** be re-calibrated on the eval dev split
   (see ``knowledge/eval/calibrate.py``).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.agents.project_planning.knowledge.embeddings import embed_texts


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

    vectors = embed_texts([req_text, *others])
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


def aspect_coverage(
    aspects: list[dict[str, str]],
    story_texts: list[str],
    threshold: float = 0.45,
) -> list[dict[str, Any]]:
    """For each aspect {id, label}, find the best-matching story text by cosine.

    Returns a list of ``{id, label, covered, best_similarity}`` dicts.
    An aspect is ``covered`` when ``best_similarity >= threshold``.
    """
    if not aspects or not story_texts:
        return [{"id": a["id"], "label": a["label"], "covered": False, "best_similarity": 0.0} for a in aspects]

    aspect_docs = [a["label"] for a in aspects]
    all_docs = [*aspect_docs, *story_texts]
    vectors = embed_texts(all_docs)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9
    vectors /= norms

    aspect_vecs = vectors[: len(aspect_docs)]
    story_vecs = vectors[len(aspect_docs) :]
    sims = aspect_vecs @ story_vecs.T  # (num_aspects, num_stories)

    out: list[dict[str, Any]] = []
    for i, a in enumerate(aspects):
        best = float(sims[i].max()) if sims.shape[1] > 0 else 0.0
        out.append({
            "id": a["id"],
            "label": a["label"],
            "covered": best >= threshold,
            "best_similarity": round(best, 3),
        })
    return out
