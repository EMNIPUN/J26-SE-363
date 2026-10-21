"""Task Complexity: the structure of a task, measured on source files and the repository as it was before the task.

Rules:
- Footprint of a task = the source (`code`) files its commits change with at least one counted line. Tests, documentation,
  configuration, generated files, assets and data files are not part of the footprint, and a file touched only by
  comments, blank lines or reformatting is not either.
- Files involved (FI) = number of footprint files. Component breadth (CB) = number of distinct components (folders) they
  are in. Dependency reach (DR) = how many other files depend on the footprint files, summed, measured on the import
  graph of the repository before the task started and only for files that existed then (new files have nothing
  depending on them yet). The graph itself is built by ingestion from source files only, never from tests or generated code.
- Story points (SP) and subtask count (SC) are the team's own numbers and come straight from the board. Both are
  averaged over the student's tasks in the sprint, as are FI, DR and CB over the tasks that have a footprint.
- A task with no commits has no footprint; its structure features are missing, not zero.

Evidence: each task may carry `footprint` ([{"path", "kind", "reach_before"}], already cleaned) or `commit_ids`, in which
case the footprint is built from the evidence commits and `evidence["repo"]["reach_before"]` ({path: reach}).
"""

import statistics
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence import schema  # noqa: E402
from evidence.common import file_clean  # noqa: E402
from evidence.lines import CLEANING_VERSION  # noqa: E402

FEATURES_VERSION = "task_complexity/1"
FEATURE_NAMES = ["TC_SP", "TC_SP_total", "TC_SC", "TC_FI", "TC_DR", "TC_CB"]
SKIP_FOLDERS = {"src", "app", "main", "java", "com", "lib"}


def component(path):
    """The part of the system a file belongs to: its first two meaningful folders."""
    parts = [p for p in PurePosixPath(path).parts[:-1] if p not in SKIP_FOLDERS]
    return "/".join(parts[:2]) if parts else "(root)"


def footprint_from_commits(commits, reach_before):
    """Cleaned footprint of the commits that implement one task."""
    seen = {}
    for c in commits:
        for f in c["files"]:
            kind, a, d, _ = file_clean(f)
            if kind == "code" and (a or d):
                seen[f["path"]] = {"path": f["path"], "kind": "code", "reach_before": int(reach_before.get(f["path"], 0))}
    return list(seen.values())


def task_structure(footprint):
    files = [f for f in footprint if f.get("kind", "code") == "code"]
    if not files:
        return None
    return {"FI": len(files), "CB": len({component(f["path"]) for f in files}), "DR": sum(int(f.get("reach_before", 0)) for f in files)}


def featurize(evidence):
    schema.validate(evidence)
    me = evidence["student_id"]
    # a task's structure belongs to the task, whoever wrote the commits, so commits by teammates that implement the
    # student's tasks travel with the evidence as `task_commits`
    commits = {c["id"]: c for c in evidence["commits"] + evidence.get("task_commits", [])}
    reach = (evidence.get("repo") or {}).get("reach_before", {})
    tasks = [t for t in evidence.get("tasks", []) if t.get("assignee") == me]
    shapes, warnings = [], []
    for t in tasks:
        footprint = t.get("footprint")
        if footprint is None:
            mine = [commits[i] for i in t.get("commit_ids", []) if i in commits]
            footprint = footprint_from_commits(mine, reach) if mine else []
        s = task_structure(footprint)
        if s:
            shapes.append(s)
    missing = len(tasks) - len(shapes)
    if missing:
        warnings.append(f"{missing} task(s) have no source-file footprint, so their structure features are missing")
    sp = [int(t["story_points"]) for t in tasks if t.get("story_points") is not None]
    sc = [int(t["subtask_count"]) for t in tasks if t.get("subtask_count") is not None]
    mean = lambda xs: round(statistics.mean(xs), 3) if xs else None  # noqa: E731
    features = {"TC_SP": mean(sp), "TC_SP_total": sum(sp), "TC_SC": mean(sc),
                "TC_FI": mean([s["FI"] for s in shapes]), "TC_DR": mean([s["DR"] for s in shapes]), "TC_CB": mean([s["CB"] for s in shapes])}
    return {"features": features, "removed": {}, "tasks_without_footprint": missing,
            "versions": {"cleaning": CLEANING_VERSION, "features": FEATURES_VERSION}, "warnings": warnings}
