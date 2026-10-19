"""Where the Scrum board's data comes from, behind one small interface.

The Scrum MCP server (scrum_board_server.py) only talks to a ``ScrumSource``. ``CsvScrumSource`` reads the exported board data of the course dataset
(``factor_models/dataset``: roster.csv, sprints.csv, scrum_board/<team>.csv). When the planning module of the platform exposes the same data,
a database-backed source with the same methods replaces it and nothing else changes.

All methods return plain JSON-compatible dicts and lists. Nothing here ever returns another student's personal data beyond ids.
"""
import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE.parent / "factor_models" / "dataset"
CRITERION = re.compile(r"(?:^|;\s*)\d+\.\s*")


def parse_criteria(text):
    """'1. a; 2. b' -> ['a', 'b']. Plain text without numbering is kept as one criterion."""
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in CRITERION.split(text) if p.strip()]
    return parts or [text]


class ScrumSource:
    """The interface the MCP server needs."""

    def list_sprints(self, team_id): ...
    def get_sprint_details(self, sprint_id): ...
    def get_team_roster(self, team_id): ...
    def get_student_tasks(self, sprint_id, student_id): ...
    def get_task_acceptance_criteria(self, task_id): ...
    def get_task_status_history(self, task_id): ...


def _read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class CsvScrumSource(ScrumSource):
    def __init__(self, data_dir=None):
        self.dir = Path(data_dir or DEFAULT_DATA)
        self._sprints = _read(self.dir / "sprints.csv")
        self._roster = _read(self.dir / "roster.csv")
        self._tasks = {}
        for f in sorted((self.dir / "scrum_board").glob("*.csv")):
            for r in _read(f):
                self._tasks[r["task_id"]] = r

    def list_sprints(self, team_id):
        return [self._sprint(r) for r in self._sprints if r["team_id"] == team_id]

    @staticmethod
    def _sprint(r):
        return {"sprint_id": r["sprint_id"], "team_id": r["team_id"], "name": r["sprint_id"], "start_date": r["start_date"], "end_date": r["end_date"], "length_days": int(r["length_days"] or 0),
                "project_domain": r.get("project_domain", "")}

    def get_sprint_details(self, sprint_id):
        for r in self._sprints:
            if r["sprint_id"] == sprint_id:
                tasks = [t for t in self._tasks.values() if t["sprint_id"] == sprint_id]
                done = [t for t in tasks if t["status"].lower() == "done"]
                return {**self._sprint(r), "total_story_points": sum(int(t["story_points"] or 0) for t in tasks), "completed_story_points": sum(int(t["story_points"] or 0) for t in done),
                        "task_count": len(tasks)}
        return {"error": f"unknown sprint {sprint_id}"}

    def get_team_roster(self, team_id):
        return [{"student_id": r["student_id"], "team_id": team_id} for r in self._roster if r["team_id"] == team_id]

    def get_student_tasks(self, sprint_id, student_id):
        out = []
        for t in self._tasks.values():
            if t["sprint_id"] == sprint_id and (not student_id or t["assignee_id"] == student_id):
                out.append({"task_id": t["task_id"], "student_id": t["assignee_id"], "sprint_id": t["sprint_id"], "title": t["task_title"], "story": t["story"], "story_points": int(t["story_points"] or 0),
                            "subtask_count": int(t["subtask_count"] or 0), "status": t["status"], "completed_by": t["completed_by"] or None, "carried_over_from": t["carried_over_from"] or None,
                            "linked_commits": (t["linked_commits"] or "").split(), "description": t["description"]})
        return out

    def get_task_acceptance_criteria(self, task_id):
        t = self._tasks.get(task_id)
        if not t:
            return {"task_id": task_id, "title": "Unknown task", "description": "", "acceptance_criteria": []}
        return {"task_id": task_id, "title": t["task_title"], "description": t["description"], "acceptance_criteria": parse_criteria(t["acceptance_criteria"])}

    def get_task_status_history(self, task_id):
        """The exported board has only the final status, so the history is that single fact, marked as such (no invented timestamps)."""
        t = self._tasks.get(task_id)
        return [] if not t else [{"status": t["status"], "at": None, "source": "final_status_only"}]
