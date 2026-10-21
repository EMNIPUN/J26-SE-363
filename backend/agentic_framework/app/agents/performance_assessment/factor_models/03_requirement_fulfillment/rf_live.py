"""Requirement Fulfillment on real evidence: the same sub-agent as the experiments (experiments/agent_critic.py), reading a real student's commits instead of the synthetic benchmark.

``EvidenceBench`` has the few methods the agent's student-only ``Scope`` needs (student_commits, tasks_of, task_public, hunk, task_commits), built from one student's
``evidence/1`` plus the unified diffs of their commits (``patches``: {sha: {path: patch}}), cleaned with evidence.lines.clean_patch (comment, blank and format-only lines removed).

Only the student's own commits are visible to the agent: the evidence of one student never contains a teammate's code, and ``Scope`` exposes no other student's data.
"""
import sys
from pathlib import Path

FM = Path(__file__).resolve().parents[1]
if str(FM) not in sys.path:
    sys.path.insert(0, str(FM))

from evidence import lines as _lines  # noqa: E402


# What the language model may be shown. Source and test code, and configuration: many tasks (deployment, gateway, pipeline) are done in configuration files, and a judge that cannot see
# them can only say "not met". Documents, generated files and data are never shown.
VISIBLE_KINDS = tuple(_lines.SOURCE_KINDS) + ("config",)


class EvidenceBench:
    def __init__(self, evidence: dict, patches: dict | None = None):
        self.ev, self.patches = evidence, patches or {}
        self.student = evidence["student_id"]
        self.sprint = evidence["sprint"]["id"]
        self._commits = []
        for c in evidence.get("commits", []):
            if c.get("is_merge"):
                continue
            files = []
            for f in c["files"]:
                if f.get("kind", _lines.classify_path(f["path"])) not in VISIBLE_KINDS:
                    continue
                stats = f.get("line_stats") or {}
                a, d = stats.get("added", {}).get("code", 0), stats.get("deleted", {}).get("code", 0)
                if a or d:
                    files.append({"path": f["path"], "added": a, "deleted": d, "kind": f.get("kind", "code")})
            if files:
                self._commits.append({"sha": c["id"], "date": c["authored_at"], "message": c.get("subject", ""), "author": self.student, "files": files})
        self.commits = {c["sha"]: c for c in self._commits}  # the agent's first step reads the files of the commits it picked from here
        self._tasks = {t["id"]: t for t in evidence.get("tasks", []) if t.get("assignee") == self.student and t.get("acceptance_criteria")}
        self._cache = {}

    # ---- the interface Scope and the agent use ---------------------------------------------------------------------------------------
    def student_commits(self, sprint, student):
        return list(self._commits) if (sprint, student) == (self.sprint, self.student) else []

    def tasks_of(self, sprint, student):
        return list(self._tasks) if (sprint, student) == (self.sprint, self.student) else []

    def task_public(self, tid):
        t = self._tasks[tid]
        return {"id": tid, "title": t.get("title", ""), "description": t.get("description", ""), "criteria": list(t["acceptance_criteria"]), "points": t.get("story_points", 0),
                "subtasks": t.get("subtask_count", 0), "carried_over": bool(t.get("carried_over_from")), "completed_by_teammate": t.get("completed_by") not in (self.student, None, "")}

    def task_commits(self, tid):
        """The truth mapping the experiments measure against does not exist for real students."""
        return []

    def hunk(self, sha, path):
        """Cleaned changed lines of one file of one commit: ["-old", ..., "+new", ...] (deleted lines first), as the benchmark gives them."""
        key = (sha, path)
        if key not in self._cache:
            patch = (self.patches.get(sha) or {}).get(path)
            rows = _lines.clean_patch(path, patch).splitlines() if patch else []
            self._cache[key] = [r for r in rows if r[:1] == "-" and not r.startswith("---")] + [r for r in rows if r[:1] == "+" and not r.startswith("+++")]
        return self._cache[key]

    # ---- helpers for the evaluator ---------------------------------------------------------------------------------------------------
    def should_judge(self, tid, provisional=False):
        """A task is judged by the language model unless it plainly has not been started (status To Do and no linked commit); during a sprint only tasks that are Done or In Review."""
        t = self._tasks[tid]
        status = (t.get("status") or "").lower()
        if provisional:
            return status in ("done", "in review")
        return not (status == "to do" and not t.get("commit_ids"))
