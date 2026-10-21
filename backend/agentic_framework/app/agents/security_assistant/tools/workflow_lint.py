"""V5 CI/CD scanners for GitHub Actions workflows: actionlint and zizmor.

zizmor covers the security checks (pull_request_target misuse, missing permissions, unpinned
actions, secrets exposure); actionlint adds syntax and expression-injection checks.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.agents.security_assistant.schemas import Category, Finding
from app.agents.security_assistant.tools.base import (
    BaseTool, NotApplicable, ScanContext, ScanOutput, ToolFailed, rel_path, run_command,
)

CWE_CICD = "CWE-829"


def has_workflows(repo: Path) -> bool:
    wf = repo / ".github" / "workflows"
    return wf.is_dir() and any(p.suffix in (".yml", ".yaml") for p in wf.iterdir())


def parse_actionlint(items: list[dict] | None, repo: Path) -> list[Finding]:
    return [
        Finding(
            category=Category.V5,
            cwe=CWE_CICD,
            file_path=rel_path(repo, i.get("filepath")),
            line=i.get("line"),
            rule_id=f"actionlint:{i.get('kind', 'unknown')}",
            severity_tool=None,
            message=i.get("message", ""),
        )
        for i in items or []
    ]


ZIZMOR_CWE = {
    "excessive-permissions": "CWE-732",
    "dangerous-triggers": "CWE-829",
    "unpinned-uses": "CWE-829",
    "template-injection": "CWE-77",
    "secrets-inherit": "CWE-522",
    "artipacked": "CWE-522",
}


def parse_zizmor(items: list[dict], repo: Path) -> list[Finding]:
    findings = []
    for i in items:
        ident = i.get("ident", "unknown")
        det = i.get("determinations") or {}
        locs = i.get("locations") or []
        path, line = None, None
        if locs:
            local = (((locs[0].get("symbolic") or {}).get("key") or {}).get("Local") or {})
            path = local.get("given_path")
            start = ((locs[0].get("concrete") or {}).get("location") or {}).get("start_point") or {}
            line = start["row"] + 1 if "row" in start else None  # zizmor rows are 0-based
        findings.append(
            Finding(
                category=Category.V5,
                cwe=ZIZMOR_CWE.get(ident, CWE_CICD),
                file_path=rel_path(repo, path),
                line=line,
                rule_id=f"zizmor:{ident}",
                severity_tool=det.get("severity"),
                message=i.get("desc", ""),
            )
        )
    return findings


@dataclass
class ActionlintTool(BaseTool):
    name: str = "actionlint"
    binary: str = "actionlint"
    version_args: tuple[str, ...] = ("-version",)

    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        if not has_workflows(ctx.repo):
            raise NotApplicable("no .github/workflows files")
        # exit 1 = problems found; 2/3 = tool error
        res = await run_command(
            [exe, "-format", "{{json .}}", "-no-color"],
            cwd=ctx.repo, timeout=self.timeout_s, accept_codes=(0, 1),
        )
        try:
            items = json.loads(res.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise ToolFailed(f"invalid_output: {exc}") from exc
        return ScanOutput(parse_actionlint(items, ctx.repo), res.stdout, res.returncode)


@dataclass
class ZizmorTool(BaseTool):
    name: str = "zizmor"
    binary: str = "zizmor"

    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        if not has_workflows(ctx.repo):
            raise NotApplicable("no .github/workflows files")
        # --offline: no GitHub API calls. Pedantic persona is what reports unpinned actions (@latest).
        # Exit codes 10-14 mean findings of increasing severity.
        res = await run_command(
            [exe, "--format", "json", "--offline", "--no-progress", "--persona", "pedantic", str(ctx.repo)],
            cwd=ctx.work_dir, timeout=self.timeout_s, accept_codes=(0, 10, 11, 12, 13, 14),
        )
        try:
            items = json.loads(res.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise ToolFailed(f"invalid_output: {exc}") from exc
        return ScanOutput(parse_zizmor(items, ctx.repo), res.stdout, res.returncode)
