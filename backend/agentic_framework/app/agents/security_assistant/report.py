"""Turn a scan result into something a person can read: a findings table, a per-tool status table, a coverage
check and two files (findings.json, report.md). Secrets are masked in everything written.

Coverage matters as much as findings: "0 findings" only means something for a category if a tool that can find
it actually ran. `coverage()` says, per category V1-V5, whether that was the case.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.agents.security_assistant import guidance as guide
from app.agents.security_assistant.redaction import redact_text
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.schemas import Category, Finding, RunStatus, ScanResult, ToolRun

CATEGORY_NAMES = {
    Category.V1: "Broken access control",
    Category.V2: "Injection",
    Category.V3: "Authentication failures",
    Category.V4: "Sensitive data exposure / hard-coded secrets",
    Category.V5: "Vulnerable dependencies and insecure CI/CD",
}

# Which tools can find which category: (tool, what it looks for, primary). A category is only "covered" if its
# primary tools ran; secondary tools find a part of it.
CAPABILITY: dict[Category, list[tuple[str, str, bool]]] = {
    Category.V1: [("codeql", "missing ownership / authorisation check queries", True),
                  ("config-scan", "only Spring rules (permitAll, no Spring Security)", False)],
    Category.V2: [("codeql", "SQL / command / XSS injection data flow", True)],
    Category.V3: [("codeql", "cookie flags, missing rate limiting", True),
                  ("config-scan", "JWT expiry, cookies, password hashing, CSRF, Spring config", True)],
    Category.V4: [("gitleaks", "secrets in files and git history", True),
                  ("trufflehog", "detector and entropy based secrets", True),
                  ("codeql", "hard-coded credentials in code", False)],
    Category.V5: [("osv-scanner", "known CVEs in manifests and lockfiles", True),
                  ("npm-audit", "known CVEs in npm packages", True),
                  ("pip-audit", "known CVEs in Python packages", True),
                  ("actionlint", "workflow syntax and expressions", True),
                  ("zizmor", "workflow security (pull_request_target, permissions, unpinned actions)", True)],
}
SNIPPET_RADIUS = 3
MAX_SNIPPETS = 80
MAX_FILE_BYTES = 1_000_000


@dataclass
class CategoryCoverage:
    level: str  # FULL | REDUCED | NONE | NOTHING TO SCAN
    note: str
    tools: dict[str, str] = field(default_factory=dict)  # tool -> ran | not applicable | skipped | failed


@dataclass
class ScanReport:
    source: str
    commit_sha: str | None
    started_at: str
    languages: list[str]
    runs: list[ToolRun]
    findings: list[Finding]
    skipped: list[str]
    warnings: list[str]
    complete: bool
    coverage: dict[Category, CategoryCoverage]
    snippets: dict[int, str] = field(default_factory=dict)  # finding index -> masked code snippet


def _state(tool: str, runs: dict[str, ToolRun], skipped: set[str]) -> str:
    if tool in skipped:
        return "skipped"
    run = runs.get(tool)
    if run is None:
        return "failed"  # expected but missing: never treat as covered
    return {RunStatus.SUCCEEDED: "ran", RunStatus.NOT_APPLICABLE: "not applicable"}.get(run.status, "failed")


def coverage(runs: list[ToolRun], skipped: list[str]) -> dict[Category, CategoryCoverage]:
    by_tool, skip = {r.tool: r for r in runs}, set(skipped)
    out: dict[Category, CategoryCoverage] = {}
    for category, tools in CAPABILITY.items():
        states = {t: _state(t, by_tool, skip) for t, _what, _p in tools}
        primary = [t for t, _w, p in tools if p and states[t] != "not applicable"]
        secondary_ran = [t for t, _w, p in tools if not p and states[t] == "ran"]
        ran = [t for t in primary if states[t] == "ran"]
        missing = [f"{t} ({states[t]})" for t in primary if states[t] != "ran"]
        if not primary:
            level, note = "NOTHING TO SCAN", "no tool for this category applies to this project"
        elif not ran:
            extra = f"; partial: {', '.join(secondary_ran)} ran" if secondary_ran else ""
            level, note = "NONE", f"{', '.join(missing)} did not run, so 0 findings here means nothing{extra}"
        elif missing:
            level, note = "REDUCED", f"{', '.join(ran)} ran; {', '.join(missing)} did not"
        else:
            level, note = "FULL", f"{', '.join(ran)} ran"
        out[category] = CategoryCoverage(level, note, states)
    return out


def _snippet(repo: Path, finding: Finding, pii: PIIRedactor) -> str | None:
    if not finding.file_path or not finding.line:
        return None
    try:
        path = (repo / finding.file_path).resolve()
        path.relative_to(repo.resolve())  # never read outside the scanned folder
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return None
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except (OSError, ValueError):
        return None
    if not 1 <= finding.line <= len(lines):
        return None
    lo, hi = max(1, finding.line - SNIPPET_RADIUS), min(len(lines), finding.line + SNIPPET_RADIUS)
    window = lines[lo - 1:hi]
    safe = pii.redact_code("\n".join(window)).split("\n")  # e-mails, phone numbers, student ids in comments and strings
    window = safe if len(safe) == len(window) else [pii.redact_code(x) for x in window]
    out = []
    for no in range(lo, hi + 1):
        text = window[no - lo]
        if no == finding.line and finding.category is Category.V4:
            text = "<line hidden: it holds the secret>"  # never show the line of a secret finding
        out.append(f"{'>' if no == finding.line else ' '} {no:4d} | {redact_text(text)}")
    return "\n".join(out)


def build_report(result: ScanResult, *, skipped: list[str] | None = None, source: str | None = None,
                 repo: Path | None = None, pii: PIIRedactor | None = None) -> ScanReport:
    skipped = sorted(skipped or [])
    snippets: dict[int, str] = {}
    pii = pii if pii is not None else PIIRedactor.from_env()  # snippets are the student's own code: personal data is replaced here too
    if repo is not None:
        for i, f in enumerate(result.findings):
            if len(snippets) >= MAX_SNIPPETS:
                break
            if text := _snippet(Path(repo), f, pii):
                snippets[i] = text
    return ScanReport(
        source=source or result.repo_url or result.repo_path, commit_sha=result.commit_sha,
        started_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), languages=result.languages,
        runs=result.runs, findings=result.findings, skipped=skipped, warnings=result.warnings,
        complete=result.complete, coverage=coverage(result.runs, skipped), snippets=snippets,
    )


# ---- plain text (console) --------------------------------------------------------------------------------------
def _cut(text: str, width: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 3] + "..."


def _location(f: Finding) -> str:
    if f.file_path:
        return f"{f.file_path}:{f.line}" if f.line else f.file_path
    return f.sink or "-"


def _sorted(findings: list[Finding]) -> list[tuple[int, Finding]]:
    return sorted(enumerate(findings), key=lambda p: (p[1].category.value, p[1].tool, p[1].file_path or "", p[1].line or 0))


def render_console(rep: ScanReport, max_rows: int = 60, out_dir: Path | None = None) -> str:
    L: list[str] = []
    L.append(f"Scan of {rep.source}" + (f" @ {rep.commit_sha[:12]}" if rep.commit_sha else ""))
    L.append(f"Languages detected: {', '.join(rep.languages) or 'none'}")
    L.append("")
    L.append("TOOLS")
    L.append(f"{'tool':<13}{'status':<16}{'findings':>8}  {'time':>6}  note")
    ran = {r.tool for r in rep.runs}
    for r in rep.runs:
        L.append(f"{r.tool:<13}{r.status.value:<16}{r.findings_count:>8}  {r.duration_s:>5.1f}s  {_cut(r.reason or '', 70)}")
    for t in rep.skipped:
        if t not in ran:
            L.append(f"{t:<13}{'SKIPPED':<16}{'-':>8}  {'-':>6}  skipped with --skip")
    L.append("")
    L.append("COVERAGE (can a tool that finds this category be trusted to have looked?)")
    for category, cov in rep.coverage.items():
        L.append(f"{category.value} {CATEGORY_NAMES[category]:<46} {cov.level:<16} {_cut(cov.note, 80)}")
    L.append("")
    counts = {c: sum(1 for f in rep.findings if f.category is c) for c in Category}
    L.append(f"FINDINGS: {len(rep.findings)} total  (" + ", ".join(f"{c.value}={n}" for c, n in counts.items()) + ")")
    L.append(f"{'#':>3} {'cat':<4}{'tool':<12}{'rule':<45}{'CWE':<9}{'location':<40}severity")
    for n, (_i, f) in enumerate(_sorted(rep.findings)[:max_rows], 1):
        L.append(f"{n:>3} {f.category.value:<4}{f.tool:<12}{_cut(f.rule_id, 44):<45}{(f.cwe or '-'):<9}"
                 f"{_cut(_location(f), 39):<40}{f.severity_tool or '-'}")
    if len(rep.findings) > max_rows:
        L.append(f"    ... {len(rep.findings) - max_rows} more in report.md / findings.json")
    L.append("")
    failed = [r for r in rep.runs if r.status not in (RunStatus.SUCCEEDED, RunStatus.NOT_APPLICABLE)]
    if failed:
        L.append("RESULT: INCOMPLETE - " + ", ".join(f"{r.tool} ({r.status.value})" for r in failed)
                 + " did not finish. Missing findings from those tools do NOT mean the project is clean.")
    else:
        L.append("RESULT: COMPLETE for the tools that ran" + (" (no tool failed)." if not rep.skipped else "."))
    if rep.skipped:
        weak = [f"{c.value} {cov.level}" for c, cov in rep.coverage.items() if cov.level in ("NONE", "REDUCED")]
        L.append(f"SKIPPED with --skip: {', '.join(rep.skipped)}. Categories affected: {', '.join(weak) or 'none'}.")
    for w in rep.warnings:
        L.append(f"WARNING: {w}")
    if out_dir:
        L.append(f"Wrote {out_dir / 'findings.json'} and {out_dir / 'report.md'}")
    return "\n".join(L)


# ---- findings.json and report.md ---------------------------------------------------------------------------------
def to_json(rep: ScanReport) -> str:
    def masked(f: Finding) -> dict:
        d = f.model_dump(mode="json")
        for key in ("message", "masked_snippet", "source", "sink"):
            if d.get(key):
                d[key] = redact_text(d[key])
        d["fix_pattern"] = guide.guidance_for(f).id  # which "how to fix" entry applies (see report.md)
        return d

    doc = {
        "scan": {"source": rep.source, "commit_sha": rep.commit_sha, "started_at": rep.started_at,
                 "languages": rep.languages, "complete": rep.complete, "skipped_tools": rep.skipped,
                 "warnings": rep.warnings},
        "coverage": {c.value: {"level": v.level, "note": v.note, "tools": v.tools} for c, v in rep.coverage.items()},
        "runs": [r.model_dump(mode="json") for r in rep.runs],
        "findings": [masked(f) for f in rep.findings],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)


def from_json(text: str) -> tuple[ScanResult, list[str]]:
    """Read a findings.json written by to_json back into a ScanResult (and the list of skipped tools)."""
    doc = json.loads(text)
    meta = doc["scan"]
    result = ScanResult(run_id="saved", repo_path=meta.get("source", ""), languages=meta.get("languages", []),
                        findings=[Finding.model_validate(f) for f in doc["findings"]],
                        runs=[ToolRun.model_validate(r) for r in doc["runs"]], commit_sha=meta.get("commit_sha"))
    return result, meta.get("skipped_tools", [])


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def how_to_fix_section(findings: list[Finding]) -> list[str]:
    """One block per kind of issue (not per finding): why it matters, fix steps, a short example in the language of the
    affected files and where it applies. Written by the team (guidance.py), the same for every scan."""
    groups: dict[str, tuple[guide.Guidance, list[Finding]]] = {}
    for f in findings:
        g = guide.guidance_for(f)
        groups.setdefault(g.id, (g, []))[1].append(f)
    if not groups:
        return []
    out = ["", "## How to fix (by type of issue)", "",
           "Standard advice, written by the course team. Every finding above points to one of these. The examples are "
           "short suggestions: adapt them to your code and run your tests.", ""]
    for g, items in sorted(groups.values(), key=lambda p: (p[0].category.value, p[0].title)):
        out += [f"### {g.category.value}: {g.title}", "", guide.render_markdown(g, items), ""]
        where = sorted({_location(f) for f in items})
        out += ["Applies to: " + ", ".join(f"`{w}`" for w in where[:8]) + (f" and {len(where) - 8} more" if len(where) > 8 else ""), ""]
    return out


def render_markdown(rep: ScanReport) -> str:
    M: list[str] = ["# Security scan report", ""]
    M += [f"- **Source:** {_cell(rep.source)}" + (f" @ `{rep.commit_sha}`" if rep.commit_sha else ""),
          f"- **Scanned:** {rep.started_at}", f"- **Languages:** {', '.join(rep.languages) or 'none'}",
          f"- **Findings:** {len(rep.findings)}"]
    failed = [r for r in rep.runs if r.status not in (RunStatus.SUCCEEDED, RunStatus.NOT_APPLICABLE)]
    if failed:
        M.append("- **Result: INCOMPLETE** - " + ", ".join(f"{r.tool} ({r.status.value})" for r in failed)
                 + " did not finish; missing findings from them do not mean the project is clean.")
    else:
        M.append("- **Result:** every tool that ran finished" + ("; some were skipped, see coverage." if rep.skipped else "."))
    if rep.skipped:
        M.append(f"- **Skipped with --skip:** {', '.join(rep.skipped)}")
    M += [f"- **Warning:** {_cell(w)}" for w in rep.warnings]
    M += ["", "## Tools", "", "| tool | status | findings | seconds | note |", "|---|---|---|---|---|"]
    ran = {r.tool for r in rep.runs}
    M += [f"| {r.tool} | {r.status.value} | {r.findings_count} | {r.duration_s:.1f} | {_cell(r.reason or '')} |" for r in rep.runs]
    M += [f"| {t} | **skipped** | - | - | skipped with --skip |" for t in rep.skipped if t not in ran]
    M += ["", "## Coverage by category", "",
          "A category with level NONE has not been checked: 0 findings there says nothing.", "",
          "| category | coverage | findings | detail |", "|---|---|---|---|"]
    for c, cov in rep.coverage.items():
        n = sum(1 for f in rep.findings if f.category is c)
        M.append(f"| {c.value} {CATEGORY_NAMES[c]} | **{cov.level}** | {n} | {_cell(cov.note)} |")
    for category in Category:
        items = [(i, f) for i, f in _sorted(rep.findings) if f.category is category]
        cov = rep.coverage[category]
        M += ["", f"## {category.value} {CATEGORY_NAMES[category]} ({len(items)})", ""]
        if cov.level in ("NONE", "REDUCED"):
            M += [f"> Coverage {cov.level}: {cov.note}", ""]
        if not items:
            M.append("No findings.")
        for n, (i, f) in enumerate(items, 1):
            M += [f"### {category.value}.{n} `{f.rule_id}` - {_cell(_location(f))}", "",
                  f"- **Tool:** {f.tool} {f.tool_version or ''}".rstrip(),
                  f"- **CWE:** {f.cwe or '-'}   **Severity (from tool):** {f.severity_tool or '-'}",
                  f"- **Where:** {_cell(_location(f))}" + (f" in `{f.function_or_endpoint}`" if f.function_or_endpoint else ""),
                  f"- **Message:** {_cell(redact_text(f.message)) or '-'}"]
            M.append(f"- **How to fix:** {guide.guidance_for(f).title} (see \"How to fix\" below)")
            if f.fixed_versions:
                M.append(f"- **Fixed in:** {', '.join(f.fixed_versions)} (from the advisory)")
            if f.source or f.sink:
                M.append(f"- **Source -> sink:** {_cell(redact_text(f.source or '-'))} -> {_cell(redact_text(f.sink or '-'))}")
            if f.masked_snippet:
                M.append(f"- **Masked value:** `{_cell(redact_text(f.masked_snippet))}`")
            if i in rep.snippets:
                M += ["", "```", rep.snippets[i], "```"]
            M.append("")
    M += how_to_fix_section(rep.findings)
    return "\n".join(M) + "\n"


def upsert_section(md_path: Path, marker: str, text: str) -> None:
    """Put `text` (which starts with `marker`, an HTML comment on its own line) into report.md: replace the section with
    that marker, or append it. A section runs until the next line that starts with another `<!-- ... -->` marker."""
    md_path = Path(md_path)
    current = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    lines, out, skipping, done = current.splitlines(), [], False, False
    for line in lines:
        if line.strip() == marker:
            skipping = True
            if not done:
                out += text.rstrip("\n").splitlines()
                done = True
            continue
        if skipping and line.startswith("<!-- "):
            skipping = False
        if not skipping:
            out.append(line)
    if not done:
        out += ([""] if out else []) + text.rstrip("\n").splitlines()
    md_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_report(rep: ScanReport, out_dir: Path) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = out_dir / "findings.json", out_dir / "report.md"
    json_path.write_text(to_json(rep), encoding="utf-8")
    md_path.write_text(render_markdown(rep), encoding="utf-8")
    return json_path, md_path
