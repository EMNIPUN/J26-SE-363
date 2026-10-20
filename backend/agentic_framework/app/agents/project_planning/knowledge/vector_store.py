"""ChromaDB knowledge base with hybrid retrieval for the Quality, Decomposition,
and DART agents.

Retrieval pipeline (all ONNX, no torch):
  1. Dense semantic search (fastembed bge-small-en-v1.5 via ChromaDB).
  2. Keyword search (BM25 via rank-bm25).
  3. Reciprocal Rank Fusion (RRF, k=60) to merge both ranked lists.
  4. Cross-encoder reranking (fastembed ms-marco-MiniLM-L-6-v2).
  5. Calibrated relevance threshold — abstains when nothing is relevant.

Each stage is independently toggleable via environment variables
(see ``knowledge/config.py``).  When rerank is off the pipeline falls back
to RRF scores; when hybrid is also off it degrades to pure dense top-k — the
same behaviour as the original all-MiniLM baseline.

Collections (seeded once from knowledge/seed/*.json):
  - ieee830_smart           : IEEE 830 quality criteria + SMART definitions
  - exemplars               : graded high/medium/low requirement examples
  - decomposition_patterns  : curated good requirement-to-stories decompositions

Public API (unchanged signatures for backward compatibility):
  ``query_standards(text, n) -> list[dict]``
  ``query_exemplars(text, n) -> list[dict]``
  ``query_patterns(text, n) -> list[dict]``
  ``warm_up() -> None``
  ``reindex() -> None``   (new — rebuilds store when the embed model changes)
"""

from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from app.agents.project_planning.knowledge import config as rag_cfg
from app.agents.project_planning.knowledge.embeddings import (
    get_embedding_function,
    rerank as cross_encoder_rerank,
)

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).resolve().parent
_SEED_DIR = _KNOWLEDGE_DIR / "seed"
_CHROMA_DIR = _KNOWLEDGE_DIR / ".chroma"
_MODEL_MARKER = _CHROMA_DIR / ".embed_model"

COLLECTION_STANDARDS = "ieee830_smart"
COLLECTION_EXEMPLARS = "exemplars"
COLLECTION_PATTERNS = "decomposition_patterns"

# ---------------------------------------------------------------------------
# Telemetry — lightweight per-query records for the eval harness and for
# the Core API to persist into rqa_retrieval_logs.
# Thread-local so concurrent requirement scoring (semaphore=3 in agent.py)
# doesn't mix retrieval logs across requirements.
# ---------------------------------------------------------------------------

import threading

_tls = threading.local()


def pop_retrieval_log() -> list[dict[str, Any]]:
    """Return and clear accumulated retrieval-run records since last call.

    Records are thread-local, so each concurrent scoring thread gets its own.
    """
    runs = getattr(_tls, "retrieval_log", [])[:]
    _tls.retrieval_log = []
    return runs


def _log_run(record: dict[str, Any]) -> None:
    if not hasattr(_tls, "retrieval_log"):
        _tls.retrieval_log = []
    _tls.retrieval_log.append(record)


# ---------------------------------------------------------------------------
# Seed loaders
# ---------------------------------------------------------------------------


