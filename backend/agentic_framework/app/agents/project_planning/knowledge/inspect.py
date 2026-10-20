"""Inspect the Quality agent's ChromaDB knowledge base.

Run from backend/agentic_framework/:
    uv run python -m app.agents.project_planning.knowledge.inspect
    uv run python -m app.agents.project_planning.knowledge.inspect "your requirement text here"

Prints every document in all collections, then shows what a given requirement
retrieves (standards + exemplars + patterns) with the full hybrid pipeline,
including citation scores and telemetry.
"""

from __future__ import annotations

import sys

from app.agents.project_planning.knowledge import (
    model_info,
    pop_retrieval_log,
    query_exemplars,
    query_patterns,
    query_standards,
    warm_up,
)
from app.agents.project_planning.knowledge.vector_store import _collections


def _dump(collection) -> None:
    data = collection.get()  # all records (ids, documents, metadatas)
    print(f"\n### {collection.name}  ({collection.count()} documents)")
    for i, (doc_id, doc, meta) in enumerate(
        zip(data["ids"], data["documents"], data["metadatas"]), start=1
    ):
        print(f"  {i:2}. [{doc_id}]  {meta}")
        print(f"      {doc[:140]}")


def main() -> None:
    # warm_up handles model-change detection and auto-reindex
    warm_up()
    standards, exemplars, patterns = _collections()

    info = model_info()
    print(f"Embed model:  {info['embed_model']}")
    print(f"Rerank model: {info['rerank_model']}")

    print("\n" + "=" * 70)
    print("KNOWLEDGE BASE CONTENTS")
    print("=" * 70)
    _dump(standards)
    _dump(exemplars)
    _dump(patterns)

    query = sys.argv[1] if len(sys.argv) > 1 else "The system shall be fast and user-friendly"
    print("\n" + "=" * 70)
    print(f"RETRIEVAL for: {query!r}")
    print("=" * 70)

    print("\nTop IEEE 830 / SMART criteria:")
    for r in query_standards(query, 5):
        score = f" (score={r['score']:.4f})" if "score" in r else ""
        print(f"  - [{r['dimension']}]{score} {r['text'][:110]}")

    print("\nTop exemplars:")
    for r in query_exemplars(query, 5):
        score = f" (score={r['score']:.4f})" if "score" in r else ""
        print(f"  - [{r['quality']}]{score} {r['requirement'][:120]}")

    print("\nTop decomposition patterns:")
    for r in query_patterns(query, 5):
        score = f" (score={r['score']:.4f})" if "score" in r else ""
        stories_preview = ", ".join(r.get("stories", [])[:2])
        print(f"  - [{r['title']}]{score} {stories_preview}")

    print("\n--- Retrieval telemetry ---")
    for run in pop_retrieval_log():
        print(f"  {run['collection']:30s}  {run['decision']:10s}  "
              f"n={run['results_count']}  top={run.get('top_score', 'n/a')}  "
              f"{run['latency_ms']:.1f}ms  hybrid={run['hybrid']}  rerank={run['rerank']}")


if __name__ == "__main__":
    main()
