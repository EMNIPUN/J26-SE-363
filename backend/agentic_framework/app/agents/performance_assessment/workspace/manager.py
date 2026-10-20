"""Read-only git workspace for the assessment agent.

Student repositories are only ever read: history, diffs, blame, file contents. Nothing in a student repository is built, installed or executed, so no container is
needed; what has to be managed is disk space, concurrency, credentials and a few ways a hostile repository or URL could misbehave.

    ws = WorkspaceManager(root)
    mirror = ws.ensure_mirror("https://github.com/org/repo", token=...)      # bare, blob-less mirror cached under root/mirrors, fetched when it exists
    with ws.worktree(url, as_of="2026-03-01T23:59:59Z") as wt:                # detached checkout at that moment, removed on exit
        out = ws.read(url, "log", "--numstat", "--since=...")                 # whitelisted read-only git commands only
        text = (wt.path / "src/app.py").read_text()

Safety rules (tests in tests/test_workspace.py):
- only https URLs on an allow-listed host (default github.com) with an ``owner/repo`` path; no other schemes (``ext::``, ``file://``), no options smuggled in a URL;
  ``allow_local=True`` is for tests only;
- the token travels in the environment of the git process (``GIT_CONFIG_*``), never in argv, never in a file, and is scrubbed from error messages;
- ``read`` accepts a fixed list of read-only subcommands and refuses options that execute programs (``--exec``, ``-c`` ...), paths with ``..`` are refused;
- hooks are disabled (``core.hooksPath`` points to an empty folder), ``protocol.allow=never`` except https, no filters/attributes run (``core.attributesFile`` empty);
- one lock per mirror, a total size cap and a time-to-live clean up old worktrees and the least recently used mirrors.
"""
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

READ_COMMANDS = {"log", "show", "diff", "blame", "ls-tree", "rev-parse", "rev-list", "cat-file", "shortlog", "ls-files", "for-each-ref", "merge-base", "name-rev", "diff-tree", "show-ref"}
FORBIDDEN_ARGS = re.compile(r"^(--exec|--upload-pack|--receive-pack|--output|-o|-c|--config|--git-dir|--work-tree|--ext-diff|--textconv|--open-files-in-pager)(=|$)")
REPO_PATH = re.compile(r"^/[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.][A-Za-z0-9_.-]*?(\.git)?/?$")


def rmtree(path):
    """Delete a folder tree, including git's read-only object files (on Windows a plain rmtree leaves them behind)."""
    def clear(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=clear)
    else:
        shutil.rmtree(path, onerror=clear)


class WorkspaceError(RuntimeError):
    pass


@dataclass
class Worktree:
    path: Path
    sha: str
    repo_url: str


