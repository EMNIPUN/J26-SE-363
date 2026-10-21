"""fetch_repo / run_pipeline against a local git repository (no network)."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.agents.security_assistant import pipeline
from app.agents.security_assistant.pipeline import (
    FetchError, fetch_repo, run_pipeline, tools_for, validate_github_url,
)
from app.agents.security_assistant.tools.config_scan import ConfigScanTool


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


class Source:
    """A local git repo plus the SHAs of its two commits."""

    def __init__(self, path, first, second):
        self.path, self.first, self.second = path, first, second

    def __str__(self):
        return str(self.path)


@pytest.fixture
def work(tmp_path):
    """Empty folder the clones are made in; tests assert it is empty again afterwards."""
    path = tmp_path / "work"
    path.mkdir()
    return path


@pytest.fixture
def source_repo(tmp_path):
    """A local repo with two commits, a .gitmodules file and a Python file."""
    repo = tmp_path / "source"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "app.py").write_text("VERSION = 1\n")
    (repo / ".gitmodules").write_text('[submodule "x"]\n\tpath = x\n\turl = https://example.invalid/x.git\n')
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "one")
    first = git(repo, "rev-parse", "HEAD")
    (repo / "app.py").write_text("VERSION = 2\n")
    git(repo, "commit", "-q", "-am", "two")
    return Source(repo, first, git(repo, "rev-parse", "HEAD"))


def fetch(src, sha=None, **kw):
    return fetch_repo(str(src), sha, _allow_local_path_for_tests=True, **kw)


# ---- URL validation ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("url", [
    "https://github.com/owner/repo", "https://github.com/owner/repo.git", "https://github.com/owner/repo/",
    "https://github.com/My-Org/my.repo_1.git",
])
def test_valid_github_urls_are_canonicalised(url):
    assert validate_github_url(url).startswith("https://github.com/") and validate_github_url(url).endswith(".git")


@pytest.mark.parametrize("url", [
    "", "http://github.com/o/r", "git@github.com:o/r.git", "https://gitlab.com/o/r",
    "https://github.com.evil.com/o/r", "https://user:pw@github.com/o/r", "https://github.com:444/o/r",
    "https://github.com/o/r/tree/main", "https://github.com/o", "https://github.com/../r",
    "https://github.com/o/r?x=1", "ssh://github.com/o/r", "file:///tmp/repo",
])
def test_other_urls_are_rejected(url):
    with pytest.raises(ValueError):
        validate_github_url(url)


def test_fetch_repo_rejects_non_github_url_without_touching_the_network(tmp_path, work):
    async def go():
        async with fetch_repo("https://gitlab.com/o/r", parent_dir=work):
            pass
    with pytest.raises(FetchError):
        run(go())
    assert list(work.iterdir()) == []


# ---- fetch_repo -------------------------------------------------------------------------------------------
def test_checks_out_the_requested_sha_and_deletes_the_clone(source_repo, tmp_path, work):
    seen = {}

    async def go():
        async with fetch(source_repo, source_repo.first, parent_dir=work) as path:
            seen["path"] = path
            seen["text"] = (path / "app.py").read_text()
            seen["head"] = git(path, "rev-parse", "HEAD")
            seen["commits"] = git(path, "rev-list", "--count", "--all")

    run(go())
    assert seen["text"] == "VERSION = 1\n" and seen["head"] == source_repo.first
    assert seen["commits"] == "2"  # full history, not a shallow clone
    assert not seen["path"].exists() and list(work.iterdir()) == []


def test_defaults_to_the_branch_tip(source_repo, tmp_path, work):
    async def go():
        async with fetch(source_repo, parent_dir=work) as path:
            return (path / "app.py").read_text()
    assert run(go()) == "VERSION = 2\n"


def test_submodules_are_not_fetched(source_repo, tmp_path, work):
    async def go():
        async with fetch(source_repo, parent_dir=work) as path:
            return (path / "x").exists(), (path / ".git" / "modules").exists()
    assert run(go()) == (False, False)


def test_bad_sha_format_is_rejected(source_repo, tmp_path, work):
    async def go():
        async with fetch(source_repo, "main; rm -rf /", parent_dir=work):
            pass
    with pytest.raises(FetchError, match="40 lowercase hex"):
        run(go())


def test_unknown_sha_fails_and_cleans_up(source_repo, tmp_path, work):
    async def go():
        async with fetch(source_repo, "f" * 40, parent_dir=work):
            pass
    with pytest.raises(FetchError):
        run(go())
    assert list(work.iterdir()) == []


def test_size_limit(source_repo, tmp_path, work):
    async def go():
        async with fetch(source_repo, max_bytes=1, parent_dir=work):
            pass
    with pytest.raises(FetchError, match="larger than"):
        run(go())
    assert list(work.iterdir()) == []


def test_git_time_limit_kills_the_process(tmp_path):
    cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
    with pytest.raises(FetchError, match="timed out"):
        run(pipeline._git(cmd, cwd=tmp_path, timeout=0.4))


def test_clone_is_deleted_even_when_the_caller_fails(source_repo, tmp_path, work):
    async def go():
        async with fetch(source_repo, parent_dir=work):
            raise RuntimeError("scan crashed")
    with pytest.raises(RuntimeError):
        run(go())
    assert list(work.iterdir()) == []


def test_git_hooks_never_run_even_in_a_hostile_environment(source_repo, tmp_path, monkeypatch, work):
    """A template with a post-checkout hook is offered through GIT_TEMPLATE_DIR; the clone must ignore it."""
    canary = tmp_path / "hook-ran"
    template = tmp_path / "template"
    (template / "hooks").mkdir(parents=True)
    hook = template / "hooks" / "post-checkout"
    hook.write_text(f"#!/bin/sh\necho ran > '{canary.as_posix()}'\n")
    hook.chmod(0o755)
    monkeypatch.setattr(pipeline, "child_env", lambda: {**os.environ, "GIT_TEMPLATE_DIR": str(template)})

    async def go():
        async with fetch(source_repo, source_repo.first, parent_dir=work):
            pass
    run(go())
    assert not canary.exists()


# ---- run_pipeline -------------------------------------------------------------------------------------------
def test_run_pipeline_scans_the_checkout_and_records_what_was_scanned(source_repo, tmp_path):
    result = run(run_pipeline(str(source_repo), source_repo.first, "full", tools=[ConfigScanTool()],
                              scan_dir=tmp_path / "scans", _allow_local_path_for_tests=True))
    assert result.commit_sha == source_repo.first and result.scan_type == "full"
    assert result.repo_url == str(source_repo) and result.complete
    assert "deleted" in result.repo_path


def test_scan_types_select_the_tools():
    assert [t.name for t in tools_for("secrets_only")] == ["gitleaks", "trufflehog"]
    assert len(tools_for("full")) == 9
    with pytest.raises(ValueError):
        tools_for("everything")
