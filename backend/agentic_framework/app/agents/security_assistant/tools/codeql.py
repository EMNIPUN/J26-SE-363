"""V1/V2/V3 (code) detection with CodeQL.

Databases are created with --build-mode=none, so no student code is built or run. The
standard security-extended query suites cover injection (V2) and parts of V1/V3 through their
CWE tags; custom queries in `queries/<language>/` (if any .ql files exist) are added on top.
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from app.agents.security_assistant.schemas import Category, Finding
from app.agents.security_assistant.tools.base import (
    BaseTool, ScanContext, ScanOutput, ToolFailed, rel_path, run_command,
)

QUERIES_DIR = Path(__file__).parent / "queries"

# Even with --build-mode=none, CodeQL 2.20 runs the project's own `./gradlew` (and a `gradle` / `mvn`
# found on PATH) to collect the dependency classpath. These switches stop that; tests/test_integration_java.py
# has a canary test that fails if a CodeQL upgrade starts running build tools again.
NO_BUILD_ENV = {
    "CODEQL_EXTRACTOR_JAVA_OPTION_BUILDLESS_CLASSPATH_FROM_BUILD_FILES": "false",
    "CODEQL_EXTRACTOR_JAVA_DISABLE_GRADLE_INIT": "true",
}

# CodeQL language -> (detected languages that use it, query pack for the standard suite)
CODEQL_LANGUAGES = {
    "python": ({"python"}, "codeql/python-queries:codeql-suites/python-security-extended.qls"),
    "java-kotlin": ({"java"}, "codeql/java-queries:codeql-suites/java-security-extended.qls"),
    "javascript-typescript": (
        {"javascript", "typescript"},
        "codeql/javascript-queries:codeql-suites/javascript-security-extended.qls",
    ),
}

CWE_CATEGORY: dict[int, Category] = {
    **{c: Category.V1 for c in (22, 23, 36, 73, 284, 285, 639, 732, 862, 863, 915, 918)},
    **{c: Category.V2 for c in (74, 77, 78, 79, 80, 89, 90, 91, 94, 95, 113, 116, 117, 611, 643, 652, 776, 917, 943)},
    **{c: Category.V3 for c in (287, 288, 290, 306, 307, 327, 328, 346, 352, 384, 521, 613, 614, 759, 760, 916, 1004, 1275)},
    **{c: Category.V4 for c in (200, 209, 312, 313, 315, 319, 321, 532, 547, 798)},
    **{c: Category.V5 for c in (829, 1104)},
}


def _resource_flags() -> list[str]:
    """Limit CodeQL memory and threads; it ran out of memory in a 3.7 GB Docker VM with defaults.

    SECURITY_ASSISTANT_CODEQL_RAM_MB (default 3000) and SECURITY_ASSISTANT_CODEQL_THREADS (default 2).
    """
    ram = os.environ.get("SECURITY_ASSISTANT_CODEQL_RAM_MB", "3000")
    threads = os.environ.get("SECURITY_ASSISTANT_CODEQL_THREADS", "2")
    return [f"--ram={ram}", f"--threads={threads}"]


def _cwe_numbers(tags: list[str]) -> list[int]:
    return [int(m.group(1)) for t in tags if (m := re.search(r"cwe[-/]0*(\d+)$", t.lower()))]


def _category(tags: list[str], rule_id: str) -> tuple[Category | None, str | None]:
    for t in tags:  # custom queries can tag the category directly
        if m := re.search(r"external/security-assistant/(V[1-5])$", t):
            cwes = _cwe_numbers(tags)
            return Category(m.group(1)), (f"CWE-{cwes[0]}" if cwes else None)
    cwes = _cwe_numbers(tags)
    for c in cwes:
        if c in CWE_CATEGORY:
            return CWE_CATEGORY[c], f"CWE-{c}"
    return None, (f"CWE-{cwes[0]}" if cwes else None)


def _location(loc: dict) -> tuple[str | None, int | None]:
    phys = (loc or {}).get("physicalLocation") or {}
    return (phys.get("artifactLocation") or {}).get("uri"), (phys.get("region") or {}).get("startLine")


def parse_sarif(doc: dict, repo: Path) -> tuple[list[Finding], str | None]:
    """Convert a SARIF document. Results whose CWE maps to none of V1-V5 are skipped."""
    findings: list[Finding] = []
    version = None
    for run in doc.get("runs") or []:
        driver = (run.get("tool") or {}).get("driver") or {}
        version = (run.get("tool", {}).get("extensions") or [{}])[0].get("semanticVersion") or driver.get("semanticVersion") or version
        rules = {r.get("id"): r for r in driver.get("rules") or []}
        for res in run.get("results") or []:
            rule_id = res.get("ruleId") or "unknown"
            props = (rules.get(rule_id) or {}).get("properties") or {}
            category, cwe = _category(props.get("tags") or [], rule_id)
            if category is None:
                continue
            locs = res.get("locations") or [{}]
            uri, line = _location(locs[0])
            logical = (locs[0].get("logicalLocations") or [{}])[0].get("fullyQualifiedName")
            source = sink = None
            flows = res.get("codeFlows") or []
            if flows:
                steps = ((flows[0].get("threadFlows") or [{}])[0].get("locations")) or []
                if steps:
                    s_uri, s_line = _location(steps[0].get("location"))
                    e_uri, e_line = _location(steps[-1].get("location"))
                    source, sink = f"{s_uri}:{s_line}", f"{e_uri}:{e_line}"
            findings.append(
                Finding(
                    category=category,
                    cwe=cwe,
                    file_path=rel_path(repo, uri),
                    line=line,
                    function_or_endpoint=logical,
                    source=source,
                    sink=sink,
                    rule_id=rule_id,
                    severity_tool=str(props.get("security-severity") or props.get("problem.severity") or "") or None,
                    message=(res.get("message") or {}).get("text", ""),
                )
            )
    return findings, version


@dataclass
class CodeQLTool(BaseTool):
    name: str = "codeql"
    binary: str = "codeql"
    languages: frozenset[str] | None = frozenset({"python", "java", "javascript", "typescript"})
    default_timeout_s: float = 900

    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        findings: list[Finding] = []
        raws: list[str] = []
        version = None
        for ql_lang, (detected, suite) in CODEQL_LANGUAGES.items():
            if not (detected & ctx.languages):
                continue
            db = ctx.work_dir / f"codeql-db-{ql_lang}"
            sarif = ctx.work_dir / f"codeql-{ql_lang}.sarif"
            await run_command(
                [exe, "database", "create", str(db), f"--language={ql_lang}",
                 f"--source-root={ctx.repo}", "--build-mode=none", "--overwrite"],
                cwd=ctx.work_dir, timeout=self.timeout_s, extra_env=NO_BUILD_ENV,
            )
            queries = [suite]
            custom = QUERIES_DIR / ql_lang
            if custom.is_dir() and any(custom.rglob("*.ql")):
                queries.append(str(custom))
            await run_command(
                [exe, "database", "analyze", str(db), *queries,
                 "--format=sarif-latest", f"--output={sarif}", *_resource_flags()],
                cwd=ctx.work_dir, timeout=self.timeout_s,
            )
            try:
                text = sarif.read_text(encoding="utf-8")
                found, version = parse_sarif(json.loads(text), ctx.repo)
            except (OSError, json.JSONDecodeError) as exc:
                raise ToolFailed(f"invalid_output ({ql_lang}): {exc}") from exc
            findings += found
            raws.append(text)
        return ScanOutput(findings, "\n".join(raws), 0, rule_pack_version=version)
