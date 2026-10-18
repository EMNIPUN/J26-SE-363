"""Requirement Fulfilment: what the judge reads, and the board-based features, computed from raw evidence.

Rules for the diff a language model reads for a task:
- Only source files (`code`, `test`), and only changed lines that are real work: comment lines, docstrings, blank lines,
  moved or re-indented lines and commented-out code are removed. A comment that says "handles empty cart" is not
  evidence that it does, and it is untrusted text a student controls, so it never reaches the judge.
- Documentation, configuration, generated files, assets and data files are left out of the diff.
- The diff is cut at a size limit with a visible marker, so the judge knows it did not see everything.
- Work finished by a teammate is not credited to the assignee.

Board features come straight from the task list; the judge's rating (1-4) is supplied on each task as `llm_rating`.
Features: RF_tasks_*, RF_completion_rate, RF_ac_ratio, RF_llm_score = mean (rating - 1) / 4, RF_carried_over,
RF_untracked_ratio = share of counted commits not linked to any task.
"""

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence import schema  # noqa: E402
from evidence.common import file_clean, meaningful_commits  # noqa: E402
from evidence.lines import CLEANING_VERSION, SOURCE_KINDS, clean_patch  # noqa: E402

FEATURES_VERSION = "requirement_fulfillment/1"
FEATURE_NAMES = ["RF_tasks_assigned", "RF_tasks_done", "RF_tasks_partial", "RF_tasks_not_started", "RF_done_by_teammate",
                 "RF_completion_rate", "RF_ac_total", "RF_ac_met", "RF_ac_ratio", "RF_llm_score", "RF_carried_over", "RF_untracked_ratio"]
MAX_DIFF_CHARS = 12000


def clean_task_diff(evidence, task, limit=MAX_DIFF_CHARS):
    """{'diff': str, 'truncated': bool, 'files': [paths]} for the task's commits, with comments and noise removed."""
    commits = {c["id"]: c for c in evidence["commits"]}
    parts, files = [], []
    for cid in task.get("commit_ids", []):
        for f in commits.get(cid, {}).get("files", []):
            kind, a, d, _ = file_clean(f)
            if kind not in SOURCE_KINDS or not f.get("patch") or not (a or d):
                continue
            body = clean_patch(f["path"], f["patch"])
            if body.strip():
                parts.append(f"--- {f['path']}\n{body}")
                files.append(f["path"])
    text = "\n".join(parts)
    truncated = len(text) > limit
    return {"diff": text[:limit] + ("\n[diff cut here]" if truncated else ""), "truncated": truncated, "files": files}


def featurize(evidence):
    schema.validate(evidence)
    me = evidence["student_id"]
    tasks = [t for t in evidence.get("tasks", []) if t.get("assignee") == me]
    done_self = [t for t in tasks if t.get("status") == "Done" and t.get("completed_by") in (me, None, "")]
    by_other = [t for t in tasks if t.get("completed_by") not in (me, None, "")]
    ac_total = sum(len(t.get("acceptance_criteria", [])) for t in tasks)
    ac_met = sum(int(t.get("criteria_met", 0)) for t in tasks if t.get("completed_by") in (me, None, ""))
    ratings = [(int(t["llm_rating"]) - 1) / 4 for t in tasks if t.get("llm_rating") is not None]
    kept = meaningful_commits(evidence)
    linked = {i for t in evidence.get("tasks", []) for i in t.get("commit_ids", [])}
    untracked = [c for c, _ in kept if c["id"] not in linked]
    features = {
        "RF_tasks_assigned": len(tasks),
        "RF_tasks_done": len(done_self),
        "RF_tasks_partial": sum(1 for t in tasks if t.get("status") in ("Partially Done", "In Progress")),
        "RF_tasks_not_started": sum(1 for t in tasks if t.get("status") == "To Do"),
        "RF_done_by_teammate": len(by_other),
        "RF_completion_rate": round(len(done_self) / len(tasks), 4) if tasks else None,
        "RF_ac_total": ac_total,
        "RF_ac_met": ac_met,
        "RF_ac_ratio": round(ac_met / ac_total, 4) if ac_total else None,
        "RF_llm_score": round(statistics.mean(ratings), 4) if ratings else None,
        "RF_carried_over": sum(1 for t in tasks if t.get("carried_over_from")),
        "RF_untracked_ratio": round(len(untracked) / len(kept), 4) if kept else None,
    }
    warnings = []
    if not tasks:
        warnings.append("no tasks assigned to this student in the sprint")
    if tasks and not ratings:
        warnings.append("tasks have no judge rating yet")
    return {"features": features, "removed": {}, "versions": {"cleaning": CLEANING_VERSION, "features": FEATURES_VERSION}, "warnings": warnings}
