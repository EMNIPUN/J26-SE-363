"""Evidence helpers used by more than one factor package: per-file clean counts, meaningful commits, sprint days."""

from datetime import date, datetime

from . import lines
from .lines import SOURCE_KINDS, classify_path, clean_counts, stats_from_patch

BULK_FILES = 150   # a commit touching more source files than this is a re-upload or scaffold, not authored work
COMMIT_CAP = 800   # net clean lines one ordinary commit can contribute to the capped total


def file_stats(f):
    """line_stats of an evidence file entry, from its patch when no counts were supplied."""
    if f.get("line_stats"):
        return f["line_stats"]
    if f.get("patch"):
        return stats_from_patch(f["path"], f["patch"])
    return None


def file_clean(f):
    """(kind, clean_added, clean_deleted, stats) for an evidence file entry."""
    kind = f.get("kind") or classify_path(f["path"])
    stats = file_stats(f)
    a, d = clean_counts(kind, stats)
    return kind, a, d, stats


def commit_summary(commit):
    """Clean totals of one commit: source files with real changes, clean lines, and what was removed."""
    files, added, deleted, test_added, touched, sources = [], 0, 0, 0, set(), 0
    for f in commit["files"]:
        kind, a, d, stats = file_clean(f)
        files.append((kind, stats))
        if kind in SOURCE_KINDS:
            sources += 1
        if a or d:
            touched.add(f["path"])
            added += a
            deleted += d
            if kind == "test":
                test_added += a
    return {"added": added, "deleted": deleted, "test_added": test_added, "files": touched,
            "source_files": sources, "kinds_stats": files}


def meaningful_commits(evidence):
    """Commits that count as work: not a merge, not a bulk upload, and at least one clean source line changed.
    Returns [(commit, summary)]."""
    out = []
    for c in evidence["commits"]:
        if c.get("is_merge"):
            continue
        summary = commit_summary(c)
        if summary["source_files"] > BULK_FILES:
            continue
        if summary["added"] + summary["deleted"] == 0:
            continue
        out.append((c, summary))
    return out


def day_index(authored_at, sprint_start):
    """Days since the sprint start, in the commit's own local date."""
    return (datetime.fromisoformat(authored_at).date() - date.fromisoformat(sprint_start)).days
