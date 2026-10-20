"""Shared embedding and reranking functions for the RAG pipeline.

Uses **fastembed** (ONNX runtime) — no torch, no sentence-transformers, no
API key. The models are downloaded once on first use and cached locally.

Two public entry points:

* ``get_embedding_function()`` — a ChromaDB-compatible callable that embeds
  a list of texts. Used by ``vector_store.py`` (collection creation) and
  ``similarity.py`` (cosine checks).
* ``rerank(query, documents, top_n)`` — cross-encoder reranker returning
  ``(doc_index, score)`` pairs sorted by descending relevance.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Sequence

import numpy as np

from app.agents.project_planning.knowledge import config as rag_cfg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding (bi-encoder)
# ---------------------------------------------------------------------------


class _FastEmbedFunction:
    """ChromaDB ``EmbeddingFunction``-compatible wrapper around fastembed.

    Implements the full ChromaDB ≥ 1.5 ``EmbeddingFunction`` protocol:

    * ``__call__`` — legacy path, still used by ``collection.add()``.
    * ``embed_documents`` — called by ``collection.add()`` in chromadb ≥ 1.5.
    * ``embed_query`` — called by ``collection.query()`` in chromadb ≥ 1.5.
    * ``name()`` — collection identity check (prevents accidental model mix).
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: Any | None = None

    def name(self) -> str:
        return f"fastembed:{self._model_name}"

    @property
    def model_name(self) -> str:
        return self._model_name

    def _ensure_model(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding

            logger.info("[rag] loading embedding model %s", self._model_name)
            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._ensure_model()
        vectors = list(model.embed(list(texts)))
        return [v.tolist() for v in vectors]

    # ChromaDB ≥ 1.5 protocol
    def embed_documents(self, input: Sequence[str]) -> list[list[float]]:  # noqa: A002
        return self._embed(input)

    def embed_query(self, input: Sequence[str]) -> list[list[float]]:  # noqa: A002
        return self._embed(input)

    # Legacy __call__ (chromadb < 1.5 and direct use)
    def __call__(self, input: Sequence[str]) -> list[list[float]]:  # noqa: A002
        return self._embed(input)


@lru_cache(maxsize=1)
def get_embedding_function() -> _FastEmbedFunction:
    """Return the singleton embedding function (process-wide cache)."""
    return _FastEmbedFunction(rag_cfg.EMBED_MODEL)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of texts and return an (N, dim) float32 array.

    Convenience for ``similarity.py`` and the eval harness that want numpy
    directly instead of a list-of-lists.
    """
    ef = get_embedding_function()
    vecs = ef(texts)
    return np.asarray(vecs, dtype=np.float32)


# ---------------------------------------------------------------------------
# Reranking (cross-encoder)
# ---------------------------------------------------------------------------

_reranker: Any | None = None


def _ensure_reranker() -> Any:
    global _reranker  # noqa: PLW0603
    if _reranker is None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        logger.info("[rag] loading rerank model %s", rag_cfg.RERANK_MODEL)
        _reranker = TextCrossEncoder(model_name=rag_cfg.RERANK_MODEL)
    return _reranker


def rerank(
    query: str,
    documents: list[str],
    *,
    top_n: int | None = None,
) -> list[tuple[int, float]]:
    """Rerank *documents* against *query* with the cross-encoder.

    Returns ``[(original_index, score), ...]`` sorted by descending score,
    truncated to *top_n* if given.
    """
    if not documents:
        return []

    reranker = _ensure_reranker()
    raw_scores = list(reranker.rerank(query, documents))

    # fastembed 0.9 returns Iterable[float] — one score per document in order.
    scored: list[tuple[int, float]] = [
        (idx, float(s)) for idx, s in enumerate(raw_scores)
    ]

    scored.sort(key=lambda x: x[1], reverse=True)
    if top_n is not None:
        scored = scored[:top_n]
    return scored


# ---------------------------------------------------------------------------
# Metadata helpers (for telemetry / eval reproducibility)
# ---------------------------------------------------------------------------


def model_info() -> dict[str, str]:
    """Return the configured model names (for logging / citation records)."""
    return {
        "embed_model": rag_cfg.EMBED_MODEL,
        "rerank_model": rag_cfg.RERANK_MODEL if rag_cfg.RERANK_ENABLED else "none",
    }
