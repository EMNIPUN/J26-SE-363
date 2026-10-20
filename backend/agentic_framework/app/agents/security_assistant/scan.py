"""Scan a folder or a public GitHub repository and show what was found.

    python -m app.agents.security_assistant.scan <folder | https://github.com/owner/repo> [options]

    --out DIR         where to write findings.json and report.md (default: scan_output/<name>_<time>)
    --skip a,b        leave tools out (repeatable), e.g. --skip codeql for the fast tools only
    --ref SHA         commit to check out when the source is a URL (default: the default branch)
    --from-json FILE  do not scan: re-render a findings.json written earlier (give the folder as <source> for snippets)
    --max-rows N      rows of the findings table printed to the console (default 60)

Exit code: 0 = every tool that ran finished, 2 = a tool failed, timed out or was unavailable, 3 = bad usage.
"""

import argparse
import asyncio
import contextlib
import re
import sys
from datetime import datetime
from pathlib import Path

from app.agents.security_assistant.pipeline import FetchError, fetch_repo
from app.agents.security_assistant.agent_loop import render_trail
from app.agents.security_assistant.governance import AUDIT_FILE, AuditLog
from app.agents.security_assistant.orchestrator import orchestrate
from app.agents.security_assistant.report import build_report, from_json, render_console, upsert_section, write_report

TRAIL_MARK = "<!-- decision-trail-orchestrator -->"
from app.agents.security_assistant.tools.runner import InvalidRepoPath, default_tools, run_all


def tool_names() -> list[str]:
    return [t.name for t in default_tools()]


def parse_skip(values: list[str] | None) -> list[str]:
    names = [n.strip() for v in (values or []) for n in v.split(",") if n.strip()]
    unknown = sorted(set(names) - set(tool_names()))
    if unknown:
        raise ValueError(f"unknown tool(s) for --skip: {', '.join(unknown)}. Valid names: {', '.join(tool_names())}")
    return sorted(set(names))


def _label(source: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", source.rstrip("/").split("/")[-1]) or "scan"
    return name[:-4] if name.endswith(".git") else name


async def scan(source: str, *, skip: list[str], ref: str | None = None, out_dir: Path | None = None,
               max_rows: int = 60) -> tuple[str, int]:
    """Returns (console text, exit code). Writes findings.json and report.md into out_dir."""
    is_url = source.startswith(("https://", "http://"))
    out_dir = out_dir or Path("scan_output") / f"{_label(source)}_{datetime.now():%Y%m%d-%H%M%S}"
    tools = [t for t in default_tools() if t.name not in skip]
    try:
        repo_ctx = fetch_repo(source, ref) if is_url else contextlib.nullcontext(Path(source))
        async with repo_ctx as repo:  # a cloned repo is deleted when this block ends, so snippets are read inside it
            if not Path(repo).is_dir():
                raise InvalidRepoPath(f"not a directory: {source}")
            outcome = await orchestrate(Path(repo), tools, skipped=skip, audit=AuditLog(out_dir / AUDIT_FILE))
            result = outcome.result
            report = build_report(result, skipped=skip, source=source, repo=Path(repo))
            report.commit_sha = ref if is_url else None
    except (FetchError, InvalidRepoPath) as exc:
        return f"cannot scan {source}: {exc}", 3
    write_report(report, out_dir)
    upsert_section(out_dir / "report.md", TRAIL_MARK, f"{TRAIL_MARK}\n" + render_trail({"Analysis Orchestrator": outcome.trail}))
    code = 0 if report.complete else 2
    return render_console(report, max_rows=max_rows, out_dir=out_dir), code


def render_saved(json_file: Path, repo: Path | None, out_dir: Path, max_rows: int = 60) -> tuple[str, int]:
    result, skipped = from_json(Path(json_file).read_text(encoding="utf-8"))
    report = build_report(result, skipped=skipped, source=result.repo_path, repo=repo)
    write_report(report, out_dir)
    return render_console(report, max_rows=max_rows, out_dir=out_dir), 0 if report.complete else 2


async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?", help="local folder or https://github.com/owner/repo")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--skip", action="append", metavar="TOOLS")
    ap.add_argument("--ref")
    ap.add_argument("--from-json", type=Path, dest="from_json")
    ap.add_argument("--max-rows", type=int, default=60)
    args = ap.parse_args(argv)
    try:
        skip = parse_skip(args.skip)
        if args.from_json:
            out = args.out or Path("scan_output") / f"{args.from_json.stem}_rerendered"
            text, code = render_saved(args.from_json, Path(args.source) if args.source else None, out, args.max_rows)
        elif args.source:
            text, code = await scan(args.source, skip=skip, ref=args.ref, out_dir=args.out, max_rows=args.max_rows)
        else:
            ap.error("give a folder or a GitHub URL (or --from-json)")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 3
    print(text)
    return code


if __name__ == "__main__":
    if sys.platform == "win32":  # tools and git are subprocesses
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
