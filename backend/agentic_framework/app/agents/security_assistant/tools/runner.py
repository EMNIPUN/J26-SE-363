"""Run every detection tool against one local repository folder.

    result = await run_all(Path("/path/to/repo"))
    result.findings   # normalised findings from all tools
    result.runs       # one ToolRun per tool (succeeded / failed / timed_out / ...)
    result.complete   # False if any tool failed: an empty findings list is then NOT "clean"
"""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

from app.agents.security_assistant.schemas import Finding, RunStatus, ScanResult, ToolRun
from app.agents.security_assistant.tools.base import BaseTool, ScanContext
from app.agents.security_assistant.tools.codeql import CodeQLTool
from app.agents.security_assistant.tools.config_scan import ConfigScanTool
from app.agents.security_assistant.tools.dependencies import NpmAuditTool, OsvScannerTool, PipAuditTool
from app.agents.security_assistant.tools.coverage_gaps import DEPENDENCY_TOOLS, find_dependency_gaps
from app.agents.security_assistant.tools.languages import detect_languages
from app.agents.security_assistant.tools.secret_scanners import GitleaksTool, TruffleHogTool
from app.agents.security_assistant.tools.workflow_lint import ActionlintTool, ZizmorTool


class InvalidRepoPath(ValueError):
    pass


def default_tools() -> list[BaseTool]:
    return [
        # Quick tools first; CodeQL (slow, memory-hungry) last.
        ConfigScanTool(), GitleaksTool(), TruffleHogTool(), OsvScannerTool(), NpmAuditTool(),
        PipAuditTool(), ActionlintTool(), ZizmorTool(), CodeQLTool(),
    ]


def _default_parallel() -> int:
    """Tools running at once: 1 (one after another) unless SECURITY_ASSISTANT_MAX_PARALLEL says otherwise."""
    try:
        return max(1, int(os.environ.get("SECURITY_ASSISTANT_MAX_PARALLEL", "1")))
    except ValueError:
        return 1


def _scan_root(repo: Path, scan_dir: Path | None) -> Path:
    root = Path(scan_dir or os.environ.get("SECURITY_ASSISTANT_SCAN_DIR") or Path(tempfile.gettempdir()) / "security_assistant_scans").resolve()
    if root == repo or repo in root.parents:
        raise InvalidRepoPath("scan output directory must be outside the scanned repository")
    return root


async def run_all(
    repo_path: str | Path,
    tools: list[BaseTool] | None = None,
    scan_dir: Path | None = None,
    max_parallel: int | None = None,
) -> ScanResult:
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        raise InvalidRepoPath(f"not a directory: {repo_path}")
    run_id = uuid.uuid4().hex[:12]
    work_dir = _scan_root(repo, scan_dir) / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    languages = detect_languages(repo)
    ctx = ScanContext(repo=repo, work_dir=work_dir, languages=languages, run_id=run_id)
    limit = asyncio.Semaphore(max_parallel or _default_parallel())

    async def one(tool: BaseTool):
        async with limit:
            return await tool.run(ctx)

    outcomes = await asyncio.gather(*(one(t) for t in (tools or default_tools())))  # keeps order

    findings: list[Finding] = [f for fs, _ in outcomes for f in fs]
    runs: list[ToolRun] = [r for _, r in outcomes]
    chosen = tools or default_tools()
    gaps = find_dependency_gaps(repo) if any(t.name in DEPENDENCY_TOOLS for t in chosen) else []  # a secrets-only scan has none
    return ScanResult(run_id=run_id, repo_path=str(repo), languages=sorted(languages), findings=findings, runs=runs, coverage_gaps=gaps)


def summarize(result: ScanResult) -> str:
    lines = [f"{r.tool:<12} {r.status.value:<15} {r.findings_count:>3} findings  {r.reason or ''}" for r in result.runs]
    verdict = "complete" if result.complete else "INCOMPLETE (a tool failed, timed out or was unavailable)"
    return "\n".join(lines + [f"scan {verdict}; {len(result.findings)} findings"])


if __name__ == "__main__":
    import sys

    res = asyncio.run(run_all(sys.argv[1]))
    print(summarize(res))
    sys.exit(0 if res.complete else 2)
