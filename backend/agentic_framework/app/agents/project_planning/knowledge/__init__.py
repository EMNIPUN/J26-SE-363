"""Knowledge-base access for the Quality, Decomposition, and DART agents.

Hybrid RAG pipeline (dense + BM25 + RRF fusion + cross-encoder rerank)
built on ChromaDB + fastembed (ONNX, no torch).
"""

from app.agents.project_planning.knowledge.embeddings import (
    embed_texts,
    get_embedding_function,
    model_info,
    rerank,
)
from app.agents.project_planning.knowledge.similarity import (
    aspect_coverage,
    cross_req_check,
)
from app.agents.project_planning.knowledge.vector_store import (
    pop_retrieval_log,
    query_exemplars,
    query_patterns,
    query_standards,
    reindex,
    warm_up,
)

__all__ = [
    "aspect_coverage",
    "cross_req_check",
    "embed_texts",
    "get_embedding_function",
    "model_info",
    "pop_retrieval_log",
    "query_exemplars",
    "query_patterns",
    "query_standards",
    "reindex",
    "rerank",
    "warm_up",
]
