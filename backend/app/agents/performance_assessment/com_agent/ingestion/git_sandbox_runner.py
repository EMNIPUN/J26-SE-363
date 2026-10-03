"""Sandboxed Git command runner on local repository clones.

Strictly aligned with:
- PLAN.md Section 12.7 (GitHub API Rate Limiting — Per-Student Cap with Sandbox Fallback)
- Strict whitelist enforcement (read-only git operations only)
- Subprocess execution with author isolation
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any
from app.agents.performance_assessment.com_agent.policies.retry_policy import retry_with_backoff

logger = logging.getLogger(__name__)

ALLOWED_GIT_COMMANDS = ["log", "diff", "show", "shortlog", "blame"]


@retry_with_backoff(max_attempts=2, base_delay_seconds=0.1)
async def run_git_command(
    repo_path: str,
    subcommand: str,
    args: Optional[List[str]] = None,
    author_filter: Optional[str] = None,
) -> str:
    """Executes a strictly whitelisted read-only git command in a subprocess.

    Raises PermissionError if subcommand is not in ALLOWED_GIT_COMMANDS.
    """
    if subcommand not in ALLOWED_GIT_COMMANDS:
        raise PermissionError(
            f"Git subcommand '{subcommand}' is forbidden. Allowed: {ALLOWED_GIT_COMMANDS}"
        )

    cmd = ["git", "-C", repo_path, subcommand]
    if author_filter:
        cmd.append(f"--author={author_filter}")
    if args:
        cmd.extend(args)

    logger.debug(f"Running sandboxed git command: {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Git command '{subcommand}' failed (code {proc.returncode}): {err_msg}")

    return stdout.decode("utf-8", errors="replace")


def parse_git_log_to_commits(raw: str) -> List[Dict[str, Any]]:
    """Parses raw git log output into normalized commit dictionaries.

    Format expected or handled: standard or custom delimiter formats.
    """
    if not raw.strip():
        return []

    commits: List[Dict[str, Any]] = []
    # Match standard commit blocks: commit <sha>\nAuthor: <name> <<email>>\nDate: <date>\n\n<message>
    blocks = re.split(r"(?m)^commit\s+([0-9a-fA-F]+)", raw)

    # First element before any match is empty or preamble
    i = 1
    while i < len(blocks):
        sha = blocks[i].strip()
        body = blocks[i + 1] if (i + 1) < len(blocks) else ""
        i += 2

        author_name = ""
        author_email = ""
        date_str = ""
        message_lines = []

        for line in body.strip().splitlines():
            line_str = line.strip()
            if line.startswith("Author:"):
                m = re.search(r"Author:\s*(.*?)\s*<([^>]+)>", line)
                if m:
                    author_name = m.group(1).strip()
                    author_email = m.group(2).strip()
            elif line.startswith("Date:"):
                date_str = line.replace("Date:", "").strip()
            elif line_str and not line.startswith("Merge:"):
                message_lines.append(line_str)

        commits.append({
            "sha": sha,
            "author": {"login": author_name or "unknown"},
            "commit": {
                "author": {
                    "name": author_name,
                    "email": author_email,
                    "date": date_str,
                },
                "message": "\n".join(message_lines),
            },
            "stats": {"additions": 0, "deletions": 0, "total": 0},
            "files": [],
            "parents": [{"sha": "unknown"}],
        })

    return commits


def parse_git_diff_to_files(raw: str) -> List[Dict[str, Any]]:
    """Parses git diff --stat or raw diff into list of touched file objects."""
    if not raw.strip():
        return []

    files: List[Dict[str, Any]] = []
    # Parse diff --stat lines e.g. " backend/app/main.py | 12 +++---"
    stat_pattern = re.compile(r"^\s*(\S+)\s*\|\s*(\d+)\s*(.*)$")

    for line in raw.splitlines():
        m = stat_pattern.match(line)
        if m:
            file_path = m.group(1).strip()
            total_changes = int(m.group(2))
            hist = m.group(3)
            adds = hist.count("+")
            dels = hist.count("-")
            files.append({
                "filename": file_path,
                "changes": total_changes,
                "additions": adds,
                "deletions": dels,
            })

    return files


class GitSandboxRunner:
    """Manages sandboxed execution on a cloned student repository."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    async def get_commits(
        self,
        author_username: str,
        author_emails: List[str],
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Collects author commits via git log."""
        # Use first email or username for author filter
        filter_str = author_emails[0] if author_emails else author_username
        args = ["--no-merges", "--date=iso-strict"]
        if since:
            args.append(f"--since={since}")
        if until:
            args.append(f"--until={until}")

        raw = await run_git_command(
            repo_path=self.repo_path,
            subcommand="log",
            args=args,
            author_filter=filter_str,
        )
        return parse_git_log_to_commits(raw)
