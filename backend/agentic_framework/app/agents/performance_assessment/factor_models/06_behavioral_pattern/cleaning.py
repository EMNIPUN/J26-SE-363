"""Behavioural Pattern: no cleaning of its own. It reads the other factors' scores, so it is only as clean as they are.

What this module does:
- Checks the inputs before the rules run: Effort, Consistency and Collaboration scores in [0, 1], the Consistency package's
  `C_bimodal` flag, and that those scores came from the same cleaning version.
- Records the open issue that matters in production: the rules need "high" and "low" thresholds. The proposal gives 0.7 and
  0.3, but calibrated scores rarely reach 0.7, so the dataset scripts used a cohort percentile (70th percentile, floor 0.35).
  A percentile is a property of a group of students, so the agent cannot compute it for one student. Before the Behavioural
  Pattern tool is used on a single student, the thresholds must be fixed numbers learned from the training cohort and stored
  with the rule set.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence.lines import CLEANING_VERSION  # noqa: E402

FEATURES_VERSION = "behavioral_pattern/1"
REQUIRED_SCORES = ("E", "C", "Co")


def validate_inputs(scores, flags, cleaning_versions=None):
    """Raise ValueError if the rule inputs are unusable. scores: {'E': .., 'C': .., 'Co': ..}; flags: {'C_bimodal': 0/1}."""
    problems = []
    for key in REQUIRED_SCORES:
        v = scores.get(key)
        if v is None or not 0.0 <= float(v) <= 1.0:
            problems.append(f"score {key} missing or outside [0, 1]: {v!r}")
    if flags.get("C_bimodal") not in (0, 1, True, False):
        problems.append("C_bimodal flag missing")
    versions = set((cleaning_versions or {}).values())
    if len(versions) > 1:
        problems.append(f"factor scores were prepared with different cleaning versions: {sorted(versions)}")
    if cleaning_versions and versions and CLEANING_VERSION not in versions:
        problems.append(f"scores were not prepared with the current cleaning version {CLEANING_VERSION}")
    if problems:
        raise ValueError("; ".join(problems))
    return True