def _load_seed(filename: str) -> list[dict[str, Any]]:
    with open(_SEED_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def _seed_standards(collection) -> None:
    rows = _load_seed("ieee830_smart.json")
    collection.add(
        ids=[r["id"] for r in rows],
        documents=[r["text"] for r in rows],
        metadatas=[{"category": r["category"], "dimension": r["dimension"]} for r in rows],
    )


def _seed_exemplars(collection) -> None:
    rows = _load_seed("exemplars.json")
    collection.add(
        ids=[r["id"] for r in rows],
        documents=[r["requirement"] for r in rows],
        metadatas=[{"quality": r["quality"], "note": r["note"]} for r in rows],
    )


def _seed_patterns(collection) -> None:
    rows = _load_seed("decomposition_patterns.json")
    collection.add(
        ids=[r["id"] for r in rows],
        documents=[r["title"] + ": " + ", ".join(r["stories"]) for r in rows],
        metadatas=[{"title": r["title"], "note": r["note"]} for r in rows],
    )


# ---------------------------------------------------------------------------
# Model marker — detect stale embeddings after a model change
# ---------------------------------------------------------------------------


def _write_model_marker() -> None:
    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    _MODEL_MARKER.write_text(rag_cfg.EMBED_MODEL, encoding="utf-8")


def _model_changed() -> bool:
    """Return True when the stored embeddings were made with a different model."""
    if not _MODEL_MARKER.exists():
        return True
    return _MODEL_MARKER.read_text(encoding="utf-8").strip() != rag_cfg.EMBED_MODEL


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------

# Cache invalidation token — incremented by reindex() to bust lru_cache.
_cache_generation: int = 0


def _get_collections_impl():
    """Open (and seed on first run) all collections.

    Uses the fastembed embedding function so vectors match the configured
    model.  If the model marker shows a mismatch the caller should call
    ``reindex()`` first.
    """
    import chromadb

    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    ef = get_embedding_function()

    standards = client.get_or_create_collection(
        COLLECTION_STANDARDS, embedding_function=ef,
    )
    exemplars = client.get_or_create_collection(
        COLLECTION_EXEMPLARS, embedding_function=ef,
    )
    patterns = client.get_or_create_collection(
        COLLECTION_PATTERNS, embedding_function=ef,
    )

    if standards.count() == 0:
        logger.info("[kb] seeding %s", COLLECTION_STANDARDS)
        _seed_standards(standards)
    if exemplars.count() == 0:
        logger.info("[kb] seeding %s", COLLECTION_EXEMPLARS)
        _seed_exemplars(exemplars)
    if patterns.count() == 0:
        logger.info("[kb] seeding %s", COLLECTION_PATTERNS)
        _seed_patterns(patterns)

    _write_model_marker()
    return standards, exemplars, patterns


@lru_cache(maxsize=1)
def _get_collections(_generation: int = 0):  # noqa: ARG001
    """Cached wrapper.  ``_generation`` busts the cache on reindex."""
    return _get_collections_impl()


def _collections():
    return _get_collections(_cache_generation)


# ---------------------------------------------------------------------------
# BM25 index (in-memory, rebuilt per process start — corpus is tiny)
# ---------------------------------------------------------------------------

_bm25_indices: dict[str, tuple[BM25Okapi, list[str], list[str]]] = {}


def _build_bm25(collection_name: str, docs: list[str], ids: list[str]) -> None:
    """Build a BM25 index over *docs* for the given collection."""
    tokenized = [doc.lower().split() for doc in docs]
    bm25 = BM25Okapi(tokenized)
    _bm25_indices[collection_name] = (bm25, docs, ids)


def _ensure_bm25(collection_name: str) -> tuple[BM25Okapi, list[str], list[str]]:
    """Return (bm25, docs, ids) for *collection_name*, building if needed."""
    if collection_name not in _bm25_indices:
        standards, exemplars, patterns = _collections()
        colmap = {
            COLLECTION_STANDARDS: standards,
            COLLECTION_EXEMPLARS: exemplars,
            COLLECTION_PATTERNS: patterns,
        }
        col = colmap[collection_name]
        data = col.get()
        _build_bm25(collection_name, data["documents"], data["ids"])
    return _bm25_indices[collection_name]


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def _rrf_fuse(
    ranked_lists: list[list[str]],
    k: int | None = None,
) -> list[tuple[str, float]]:
    """Fuse multiple ranked lists of document IDs via RRF.

    Returns ``[(doc_id, rrf_score), ...]`` sorted by descending fused score.
    """
    if k is None:
        k = rag_cfg.RRF_K
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# Core hybrid retrieval
# ---------------------------------------------------------------------------


def _hybrid_retrieve(
    collection_name: str,
    query: str,
    n: int,
) -> list[tuple[str, float]]:
    """Run the full hybrid retrieval pipeline for *collection_name*.

    Returns ``[(doc_id, score), ...]`` of length ≤ *n*, sorted by descending
    relevance.  The ``score`` is the reranker score when reranking is on, or
    the RRF fusion score otherwise.

    If all candidates fall below ``rag_cfg.MIN_SCORE`` an empty list is
    returned (abstention).
    """
    t0 = time.perf_counter()
    candidates = rag_cfg.CANDIDATES

    # --- 1. Dense retrieval via ChromaDB (always on) ---
    standards, exemplars, patterns = _collections()
    colmap = {
        COLLECTION_STANDARDS: standards,
        COLLECTION_EXEMPLARS: exemplars,
        COLLECTION_PATTERNS: patterns,
    }
    col = colmap[collection_name]

    # Clamp to collection size to avoid ChromaDB errors
    dense_n = min(candidates, col.count())
    dense_res = col.query(query_texts=[query], n_results=max(dense_n, 1))
    dense_ids: list[str] = dense_res["ids"][0]

    # --- 2. BM25 keyword retrieval (if hybrid enabled) ---
    if rag_cfg.HYBRID_ENABLED:
        bm25, bm25_docs, bm25_ids = _ensure_bm25(collection_name)
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)
        # Rank by BM25 score descending
        ranked_indices = bm25_scores.argsort()[::-1][:candidates]
        bm25_ranked_ids = [bm25_ids[i] for i in ranked_indices]

        # --- 3. RRF fusion ---
        fused = _rrf_fuse([dense_ids, bm25_ranked_ids])
    else:
        # Dense-only fallback: use Chroma ordering directly
        fused = [(doc_id, 1.0 / (i + 1)) for i, doc_id in enumerate(dense_ids)]

    # Limit to the top pool before reranking
    pool_ids = [doc_id for doc_id, _ in fused[: candidates * 2]]

    # --- 4. Cross-encoder reranking (if enabled) ---
    if rag_cfg.RERANK_ENABLED and pool_ids:
        # Fetch the actual document texts for the pool
        pool_data = col.get(ids=pool_ids)
        id_to_doc = dict(zip(pool_data["ids"], pool_data["documents"]))
        pool_docs = [id_to_doc[did] for did in pool_ids]

        reranked = cross_encoder_rerank(query, pool_docs, top_n=n)
        result = [(pool_ids[idx], score) for idx, score in reranked]
    else:
        result = fused[:n]

    # --- 5. Threshold / abstention ---
    if rag_cfg.MIN_SCORE > 0.0:
        result = [(did, s) for did, s in result if s >= rag_cfg.MIN_SCORE]

    elapsed_ms = (time.perf_counter() - t0) * 1000

    # --- Telemetry ---
    decision = "retrieved" if result else "abstained"
    _log_run({
        "collection": collection_name,
        "query": query[:200],
        "decision": decision,
        "results_count": len(result),
        "top_score": round(result[0][1], 4) if result else None,
        "candidates_dense": len(dense_ids),
        "candidates_bm25": len(bm25_ranked_ids) if rag_cfg.HYBRID_ENABLED else 0,
        "hybrid": rag_cfg.HYBRID_ENABLED,
        "rerank": rag_cfg.RERANK_ENABLED,
        "min_score": rag_cfg.MIN_SCORE,
        "embed_model": rag_cfg.EMBED_MODEL,
        "rerank_model": rag_cfg.RERANK_MODEL if rag_cfg.RERANK_ENABLED else None,
        "latency_ms": round(elapsed_ms, 1),
    })

    return result


