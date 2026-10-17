"""Normalised shapes produced by the Security Assistant detection tools (deterministic, no LLM)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    V1 = "V1"  # Broken access control
    V2 = "V2"  # Injection
    V3 = "V3"  # Authentication failures
    V4 = "V4"  # Sensitive data exposure / hard-coded secrets
    V5 = "V5"  # Vulnerable dependencies and insecure CI/CD


class RunStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    UNAVAILABLE = "unavailable"  # binary missing
    NOT_APPLICABLE = "not_applicable"  # nothing for this tool to scan (e.g. no lockfile)


class Finding(BaseModel):
    """One scanner result. Secret values are never stored, only a masked form."""

    category: Category
    cwe: str | None = None
    file_path: str | None = None  # relative to the scanned repo
    line: int | None = None
    function_or_endpoint: str | None = None
    source: str | None = None
    sink: str | None = None
    rule_id: str
    tool: str = ""
    tool_version: str | None = None
    severity_tool: str | None = None  # severity as reported by the tool, unmapped
    message: str = ""
    masked_snippet: str | None = None
    raw_output_ref: str | None = None

    # Filled by later stages; empty here.
    confidence: float | None = None
    linked_requirement: str | None = None
    linked_commit: str | None = None
    risk_score: float | None = None
    fix_pattern: str | None = None
    probe_question: str | None = None


class ToolRun(BaseModel):
    """Record of one tool execution. `status` tells a failure apart from a clean scan."""

    tool: str
    status: RunStatus
    reason: str | None = None
    tool_version: str | None = None
    rule_pack_version: str | None = None
    started_at: datetime
    duration_s: float = 0.0
    exit_code: int | None = None
    raw_output_ref: str | None = None
    findings_count: int = 0


class ScanResult(BaseModel):
    run_id: str
    repo_path: str
    languages: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    runs: list[ToolRun] = Field(default_factory=list)

    @property
    def complete(self) -> bool:
        """True only if every tool either succeeded or had nothing to scan.

        An empty `findings` list with complete=False means "not fully scanned", not "clean".
        """
        return all(r.status in (RunStatus.SUCCEEDED, RunStatus.NOT_APPLICABLE) for r in self.runs)

    @property
    def warnings(self) -> list[str]:
        """Limitations of runs that succeeded, e.g. "Gradle dependencies NOT scanned: no lockfile"."""
        return [f"{r.tool}: {r.reason}" for r in self.runs if r.status is RunStatus.SUCCEEDED and r.reason]
