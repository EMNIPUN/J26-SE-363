"""ChromaDB knowledge base for the Quality and Decomposition agents' retrieval tools.

Collections (embedded with ChromaDB's default all-MiniLM-L6-v2 / 384-d ONNX model,
the SBERT model named in the proposal — no torch required):
  - ieee830_smart           : IEEE 830 quality criteria + SMART definitions
  - exemplars               : graded high/medium/low requirement examples
  - decomposition_patterns  : curated good requirement-to-stories decompositions

Seeded once from knowledge/seed/*.json into a local persistent store; subsequent
runs reuse it. Queries power standard_retriever, exemplar_retriever, and
pattern_retriever.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).resolve().parent
_SEED_DIR = _KNOWLEDGE_DIR / "seed"
_CHROMA_DIR = _KNOWLEDGE_DIR / ".chroma"

COLLECTION_STANDARDS = "ieee830_smart"
COLLECTION_EXEMPLARS = "exemplars"
COLLECTION_PATTERNS = "decomposition_patterns"


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


@lru_cache(maxsize=1)
def _get_collections():
    """Open (and seed on first run) all collections. Cached per process."""
    import chromadb

    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))

    standards = client.get_or_create_collection(COLLECTION_STANDARDS)
    exemplars = client.get_or_create_collection(COLLECTION_EXEMPLARS)
    patterns = client.get_or_create_collection(COLLECTION_PATTERNS)

    if standards.count() == 0:
        logger.info("[kb] seeding %s", COLLECTION_STANDARDS)
        _seed_standards(standards)
    if exemplars.count() == 0:
        logger.info("[kb] seeding %s", COLLECTION_EXEMPLARS)
        _seed_exemplars(exemplars)
    if patterns.count() == 0:
        logger.info("[kb] seeding %s", COLLECTION_PATTERNS)
        _seed_patterns(patterns)

    return standards, exemplars, patterns


def query_standards(text: str, n: int = 3) -> list[dict[str, Any]]:
    """Retrieve the most relevant IEEE 830 / SMART criteria for a requirement."""
    standards, _, _ = _get_collections()
    res = standards.query(query_texts=[text], n_results=n)
    out: list[dict[str, Any]] = []
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        out.append({"text": doc, "dimension": meta.get("dimension"), "category": meta.get("category")})
    return out


def query_exemplars(text: str, n: int = 3) -> list[dict[str, Any]]:
    """Retrieve graded example requirements similar to the given one."""
    _, exemplars, _ = _get_collections()
    res = exemplars.query(query_texts=[text], n_results=n)
    out: list[dict[str, Any]] = []
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        out.append({"requirement": doc, "quality": meta.get("quality"), "note": meta.get("note")})
    return out


def query_patterns(text: str, n: int = 3) -> list[dict[str, Any]]:
    """Retrieve decomposition patterns similar to the given requirement."""
    _, _, patterns = _get_collections()
    res = patterns.query(query_texts=[text], n_results=n)
    seed = _load_seed("decomposition_patterns.json")
    seed_map = {r["id"]: r for r in seed}
    out: list[dict[str, Any]] = []
    for doc_id, meta in zip(res["ids"][0], res["metadatas"][0]):
        full = seed_map.get(doc_id, {})
        out.append({
            "id": doc_id,
            "title": meta.get("title", ""),
            "stories": full.get("stories", []),
            "note": meta.get("note", ""),
        })
    return out


def warm_up() -> None:
    """Build/seed the store eagerly (downloads the ONNX embedding model once)."""
    _get_collections()
