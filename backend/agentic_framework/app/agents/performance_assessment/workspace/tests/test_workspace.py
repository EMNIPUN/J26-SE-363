"""Tests of the read-only git workspace (uses a throwaway local repository; no network)."""
import os
import subprocess
import time

import pytest

from app.agents.performance_assessment.workspace import WorkspaceError, WorkspaceManager


def _git(cwd, *args, date=None):
    env = {**os.environ, "GIT_AUTHOR_NAME": "A", "GIT_AUTHOR_EMAIL": "a@x.org", "GIT_COMMITTER_NAME": "A", "GIT_COMMITTER_EMAIL": "a@x.org"}
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "origin"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    (r / "a.py").write_text("def f():\n    return 1\n")
    _git(r, "add", "."); _git(r, "commit", "-q", "-m", "first", date="2026-03-01T10:00:00Z")
    (r / "a.py").write_text("def f():\n    return 2\n")
    _git(r, "commit", "-qam", "second", date="2026-03-10T10:00:00Z")
    return r


@pytest.fixture()
def ws(tmp_path):
    return WorkspaceManager(tmp_path / "ws", allow_local=True)


# ---- URL rules ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["git@github.com:org/repo.git", "http://github.com/org/repo", "file:///etc", "ext::sh -c id", "https://evil.com/org/repo", "https://user:pw@github.com/org/repo",
                                 "https://github.com/org/repo?x=1", "https://github.com/org", "https://github.com/org/repo/../../x", "--upload-pack=touch /tmp/x", "https://github.com/-o/repo"])
def test_urls_that_are_not_plain_github_https_are_refused(tmp_path, url):
    with pytest.raises(WorkspaceError):
        WorkspaceManager(tmp_path / "ws").normalize(url)


def test_a_normal_github_url_is_canonicalised(tmp_path):
    w = WorkspaceManager(tmp_path / "ws")
    assert w.normalize("https://GitHub.com/org/repo/") == "https://github.com/org/repo.git"
    assert w.normalize("https://github.com/org/repo.git") == "https://github.com/org/repo.git"


# ---- mirrors, reading, worktrees ---------------------------------------------------------------------------------------------------

def test_mirror_is_created_then_fetched(ws, repo):
    path = ws.ensure_mirror(str(repo))
    assert (path / "HEAD").exists()
    (repo / "b.py").write_text("x = 1\n")
    _git(repo, "add", "."); _git(repo, "commit", "-q", "-m", "third", date="2026-03-20T10:00:00Z")
    ws.ensure_mirror(str(repo))
    assert "third" in ws.read(str(repo), "log", "--format=%s", "main")


def test_resolve_by_time_picks_the_last_commit_before_it(ws, repo):
    ws.ensure_mirror(str(repo))
    assert ws.resolve(str(repo), "main", "2026-03-05T00:00:00Z") != ws.resolve(str(repo), "main")
    with pytest.raises(WorkspaceError):
        ws.resolve(str(repo), "main", "2025-01-01T00:00:00Z")


def test_worktree_has_the_files_at_that_time_and_is_removed_afterwards(ws, repo):
    ws.ensure_mirror(str(repo))
    with ws.worktree(str(repo), ref="main", as_of="2026-03-05T00:00:00Z") as wt:
        assert (wt.path / "a.py").read_text().strip().endswith("return 1")
        kept = wt.path
    assert not kept.exists()
    with ws.worktree(str(repo), ref="main") as wt:
        assert (wt.path / "a.py").read_text().strip().endswith("return 2")


def test_worktree_is_removed_even_when_the_block_raises(ws, repo):
    ws.ensure_mirror(str(repo))
    kept = None
    with pytest.raises(RuntimeError):
        with ws.worktree(str(repo), ref="main") as wt:
            kept = wt.path
            raise RuntimeError("boom")
    assert not kept.exists()


def test_blame_works_on_the_mirror(ws, repo):
    ws.ensure_mirror(str(repo))
    out = ws.read(str(repo), "blame", "-w", "--line-porcelain", "main", "--", "a.py")
    assert "return 2" in out


# ---- what is refused ---------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("args", [("checkout", "main"), ("push", "origin"), ("config", "user.name", "x"), ("gc",), ("clean", "-fd"), ("reset", "--hard"), ()])
def test_commands_that_change_anything_are_refused(ws, repo, args):
    ws.ensure_mirror(str(repo))
    with pytest.raises(WorkspaceError):
        ws.read(str(repo), *args)


@pytest.mark.parametrize("arg", ["--output=/tmp/x", "-c", "--exec=sh", "--ext-diff", "--git-dir=/x", "../../etc/passwd"])
def test_dangerous_arguments_are_refused(ws, repo, arg):
    ws.ensure_mirror(str(repo))
    with pytest.raises(WorkspaceError):
        ws.read(str(repo), "log", arg)


def test_reading_without_a_mirror_is_an_error(ws, repo):
    with pytest.raises(WorkspaceError):
        ws.read(str(repo), "log")


def test_the_token_is_not_in_the_environment_arguments_or_error_messages(ws, tmp_path):
    env = ws._env(token="SECRET-TOKEN")
    assert "SECRET-TOKEN" not in " ".join(k for k in env) and any("SECRET-TOKEN" not in v for v in env.values())
    w = WorkspaceManager(tmp_path / "ws2")
    with pytest.raises(WorkspaceError) as e:
        w._run(["rev-parse", "--verify", "nope-SECRET-TOKEN"], cwd=tmp_path, token="SECRET-TOKEN")
    assert "SECRET-TOKEN" not in str(e.value)


def test_hooks_are_disabled(ws, repo):
    env = ws._env()
    pairs = {env[f"GIT_CONFIG_KEY_{i}"]: env[f"GIT_CONFIG_VALUE_{i}"] for i in range(int(env["GIT_CONFIG_COUNT"]))}
    assert pairs["core.hooksPath"] == str(ws.empty) and pairs["protocol.allow"] == "never"


# ---- housekeeping ------------------------------------------------------------------------------------------------------------------

def test_cleanup_removes_old_worktrees_and_least_recently_used_mirrors(tmp_path, repo):
    w = WorkspaceManager(tmp_path / "ws", allow_local=True, ttl_hours=1, max_total_bytes=1)
    w.ensure_mirror(str(repo))
    old = w.trees / "stale"
    old.mkdir()
    (old / "x").write_text("x")
    os.utime(old, (time.time() - 7200, time.time() - 7200))
    removed = w.cleanup()
    assert "stale" in removed and not old.exists()
    assert not w.mirror_path(str(repo)).exists()  # over the size cap, so the mirror went too


def test_two_mirrors_do_not_collide(ws, repo, tmp_path):
    other = tmp_path / "origin2"
    other.mkdir()
    _git(other, "init", "-q", "-b", "main")
    (other / "z.py").write_text("z = 1\n")
    _git(other, "add", "."); _git(other, "commit", "-q", "-m", "z", date="2026-03-01T10:00:00Z")
    assert ws.ensure_mirror(str(repo)) != ws.ensure_mirror(str(other))