# ---------------------------------------------------------------------------
# Public query API (signatures unchanged from the original for compat)
# ---------------------------------------------------------------------------


def query_standards(text: str, n: int = 3) -> list[dict[str, Any]]:
    """Retrieve the most relevant IEEE 830 / SMART criteria for a requirement."""
    n = n or rag_cfg.TOP_K
    results = _hybrid_retrieve(COLLECTION_STANDARDS, text, n)
    if not results:
        return []

    standards, _, _ = _collections()
    hit_ids = [doc_id for doc_id, _ in results]
    data = standards.get(ids=hit_ids)
    id_to_meta = dict(zip(data["ids"], data["metadatas"]))
    id_to_doc = dict(zip(data["ids"], data["documents"]))

    out: list[dict[str, Any]] = []
    for doc_id, score in results:
        meta = id_to_meta.get(doc_id, {})
        out.append({
            "text": id_to_doc.get(doc_id, ""),
            "dimension": meta.get("dimension"),
            "category": meta.get("category"),
            # New: citation fields (backward-compatible — consumers that don't
            # read them are unaffected).
            "chunk_id": doc_id,
            "score": round(score, 4),
        })
    return out


def query_exemplars(text: str, n: int = 3) -> list[dict[str, Any]]:
    """Retrieve graded example requirements similar to the given one."""
    n = n or rag_cfg.TOP_K
    results = _hybrid_retrieve(COLLECTION_EXEMPLARS, text, n)
    if not results:
        return []

    _, exemplars, _ = _collections()
    hit_ids = [doc_id for doc_id, _ in results]
    data = exemplars.get(ids=hit_ids)
    id_to_meta = dict(zip(data["ids"], data["metadatas"]))
    id_to_doc = dict(zip(data["ids"], data["documents"]))

    out: list[dict[str, Any]] = []
    for doc_id, score in results:
        meta = id_to_meta.get(doc_id, {})
        out.append({
            "requirement": id_to_doc.get(doc_id, ""),
            "quality": meta.get("quality"),
            "note": meta.get("note"),
            "chunk_id": doc_id,
            "score": round(score, 4),
        })
    return out


