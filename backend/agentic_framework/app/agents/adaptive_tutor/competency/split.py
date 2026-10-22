"""Chronological train/test splits for BKT hold-out evaluation.

Sequences stay in time order. Later answers are held out as unseen test steps.
Random shuffles are intentionally not used.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

# Defaults: leave-last-1; need ≥2 train observations so warm-start is meaningful.
DEFAULT_TEST_SIZE = 1
DEFAULT_MIN_TRAIN = 2
DEFAULT_MIN_TEST = 1


@dataclass(frozen=True)
class ChronologicalSplit:
    """One concept sequence split into train (earlier) and test (later)."""

    concept_id: str
    train: list[bool]
    test: list[bool]

    @property
    def train_count(self) -> int:
        return len(self.train)

    @property
    def test_count(self) -> int:
        return len(self.test)


def split_sequence_chronological(
    observations: Sequence[bool],
    *,
    test_size: int = DEFAULT_TEST_SIZE,
    min_train: int = DEFAULT_MIN_TRAIN,
    min_test: int = DEFAULT_MIN_TEST,
) -> tuple[list[bool], list[bool]] | None:
    """Split one chronological sequence into ``(train, test)``.

    Returns ``None`` when the sequence is too short for the requested split.
    """
    if test_size < 1:
        raise ValueError("test_size must be >= 1")
    if min_train < 1:
        raise ValueError("min_train must be >= 1")
    if min_test < 1:
        raise ValueError("min_test must be >= 1")
    if test_size < min_test:
        raise ValueError("test_size must be >= min_test")

    seq = list(observations)
    if len(seq) < min_train + test_size:
        return None

    train = seq[:-test_size]
    test = seq[-test_size:]
    if len(train) < min_train or len(test) < min_test:
        return None
    return train, test


def split_observations_by_concept(
    observations_by_concept: dict[str, Sequence[bool]],
    *,
    concept_ids: Sequence[str] | None = None,
    test_size: int = DEFAULT_TEST_SIZE,
    min_train: int = DEFAULT_MIN_TRAIN,
    min_test: int = DEFAULT_MIN_TEST,
) -> tuple[list[ChronologicalSplit], list[str]]:
    """Split each concept sequence; return ``(usable_splits, skipped_concept_ids)``."""
    ordered_ids = (
        list(concept_ids)
        if concept_ids is not None
        else sorted(observations_by_concept.keys())
    )
    usable: list[ChronologicalSplit] = []
    skipped: list[str] = []
    for concept_id in ordered_ids:
        cid = concept_id.strip() if isinstance(concept_id, str) else ""
        if not cid:
            continue
        seq = observations_by_concept.get(cid, [])
        split = split_sequence_chronological(
            seq,
            test_size=test_size,
            min_train=min_train,
            min_test=min_test,
        )
        if split is None:
            skipped.append(cid)
            continue
        train, test = split
        usable.append(ChronologicalSplit(concept_id=cid, train=train, test=test))
    return usable, skipped
