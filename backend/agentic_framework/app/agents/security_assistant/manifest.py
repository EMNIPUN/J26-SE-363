"""run.json: where a run came from, written next to report.json (read by the frontend's Security Assistant pages).

Provenance only: no student data, no local paths, no secrets. `checkout` says how the code was made available to the scanners:
a public repository is cloned into a temporary folder that is deleted when the run ends; a local folder is opened in place.
The scanners only read the code; nothing in the checkout is executed.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

MANIFEST_VERSION = "run-manifest-v1"
TRIGGERS = ("manual", "push", "merged_pr")


def build(*, report: dict, is_url: bool, label: str, repo_url: str | None, commit_sha: str | None, seconds: float,
          trigger: str = "manual", now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    scan = report["scan"]
    usage = report.get("llm_usage") or {}
    return {
        "manifest_version": MANIFEST_VERSION,
        "repo": repo_url if is_url else label,  # a local folder is shown by its folder name only, never its path
        "commit_sha": commit_sha,
        "trigger": trigger,
        "scan_type": "reused-scan" if scan["reused"] else "full",
        "started_at": (now - timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checkout": {"kind": "clone-tempdir" if is_url else "local-folder", "read_only": True,
                     "deleted_after": bool(is_url), "code_executed": False},
        "tools": [{"tool": r["tool"], "version": r["tool_version"]} for r in scan["tool_runs"]],
        "llm": {"model": report["meta"]["llm_model"], "temperature": report["meta"].get("temperature"), "seed": usage.get("seed"),
                "interpreter_prompt": report["meta"]["interpreter_prompt"], "trace_prompt": report["meta"]["trace_prompt"]},
    }


def write(out: Path, manifest: dict) -> Path:
    path = Path(out) / "run.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def set_trigger(out: Path, trigger: str) -> None:
    """Record how the run was started (the command line knows; the workflow does not)."""
    if trigger not in TRIGGERS:
        raise ValueError(f"trigger must be one of {', '.join(TRIGGERS)}")
    path = Path(out) / "run.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["trigger"] = trigger
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
