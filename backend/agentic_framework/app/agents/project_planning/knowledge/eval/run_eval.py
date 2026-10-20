#!/usr/bin/env python
"""RAG evaluation harness — the core research deliverable.

Compares four retrieval configurations on the labelled benchmark and reports
standard IR metrics.  Runs **offline** (no LLM calls) — cheap, deterministic,
and reproducible.

Systems evaluated:
  1. baseline     — original MiniLM dense-only top-3
  2. dense-new    — bge-small-en-v1.5 dense-only
  3. hybrid       — bge dense + BM25 + RRF
  4. hybrid+rerank — bge dense + BM25 + RRF + cross-encoder rerank

Metrics per system:
  - Recall@5       — fraction of relevant docs retrieved in top 5
  - MRR@10         — mean reciprocal rank of first relevant doc (cut at 10)
  - nDCG@10        — normalized discounted cumulative gain at 10
  - Abstention acc — fraction of correctly-handled abstention queries
  - Latency p50/p95 (ms)

Usage (from backend/agentic_framework/):
  uv run python -m app.agents.project_planning.knowledge.eval.run_eval
  uv run python -m app.agents.project_planning.knowledge.eval.run_eval --split dev
  uv run python -m app.agents.project_planning.knowledge.eval.run_eval --split test --out results.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so imports work
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[6]  # backend/agentic_framework
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_BENCHMARK_FILE = Path(__file__).resolve().parent / "benchmark.jsonl"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
    """Fraction of relevant documents found in the top-k retrieved."""
    if not relevant_ids:
        return 1.0  # no relevant → vacuously complete
    top_k = set(retrieved_ids[:k])
    return len(top_k & set(relevant_ids)) / len(relevant_ids)


def mrr_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 10) -> float:
    """Reciprocal rank of the first relevant document in the top-k."""
    relevant_set = set(relevant_ids)
    for rank, doc_id in enumerate(retrieved_ids[:k], start=1):
        if doc_id in relevant_set:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 10) -> float:
    """Normalized Discounted Cumulative Gain at k (binary relevance)."""
    relevant_set = set(relevant_ids)
    if not relevant_set:
        return 1.0

    dcg = 0.0
    for rank, doc_id in enumerate(retrieved_ids[:k], start=1):
        if doc_id in relevant_set:
            dcg += 1.0 / math.log2(rank + 1)

    ideal_count = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, ideal_count + 1))
    return dcg / idcg if idcg > 0 else 0.0


# ---------------------------------------------------------------------------
# Retrieval system wrappers
# ---------------------------------------------------------------------------


def _run_system(
    system_name: str,
    query: str,
    collection: str,
    n: int = 5,
) -> tuple[list[str], float]:
    """Run a retrieval system and return (retrieved_ids, latency_ms).

    Each system sets the env-var toggles before calling the shared pipeline.
    """
    # Import here so env overrides take effect
    from app.agents.project_planning.knowledge import config as rag_cfg
    from app.agents.project_planning.knowledge.vector_store import (
        _hybrid_retrieve,
        pop_retrieval_log,
    )

    if system_name == "baseline":
        # Simulate the original all-MiniLM dense-only top-3
        # (requires the baseline Chroma store — see below)
        rag_cfg.HYBRID_ENABLED = False
        rag_cfg.RERANK_ENABLED = False
        rag_cfg.MIN_SCORE = 0.0
    elif system_name == "dense-new":
        rag_cfg.HYBRID_ENABLED = False
        rag_cfg.RERANK_ENABLED = False
        rag_cfg.MIN_SCORE = 0.0
    elif system_name == "hybrid":
        rag_cfg.HYBRID_ENABLED = True
        rag_cfg.RERANK_ENABLED = False
        rag_cfg.MIN_SCORE = 0.0
    elif system_name == "hybrid+rerank":
        rag_cfg.HYBRID_ENABLED = True
        rag_cfg.RERANK_ENABLED = True
        rag_cfg.MIN_SCORE = 0.0
    else:
        raise ValueError(f"Unknown system: {system_name}")

    t0 = time.perf_counter()
    results = _hybrid_retrieve(collection, query, n)
    latency = (time.perf_counter() - t0) * 1000
    pop_retrieval_log()  # discard telemetry during eval

    return [doc_id for doc_id, _ in results], latency


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

SYSTEMS = ["dense-new", "hybrid", "hybrid+rerank"]
# NOTE: "baseline" is excluded by default because it requires the old MiniLM
# Chroma store.  To include it, rebuild the store with the old model and add
# "baseline" to SYSTEMS.  Alternatively, compare "dense-new" (pure dense with
# the new model) against "hybrid+rerank" to show method-only improvement.


def load_benchmark(split: str | None = None) -> list[dict[str, Any]]:
    """Load benchmark queries, optionally filtering by split."""
    queries = []
    with open(_BENCHMARK_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if split and entry.get("split") != split:
                continue
            queries.append(entry)
    return queries


def evaluate(
    split: str | None = None,
    systems: list[str] | None = None,
    n: int = 5,
) -> dict[str, dict[str, float]]:
    """Run all systems on the benchmark and return metrics per system."""
    queries = load_benchmark(split)
    if not queries:
        print(f"No benchmark queries found for split={split!r}")
        return {}

    if systems is None:
        systems = SYSTEMS

    # Warm up the knowledge base once
    from app.agents.project_planning.knowledge.vector_store import warm_up
    warm_up()

    results: dict[str, dict[str, list[float]]] = {
        s: {"recall@5": [], "mrr@10": [], "ndcg@10": [], "abstention_acc": [], "latency": []}
        for s in systems
    }

    for q in queries:
        query = q["query"]
        collection = q["collection"]
        relevant = q["relevant_ids"]
        expect_abstain = q.get("expect_abstain", False)

        for sys_name in systems:
            retrieved_ids, latency = _run_system(sys_name, query, collection, n)

            results[sys_name]["recall@5"].append(recall_at_k(retrieved_ids, relevant, 5))
            results[sys_name]["mrr@10"].append(mrr_at_k(retrieved_ids, relevant, 10))
            results[sys_name]["ndcg@10"].append(ndcg_at_k(retrieved_ids, relevant, 10))
            results[sys_name]["latency"].append(latency)

            # Abstention accuracy: correct when (expect_abstain → empty) or
            # (not expect_abstain → non-empty)
            abstained = len(retrieved_ids) == 0
            correct = (expect_abstain and abstained) or (not expect_abstain and not abstained)
            results[sys_name]["abstention_acc"].append(1.0 if correct else 0.0)

    # Aggregate
    aggregated: dict[str, dict[str, float]] = {}
    for sys_name in systems:
        r = results[sys_name]
        latencies = sorted(r["latency"])
        p50_idx = max(0, len(latencies) // 2 - 1)
        p95_idx = max(0, int(len(latencies) * 0.95) - 1)
        aggregated[sys_name] = {
            "recall@5": _mean(r["recall@5"]),
            "mrr@10": _mean(r["mrr@10"]),
            "ndcg@10": _mean(r["ndcg@10"]),
            "abstention_acc": _mean(r["abstention_acc"]),
            "latency_p50": latencies[p50_idx] if latencies else 0,
            "latency_p95": latencies[p95_idx] if latencies else 0,
        }

    return aggregated


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def print_table(results: dict[str, dict[str, float]]) -> str:
    """Format results as a Markdown table and return the string."""
    headers = ["System", "Recall@5", "MRR@10", "nDCG@10", "Abstain Acc", "p50 (ms)", "p95 (ms)"]
    rows = []
    for sys_name, metrics in results.items():
        rows.append([
            sys_name,
            f"{metrics['recall@5']:.3f}",
            f"{metrics['mrr@10']:.3f}",
            f"{metrics['ndcg@10']:.3f}",
            f"{metrics['abstention_acc']:.3f}",
            f"{metrics['latency_p50']:.1f}",
            f"{metrics['latency_p95']:.1f}",
        ])

    col_widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]
    sep = "| " + " | ".join("-" * w for w in col_widths) + " |"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths)) + " |"
    body_lines = [
        "| " + " | ".join(cell.ljust(w) for cell, w in zip(row, col_widths)) + " |"
        for row in rows
    ]

    table = "\n".join([header_line, sep, *body_lines])
    return table


def write_csv(results: dict[str, dict[str, float]], path: str) -> None:
    """Write results to a CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["system", "recall@5", "mrr@10", "ndcg@10", "abstention_acc", "latency_p50", "latency_p95"])
        for sys_name, metrics in results.items():
            writer.writerow([sys_name, *[f"{v:.4f}" for v in metrics.values()]])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG evaluation harness")
    parser.add_argument("--split", choices=["dev", "val", "test"], default=None,
                        help="Benchmark split to evaluate (default: all)")
    parser.add_argument("--out", default=None, help="CSV output path")
    parser.add_argument("--systems", nargs="+", default=None,
                        help="Systems to evaluate (default: dense-new hybrid hybrid+rerank)")
    args = parser.parse_args()

    print(f"Running evaluation (split={args.split or 'all'})...\n")
    results = evaluate(split=args.split, systems=args.systems)

    if not results:
        print("No results.")
        return

    table = print_table(results)
    print(table)

    if args.out:
        write_csv(results, args.out)
        print(f"\nResults written to {args.out}")


if __name__ == "__main__":
    main()
