"""Scrum board MCP server (stdio). The assessment agent calls these tools; it never reads the board's storage directly.

    python scrum_board_server.py                      # serves the course dataset; SCRUM_DATA_DIR overrides the folder

Tools: list_sprints, get_sprint_details, get_team_roster, get_student_tasks, get_task_acceptance_criteria, get_task_status_history.
The data comes from a ScrumSource (scrum_source.py); swap it for the planning module's source without touching the tools.
"""
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrum_source import CsvScrumSource  # noqa: E402

source = CsvScrumSource(os.environ.get("SCRUM_DATA_DIR") or None)
mcp = FastMCP("scrum-board")


@mcp.tool()
def list_sprints(team_id: str) -> list[dict]:
    """All sprints of a team with their dates."""
    return source.list_sprints(team_id)


@mcp.tool()
def get_sprint_details(sprint_id: str) -> dict:
    """Sprint metadata: dates, story points planned and completed."""
    return source.get_sprint_details(sprint_id)


@mcp.tool()
def get_team_roster(team_id: str) -> list[dict]:
    """Student ids of a team."""
    return source.get_team_roster(team_id)


@mcp.tool()
def get_student_tasks(sprint_id: str, student_id: str) -> list[dict]:
    """Tasks assigned to a student in a sprint (status, story points, subtasks, linked commits)."""
    return source.get_student_tasks(sprint_id, student_id)


@mcp.tool()
def get_task_acceptance_criteria(task_id: str) -> dict:
    """Description and the list of acceptance criteria of a task."""
    return source.get_task_acceptance_criteria(task_id)


@mcp.tool()
def get_task_status_history(task_id: str) -> list[dict]:
    """Column transitions of a task (the exported board gives only the final status)."""
    return source.get_task_status_history(task_id)


if __name__ == "__main__":
    mcp.run()
