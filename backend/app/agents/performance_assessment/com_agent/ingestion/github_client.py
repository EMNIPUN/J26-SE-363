"""GitHub client adapter layer for com_agent evidence gathering.

Strictly aligned with:
- PLAN.md Section 4 (GitHub Hybrid Evidence Strategy)
- PLAN.md Section 5 (Clean Student Author Filtering & Merge Commit Exclusion)
- PLAN.md Section 12.6 (Retry Policy on Remote Calls)
- PLAN.md Section 12.7 (GitHub API Rate Limiting & Sandbox Mode Fallback)
"""

import abc
import json
import logging
import pathlib
from typing import Dict, List, Optional, Any
from app.agents.performance_assessment.com_agent.policies.retry_policy import retry_with_backoff
from app.agents.performance_assessment.com_agent.config.settings_loader import settings, IS_DEV_MODE

logger = logging.getLogger(__name__)

MOCK_GITHUB_DIR = (
    pathlib.Path(__file__).resolve().parent.parent / "mock_context" / "mock_github_responses"
)


class GitHubClientProtocol(abc.ABC):
    """Abstract interface contract for GitHub API data gathering."""

    @abc.abstractmethod
    async def get_commits(
        self,
        repo_url: str,
        author_username: str,
        author_emails: List[str],
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve commits authored by student, excluding merge commits."""
        pass

    @abc.abstractmethod
    async def get_pull_requests(
        self,
        repo_url: str,
        author_username: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve pull requests within sprint window."""
        pass

    @abc.abstractmethod
    async def get_review_comments(
        self,
        repo_url: str,
        pr_ids: Optional[List[int]] = None,
        reviewer_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve review comments submitted by student on pull requests."""
        pass

    @abc.abstractmethod
    async def get_issue_comments(
        self,
        repo_url: str,
        author_username: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve issue discussion comments submitted by student."""
        pass


class MockGitHubClient(GitHubClientProtocol):
    """Mock GitHub client serving realistic responses from JSON fixtures."""

    def __init__(self, mock_dir: Optional[pathlib.Path] = None):
        self.mock_dir = mock_dir or MOCK_GITHUB_DIR

    def _load_fixture(self, filename: str) -> Any:
        path = self.mock_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Mock fixture not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.1)
    async def get_commits(
        self,
        repo_url: str,
        author_username: str,
        author_emails: List[str],
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raw_commits: List[Dict[str, Any]] = self._load_fixture("commits.json")
        email_set = set(e.lower() for e in author_emails)
        username_lower = author_username.lower()

        filtered: List[Dict[str, Any]] = []
        for c in raw_commits:
            # Exclude merge commits (parents > 1) per PLAN.md §5
            parents = c.get("parents", [])
            if len(parents) > 1:
                continue

            # Author identity match (login OR email)
            author_login = c.get("author", {}).get("login", "").lower()
            commit_email = c.get("commit", {}).get("author", {}).get("email", "").lower()
            is_author = (author_login == username_lower) or (commit_email in email_set)
            if not is_author:
                continue

            # Date window match
            commit_date = c.get("commit", {}).get("author", {}).get("date", "")
            if since and commit_date < since:
                continue
            if until and commit_date > until:
                continue

            filtered.append(c)

        return filtered

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.1)
    async def get_pull_requests(
        self,
        repo_url: str,
        author_username: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raw_prs: List[Dict[str, Any]] = self._load_fixture("pull_requests.json")
        filtered: List[Dict[str, Any]] = []

        for p in raw_prs:
            if author_username:
                pr_user = p.get("user", {}).get("login", "")
                if pr_user.lower() != author_username.lower():
                    continue

            created_at = p.get("created_at", "")
            if since and created_at < since:
                continue
            if until and created_at > until:
                continue

            filtered.append(p)

        return filtered

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.1)
    async def get_review_comments(
        self,
        repo_url: str,
        pr_ids: Optional[List[int]] = None,
        reviewer_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raw_prs: List[Dict[str, Any]] = self._load_fixture("pull_requests.json")
        pr_id_set = set(pr_ids) if pr_ids else set()
        reviewer_lower = reviewer_username.lower() if reviewer_username else None

        collected_reviews: List[Dict[str, Any]] = []
        for p in raw_prs:
            if pr_ids and p.get("id") not in pr_id_set and p.get("number") not in pr_id_set:
                continue

            for r in p.get("reviews", []):
                rev_user = r.get("user", {}).get("login", "").lower()
                if reviewer_lower and rev_user != reviewer_lower:
                    continue
                collected_reviews.append(r)

        return collected_reviews

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.1)
    async def get_issue_comments(
        self,
        repo_url: str,
        author_username: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raw_comments: List[Dict[str, Any]] = self._load_fixture("issues.json")
        filtered: List[Dict[str, Any]] = []

        for c in raw_comments:
            if author_username:
                c_user = c.get("user", {}).get("login", "")
                if c_user.lower() != author_username.lower():
                    continue

            created_at = c.get("created_at", "")
            if since and created_at < since:
                continue
            if until and created_at > until:
                continue

            filtered.append(c)

        return filtered


class RealGitHubClient(GitHubClientProtocol):
    """Production GitHub client interface (stub for external MCP connector)."""

    async def get_commits(
        self,
        repo_url: str,
        author_username: str,
        author_emails: List[str],
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("RealGitHubClient requires GitHub MCP server in production")

    async def get_pull_requests(
        self,
        repo_url: str,
        author_username: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("RealGitHubClient requires GitHub MCP server in production")

    async def get_review_comments(
        self,
        repo_url: str,
        pr_ids: Optional[List[int]] = None,
        reviewer_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("RealGitHubClient requires GitHub MCP server in production")

    async def get_issue_comments(
        self,
        repo_url: str,
        author_username: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("RealGitHubClient requires GitHub MCP server in production")


class CountingGitHubClientWrapper(GitHubClientProtocol):
    """Decorator tracking API call volume per student and managing sandbox fallback."""

    def __init__(
        self,
        underlying: GitHubClientProtocol,
        state: Optional[Dict[str, Any]] = None,
        max_calls: Optional[int] = None,
        sandbox_runner: Optional[Any] = None,
    ):
        self.underlying = underlying
        self.state = state
        self.max_calls = (
            max_calls
            if max_calls is not None
            else settings.github_api.max_calls_per_student
        )
        self.sandbox_runner = sandbox_runner

    def _record_call(self) -> None:
        if self.state is not None:
            count = self.state.get("github_api_call_count", 0) + 1
            self.state["github_api_call_count"] = count
            if count >= self.max_calls:
                self.state["github_sandbox_mode"] = True
                logger.warning(
                    f"GitHub API call cap reached ({count}/{self.max_calls}). Activated github_sandbox_mode."
                )

    async def get_commits(
        self,
        repo_url: str,
        author_username: str,
        author_emails: List[str],
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._record_call()
        # Fallback to local sandbox runner if active and available
        if (
            self.state
            and self.state.get("github_sandbox_mode", False)
            and self.sandbox_runner is not None
        ):
            logger.info("Routing get_commits to GitSandboxRunner due to rate limit fallback.")
            return await self.sandbox_runner.get_commits(
                author_username=author_username,
                author_emails=author_emails,
                since=since,
                until=until,
            )
        return await self.underlying.get_commits(
            repo_url, author_username, author_emails, since, until
        )

    async def get_pull_requests(
        self,
        repo_url: str,
        author_username: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._record_call()
        return await self.underlying.get_pull_requests(repo_url, author_username, since, until)

    async def get_review_comments(
        self,
        repo_url: str,
        pr_ids: Optional[List[int]] = None,
        reviewer_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._record_call()
        return await self.underlying.get_review_comments(repo_url, pr_ids, reviewer_username)

    async def get_issue_comments(
        self,
        repo_url: str,
        author_username: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._record_call()
        return await self.underlying.get_issue_comments(repo_url, author_username, since, until)


def get_github_client(
    is_dev: Optional[bool] = None,
    state: Optional[Dict[str, Any]] = None,
    sandbox_runner: Optional[Any] = None,
) -> GitHubClientProtocol:
    """Factory creating configured GitHubClient (mock or real, with counting wrapper)."""
    if is_dev is None:
        is_dev = IS_DEV_MODE

    base_client = MockGitHubClient() if is_dev else RealGitHubClient()
    return CountingGitHubClientWrapper(
        underlying=base_client,
        state=state,
        sandbox_runner=sandbox_runner,
    )
