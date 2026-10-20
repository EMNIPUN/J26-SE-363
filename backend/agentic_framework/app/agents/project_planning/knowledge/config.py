"""RAG pipeline configuration for the Project Planning knowledge base.

All settings have safe defaults that match the upgraded pipeline.  Override via
environment variables (prefixed ``PLANNING_RAG_``) in backend/agentic_framework/.env.
Set ``PLANNING_RAG_HYBRID=false`` or ``PLANNING_RAG_RERANK=false`` to disable
individual stages — useful for A/B evaluation or fallback.
"""

from __future__ import annotations

import os


def _bool_env(key: str, default: bool) -> bool:
    val = os.getenv(key, "").strip().lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


# ---------------------------------------------------------------------------
# Embedding model (fastembed, ONNX — no torch required)
# ---------------------------------------------------------------------------
EMBED_MODEL: str = os.getenv(
    "PLANNING_RAG_EMBED_MODEL", "BAAI/bge-small-en-v1.5"
)

# ---------------------------------------------------------------------------
# Cross-encoder reranker (fastembed, ONNX)
# ---------------------------------------------------------------------------
RERANK_MODEL: str = os.getenv(
    "PLANNING_RAG_RERANK_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2"
)

# ---------------------------------------------------------------------------
# Pipeline toggles
# ---------------------------------------------------------------------------
HYBRID_ENABLED: bool = _bool_env("PLANNING_RAG_HYBRID", True)
RERANK_ENABLED: bool = _bool_env("PLANNING_RAG_RERANK", True)

# ---------------------------------------------------------------------------
# Retrieval pool sizes
# ---------------------------------------------------------------------------
# Candidates fetched from *each* retriever (dense + BM25) before fusion.
CANDIDATES: int = int(os.getenv("PLANNING_RAG_CANDIDATES", "20"))

# Final top-k returned to the agent tool after reranking / threshold.
TOP_K: int = int(os.getenv("PLANNING_RAG_TOP_K", "5"))

# ---------------------------------------------------------------------------
# Relevance threshold — results below this rerank / cosine score are dropped.
# Set to 0.0 to disable abstention (always return TOP_K results).
# Calibrate on the eval dev split (Phase 5) before committing a value.
# ---------------------------------------------------------------------------
MIN_SCORE: float = float(os.getenv("PLANNING_RAG_MIN_SCORE", "0.0"))

# ---------------------------------------------------------------------------
# RRF fusion constant (standard default k=60)
# ---------------------------------------------------------------------------
RRF_K: int = int(os.getenv("PLANNING_RAG_RRF_K", "60"))
