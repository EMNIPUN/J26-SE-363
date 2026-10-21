"""Fetch a repository safely and run the detection tools on it.

    result = await run_pipeline("https://github.com/owner/repo")                   # manual entry path
    result = await run_pipeline(url, sha, scan_type="secrets_only")                 # used by the webhook path

`fetch_repo` is the only place that clones. The repository is untrusted data: git is only used to
download and check out files, and nothing from the checkout is ever executed.
"""

import asyncio
import os
import re
import shutil
import stat
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from app.agents.security_assistant.schemas import ScanResult
from app.agents.security_assistant.tools.base import BaseTool, _kill, child_env
from app.agents.security_assistant.tools.runner import default_tools, run_all
from app.agents.security_assistant.tools.secret_scanners import GitleaksTool, TruffleHogTool

DEFAULT_MAX_BYTES = 500 * 1024 * 1024
DEFAULT_TIMEOUT_S = 300.0
SCAN_TYPES = ("full", "secrets_only")

_GITHUB_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]{1,100})/([A-Za-z0-9_.-]{1,100}?)(?:\.git)?/?$")
_SHA = re.compile(r"^[0-9a-f]{40}$")

# Git must not read the machine or user config, ask for credentials, or fetch LFS files.
_GIT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_LFS_SKIP_SMUDGE": "1",
    "GIT_ASKPASS": "",
}


class FetchError(Exception):
    """The repository could not be fetched safely (bad URL or SHA, too large, too slow, git failed)."""


def validate_github_url(url: str) -> str:
    """Return the canonical clone URL for an https://github.com/<owner>/<repo> URL, else raise ValueError."""
    m = _GITHUB_URL.match(url or "")
    if not m or set(m.group(1)) == {"."} or set(m.group(2)) == {"."}:
        raise ValueError("only https://github.com/<owner>/<repo> repository URLs are accepted")
    return f"https://github.com/{m.group(1)}/{m.group(2)}.git"


def _dir_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


def _rmtree(path: Path) -> None:
    def make_writable(func, p, _exc):  # git object files are read-only on Windows
        os.chmod(p, stat.S_IWRITE)
        func(p)

    shutil.rmtree(path, onerror=make_writable)


async def _git(argv: list[str], *, cwd: Path, timeout: float, watch: Path | None = None,
               max_bytes: int = DEFAULT_MAX_BYTES) -> str:
    """Run one fixed git command with a time limit and (optionally) a limit on the size of `watch`."""
    # own session on POSIX: _kill() signals the whole process group and must never reach our own
    session = {} if sys.platform == "win32" else {"start_new_session": True}
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=str(cwd), env={**child_env(), **_GIT_ENV}, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **session,
        )
    except NotImplementedError as exc:  # Windows selector event loop
        raise FetchError("event loop cannot start subprocesses (use a Proactor loop on Windows)") from exc
    except FileNotFoundError as exc:
        raise FetchError("git is not installed") from exc
    comm = asyncio.ensure_future(proc.communicate())
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        done, _ = await asyncio.wait({comm}, timeout=max(0.01, min(1.0, timeout / 2)))
        if done:
            break
        if loop.time() > deadline:
            _kill(proc)
            await proc.wait()
            raise FetchError(f"git timed out after {timeout:g}s")
        if watch is not None and _dir_size(watch) > max_bytes:
            _kill(proc)
            await proc.wait()
            raise FetchError(f"repository is larger than {max_bytes // (1024 * 1024)} MB")
    out, err = comm.result()
    if proc.returncode != 0:
        raise FetchError(f"git failed (exit {proc.returncode}): {err.decode('utf-8', 'replace').strip()[-300:]}")
    return out.decode("utf-8", "replace")