class WorkspaceManager:
    def __init__(self, root, *, allow_hosts=("github.com",), max_total_bytes=8 * 1024**3, ttl_hours=72, git="git", allow_local=False, timeout=600):
        self.root = Path(root).resolve()
        self.mirrors, self.trees, self.empty = self.root / "mirrors", self.root / "worktrees", self.root / "empty"
        for d in (self.mirrors, self.trees, self.empty):
            d.mkdir(parents=True, exist_ok=True)
        self.allow_hosts, self.max_total_bytes, self.ttl, self.git, self.allow_local, self.timeout = tuple(allow_hosts), max_total_bytes, ttl_hours * 3600, git, allow_local, timeout
        self._locks, self._guard = {}, threading.Lock()

    # ---- urls and paths --------------------------------------------------------------------------------------------------------------
    def normalize(self, repo_url):
        """The canonical clone URL, or WorkspaceError. https on an allowed host with owner/repo only."""
        if self.allow_local and Path(str(repo_url)).exists():
            return str(Path(repo_url).resolve())
        u = urlparse(str(repo_url).strip())
        if u.scheme != "https" or (u.hostname or "").lower() not in self.allow_hosts or u.username or u.password or u.query or u.fragment or not REPO_PATH.match(u.path or ""):
            raise WorkspaceError(f"repository URL not allowed: only https://<{'|'.join(self.allow_hosts)}>/owner/repo")
        path = u.path.rstrip("/")
        return f"https://{u.hostname.lower()}{path if path.endswith('.git') else path + '.git'}"

    def mirror_path(self, repo_url):
        return self.mirrors / (hashlib.sha256(self.normalize(repo_url).encode()).hexdigest()[:20] + ".git")

    def _lock(self, key):
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    # ---- running git -----------------------------------------------------------------------------------------------------------------
    def _env(self, token=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k not in ("SSH_ASKPASS",)}
        cfg = [("core.hooksPath", str(self.empty)), ("protocol.allow", "never"), ("protocol.https.allow", "always"), ("core.attributesFile", os.devnull), ("core.fsmonitor", "false"), ("gc.auto", "0"), ("core.quotepath", "false")]
        if self.allow_local:
            cfg += [("protocol.file.allow", "always")]
        if token:
            import base64
            cfg.append(("http.extraHeader", "Authorization: Basic " + base64.b64encode(f"x-access-token:{token}".encode()).decode()))
        env["GIT_CONFIG_COUNT"] = str(len(cfg))
        for i, (k, v) in enumerate(cfg):
            env[f"GIT_CONFIG_KEY_{i}"], env[f"GIT_CONFIG_VALUE_{i}"] = k, v
        env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "LC_ALL": "C"})
        return env

    def _run(self, args, *, cwd=None, token=None, input_text=None):
        try:
            p = subprocess.run([self.git, *args], cwd=cwd, env=self._env(token), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=self.timeout, input=input_text, check=False)
        except subprocess.TimeoutExpired as e:
            raise WorkspaceError(f"git {args[0]} timed out after {self.timeout}s") from e
        if p.returncode != 0:
            msg = (p.stderr or p.stdout or "").strip()
            if token:
                msg = msg.replace(token, "***")
            raise WorkspaceError(f"git {args[0]} failed: {msg[:500]}")
        return p.stdout

    # ---- mirrors ---------------------------------------------------------------------------------------------------------------------
    def ensure_mirror(self, repo_url, token=None):
        """Create the bare, blob-less mirror, or fetch into it. Returns its path."""
        url, path = self.normalize(repo_url), self.mirror_path(repo_url)
        with self._lock(str(path)):
            if (path / "HEAD").exists():
                self._run(["fetch", "--prune", "--quiet", "origin", "+refs/heads/*:refs/heads/*", "+refs/pull/*/head:refs/pull/*/head"], cwd=path, token=token)
            else:
                tmp = Path(tempfile.mkdtemp(dir=self.mirrors, prefix="clone-"))
                try:
                    self._run(["clone", "--mirror", "--filter=blob:none", "--quiet", url, str(tmp / "r.git")], token=token)
                    shutil.move(str(tmp / "r.git"), str(path))
                finally:
                    rmtree(tmp)
            os.utime(path, None)
        return path

    # ---- reading ---------------------------------------------------------------------------------------------------------------------
    def read(self, repo_url, *args, token=None):
        """Run one whitelisted read-only git command against the mirror and return its output."""
        if not args or args[0] not in READ_COMMANDS:
            raise WorkspaceError(f"git command not allowed: {args[0] if args else ''!r}")
        for a in args[1:]:
            if FORBIDDEN_ARGS.match(a) or ".." in Path(a).parts:
                raise WorkspaceError(f"argument not allowed: {a!r}")
        path = self.mirror_path(repo_url)
        if not (path / "HEAD").exists():
            raise WorkspaceError("mirror does not exist; call ensure_mirror first")
        with self._lock(str(path)):
            os.utime(path, None)
            return self._run([args[0], *args[1:]], cwd=path, token=token)

    def resolve(self, repo_url, ref=None, as_of=None, token=None):
        """Full SHA of ``ref`` (default: the default branch), or of its last commit not after ``as_of`` (ISO date-time)."""
        ref = ref or "HEAD"
        if as_of:
            sha = self.read(repo_url, "rev-list", "-1", f"--before={as_of}", ref, token=token).strip()
        else:
            sha = self.read(repo_url, "rev-parse", "--verify", f"{ref}^{{commit}}", token=token).strip()
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise WorkspaceError(f"no commit found for ref={ref!r} as_of={as_of!r}")
        return sha

    @contextmanager
    def worktree(self, repo_url, *, ref=None, as_of=None, token=None):
        """A detached checkout of the repository at ``ref`` / ``as_of``, deleted when the block ends."""
        mirror = self.ensure_mirror(repo_url, token=token) if not self.mirror_path(repo_url).exists() else self.mirror_path(repo_url)
        sha = self.resolve(repo_url, ref, as_of, token)
        dest = (self.trees / uuid.uuid4().hex).resolve()
        if self.trees.resolve() not in dest.parents:
            raise WorkspaceError("worktree path escaped the workspace")
        with self._lock(str(mirror)):
            self._run(["worktree", "add", "--detach", "--force", str(dest), sha], cwd=mirror, token=token)
        try:
            yield Worktree(dest, sha, self.normalize(repo_url))
        finally:
            with self._lock(str(mirror)):
                try:
                    self._run(["worktree", "remove", "--force", str(dest)], cwd=mirror)
                except WorkspaceError:
                    pass
            rmtree(dest)
            try:
                self._run(["worktree", "prune"], cwd=mirror)
            except WorkspaceError:
                pass

    # ---- housekeeping ----------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _size(path):
        return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())

    def total_bytes(self):
        return self._size(self.mirrors) + self._size(self.trees)

    def cleanup(self, now=None):
        """Delete worktrees older than the time-to-live, then least recently used mirrors until under the size cap. Returns what was removed."""
        now, removed = now or time.time(), []
        for t in self.trees.iterdir():
            if now - t.stat().st_mtime > self.ttl:
                rmtree(t)
                removed.append(t.name)
        mirrors = sorted((m for m in self.mirrors.iterdir() if m.suffix == ".git"), key=lambda m: m.stat().st_mtime)
        while mirrors and self.total_bytes() > self.max_total_bytes:
            m = mirrors.pop(0)
            lock = self._lock(str(m))
            if lock.acquire(blocking=False):
                try:
                    rmtree(m)
                    removed.append(m.name)
                finally:
                    lock.release()
        return removed
