"""Student-only access to a repository and a board (plan.md, section 3).

A ``Scope`` is created for one student and one sprint. Every tool closes over that pair; none takes a student argument, so a model
cannot name another student. Teammates' commits, hunks and tasks are never returned: not by listing, not by reading a commit id
that happens to be known, not by searching for a string that only a teammate wrote. ``tests/test_scope.py`` tries each of these.

Tool results are plain text, size-capped, and every line a tool returns is recorded so that the share of the student's changed
lines that was actually read ("coverage") and the evidence a verdict cites can be checked by code.
"""

import re

from .schema import est_tokens

MAX_READ_LINES = 120
MAX_SEARCH_RESULTS = 25
MAX_LIST = 60


class Scope:
    def __init__(self, bench, sprint, student):
        self.bench, self.sprint, self.student = bench, sprint, student
        self._own = {c["sha"]: c for c in bench.student_commits(sprint, student)}
        self.seen = set()          # (sha, path, line_index) of every changed line returned to the model
        self.calls = []            # (tool, args) log
        self.tool_tokens = 0

    # --- bookkeeping ---------------------------------------------------------------------------------------------------

    def _log(self, tool, **args):
        self.calls.append((tool, args))

    def _out(self, text):
        self.tool_tokens += est_tokens(text)
        return text

    def total_lines(self, shas=None):
        return sum(f["added"] + f["deleted"] for s, c in self._own.items() if shas is None or s in shas for f in c["files"])

    def coverage(self, shas=None):
        """Share of the student's changed lines (optionally of some commits) that the model has been shown."""
        total = self.total_lines(shas)
        seen = sum(1 for (s, _, _) in self.seen if shas is None or s in shas)
        return min(1.0, seen / total) if total else 1.0

    # --- tools ---------------------------------------------------------------------------------------------------------

    def my_tasks(self):
        """The student's own tasks for the sprint. No status, no other student's task."""
        self._log("my_tasks")
        rows = []
        for tid in self.bench.tasks_of(self.sprint, self.student):
            t = self.bench.task_public(tid)
            flag = " [completed by a teammate]" if t["completed_by_teammate"] else ""
            flag += " [carried over from an earlier sprint]" if t["carried_over"] else ""
            crit = "\n".join(f"    C{i + 1}. {c}" for i, c in enumerate(t["criteria"]))
            rows.append(f"{t['id']} | {t['title']} | {t['points']} points, {t['subtasks']} subtasks{flag}\n  {t['description']}\n{crit}")
        return self._out("\n".join(rows) if rows else "no tasks assigned")

    def list_commits(self):
        """The student's commits in the sprint: id, date, message, counted lines per file."""
        self._log("list_commits")
        out = []
        for c in list(self._own.values())[:MAX_LIST * 4]:
            files = ", ".join(f"{f['path']}(+{f['added']}/-{f['deleted']})" for f in c["files"][:8])
            more = f" … {len(c['files']) - 8} more files" if len(c["files"]) > 8 else ""
            out.append(f"{c['sha']} {c['date'][:10]} {c['message']} | {files or 'no source files'}{more}")
        return self._out("\n".join(out) if out else "no commits")

    def task_commit_hints(self, task_id):
        """Commits of the student whose message names the task. Others may belong to it too; this only finds the ones that say so."""
        self._log("task_commit_hints", task_id=task_id)
        if task_id not in self.bench.tasks_of(self.sprint, self.student):
            return self._out(f"unknown task {task_id}")
        hits = [c for c in self._own.values() if task_id in c["message"]]
        return self._out("\n".join(f"{c['sha']} {c['date'][:10]} {c['message']}" for c in hits) or "no commit message names this task")

    def list_changes(self, sha):
        self._log("list_changes", sha=sha)
        c = self._own.get(sha)
        if not c:
            return self._out(f"unknown commit {sha}")
        return self._out(f"{sha} {c['message']}\n" + "\n".join(f"{f['path']} +{f['added']} -{f['deleted']}" for f in c["files"]))

    def read_hunk(self, sha, path, start=0, max_lines=MAX_READ_LINES):
        """Cleaned changed lines of one file of one commit from line ``start``, capped. Returns a continuation hint."""
        self._log("read_hunk", sha=sha, path=path, start=start)
        c = self._own.get(sha)
        if not c or not any(f["path"] == path for f in c["files"]):
            return self._out(f"unknown commit or file: {sha} {path}")
        lines = self.bench.hunk(sha, path)
        start = max(0, int(start))
        end = min(len(lines), start + min(int(max_lines), MAX_READ_LINES))
        for i in range(start, end):
            self.seen.add((sha, path, i))
        body = "\n".join(f"{i}: {lines[i]}" for i in range(start, end))
        tail = f"\n[{len(lines) - end} more lines; continue with start={end}]" if end < len(lines) else "\n[end of file]"
        return self._out(f"{sha} {path} lines {start}-{end - 1} of {len(lines)}\n{body}{tail}")

    def search_changes(self, query, max_results=MAX_SEARCH_RESULTS):
        """Case-insensitive search of the student's own changed lines. Returns commit, file, line index and the line."""
        self._log("search_changes", query=query)
        try:
            rx = re.compile(query, re.I)
        except re.error:
            rx = re.compile(re.escape(query), re.I)
        hits = []
        for sha, c in self._own.items():
            for f in c["files"]:
                for i, line in enumerate(self.bench.hunk(sha, f["path"])):
                    if line.startswith("+") and rx.search(line):
                        hits.append((sha, f["path"], i, line))
                        if len(hits) >= max_results:
                            break
                if len(hits) >= max_results:
                    break
            if len(hits) >= max_results:
                break
        for sha, path, i, _ in hits:
            self.seen.add((sha, path, i))
        text = "\n".join(f"{sha} {path}:{i}: {line}" for sha, path, i, line in hits)
        return self._out(text or "no match in your changes")

    # --- facts for scoring (not tools) -------------------------------------------------------------------------------------

    def own_shas(self):
        return set(self._own)
