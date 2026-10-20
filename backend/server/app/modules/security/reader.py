"""Reads the result folders of the Security Assistant. Read-only: nothing here writes, and nothing imports the agent's code.

    <root>/<team-code>/<run-id>/{report.json, run.json, audit.jsonl, report.md, trace_mapping.local.json}
    <root>/_shared/<file>.{mmd,md,csv}

Safety rules (tests/test_security_assistant_reader.py):
  * a team code, run id or shared file name that is not a plain name is refused, and every resolved path must stay inside the root;
  * only the whitelisted file names are ever opened, and trace_mapping.local.json only to answer "which contributor id is this e-mail",
    never to return its content;
  * every string that leaves is checked again for secrets and e-mail addresses, and a contributor id that is not C-xxxxxxxx is dropped.
"""

import json
import re
from pathlib import Path

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
SHARED_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.(mmd|md|csv)$")
CONTRIBUTOR = re.compile(r"^C-[0-9a-f]{8}$")
REPORT, MANIFEST, AUDIT, MARKDOWN, MAPPING = "report.json", "run.json", "audit.jsonl", "report.md", "trace_mapping.local.json"
STATUSES = ("confirmed", "dismissed", "uncertain")
CATEGORIES = ("V1", "V2", "V3", "V4", "V5")
DROPPED_KEYS = {"email", "author", "author_email", "author_name", "authors"}

_SECRETS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{8,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"),
]
_ASSIGNED = re.compile(r"""(?i)\b((?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*)(["'])(?!\[REDACTED)[^"'\s]{8,}\2""")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


class NotFound(Exception):
    """No such team folder, run, or file (also raised for a name that is not allowed: the caller cannot tell the difference)."""


def clean_text(text: str) -> str:
    for pattern in _SECRETS:
        text = pattern.sub("[REDACTED by API]", text)
    text = _ASSIGNED.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED by API]{m.group(2)}", text)
    return _EMAIL.sub("[email removed]", text)


def sanitize(node):
    """A copy of a JSON value that is safe to return: strings re-checked, address-like keys dropped, contributor ids validated."""
    if isinstance(node, str):
        return clean_text(node)
    if isinstance(node, list):
        return [sanitize(v) for v in node]
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key in DROPPED_KEYS:
                continue
            if key == "contributor":
                out[key] = value if isinstance(value, str) and CONTRIBUTOR.match(value) else None
            else:
                out[key] = sanitize(value)
        return out
    return node


def counts(findings: list[dict]) -> dict[str, dict[str, int]]:
    """{category: {confirmed, dismissed, uncertain, not interpreted}} over the report's findings."""
    out = {c: {s: 0 for s in (*STATUSES, "not interpreted")} for c in CATEGORIES}
    for f in findings:
        row = out.setdefault(f["category"], {s: 0 for s in (*STATUSES, "not interpreted")})
        row[f["status"] if f["status"] in row else "uncertain"] += 1
    return out


class ResultsReader:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    # ---- paths ---------------------------------------------------------------------------------------------------------------------------
    def _inside(self, *parts: str) -> Path:
        path = self.root.joinpath(*parts)
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError:
            raise NotFound("outside the results folder") from None
        return path

    def _run_dir(self, team: str, run_id: str) -> Path:
        if not (NAME.match(team) and NAME.match(run_id)):
            raise NotFound("no such run")
        path = self._inside(team, run_id)
        if not path.is_dir():
            raise NotFound("no such run")
        return path

    @staticmethod
    def _json(path: Path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise NotFound(f"{path.name} is missing or not valid") from None

    # ---- runs ----------------------------------------------------------------------------------------------------------------------------
    def run_ids(self, team: str) -> list[str]:
        if not NAME.match(team):
            return []
        folder = self._inside(team)
        if not folder.is_dir():
            return []
        return sorted(p.name for p in folder.iterdir() if p.is_dir() and NAME.match(p.name) and (p / REPORT).is_file())

    def run(self, team: str, run_id: str) -> dict:
        """{"run_id", "manifest", "report"} with every string re-checked. `manifest` is {} for a run folder without run.json."""
        folder = self._run_dir(team, run_id)
        report = self._json(folder / REPORT)
        try:
            manifest = self._json(folder / MANIFEST)
        except NotFound:
            manifest = {}
        return {"run_id": run_id, "manifest": sanitize(manifest), "report": sanitize(report)}

    def summaries(self, team: str) -> list[dict]:
        """One line per run, newest first."""
        rows = []
        for run_id in self.run_ids(team):
            try:
                run = self.run(team, run_id)
            except NotFound:
                continue
            m, rep = run["manifest"], run["report"]
            rows.append({"run_id": run_id, "started_at": m.get("started_at"), "trigger": m.get("trigger"), "scan_type": m.get("scan_type"),
                         "repo": m.get("repo") or rep["meta"].get("source"), "commit_sha": m.get("commit_sha"),
                         "complete": bool(rep["run"]["complete"]), "counts": counts(rep["findings"])})
        return sorted(rows, key=lambda r: (r["started_at"] or "", r["run_id"]), reverse=True)

    def audit(self, team: str, run_id: str) -> list[dict]:
        folder = self._run_dir(team, run_id)
        path = folder / AUDIT
        if not path.is_file():
            return []
        lines = []
        for text in path.read_text(encoding="utf-8").splitlines():
            try:
                lines.append(sanitize(json.loads(text)))
            except ValueError:
                continue
        return lines

    def contributor_ids(self, team: str, run_id: str, email: str | None) -> list[str]:
        """The contributor ids of this e-mail address in the run's local mapping. The file itself is never returned."""
        if not email:
            return []
        folder = self._run_dir(team, run_id)
        try:
            people = self._json(folder / MAPPING).get("contributors", {})
        except NotFound:
            return []
        wanted = email.strip().lower()
        return sorted(pid for pid, who in people.items()
                      if CONTRIBUTOR.match(pid) and isinstance(who, dict) and (who.get("email") or "").strip().lower() == wanted)

    # ---- shared files (diagrams, RQ1) ------------------------------------------------------------------------------------------------------
    def shared(self, name: str) -> str:
        if not SHARED_NAME.match(name):
            raise NotFound("no such file")
        path = self._inside("_shared", name)
        if not path.is_file():
            raise NotFound("no such file")
        return clean_text(path.read_text(encoding="utf-8"))
