"""GitHubREST against a fake GitHub (httpx.MockTransport): pagination, the per-PR bundle, rate-limit behaviour, request budget."""
import httpx
import pytest

from app.agents.performance_assessment.com_agent.ingestion.github_rest import GitHubError, GitHubRateLimited, GitHubREST, owner_repo


def fake_github(requests, limited_first=0, retry_after="1"):
    state = {"limited": limited_first}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        path = request.url.path
        if state["limited"] > 0:
            state["limited"] -= 1
            return httpx.Response(429, headers={"retry-after": retry_after}, json={"message": "rate limit"})
        if path == "/repos/org/repo/pulls":
            page = request.url.params.get("page", "1")
            if page == "1":
                items = [{"number": 2, "updated_at": "2026-03-09T00:00:00Z", "user": {"login": "bob"}}]
                return httpx.Response(200, json=items, headers={"link": '<https://api.github.com/repos/org/repo/pulls?page=2>; rel="next"'})
            return httpx.Response(200, json=[{"number": 1, "updated_at": "2026-03-05T00:00:00Z", "user": {"login": "amy"}}, {"number": 0, "updated_at": "2026-01-01T00:00:00Z", "user": {"login": "old"}}])
        if path.endswith("/pulls/2") or path.endswith("/pulls/1"):
            return httpx.Response(200, json={"merged_by": {"login": "amy"} if path.endswith("/1") else None})
        if path.endswith("/reviews"):
            return httpx.Response(200, json=[{"user": {"login": "amy"}, "state": "APPROVED", "body": "ok", "submitted_at": "2026-03-09T01:00:00Z"}])
        if path.endswith("/comments"):
            return httpx.Response(200, json=[])
        if path.endswith("/commits"):
            return httpx.Response(200, json=[{"sha": "a" * 40}])
        return httpx.Response(404, json={"message": "nope"})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_owner_repo_parsing():
    assert owner_repo("https://github.com/org/repo.git") == "org/repo"
    assert owner_repo("https://github.com/org/repo/") == "org/repo"
    with pytest.raises(GitHubError):
        owner_repo("https://github.com/org")


@pytest.mark.asyncio
async def test_bundle_follows_pages_stops_at_old_pull_requests_and_attaches_everything():
    seen = []
    gh = GitHubREST(client=fake_github(seen))
    prs = await gh.pulls_bundle("https://github.com/org/repo", since="2026-03-01T00:00:00Z")
    assert [p["number"] for p in prs] == [2, 1]  # PR 0 was last updated before `since`
    assert prs[1]["merged_by"] == "amy" and prs[0]["merged_by"] is None
    assert prs[0]["_reviews"][0]["state"] == "APPROVED" and prs[0]["_commits"] == ["a" * 40]
    assert any("page=2" in u for u in seen)


@pytest.mark.asyncio
async def test_a_short_rate_limit_is_waited_out_once():
    waits = []

    async def fake_sleep(s):
        waits.append(s)

    gh = GitHubREST(client=fake_github([], limited_first=1, retry_after="2"), sleep=fake_sleep)
    assert (await gh.pulls_bundle("https://github.com/org/repo", since="2026-03-01T00:00:00Z"))
    assert waits and 2 <= waits[0] <= 3


@pytest.mark.asyncio
async def test_a_long_rate_limit_is_not_waited_out():
    gh = GitHubREST(client=fake_github([], limited_first=5, retry_after="3600"), max_wait=60)
    with pytest.raises(GitHubRateLimited):
        await gh.pulls_bundle("https://github.com/org/repo")


@pytest.mark.asyncio
async def test_repeated_rate_limits_stop_after_three_attempts():
    async def no_sleep(_):
        pass

    gh = GitHubREST(client=fake_github([], limited_first=10, retry_after="1"), sleep=no_sleep)
    with pytest.raises(GitHubRateLimited):
        await gh.pulls_bundle("https://github.com/org/repo")


@pytest.mark.asyncio
async def test_request_budget_is_enforced():
    gh = GitHubREST(client=fake_github([]), max_requests=3)
    with pytest.raises(GitHubError, match="budget"):
        await gh.pulls_bundle("https://github.com/org/repo", since="2026-03-01T00:00:00Z")


@pytest.mark.asyncio
async def test_errors_are_reported_not_swallowed():
    gh = GitHubREST(client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404, json={"message": "Not Found"}))))
    with pytest.raises(GitHubError, match="404"):
        await gh.pulls_bundle("https://github.com/org/repo")
