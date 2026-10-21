"""Where the Scrum board's data comes from, behind one small interface.

The Scrum MCP server (scrum_board_server.py) only talks to a ``ScrumSource``. ``CsvScrumSource`` reads the exported board data of the course dataset
(``factor_models/dataset``: roster.csv, sprints.csv, scrum_board/<team>.csv). When the planning module of the platform exposes the same data,
a database-backed source with the same methods replaces it and nothing else changes.

All methods return plain JSON-compatible dicts and lists. Nothing here ever returns another student's personal data beyond ids.
"""
import csv
import json
import os
import re
from datetime import date, datetime
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


def _fixture_dirs():
    dirs = []
    if os.environ.get("SCRUM_SIMULATOR_DATA_DIR"):
        dirs.append(Path(os.environ["SCRUM_SIMULATOR_DATA_DIR"]))
    for p in [HERE.parents[4], HERE.parents[3]]:
        cand = p / "server" / "data" / "scrum_simulator"
        if cand.exists() and cand not in dirs:
            dirs.append(cand)
    return dirs


class ScrumSource:
    """The interface the MCP server needs."""

    def list_sprints(self, team_id): ...
    def get_sprint_details(self, sprint_id): ...
    def get_team_roster(self, team_id): ...
    def get_student_tasks(self, sprint_id, student_id): ...
    def get_task_acceptance_criteria(self, task_id): ...
    def get_task_status_history(self, task_id): ...


