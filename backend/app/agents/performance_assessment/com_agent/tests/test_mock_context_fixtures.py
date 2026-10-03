"""Unit tests for mock context fixtures (T0.4)."""

import json
import pathlib
import pytest

MOCK_DIR = pathlib.Path(__file__).resolve().parent.parent / "mock_context"

def test_student_context_fixture():
    student_file = MOCK_DIR / "student_context.json"
    assert student_file.exists(), "student_context.json must exist"
    with open(student_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_fields = [
        "student_id",
        "student_name",
        "student_github_username",
        "student_git_emails",
        "team_id",
        "sprint_id",
        "repo_url",
        "sprint_start",
        "sprint_end",
        "assigned_tasks",
    ]
    for field in required_fields:
        assert field in data, f"Missing required context field: {field}"
        assert data[field], f"Field {field} must not be empty"

    assert isinstance(data["student_git_emails"], list)
    assert len(data["student_git_emails"]) >= 2, "Must contain at least 2 emails to test multi-email identity resolution"

    assert isinstance(data["assigned_tasks"], list)
    assert len(data["assigned_tasks"]) >= 3, "Must contain at least 3 tasks"
    for task in data["assigned_tasks"]:
        assert "task_id" in task
        assert "title" in task
        assert "story_points" in task
        assert task["story_points"] > 0

def test_commits_fixture():
    commits_file = MOCK_DIR / "mock_github_responses" / "commits.json"
    assert commits_file.exists(), "commits.json must exist"
    with open(commits_file, "r", encoding="utf-8") as f:
        commits = json.load(f)

    assert isinstance(commits, list)
    assert len(commits) >= 12, "Must contain at least 12 commits"

    alice_emails = {"alice@student.sliit.lk", "alice.p@gmail.com"}
    found_emails = set()
    alice_commits = []
    teammate_commits = []
    merge_commits = []

    for c in commits:
        assert "sha" in c
        assert "author" in c
        assert "commit" in c
        assert "date" in c["commit"]["author"]
        assert "stats" in c
        assert "files" in c
        assert "parents" in c

        author_login = c["author"].get("login")
        author_email = c["commit"]["author"].get("email")

        if author_login == "alice-perera":
            alice_commits.append(c)
            found_emails.add(author_email)
            if len(c["parents"]) > 1:
                merge_commits.append(c)
        else:
            teammate_commits.append(c)

    assert len(alice_commits) >= 12, f"Expected >= 12 Alice commits, got {len(alice_commits)}"
    assert alice_emails.issubset(found_emails), f"Missing emails in Alice commits: {alice_emails - found_emails}"
    assert len(teammate_commits) >= 2, f"Expected >= 2 teammate commits, got {len(teammate_commits)}"
    assert len(merge_commits) >= 1, f"Expected >= 1 merge commit with parents > 1 for merge filtering test"


def test_pull_requests_fixture():
    pr_file = MOCK_DIR / "mock_github_responses" / "pull_requests.json"
    assert pr_file.exists(), "pull_requests.json must exist"
    with open(pr_file, "r", encoding="utf-8") as f:
        prs = json.load(f)

    assert isinstance(prs, list)
    assert len(prs) == 4, f"Expected exactly 4 PRs, got {len(prs)}"

    alice_prs = [p for p in prs if p["user"]["login"] == "alice-perera"]
    teammate_prs = [p for p in prs if p["user"]["login"] != "alice-perera"]

    assert len(alice_prs) == 2, f"Expected 2 PRs authored by Alice, got {len(alice_prs)}"
    assert len(teammate_prs) == 2, f"Expected 2 PRs authored by teammates, got {len(teammate_prs)}"

    # Test that Alice reviewed teammates' PRs (Collaboration depth)
    alice_reviews = []
    for p in teammate_prs:
        for r in p.get("reviews", []):
            if r["user"]["login"] == "alice-perera":
                alice_reviews.append(r)
                assert len(r["body"]) > 20, "Alice review comment must have substantive depth"

    assert len(alice_reviews) >= 2, f"Expected Alice to have reviewed teammates' PRs, got {len(alice_reviews)} reviews"

    # Test that Alice responded to review comments on her own PRs
    alice_response_comments = []
    for p in alice_prs:
        for c in p.get("comments", []):
            if c["user"]["login"] == "alice-perera":
                alice_response_comments.append(c)

    assert len(alice_response_comments) >= 1, "Expected Alice to have responded to comments on her PRs"


def test_issues_fixture():
    issues_file = MOCK_DIR / "mock_github_responses" / "issues.json"
    assert issues_file.exists(), "issues.json must exist"
    with open(issues_file, "r", encoding="utf-8") as f:
        comments = json.load(f)

    assert isinstance(comments, list)
    assert len(comments) == 6, f"Expected exactly 6 issue comments, got {len(comments)}"

    alice_comments = [c for c in comments if c["user"]["login"] == "alice-perera"]
    other_comments = [c for c in comments if c["user"]["login"] != "alice-perera"]

    assert len(alice_comments) == 3, f"Expected 3 Alice issue comments, got {len(alice_comments)}"
    assert len(other_comments) == 3, f"Expected 3 other issue comments, got {len(other_comments)}"

    # Test that Alice commented on teammates' issues (Collaboration)
    for c in alice_comments:
        assert c["issue_author"]["login"] != "alice-perera", "Alice comments must be on teammates' issues"
        assert "reactions" in c, "Reactions dictionary must be present"
        assert len(c["body"]) > 20, "Issue comment must have substantive technical depth"

    # Test mention detection (MC)
    has_mention = any("@" in c["body"] for c in alice_comments)
    assert has_mention, "Expected at least one Alice comment to mention a teammate (@username)"


def test_sprint_details_fixture():
    sprint_file = MOCK_DIR / "mock_scrum_responses" / "sprint_details.json"
    student_file = MOCK_DIR / "student_context.json"
    assert sprint_file.exists(), "sprint_details.json must exist"

    with open(sprint_file, "r", encoding="utf-8") as f:
        sprint_data = json.load(f)
    with open(student_file, "r", encoding="utf-8") as f:
        student_data = json.load(f)

    assert sprint_data["sprint_id"] == student_data["sprint_id"]
    assert sprint_data["start_date"] == student_data["sprint_start"]
    assert sprint_data["end_date"] == student_data["sprint_end"]
    assert sprint_data["status"] == "completed"
    assert sprint_data["completed_story_points"] > 0


def test_student_tasks_fixture():
    tasks_file = MOCK_DIR / "mock_scrum_responses" / "student_tasks.json"
    student_file = MOCK_DIR / "student_context.json"
    assert tasks_file.exists(), "student_tasks.json must exist"

    with open(tasks_file, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    with open(student_file, "r", encoding="utf-8") as f:
        student_data = json.load(f)

    assert isinstance(tasks, list)
    assert len(tasks) == 3, f"Expected 3 tasks, got {len(tasks)}"

    context_task_ids = {t["task_id"] for t in student_data["assigned_tasks"]}
    scrum_task_ids = {t["task_id"] for t in tasks}
    assert context_task_ids == scrum_task_ids, "Task IDs must match student_context.json"

    completed = [t for t in tasks if t["status"] == "Done"]
    in_progress = [t for t in tasks if t["status"] == "In Progress"]
    assert len(completed) == 2, f"Expected 2 completed tasks, got {len(completed)}"
    assert len(in_progress) == 1, f"Expected 1 in-progress task, got {len(in_progress)}"

    for t in tasks:
        assert t["student_id"] == "STU-001"
        assert t["story_points"] > 0
        assert t["subtask_count"] > 0


def test_task_acceptance_criteria_fixture():
    ac_file = MOCK_DIR / "mock_scrum_responses" / "task_acceptance_criteria.json"
    student_file = MOCK_DIR / "student_context.json"
    assert ac_file.exists(), "task_acceptance_criteria.json must exist"

    with open(ac_file, "r", encoding="utf-8") as f:
        ac_data = json.load(f)
    with open(student_file, "r", encoding="utf-8") as f:
        student_data = json.load(f)

    for task in student_data["assigned_tasks"]:
        tid = task["task_id"]
        assert tid in ac_data, f"Task {tid} must have acceptance criteria entry"
        entry = ac_data[tid]
        assert entry["task_id"] == tid
        assert len(entry["description"]) > 20, "Task description must be substantive"
        assert isinstance(entry["acceptance_criteria"], list)
        assert len(entry["acceptance_criteria"]) >= 3, f"Task {tid} must have at least 3 acceptance criteria"


def test_task_status_history_fixture():
    history_file = MOCK_DIR / "mock_scrum_responses" / "task_status_history.json"
    student_file = MOCK_DIR / "student_context.json"
    assert history_file.exists(), "task_status_history.json must exist"

    with open(history_file, "r", encoding="utf-8") as f:
        history_data = json.load(f)
    with open(student_file, "r", encoding="utf-8") as f:
        student_data = json.load(f)

    for task in student_data["assigned_tasks"]:
        tid = task["task_id"]
        assert tid in history_data, f"Task {tid} must have status history entry"
        transitions = history_data[tid]
        assert isinstance(transitions, list)
        assert len(transitions) >= 2, f"Task {tid} must have at least 2 status transitions"

        # Check chronological order
        timestamps = [t["timestamp"] for t in transitions]
        assert timestamps == sorted(timestamps), f"Transitions for {tid} must be chronological"

        columns = [t["column"] for t in transitions]
        assert columns[0] == "Todo", "First status must be 'Todo'"
        if task["status"] == "Done":
            assert columns[-1] == "Done", f"Completed task {tid} must end in 'Done'"
        else:
            assert columns[-1] != "Done", f"In-progress task {tid} must not end in 'Done'"
