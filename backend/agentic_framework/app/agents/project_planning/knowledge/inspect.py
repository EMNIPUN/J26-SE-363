"""Inspect the Quality agent's ChromaDB knowledge base.

Run from backend/agentic_framework/:
    py -m uv run python -m app.agents.project_planning.knowledge.inspect
    py -m uv run python -m app.agents.project_planning.knowledge.inspect "your requirement text here"

Prints every document in both collections, then shows what a given requirement
retrieves (standards + exemplars + a self-similarity demo).
"""

from __future__ import annotations

import sys

from app.agents.project_planning.knowledge import query_exemplars, query_standards
from app.agents.project_planning.knowledge.vector_store import _get_collections


def _dump(collection) -> None:
    data = collection.get()  # all records (ids, documents, metadatas)
    print(f"\n### {collection.name}  ({collection.count()} documents)")
    for i, (doc_id, doc, meta) in enumerate(
        zip(data["ids"], data["documents"], data["metadatas"]), start=1
    ):
        print(f"  {i:2}. [{doc_id}]  {meta}")
        print(f"      {doc[:140]}")


def main() -> None:
    standards, exemplars = _get_collections()

    print("=" * 70)
    print("KNOWLEDGE BASE CONTENTS")
    print("=" * 70)
    _dump(standards)
    _dump(exemplars)

    query = sys.argv[1] if len(sys.argv) > 1 else "The system shall be fast and user-friendly"
    print("\n" + "=" * 70)
    print(f"RETRIEVAL for: {query!r}")
    print("=" * 70)
    print("\nTop IEEE 830 / SMART criteria:")
    for r in query_standards(query, 3):
        print(f"  - [{r['dimension']}] {r['text'][:110]}")
    print("\nTop exemplars:")
    for r in query_exemplars(query, 3):
        print(f"  - [{r['quality']}] {r['requirement']}")


if __name__ == "__main__":
    main()
