"""GitHub REST access for pull requests, reviews and comments (repository content is read from the git workspace, not from the API).

    gh = GitHubREST(token)
    prs = await gh.pulls_bundle("https://github.com/org/repo", since="2026-03-01T00:00:00Z")

Each pull request dict is the GitHub payload plus ``_reviews``, ``_review_comments``, ``_issue_comments``, ``_commits`` (list of SHAs) and ``merged_by`` (login or None).
Unlike the dataset script, a rate limit is waited out at most twice and for at most ``max_wait`` seconds, then ``GitHubRateLimited`` is raised; the number of requests is capped
so one team cannot use up a token.
"""
import asyncio
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx


class GitHubError(RuntimeError):
    pass


class GitHubRateLimited(GitHubError):
    pass


def owner_repo(repo_url: str) -> str:
    path = urlparse(repo_url).path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.][A-Za-z0-9_.-]*", path):
        raise GitHubError(f"not a GitHub repository URL: {repo_url!r}")
    return path


class GitHubREST:
    def __init__(self, token: Optional[str] = None, *, client: Optional[httpx.AsyncClient] = None, base: str = "https://api.github.com", max_wait: float = 60.0,
                 per_page: int = 100, max_pages: int = 10, max_requests: int = 600, concurrency: int = 6, sleep=asyncio.sleep):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "selvia-assessment-agent"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = client or httpx.AsyncClient(headers=headers, timeout=30.0)
        self.base, self.max_wait, self.per_page, self.max_pages, self.max_requests, self._sleep = base.rstrip("/"), max_wait, per_page, max_pages, max_requests, sleep
        self.requests = 0
        self.concurrency = max(1, concurrency)  # pull requests read at the same time

    async def aclose(self):
        await self._client.aclose()

    async def _get(self, url: str, params: Optional[dict] = None) -> httpx.Response:
        for attempt in range(3):
            if self.requests >= self.max_requests:
                raise GitHubError(f"request budget of {self.max_requests} used up")
            self.requests += 1
            r = await self._client.get(url, params=params)
            limited = r.status_code == 429 or (r.status_code == 403 and (r.headers.get("x-ratelimit-remaining") == "0" or "retry-after" in r.headers or "rate limit" in r.text.lower()))
            if not limited:
                if r.status_code >= 400:
                    raise GitHubError(f"GitHub {r.status_code} for {url}: {r.text[:200]}")
                return r
            wait = float(r.headers.get("retry-after") or max(0.0, float(r.headers.get("x-ratelimit-reset", 0)) - time.time()) or 1.0)
            if attempt == 2 or wait > self.max_wait:
                raise GitHubRateLimited(f"rate limited by GitHub; would need to wait {wait:.0f}s")
            await self._sleep(wait + 0.5)
        raise GitHubRateLimited("rate limited")  # pragma: no cover

    async def _paged(self, path: str, params: Optional[dict] = None, stop=None) -> List[Dict[str, Any]]:
        out, url, q = [], f"{self.base}{path}", {"per_page": self.per_page, **(params or {})}
        for _ in range(self.max_pages):
            r = await self._get(url, q)
            page = r.json()
            for item in page:
                if stop and stop(item):
                    return out
                out.append(item)
            nxt = r.links.get("next", {}).get("url")
            if not nxt:
                break
            url, q = nxt, None
        return out

    async def pulls_bundle(self, repo_url: str, since: Optional[str] = None, max_prs: int = 150) -> List[Dict[str, Any]]:
        """Pull requests updated since ``since`` with their reviews, comments, commit SHAs and merger."""
        slug = owner_repo(repo_url)
        pulls = await self._paged(f"/repos/{slug}/pulls", {"state": "all", "sort": "updated", "direction": "desc"}, stop=(lambda p: since and p["updated_at"] < since))
        # Five requests per pull request, and every pull request is independent of the others: they ran one after another (minutes for a busy repository). They now run together,
        # a few pull requests at a time, within the same request budget and rate-limit handling. The order of the result is the order GitHub gave.
        gate = asyncio.Semaphore(self.concurrency)

        async def one(p):
            n = p["number"]
            async with gate:
                detail, reviews, review_comments, issue_comments, commits = await asyncio.gather(
                    self._get(f"{self.base}/repos/{slug}/pulls/{n}"), self._paged(f"/repos/{slug}/pulls/{n}/reviews"), self._paged(f"/repos/{slug}/pulls/{n}/comments"),
                    self._paged(f"/repos/{slug}/issues/{n}/comments"), self._paged(f"/repos/{slug}/pulls/{n}/commits"))
            p["merged_by"] = ((detail.json().get("merged_by") or {}).get("login"))
            p["_reviews"], p["_review_comments"], p["_issue_comments"] = reviews, review_comments, issue_comments
            p["_commits"] = [c["sha"] for c in commits]
            return p

        return list(await asyncio.gather(*(one(p) for p in pulls[:max_prs])))
