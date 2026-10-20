#!/usr/bin/env python
"""Threshold calibration for the RAG pipeline.

Sweeps ``MIN_SCORE`` (and optionally the similarity thresholds used by
``cross_req_check`` / ``aspect_coverage``) on the **dev** split of the
benchmark, reporting the trade-off between recall and abstention accuracy
at each candidate value.

Usage (from backend/agentic_framework/):
  uv run python -m app.agents.project_planning.knowledge.eval.calibrate
  uv run python -m app.agents.project_planning.knowledge.eval.calibrate --sweep-cross-req
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[6]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.agents.project_planning.knowledge.eval.run_eval import (
    _mean,
    _run_system,
    load_benchmark,
    ndcg_at_k,
    recall_at_k,
)


def sweep_min_score(
    queries: list[dict],
    system: str = "hybrid+rerank",
    thresholds: list[float] | None = None,
) -> None:
    """Sweep MIN_SCORE on the dev split and print recall vs. abstention."""
    from app.agents.project_planning.knowledge import config as rag_cfg
    from app.agents.project_planning.knowledge.vector_store import warm_up

    warm_up()

    if thresholds is None:
        thresholds = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6]

    print(f"{'Threshold':>10} {'Recall@5':>10} {'nDCG@10':>10} {'Abstain Acc':>12} {'Avg Results':>12}")
    print("-" * 58)

    for t in thresholds:
        rag_cfg.MIN_SCORE = t
        recalls = []
        ndcgs = []
        abstention_accs = []
        result_counts = []

        for q in queries:
            retrieved_ids, _ = _run_system(system, q["query"], q["collection"], 5)
            relevant = q["relevant_ids"]
            expect_abstain = q.get("expect_abstain", False)

            recalls.append(recall_at_k(retrieved_ids, relevant, 5))
            ndcgs.append(ndcg_at_k(retrieved_ids, relevant, 10))
            abstained = len(retrieved_ids) == 0
            correct = (expect_abstain and abstained) or (not expect_abstain and not abstained)
            abstention_accs.append(1.0 if correct else 0.0)
            result_counts.append(len(retrieved_ids))

        print(
            f"{t:>10.2f} {_mean(recalls):>10.3f} {_mean(ndcgs):>10.3f} "
            f"{_mean(abstention_accs):>12.3f} {_mean(result_counts):>12.1f}"
        )

    # Reset
    rag_cfg.MIN_SCORE = 0.0


def sweep_cross_req_threshold(
    test_pairs: list[tuple[str, list[str], bool]],
    thresholds: list[float] | None = None,
) -> None:
    """Sweep the cross_req_check cosine threshold.

    ``test_pairs`` = [(req_text, other_texts, expect_duplicate), ...]
    """
    from app.agents.project_planning.knowledge.similarity import cross_req_check

    if thresholds is None:
        thresholds = [0.60, 0.65, 0.70, 0.75, 0.78, 0.80, 0.85, 0.90]

    print(f"\n{'Threshold':>10} {'True Pos':>10} {'False Pos':>10} {'False Neg':>10}")
    print("-" * 44)

    for t in thresholds:
        tp = fp = fn = 0
        for req_text, others, expect_dup in test_pairs:
            hits = cross_req_check(req_text, others, threshold=t)
            found_dup = len(hits) > 0
            if expect_dup and found_dup:
                tp += 1
            elif not expect_dup and found_dup:
                fp += 1
            elif expect_dup and not found_dup:
                fn += 1
        print(f"{t:>10.2f} {tp:>10} {fp:>10} {fn:>10}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG threshold calibration")
    parser.add_argument("--sweep-cross-req", action="store_true",
                        help="Also sweep the cross_req_check cosine threshold")
    args = parser.parse_args()

    queries = load_benchmark(split="dev")
    if not queries:
        print("No dev-split queries found.  Add entries to benchmark.jsonl with split='dev'.")
        return

    print("=== MIN_SCORE sweep (hybrid+rerank, dev split) ===\n")
    sweep_min_score(queries)

    if args.sweep_cross_req:
        print("\n=== cross_req_check threshold sweep ===")
        print("(Add your own test pairs in this script's main() to calibrate.)")
        # Example: uncomment and populate with real test data
        # test_pairs = [
        #     ("The system shall allow login", ["The system shall permit authentication"], True),
        #     ("The system shall allow login", ["The system shall generate reports"], False),
        # ]
        # sweep_cross_req_threshold(test_pairs)


if __name__ == "__main__":
    main()
