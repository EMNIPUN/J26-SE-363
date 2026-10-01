"""Tests for student evidence isolation and filtering (T2.2 & PLAN.md Section 11)."""

import pytest
from app.agents.performance_assessment.com_agent.ingestion.github_client import (
    MockGitHubClient,
    RealGitHubClient,
    CountingGitHubClientWrapper,
    get_github_client,
)

@pytest.mark.asyncio
async def test_mock_github_client_commits_filtering():
    client = MockGitHubClient()
    commits = await client.get_commits(
        repo_url="https://github.com/org/project-repo",
        author_username="alice-perera",
        author_emails=["alice@student.sliit.lk", "alice.p@gmail.com"]
    )

    # 1. Total student commits returned (excluding merge commits and teammates)
    assert len(commits) == 12

    # 2. Verify all commits belong to Alice
    for c in commits:
        is_alice = (
            c["author"]["login"] == "alice-perera" or
            c["commit"]["author"]["email"] in ["alice@student.sliit.lk", "alice.p@gmail.com"]
        )
        assert is_alice, f"Commit {c['sha']} does not belong to Alice"
        # Verify NO merge commits
        assert len(c["parents"]) == 1, f"Commit {c['sha']} is a merge commit"

    # 3. Verify both emails are represented in the results
    emails = {c["commit"]["author"]["email"] for c in commits}
    assert "alice@student.sliit.lk" in emails
    assert "alice.p@gmail.com" in emails

@pytest.mark.asyncio
async def test_mock_github_client_date_window_filtering():
    client = MockGitHubClient()
    commits = await client.get_commits(
        repo_url="https://github.com/org/project-repo",
        author_username="alice-perera",
        author_emails=["alice@student.sliit.lk", "alice.p@gmail.com"],
        since="2025-09-02T00:00:00Z",
        until="2025-09-05T23:59:59Z"
    )
    # Should only return the 2 commits within Sept 2 - Sept 5
    assert len(commits) == 3
    for c in commits:
        date = c["commit"]["author"]["date"]
        assert "2025-09-02" <= date <= "2025-09-05T23:59:59Z"

@pytest.mark.asyncio
async def test_mock_github_client_pull_requests():
    client = MockGitHubClient()
    alice_prs = await client.get_pull_requests(
        repo_url="https://github.com/org/project-repo",
        author_username="alice-perera"
    )
    assert len(alice_prs) == 2
    for p in alice_prs:
        assert p["user"]["login"] == "alice-perera"

    bob_prs = await client.get_pull_requests(
        repo_url="https://github.com/org/project-repo",
        author_username="bob-silva"
    )
    assert len(bob_prs) == 2
    for p in bob_prs:
        assert p["user"]["login"] == "bob-silva"

@pytest.mark.asyncio
async def test_mock_github_client_reviews_and_issues():
    client = MockGitHubClient()

    # Alice reviews on Bob's PRs #3 and #4
    reviews = await client.get_review_comments(
        repo_url="https://github.com/org/project-repo",
        pr_ids=[3, 4, 103, 104],
        reviewer_username="alice-perera"
    )
    assert len(reviews) >= 2
    for r in reviews:
        assert r["user"]["login"] == "alice-perera"

    # Alice's issue comments on teammates' issues
    comments = await client.get_issue_comments(
        repo_url="https://github.com/org/project-repo",
        author_username="alice-perera"
    )
    assert len(comments) == 3
    for c in comments:
        assert c["user"]["login"] == "alice-perera"

@pytest.mark.asyncio
async def test_real_github_client_raises_not_implemented():
    real = RealGitHubClient()
    with pytest.raises(NotImplementedError):
        await real.get_commits("url", "user", ["e@e.com"])
    with pytest.raises(NotImplementedError):
        await real.get_pull_requests("url")
    with pytest.raises(NotImplementedError):
        await real.get_review_comments("url", [1])
    with pytest.raises(NotImplementedError):
        await real.get_issue_comments("url")