def query_patterns(text: str, n: int = 3) -> list[dict[str, Any]]:
    """Retrieve decomposition patterns similar to the given requirement."""
    n = n or rag_cfg.TOP_K
    results = _hybrid_retrieve(COLLECTION_PATTERNS, text, n)
    if not results:
        return []

    seed = _load_seed("decomposition_patterns.json")
    seed_map = {r["id"]: r for r in seed}

    _, _, patterns = _collections()
    hit_ids = [doc_id for doc_id, _ in results]
    data = patterns.get(ids=hit_ids)
    id_to_meta = dict(zip(data["ids"], data["metadatas"]))

    out: list[dict[str, Any]] = []
    for doc_id, score in results:
        meta = id_to_meta.get(doc_id, {})
        full = seed_map.get(doc_id, {})
        out.append({
            "id": doc_id,
            "title": meta.get("title", ""),
            "stories": full.get("stories", []),
            "note": meta.get("note", ""),
            "chunk_id": doc_id,
            "score": round(score, 4),
        })
    return out


# ---------------------------------------------------------------------------
# Warm-up & reindex
# ---------------------------------------------------------------------------


def warm_up() -> None:
    """Build/seed the store eagerly (downloads ONNX models once on first use).

    If the embedding model has changed since the last seeding, triggers a full
    reindex automatically — collections are rebuilt with the new model.
    """
    if _model_changed():
        logger.info("[kb] embed model changed → reindexing")
        reindex()
    else:
        _collections()


def reindex() -> None:
    """Rebuild all collections with the current embedding model.

    Deletes the persistent store and re-seeds from the JSON corpus. Call this
    after changing ``PLANNING_RAG_EMBED_MODEL`` or updating seed data.
    """
    import shutil

    global _cache_generation  # noqa: PLW0603

    logger.info("[kb] reindexing — deleting %s", _CHROMA_DIR)
    if _CHROMA_DIR.exists():
        shutil.rmtree(_CHROMA_DIR)

    # Clear caches so collections are re-created
    _get_collections.cache_clear()
    _bm25_indices.clear()
    _cache_generation += 1

    # Re-create and seed
    _collections()
    logger.info("[kb] reindex complete (model: %s)", rag_cfg.EMBED_MODEL)