@asynccontextmanager
async def fetch_repo(
    repo_url: str,
    commit_sha: str | None = None,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    parent_dir: str | Path | None = None,
    _allow_local_path_for_tests: bool = False,
):
    """Clone `repo_url` (full history), check out `commit_sha` (or the default branch), yield the folder,
    and delete everything afterwards.

    Safety: https://github.com URLs only; hooks and the template directory are disabled; submodules and
    Git LFS are not fetched; symlinks are written as plain files; size and time limits are enforced
    while cloning; nothing from the repository is executed.
    """
    if commit_sha is not None and not _SHA.match(commit_sha):
        raise FetchError("commit SHA must be 40 lowercase hex characters")
    local = _allow_local_path_for_tests and Path(repo_url).is_dir()
    try:
        source = str(Path(repo_url).resolve()) if local else validate_github_url(repo_url)
    except ValueError as exc:
        raise FetchError(str(exc)) from exc

    root = Path(tempfile.mkdtemp(prefix="security_assistant_repo_", dir=parent_dir))
    try:
        empty = root / "empty"  # used as git template dir and hooks dir: no hook can ever run
        empty.mkdir()
        dest = root / "repo"
        cfg = [
            "-c", f"core.hooksPath={empty}", "-c", "core.symlinks=false", "-c", "core.fsmonitor=false",
            "-c", "core.autocrlf=false", "-c", "transfer.fsckObjects=true", "-c", "advice.detachedHead=false",
            "-c", "filter.lfs.smudge=", "-c", "filter.lfs.process=", "-c", "filter.lfs.required=false",
            "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
            "-c", f"protocol.file.allow={'always' if local else 'never'}",
        ]
        await _git(["git", *cfg, "clone", "--no-checkout", f"--template={empty}", "--", source, str(dest)],
                   cwd=root, timeout=timeout_s, watch=dest, max_bytes=max_bytes)

        target = commit_sha or "HEAD"
        try:
            await _git(["git", *cfg, "-C", str(dest), "checkout", "--detach", "--force", target],
                       cwd=root, timeout=timeout_s)
        except FetchError:
            if not commit_sha:
                raise
            # the commit may not be on any branch tip: ask the server for it by id, then retry once
            await _git(["git", *cfg, "-C", str(dest), "fetch", "--no-tags", "origin", commit_sha],
                       cwd=root, timeout=timeout_s, watch=dest, max_bytes=max_bytes)
            await _git(["git", *cfg, "-C", str(dest), "checkout", "--detach", "--force", commit_sha],
                       cwd=root, timeout=timeout_s)

        if _dir_size(dest) > max_bytes:
            raise FetchError(f"repository is larger than {max_bytes // (1024 * 1024)} MB")
        head = (await _git(["git", *cfg, "-C", str(dest), "rev-parse", "HEAD"], cwd=root, timeout=timeout_s)).strip()
        if commit_sha and head != commit_sha:
            raise FetchError("checked out commit does not match the requested SHA")
        yield dest
    finally:
        _rmtree(root)


def tools_for(scan_type: str) -> list[BaseTool]:
    if scan_type == "secrets_only":
        return [GitleaksTool(), TruffleHogTool()]
    if scan_type == "full":
        return default_tools()
    raise ValueError(f"unknown scan_type {scan_type!r}; expected one of {SCAN_TYPES}")


async def run_pipeline(
    repo_url: str,
    commit_sha: str | None = None,
    scan_type: str = "full",
    *,
    scan_dir: Path | None = None,
    tools: list[BaseTool] | None = None,
    max_parallel: int | None = None,
    **fetch_options,
) -> ScanResult:
    """fetch_repo -> run_all -> delete the checkout. Raises FetchError if the repo cannot be fetched."""
    chosen = tools if tools is not None else tools_for(scan_type)
    async with fetch_repo(repo_url, commit_sha, **fetch_options) as repo:
        result = await run_all(repo, tools=chosen, scan_dir=scan_dir, max_parallel=max_parallel)
    result.repo_url, result.commit_sha, result.scan_type = repo_url, commit_sha, scan_type
    result.repo_path = "(deleted after the scan)"
    return result
