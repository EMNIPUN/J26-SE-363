"""V4 secret scanners: Gitleaks (full git history) and TruffleHog (entropy/detectors)."""

import json
from dataclasses import dataclass
from pathlib import Path

from app.agents.security_assistant.schemas import Category, Finding
from app.agents.security_assistant.tools.base import (
    BaseTool, ScanContext, ScanOutput, ToolFailed, mask_secret, rel_path, run_command,
)

CWE_HARDCODED_CREDENTIALS = "CWE-798"


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    return value if value == "REDACTED" else mask_secret(value)


def parse_gitleaks(report: list[dict], repo: Path) -> list[Finding]:
    """Gitleaks JSON report (run with --redact, so values arrive already hidden)."""
    findings = []
    for item in report:
        findings.append(
            Finding(
                category=Category.V4,
                cwe=CWE_HARDCODED_CREDENTIALS,
                file_path=rel_path(repo, item.get("File")),
                line=item.get("StartLine"),
                source=f"commit:{item['Commit']}" if item.get("Commit") else None,
                rule_id=item.get("RuleID", "unknown"),
                severity_tool=None,  # gitleaks reports no severity
                message=item.get("Description", ""),
                masked_snippet=_mask(item.get("Secret")),
            )
        )
    return findings


@dataclass
class GitleaksTool(BaseTool):
    name: str = "gitleaks"
    binary: str = "gitleaks"
    version_args: tuple[str, ...] = ("version",)

    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        report = ctx.work_dir / "gitleaks-report.json"
        argv = [
            exe, "detect", "--source", str(ctx.repo), "--report-format", "json",
            "--report-path", str(report), "--redact", "--no-banner", "--exit-code", "0",
        ]
        if not (ctx.repo / ".git").exists():
            argv.append("--no-git")  # no history to scan; recorded in the raw output
        res = await run_command(argv, cwd=ctx.work_dir, timeout=self.timeout_s)
        try:
            data = json.loads(report.read_text(encoding="utf-8") or "[]")
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolFailed(f"invalid_output: {exc}") from exc
        for item in data:  # keep nothing but redacted values in the saved raw output
            item["Secret"] = "REDACTED"
            item["Match"] = "REDACTED"
        return ScanOutput(parse_gitleaks(data, ctx.repo), json.dumps(data, indent=1), res.returncode)


def parse_trufflehog(lines: list[dict], repo: Path) -> list[Finding]:
    findings = []
    for item in lines:
        git = ((item.get("SourceMetadata") or {}).get("Data") or {}).get("Git") or {}
        fs = ((item.get("SourceMetadata") or {}).get("Data") or {}).get("Filesystem") or {}
        raw = item.get("Raw") or ""
        findings.append(
            Finding(
                category=Category.V4,
                cwe=CWE_HARDCODED_CREDENTIALS,
                file_path=rel_path(repo, git.get("file") or fs.get("file")),
                line=git.get("line") or fs.get("line"),
                source=f"commit:{git['commit']}" if git.get("commit") else None,
                rule_id=item.get("DetectorName", "unknown"),
                severity_tool=None,
                message=f"{item.get('DetectorName', 'secret')} candidate",
                masked_snippet=mask_secret(raw) if raw else None,
            )
        )
    return findings


@dataclass
class TruffleHogTool(BaseTool):
    name: str = "trufflehog"
    binary: str = "trufflehog"

    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        # --no-verification: never send found credentials to the provider to test them.
        source = ["git", f"file://{ctx.repo}"] if (ctx.repo / ".git").exists() else ["filesystem", str(ctx.repo)]
        argv = [exe, *source, "--json", "--no-update", "--no-verification"]
        res = await run_command(argv, cwd=ctx.work_dir, timeout=self.timeout_s)
        lines = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ToolFailed(f"invalid_output: {exc}") from exc
            if "DetectorName" in obj:  # skip log lines that are also JSON
                lines.append(obj)
        findings = parse_trufflehog(lines, ctx.repo)
        for obj in lines:  # scrub every field that can hold the secret before saving
            for key in ("Raw", "RawV2", "Redacted"):
                if obj.get(key):
                    obj[key] = mask_secret(obj[key])
        return ScanOutput(findings, "\n".join(json.dumps(o) for o in lines), res.returncode)
