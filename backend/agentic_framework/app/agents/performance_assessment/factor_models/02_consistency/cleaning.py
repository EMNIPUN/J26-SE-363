"""Consistency: which days count as active, and the rhythm features, computed from raw evidence.

Rules:
- A day is active only if the student made a counted commit that day (same definition of counted commit as Effort:
  not a merge, not a bulk upload, at least one counted source line). A README tweak or a reformat does not make a day active.
- The size of a day's work is the counted lines changed (added + deleted) that day, each commit capped at 800, and at least 1
  for a counted commit. Comments, blank lines, docs, config and moved lines do not make a heavy day.
- Days are taken from the commit's own local date, relative to the sprint start.
- Commits dated outside the sprint window are ignored.

Features: C_AWR active-day share; C_DC share of work in the last 3 days; C_LI_norm longest idle stretch / days;
C_CV_norm rhythm spread (coefficient of variation of daily work, scaled to 0-1); C_first_active_day; C_bimodal two bursts.
"""

import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence import schema  # noqa: E402
from evidence.common import COMMIT_CAP, day_index, meaningful_commits  # noqa: E402
from evidence.lines import CLEANING_VERSION  # noqa: E402

FEATURES_VERSION = "consistency/1"
FEATURE_NAMES = ["C_AWR", "C_DC", "C_LI_norm", "C_CV_norm", "C_first_active_day", "C_bimodal", "C_no_activity"]
DEADLINE_DAYS = 3


def longest_gap(active, days):
    longest = run = 0
    for d in range(days):
        run = 0 if d in active else run + 1
        longest = max(longest, run)
    return longest


def bursts(active_days, churn_by_day, gap=4, share=0.2):
    """True when the work falls into two or more bursts separated by more than `gap` idle days, each holding at least
    `share` of the sprint's work."""
    if len(active_days) < 2:
        return False
    days = sorted(active_days)
    groups, current = [], [days[0]]
    for d in days[1:]:
        if d - current[-1] > gap:
            groups.append(current)
            current = [d]
        else:
            current.append(d)
    groups.append(current)
    total = sum(churn_by_day.values()) or 1
    return sum(1 for g in groups if sum(churn_by_day.get(d, 0) for d in g) / total >= share) >= 2


def featurize(evidence):
    schema.validate(evidence)
    sprint = evidence["sprint"]
    days = int(sprint["days"])
    churn, active, ignored = {}, set(), 0
    for c, s in meaningful_commits(evidence):
        d = day_index(c["authored_at"], sprint["start"])
        if not 0 <= d < days:
            ignored += 1
            continue
        active.add(d)
        churn[d] = churn.get(d, 0) + (min(COMMIT_CAP, s["added"] + s["deleted"]) or 1)
    warnings = [f"{ignored} counted commit(s) fall outside the sprint window and were ignored"] if ignored else []
    if not active:
        features = {"C_AWR": 0.0, "C_DC": 1.0, "C_LI_norm": 1.0, "C_CV_norm": 1.0, "C_first_active_day": None,
                    "C_bimodal": 0, "C_no_activity": 1}
        warnings.append("no counted work in this sprint")
    else:
        daily = [churn.get(d, 0) for d in range(days)]
        total = sum(daily)
        mean = total / days
        cv = statistics.pstdev(daily) / mean if mean else 0
        features = {
            "C_AWR": round(len(active) / days, 4),
            "C_DC": round(sum(daily[-DEADLINE_DAYS:]) / total, 4),
            "C_LI_norm": round(longest_gap(active, days) / days, 4),
            "C_CV_norm": round(min(1.0, cv / math.sqrt(days - 1)), 4),
            "C_first_active_day": min(active),
            "C_bimodal": int(bursts(active, churn)),
            "C_no_activity": 0,
        }
    return {"features": features, "removed": {}, "versions": {"cleaning": CLEANING_VERSION, "features": FEATURES_VERSION}, "warnings": warnings}
