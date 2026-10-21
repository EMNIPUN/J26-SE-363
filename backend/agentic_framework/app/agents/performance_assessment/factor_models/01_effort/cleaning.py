"""Effort: what counts as effort, and the features, computed from raw evidence (cleaning version in evidence/lines.py).

What the Effort tool does with a student's sprint evidence:
- Lines that count: added and deleted `code` lines in source (`code` and `test`) files. Comment-only lines, docstrings,
  commented-out code, blank lines, formatting-only and moved lines, documentation, configuration, generated files, assets
  and data files do not count.
- Commits that count: not a merge, not a bulk upload (over 150 source files), and at least one counted line changed.
  A commit that only edits a README or reformats code is not effort.
- Files that count: source files with at least one counted line in a counted commit.
- The per-commit net line contribution is capped at 800, so one bulk-like commit cannot dominate.
- Tasks done: tasks assigned to the student, marked Done, and completed by them.
- Review activity: reviews and comments on other people's pull requests, plus merges of other people's pull requests.

Returns the features, what was removed, and warnings. Nothing here scores; scoring is the model's job.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence import schema  # noqa: E402
from evidence.common import COMMIT_CAP, commit_summary, meaningful_commits  # noqa: E402
from evidence.lines import CLEANING_VERSION, removed_summary  # noqa: E402

FEATURES_VERSION = "effort/1"
FEATURE_NAMES = ["E_CC", "E_LOC_added", "E_LOC_deleted", "E_LOC_net", "E_LOC_net_capped", "E_FC", "E_CT", "E_RD", "E_test_lines"]


def featurize(evidence):
    schema.validate(evidence)
    me = evidence["student_id"]
    kept = meaningful_commits(evidence)
    non_merge = [c for c in evidence["commits"] if not c.get("is_merge")]
    added = sum(s["added"] for _, s in kept)
    deleted = sum(s["deleted"] for _, s in kept)
    files = set().union(*(s["files"] for _, s in kept)) if kept else set()

    tasks = evidence.get("tasks", [])
    done = [t for t in tasks if t.get("assignee") == me and t.get("status") == "Done" and t.get("completed_by") in (me, None, "")]
    reviews = [r for r in evidence.get("reviews", []) if r.get("reviewer") == me and r.get("pr_author") != me]
    comments = [m for m in evidence.get("comments", []) if m.get("author") == me and m.get("pr_author") != me]

    features = {
        "E_CC": len(kept),
        "E_LOC_added": added,
        "E_LOC_deleted": deleted,
        "E_LOC_net": added - deleted,
        "E_LOC_net_capped": sum(max(-COMMIT_CAP, min(COMMIT_CAP, s["added"] - s["deleted"])) for _, s in kept),
        "E_FC": len(files),
        "E_CT": len(done),
        "E_RD": len(reviews) + len(comments) + int(evidence.get("merged_for_others", 0)),
        "E_test_lines": sum(s["test_added"] for _, s in kept),
    }
    all_files = [pair for c in non_merge for pair in commit_summary(c)["kinds_stats"]]
    warnings = []
    dropped = len(non_merge) - len(kept)
    if dropped:
        warnings.append(f"{dropped} commit(s) changed no counted source line and were not counted as effort")
    if not kept:
        warnings.append("no counted work in this sprint")
    return {"features": features, "removed": removed_summary(all_files), "commits_not_counted": dropped,
            "versions": {"cleaning": CLEANING_VERSION, "features": FEATURES_VERSION}, "warnings": warnings}