def _read(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class CsvScrumSource(ScrumSource):
    def __init__(self, data_dir=None):
        self.dir = Path(data_dir or DEFAULT_DATA)
        self._sprints = _read(self.dir / "sprints.csv")
        self._roster = _read(self.dir / "roster.csv")
        self._tasks = {}
        if (self.dir / "scrum_board").exists():
            for f in sorted((self.dir / "scrum_board").glob("*.csv")):
                for r in _read(f):
                    self._tasks[r["task_id"]] = r

        # Load simulated JSON fixtures
        self._json_fixtures = []
        for d in _fixture_dirs():
            if d.exists():
                for jf in sorted(d.glob("*.json")):
                    if jf.name.endswith(".schema.json"):
                        continue
                    try:
                        data = json.loads(jf.read_text(encoding="utf-8"))
                        if isinstance(data, dict) and "sprints" in data:
                            self._json_fixtures.append(data)
                    except Exception:
                        pass

    def list_sprints(self, team_id):
        # 1. Match from JSON fixtures
        for fix in self._json_fixtures:
            proj = fix.get("project") or {}
            if proj.get("project_id") == team_id or len(self._json_fixtures) == 1:
                return [
                    {
                        "sprint_id": s["sprint_id"],
                        "team_id": proj.get("project_id", team_id),
                        "name": s.get("name", s["sprint_id"]),
                        "start_date": str(s["start_date"]),
                        "end_date": str(s["end_date"]),
                        "length_days": (datetime.fromisoformat(str(s["end_date"])).date() - datetime.fromisoformat(str(s["start_date"])).date()).days if "end_date" in s and "start_date" in s else 14,
                        "project_domain": proj.get("project_domain", ""),
                    }
                    for s in fix.get("sprints", [])
                ]
        # 2. Match from CSV
        return [self._sprint(r) for r in self._sprints if r["team_id"] == team_id]

    @staticmethod
    def _sprint(r):
        return {"sprint_id": r["sprint_id"], "team_id": r["team_id"], "name": r["sprint_id"], "start_date": r["start_date"], "end_date": r["end_date"], "length_days": int(r["length_days"] or 0),
                "project_domain": r.get("project_domain", "")}

    def get_sprint_details(self, sprint_id):
        # 1. Check JSON fixtures
        for fix in self._json_fixtures:
            sprint = next((s for s in fix.get("sprints", []) if s.get("sprint_id") == sprint_id), None)
            if sprint:
                tasks = [t for t in fix.get("tasks", []) if t.get("sprint_id") == sprint_id]
                done = [t for t in tasks if str(t.get("status", "")).lower() == "done"]
                start_d = str(sprint["start_date"])
                end_d = str(sprint["end_date"])
                try:
                    days = (datetime.fromisoformat(end_d).date() - datetime.fromisoformat(start_d).date()).days
                except Exception:
                    days = 14
                proj = fix.get("project") or {}
                return {
                    "sprint_id": sprint["sprint_id"],
                    "team_id": proj.get("project_id", ""),
                    "name": sprint.get("name", sprint["sprint_id"]),
                    "start_date": start_d,
                    "end_date": end_d,
                    "length_days": days,
                    "project_domain": proj.get("project_domain", ""),
                    "total_story_points": sum(int(t.get("story_points") or 0) for t in tasks),
                    "completed_story_points": sum(int(t.get("story_points") or 0) for t in done),
                    "task_count": len(tasks),
                }

        # 2. Check CSV
        for r in self._sprints:
            if r["sprint_id"] == sprint_id:
                tasks = [t for t in self._tasks.values() if t["sprint_id"] == sprint_id]
                done = [t for t in tasks if t["status"].lower() == "done"]
                return {**self._sprint(r), "total_story_points": sum(int(t["story_points"] or 0) for t in tasks), "completed_story_points": sum(int(t["story_points"] or 0) for t in done),
                        "task_count": len(tasks)}
        return {"error": f"unknown sprint {sprint_id}"}

    def get_team_roster(self, team_id):
        for fix in self._json_fixtures:
            proj = fix.get("project") or {}
            if proj.get("project_id") == team_id or len(self._json_fixtures) == 1:
                return [
                    {"student_id": s["student_id"], "name": s.get("name", ""), "email": s.get("email", ""), "team_id": team_id}
                    for s in fix.get("students", [])
                ]
        return [{"student_id": r["student_id"], "team_id": team_id} for r in self._roster if r["team_id"] == team_id]

    def get_student_tasks(self, sprint_id, student_id):
        # 1. Check JSON fixtures
        for fix in self._json_fixtures:
            tasks = [t for t in fix.get("tasks", []) if t.get("sprint_id") == sprint_id]
            if tasks:
                out = []
                for t in tasks:
                    assignees = t.get("assignee_ids") or ([t["assignee_id"]] if "assignee_id" in t else [])
                    if not student_id or student_id in assignees or student_id == t.get("student_id"):
                        out.append({
                            "task_id": t["task_id"],
                            "student_id": assignees[0] if assignees else "",
                            "student_ids": assignees,
                            "sprint_id": t["sprint_id"],
                            "title": t.get("title", ""),
                            "story": t.get("title", ""),
                            "story_points": int(t.get("story_points") or 0),
                            "subtask_count": int(t.get("subtask_count") or 0),
                            "status": t.get("status", "todo"),
                            "completed_by": t.get("completed_by") or None,
                            "carried_over_from": t.get("carried_over_from") or None,
                            "linked_commits": t.get("linked_commits") or [],
                            "description": t.get("description", ""),
                        })
                return out

        # 2. Check CSV
        out = []
        for t in self._tasks.values():
            if t["sprint_id"] == sprint_id and (not student_id or t["assignee_id"] == student_id):
                out.append({"task_id": t["task_id"], "student_id": t["assignee_id"], "sprint_id": t["sprint_id"], "title": t["task_title"], "story": t["story"], "story_points": int(t["story_points"] or 0),
                            "subtask_count": int(t["subtask_count"] or 0), "status": t["status"], "completed_by": t["completed_by"] or None, "carried_over_from": t["carried_over_from"] or None,
                            "linked_commits": (t["linked_commits"] or "").split(), "description": t["description"]})
        return out

    def get_task_acceptance_criteria(self, task_id):
        # 1. Check JSON fixtures
        for fix in self._json_fixtures:
            t = next((x for x in fix.get("tasks", []) if x.get("task_id") == task_id), None)
            if t:
                crit = t.get("acceptance_criteria") or []
                if isinstance(crit, str):
                    crit = parse_criteria(crit)
                return {
                    "task_id": task_id,
                    "title": t.get("title", ""),
                    "description": t.get("description", ""),
                    "acceptance_criteria": crit,
                }

        # 2. Check CSV
        t = self._tasks.get(task_id)
        if not t:
            return {"task_id": task_id, "title": "Unknown task", "description": "", "acceptance_criteria": []}
        return {"task_id": task_id, "title": t["task_title"], "description": t["description"], "acceptance_criteria": parse_criteria(t["acceptance_criteria"])}

    def get_task_status_history(self, task_id):
        # 1. Check JSON fixtures
        for fix in self._json_fixtures:
            hist = fix.get("status_history", {}).get(task_id)
            if hist:
                return hist
            t = next((x for x in fix.get("tasks", []) if x.get("task_id") == task_id), None)
            if t:
                return [{"status": t.get("status", "unknown"), "at": None, "source": "fixture_final_status"}]

        # 2. Check CSV
        t = self._tasks.get(task_id)
        return [] if not t else [{"status": t["status"], "at": None, "source": "final_status_only"}]
