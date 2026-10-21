"""Shared machinery for every detection adapter.

Rules enforced here, once, for all tools:
- fixed argv via create_subprocess_exec, never a shell, repo path passed as one argument
- a time limit per tool; the process is killed on timeout
- a minimal environment for child processes and a working directory outside the repo
- every outcome is recorded in a ToolRun, so a failure never looks like a clean scan
- secrets are masked before a Finding is built or raw output is saved
"""

import asyncio
import os
import shutil
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.agents.security_assistant.schemas import Finding, RunStatus, ToolRun

MAX_OUTPUT_BYTES = 100 * 1024 * 1024
DEFAULT_TIMEOUT_S = 300
_ENV_KEEP = ("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR", "LANG")


class ToolFailed(Exception):
    """The tool ran but did not give a usable result."""


class ToolTimeout(Exception):
    pass


class NotApplicable(Exception):
    """There was nothing for this tool to scan."""


@dataclass
class ScanContext:
    repo: Path
    work_dir: Path  # outside the repo; raw outputs and temp copies go here
    languages: set[str]
    run_id: str = ""


@dataclass
class ScanOutput:
    findings: list[Finding]
    raw: str  # already free of secret values
    exit_code: int | None = None
    rule_pack_version: str | None = None
    note: str | None = None  # a limitation of a successful run, shown as ToolRun.reason


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def mask_secret(value: str) -> str:
    """Keep only the first and last two characters of a secret."""
    if len(value) <= 8:
        return "****"
    return f"{value[:2]}****{value[-2:]}"


def child_env() -> dict[str, str]:
    return {k: os.environ[k] for k in _ENV_KEEP if k in os.environ}


async def run_command(
    argv: list[str], *, cwd: Path, timeout: float, accept_codes: tuple[int, ...] = (0,),
    extra_env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a fixed command. Raises ToolTimeout, or ToolFailed on unexpected exit codes."""
    kwargs: dict = {}
    if sys.platform != "win32":
        kwargs["start_new_session"] = True  # so the whole process group can be killed
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd),
            env={**child_env(), **(extra_env or {})},
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs,
        )
    except NotImplementedError as exc:  # Windows selector event loop cannot spawn processes
        raise ToolFailed("event loop cannot start subprocesses (use a Proactor loop on Windows)") from exc
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        _kill(proc)
        await proc.wait()
        raise ToolTimeout(f"exceeded {timeout:g}s") from None
    result = CommandResult(
        proc.returncode,
        out[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"),
        err[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"),
    )
    if result.returncode not in accept_codes:
        tail = result.stderr.strip()[-300:]
        raise ToolFailed(f"exit code {result.returncode}: {tail}")
    return result


def _kill(proc: asyncio.subprocess.Process) -> None:
    try:
        if sys.platform == "win32":
            os.system(f"taskkill /F /T /PID {proc.pid} >NUL 2>&1")
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.kill()
    except ProcessLookupError:
        pass


def rel_path(repo: Path, file: str | None) -> str | None:
    """Make a tool-reported path relative to the repo, with forward slashes."""
    if not file:
        return None
    file = file.removeprefix("file://")
    p = Path(file)
    if p.is_absolute():
        try:
            file = str(p.resolve().relative_to(repo.resolve()))
        except (ValueError, OSError):
            pass
    file = file.replace("\\", "/")
    return file[2:] if file.startswith("./") else file


@dataclass
class BaseTool:
    """Adapter interface: check_available() and run(ctx) -> (findings, ToolRun)."""

    name: str = ""
    binary: str | None = None  # None for in-process tools
    version_args: tuple[str, ...] = ("--version",)
    languages: frozenset[str] | None = None  # None = applies to any repository
    default_timeout_s: float = DEFAULT_TIMEOUT_S
    _version: str | None = field(default=None, init=False, repr=False)

    # --- to be implemented by adapters -------------------------------------------------
    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        raise NotImplementedError

    # --- common behaviour --------------------------------------------------------------
    @property
    def timeout_s(self) -> float:
        for key in (f"SECURITY_ASSISTANT_TOOL_TIMEOUT_{self.name.upper()}", "SECURITY_ASSISTANT_TOOL_TIMEOUT"):
            if os.environ.get(key):
                try:
                    return float(os.environ[key])
                except ValueError:
                    pass
        return self.default_timeout_s

    def executable(self) -> str | None:
        return shutil.which(self.binary) if self.binary else None

    async def get_version(self, exe: str | None) -> str | None:
        if exe is None:
            return None
        try:
            res = await run_command(
                [exe, *self.version_args], cwd=Path.cwd(), timeout=30, accept_codes=(0, 1)
            )
            text = (res.stdout or res.stderr).strip()
            return text.splitlines()[0][:100] if text else None
        except (ToolFailed, ToolTimeout, OSError):
            return None

    async def check_available(self) -> tuple[bool, str | None]:
        """(available, version). In-process tools are always available."""
        if self.binary is None:
            return True, "builtin"
        exe = self.executable()
        if exe is None:
            return False, None
        return True, await self.get_version(exe)

    async def run(self, ctx: ScanContext) -> tuple[list[Finding], ToolRun]:
        started = datetime.now(timezone.utc)
        t0 = asyncio.get_event_loop().time()
        run = ToolRun(tool=self.name, status=RunStatus.FAILED, started_at=started)
        findings: list[Finding] = []
        raw = ""
        try:
            exe = self.executable()
            if self.binary and exe is None:
                run.status, run.reason = RunStatus.UNAVAILABLE, "binary_not_found"
                return [], run
            if self.languages is not None and not (self.languages & ctx.languages):
                run.status = RunStatus.NOT_APPLICABLE
                run.reason = f"no {'/'.join(sorted(self.languages))} files in repository"
                return [], run
            run.tool_version = "builtin" if self.binary is None else await self.get_version(exe)
            out = await self.scan(ctx, exe)
            findings, raw = out.findings, out.raw
            run.exit_code, run.rule_pack_version = out.exit_code, out.rule_pack_version
            run.reason = out.note
            run.status = RunStatus.SUCCEEDED
        except NotApplicable as exc:
            run.status, run.reason = RunStatus.NOT_APPLICABLE, str(exc)
        except ToolTimeout as exc:
            run.status, run.reason = RunStatus.TIMED_OUT, str(exc)
        except ToolFailed as exc:
            run.status, run.reason = RunStatus.FAILED, str(exc)
        except Exception as exc:  # an adapter bug must not look like a clean scan
            run.status, run.reason = RunStatus.FAILED, f"{type(exc).__name__}: {exc}"[:300]
        finally:
            run.duration_s = round(asyncio.get_event_loop().time() - t0, 3)

        if raw:
            ref = ctx.work_dir / f"{self.name}.raw.txt"
            ref.write_text(raw, encoding="utf-8")
            run.raw_output_ref = str(ref)
        if run.status is not RunStatus.SUCCEEDED:
            findings = []
        findings = self._stamp(findings, run)
        run.findings_count = len(findings)
        return findings, run

    def _stamp(self, findings: list[Finding], run: ToolRun) -> list[Finding]:
        seen: set[tuple] = set()
        unique: list[Finding] = []
        for f in findings:
            key = (f.rule_id, f.file_path, f.line, f.sink)
            if key in seen:
                continue
            seen.add(key)
            f.tool, f.tool_version, f.raw_output_ref = self.name, run.tool_version, run.raw_output_ref
            unique.append(f)
        return unique
