"""The raw-evidence contract (version 1): what the agent hands to a factor package, and what comes back.

The agent stores evidence exactly as it fetched it (nothing cleaned). A factor package turns it into features with its own
`cleaning.py`, scores it, and returns a result that says what was removed. The training data is built from the same
structure, so a model never sees anything at training time that the tool cannot receive at run time.

Evidence for one student in one sprint:

    {
      "schema": "evidence/1",
      "student_id": "STU-007", "team_id": "T05",
      "sprint": {"id": "T05-S2", "start": "2026-02-02", "days": 14},
      "commits": [
        {"id": "...", "authored_at": "2026-02-03T10:12:00+05:30", "is_merge": false, "subject": "...",
         "files": [{"path": "api/orders.js", "status": "M", "added": 40, "deleted": 5,
                    "patch": "<unified diff or null>",
                    "line_stats": {"added": {"code": 30, "comment": 4, "blank": 6, "format_only": 0},
                                   "deleted": {...}}}]}          # line_stats OR patch; line_stats wins when both given
      ],
      "tasks": [
        {"id": "...", "title": "...", "description": "...", "acceptance_criteria": ["..."],
         "story_points": 5, "subtask_count": 3, "assignee": "STU-007", "status": "Done",
         "completed_by": "STU-007", "carried_over_from": null, "commit_ids": ["..."],
         "footprint": [{"path": "api/orders.js", "kind": "code", "reach_before": 3}]}   # structure before the task started
      ],
      "pull_requests": [{"id": "...", "author": "STU-007", "created_at": "...", "merged_at": null, "closed_at": null}],
      "reviews": [{"pr_id": "...", "reviewer": "STU-007", "pr_author": "STU-002", "state": "COMMENTED", "body": "...", "at": "..."}],
      "comments": [{"pr_id": "...", "author": "STU-007", "pr_author": "STU-002", "kind": "discussion",
                    "body": "...", "at": "...", "is_reply": false, "mentions": 0}],
      "merged_for_others": 0,
      "ownership": {"added_lines": 800, "surviving_lines": 560, "files": 12, "primary_files": 9, "owned_files": 4}
    }

Result of a factor tool:

    {"factor": "effort", "score": 0.61, "interval": [0.52, 0.70], "features": {...},
     "removed": {"comment": 120, "blank": 210, "docs_or_config": 340, "format_only": 15},
     "versions": {"cleaning": "1.0.0", "model": "..."}, "warnings": ["..."]}
"""

SCHEMA = "evidence/1"
REQUIRED = ("schema", "student_id", "sprint", "commits")
FILE_KEYS = ("path",)


def validate(evidence):
    """Raise ValueError listing everything wrong. Called by every factor package before it cleans anything."""
    problems = []
    for key in REQUIRED:
        if key not in evidence:
            problems.append(f"missing '{key}'")
    if evidence.get("schema") != SCHEMA:
        problems.append(f"schema must be '{SCHEMA}', got {evidence.get('schema')!r}")
    sprint = evidence.get("sprint") or {}
    for key in ("id", "start", "days"):
        if key not in sprint:
            problems.append(f"sprint missing '{key}'")
    for i, commit in enumerate(evidence.get("commits", [])):
        for key in ("id", "authored_at", "files"):
            if key not in commit:
                problems.append(f"commit {i} missing '{key}'")
        for j, f in enumerate(commit.get("files", [])):
            if "path" not in f:
                problems.append(f"commit {i} file {j} missing 'path'")
            if not f.get("line_stats") and not f.get("patch") and not (f.get("added") == 0 and f.get("deleted") == 0):
                problems.append(f"commit {i} file {j} ({f.get('path')}) needs line_stats or patch")
    if problems:
        raise ValueError("invalid evidence: " + "; ".join(problems))
    return True