@pytest.mark.asyncio
async def test_counting_github_client_wrapper_rate_limit():
    state = {"github_api_call_count": 0, "github_sandbox_mode": False}
    client = CountingGitHubClientWrapper(
        underlying=MockGitHubClient(),
        state=state,
        max_calls=3
    )

    # Call 1
    await client.get_commits("url", "alice-perera", ["alice@student.sliit.lk"])
    assert state["github_api_call_count"] == 1
    assert state["github_sandbox_mode"] is False

    # Call 2
    await client.get_pull_requests("url")
    assert state["github_api_call_count"] == 2
    assert state["github_sandbox_mode"] is False

    # Call 3 -> Reaches cap of 3
    await client.get_issue_comments("url")
    assert state["github_api_call_count"] == 3
    assert state["github_sandbox_mode"] is True

def test_github_client_factory():
    client_dev = get_github_client(is_dev=True)
    assert isinstance(client_dev, CountingGitHubClientWrapper)
    assert isinstance(client_dev.underlying, MockGitHubClient)

    client_prod = get_github_client(is_dev=False)
    assert isinstance(client_prod, CountingGitHubClientWrapper)
    assert isinstance(client_prod.underlying, RealGitHubClient)

from app.agents.performance_assessment.com_agent.ingestion.git_sandbox_runner import (
    ALLOWED_GIT_COMMANDS,
    run_git_command,
    parse_git_log_to_commits,
    parse_git_diff_to_files,
    GitSandboxRunner,
)

# --- T2.3: GitSandboxRunner Tests ---

@pytest.mark.asyncio
async def test_git_sandbox_whitelist_enforcement():
    assert set(ALLOWED_GIT_COMMANDS) == {"log", "diff", "show", "shortlog", "blame"}

    # Forbidden subcommands must raise PermissionError
    for forbidden in ["push", "commit", "checkout", "reset", "rm", "branch", "clone"]:
        with pytest.raises(PermissionError):
            await run_git_command(repo_path=".", subcommand=forbidden)

def test_parse_git_log_to_commits():
    raw_log = """commit a1b2c3d4e5f67890
Author: Alice Perera <alice@student.sliit.lk>
Date:   2025-09-02T10:15:00Z

    Initial project setup and configuration

commit f9e8d7c6b5a43210
Author: Alice P <alice.p@gmail.com>
Date:   2025-09-03T14:30:00Z

    Implement session token generator
"""
    commits = parse_git_log_to_commits(raw_log)
    assert len(commits) == 2
    assert commits[0]["sha"] == "a1b2c3d4e5f67890"
    assert commits[0]["commit"]["author"]["name"] == "Alice Perera"
    assert commits[0]["commit"]["author"]["email"] == "alice@student.sliit.lk"
    assert commits[0]["commit"]["message"] == "Initial project setup and configuration"

    assert commits[1]["sha"] == "f9e8d7c6b5a43210"
    assert commits[1]["commit"]["author"]["email"] == "alice.p@gmail.com"

def test_parse_git_diff_to_files():
    raw_stat = """ backend/app/main.py   | 15 ++++++++++-----
 backend/app/auth.py   |  8 ++++++++
 2 files changed, 18 insertions(+), 5 deletions(-)
"""
    files = parse_git_diff_to_files(raw_stat)
    assert len(files) == 2
    assert files[0]["filename"] == "backend/app/main.py"
    assert files[0]["changes"] == 15
    assert files[0]["additions"] == 10
    assert files[0]["deletions"] == 5

    assert files[1]["filename"] == "backend/app/auth.py"
    assert files[1]["additions"] == 8
    assert files[1]["deletions"] == 0


@pytest.mark.asyncio
async def test_run_git_command_includes_author_flag(monkeypatch):
    """T8.2.7: run_git_command always includes --author flag in executed command."""
    captured_cmds = []

    class DummyProc:
        returncode = 0
        async def communicate(self):
            return b"commit dummy", b""

    async def mock_subprocess_exec(*cmd, **kwargs):
        captured_cmds.append(list(cmd))
        return DummyProc()

    monkeypatch.setattr("asyncio.create_subprocess_exec", mock_subprocess_exec)

    await run_git_command(
        repo_path="/path/to/repo",
        subcommand="log",
        author_filter="alice@student.sliit.lk",
    )

    assert len(captured_cmds) == 1
    cmd = captured_cmds[0]
    assert "git" in cmd
    assert "-C" in cmd
    assert "log" in cmd
    assert "--author=alice@student.sliit.lk" in cmd

