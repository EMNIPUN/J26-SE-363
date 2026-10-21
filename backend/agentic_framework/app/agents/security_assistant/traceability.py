"""Traceability: from a confirmed finding to the commit that introduced it and, when requirement files are given, to the
user story and sprint task it belongs to.

Input files (local JSON for now; treat the format as the future contract with the Requirements agent):

  requirements.json  {"stories": [{"id": "US-01", "title": "...", "acceptance_criteria": ["...", "..."]}]}
  tasks.json         {"tasks": [{"id": "T-101", "title": "...", "sprint": "Sprint 1", "story_id": "US-01" | null,
                                 "commits": ["<sha or at least 7 characters of it>", ...]}]}

Ids are letters, digits, "." "_" "-" (for example US-01, T-101). Both files are optional. Without a requirements file
findings are linked to commits only.

Wording: this is the *introducing commit* (the commit that added the line), found with read-only `git log -L`. Nothing here
says who is to blame: a contributor appears only as a pseudonymous id (a keyed hash of the author); the mapping back to the
real name and email stays in a local, git-ignored file and is never put in a prompt, report or JSON output.
"""

import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from app.agents.security_assistant.interpreter.evidence import _git_read
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.schemas import Finding

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,39}$")
SHA = re.compile(r"^[0-9a-f]{7,40}$")
RULE_CONFIDENCE = {"commit_message_reference": 0.95, "task_commit_list": 0.95, "task_linked_story": 0.9,
                   "file_or_endpoint_mentioned": 0.7}
MAX_CRITERIA = 12


class FormatError(ValueError):
    """A requirements or tasks file does not match the documented format."""


# ---- the two input files ---------------------------------------------------------------------------------------------------
@dataclass
class Story:
    id: str
    title: str
    acceptance_criteria: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join([self.title, *self.acceptance_criteria])


@dataclass
class Task:
    id: str
    title: str
    sprint: str | None = None
    story_id: str | None = None
    commits: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.title


def _read(path: Path, key: str) -> list[dict]:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FormatError(f"{path}: cannot read as JSON ({exc.__class__.__name__})") from exc
    items = doc.get(key) if isinstance(doc, dict) else None
    if not isinstance(items, list):
        raise FormatError(f'{path}: expected an object with a list under "{key}"')
    return items


def _check_id(path, value, what) -> str:
    if not isinstance(value, str) or not ID_PATTERN.match(value):
        raise FormatError(f"{path}: {what} id {value!r} must be letters, digits, '.', '_' or '-' (at most 40 characters)")
    return value


def load_stories(path: Path) -> list[Story]:
    stories, seen = [], set()
    for raw in _read(path, "stories"):
        sid = _check_id(path, raw.get("id"), "story")
        if sid in seen:
            raise FormatError(f"{path}: duplicate story id {sid}")
        seen.add(sid)
        criteria = raw.get("acceptance_criteria") or []
        if not isinstance(raw.get("title"), str) or not isinstance(criteria, list):
            raise FormatError(f'{path}: story {sid} needs a "title" string and an "acceptance_criteria" list')
        stories.append(Story(sid, raw["title"], [str(c) for c in criteria][:MAX_CRITERIA]))
    return stories


def load_tasks(path: Path) -> list[Task]:
    tasks, seen = [], set()
    for raw in _read(path, "tasks"):
        tid = _check_id(path, raw.get("id"), "task")
        if tid in seen:
            raise FormatError(f"{path}: duplicate task id {tid}")
        seen.add(tid)
        story_id = raw.get("story_id")
        if story_id is not None:
            _check_id(path, story_id, "story")
        commits = raw.get("commits") or []
        if not isinstance(raw.get("title"), str) or not isinstance(commits, list) or not all(isinstance(c, str) for c in commits):
            raise FormatError(f'{path}: task {tid} needs a "title" string and a "commits" list of strings')
        tasks.append(Task(tid, raw["title"], raw.get("sprint"), story_id, [c.lower() for c in commits]))
    return tasks


# ---- pseudonymous contributors -------------------------------------------------------------------------------------------------
class Pseudonymizer:
    """C-xxxxxxxx = keyed hash of the author's email (or name). The key and the mapping back to the person stay in a local
    file (`trace_mapping.local.json`, git-ignored); reuse the same output folder, or set SECURITY_ASSISTANT_PSEUDONYM_SALT,
    to keep the ids stable between runs."""

    def __init__(self, salt: str, mapping: dict[str, dict] | None = None):
        self._salt, self.mapping = salt, mapping or {}

    @classmethod
    def load(cls, path: Path) -> "Pseudonymizer":
        salt_env = os.environ.get("SECURITY_ASSISTANT_PSEUDONYM_SALT")
        try:
            saved = json.loads(Path(path).read_text(encoding="utf-8"))
            return cls(salt_env or saved["salt"], saved.get("contributors", {}))
        except (OSError, ValueError, KeyError):
            return cls(salt_env or secrets.token_hex(16))

    def id_for(self, name: str, email: str) -> str:
        key = (email or name or "unknown").strip().lower()
        pid = "C-" + hmac.new(self._salt.encode(), key.encode(), sha256).hexdigest()[:8]
        self.mapping[pid] = {"name": name, "email": email}
        return pid

    def save(self, path: Path) -> Path | None:
        if not self.mapping:
            return None
        Path(path).write_text(json.dumps(
            {"WARNING": "local only: maps pseudonymous contributor ids to real people; do not share or commit",
             "salt": self._salt, "contributors": self.mapping}, indent=2, ensure_ascii=False), encoding="utf-8")
        return Path(path)


# ---- the introducing commit ---------------------------------------------------------------------------------------------------------
@dataclass
class Commit:
    sha: str
    date: str
    subject: str
    body: str
    author_name: str  # kept in memory to build the pseudonym; never written out
    author_email: str

    @property
    def message(self) -> str:
        return f"{self.subject}\n{self.body}".strip()


_FORMAT = "--format=COMMIT%x1f%H%x1f%cI%x1f%an%x1f%ae%x1f%s%x1f%b%x1e"


def _parse_commits(output: str) -> list[Commit]:
    commits = []
    for chunk in output.split("COMMIT\x1f")[1:]:
        record = chunk.split("\x1e", 1)[0]
        parts = record.split("\x1f")
        if len(parts) >= 6 and re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            commits.append(Commit(sha=parts[0], date=parts[1], author_name=parts[2], author_email=parts[3],
                                  subject=parts[4], body=parts[5] if len(parts) > 5 else ""))
    return commits


def introducing_commit(repo: Path, f_path: str | None, line: int | None, start_rev: str | None = None,
                       needle: str | None = None) -> tuple[Commit | None, str]:
    """(commit, note). The commit that ADDED the line: the oldest entry of the line's history (`git log -L`). For a file
    that no longer exists (history only, for example a deleted secret) the search starts at `start_rev`, the commit the scanner
    reported. Without a line number (a dependency) the first commit that added `needle` to the file is used."""
    repo = Path(repo)
    if not (repo / ".git").exists():
        return None, "the folder has no git history"
    if not f_path or ".." in Path(f_path).parts or Path(f_path).is_absolute():
        return None, "the finding has no usable file path"
    rev = start_rev if start_rev and SHA.match(start_rev) else None
    if line:
        args = ["log", "--no-color", f"-L{line},{line}:{f_path}", _FORMAT]
        if rev:  # a scanner that reports a commit (secrets) numbered the line in that commit's version of the file
            args.insert(2, rev)
        out = _git_read(repo, *args, timeout=40)
        commits = _parse_commits(out) if out else []
        if commits:
            return commits[-1], "found by the line's history (git log -L): the commit that added the line"
        return None, "no introducing commit found: the line has no history in this repository"
    if needle:
        out = _git_read(repo, "log", "--no-color", "--reverse", "-S" + needle, _FORMAT, "--", f_path, timeout=40)
        commits = _parse_commits(out) if out else []
        if commits:
            return commits[0], f"found by the first commit that added '{needle}' to the file"
    return None, "no introducing commit found: no line number to look up"


# ---- links ------------------------------------------------------------------------------------------------------------------------------
@dataclass
class Link:
    kind: str  # "story" or "task"
    id: str
    title: str
    status: str  # "verified" (a rule supports it) or "candidate" (only proposed)
    methods: list[str]
    evidence: list[str]
    confidence: float

    def as_dict(self) -> dict:
        return {"kind": self.kind, "id": self.id, "title": self.title, "status": self.status, "methods": self.methods,
                "evidence": self.evidence, "confidence": round(self.confidence, 2)}


@dataclass
class Proposal:
    """What the LLM proposed (already checked for a valid shape and real evidence ids)."""
    story_id: str | None = None
    task_id: str | None = None
    rationale: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0


def _mentions(text: str, needle: str) -> bool:
    return bool(needle) and re.search(rf"(?<![\w.-]){re.escape(needle)}(?![\w-])", text, re.I) is not None


def _same_commit(listed: str, sha: str) -> bool:
    return len(listed) >= 7 and (sha.startswith(listed) or listed.startswith(sha[:len(listed)]))


def build_links(finding: Finding, commit: Commit | None, stories: list[Story], tasks: list[Task],
                proposal: Proposal | None = None) -> tuple[list[Link], list[dict], list[str]]:
    """Deterministic validation. A link is *verified* only when a rule supports it:
      1. the introducing commit's message mentions the story or task id;
      2. the task lists the introducing commit;
      3. a task's story (from 1 or 2);
      4. the file or endpoint appears in the story or task text, and in exactly one of them (if several mention it, the
         match is too vague to verify and stays a candidate).
    Everything else the LLM proposed is a *candidate*. Ids that do not exist are rejected. Returns (links, rejected, notes)."""
    links: dict[tuple[str, str], Link] = {}
    notes: list[str] = []

    def add(kind, item, status, method, evidence, confidence):
        link = links.get((kind, item.id))
        if link is None:
            links[(kind, item.id)] = Link(kind, item.id, item.title, status, [method], [evidence], confidence)
            return
        if method not in link.methods:
            link.methods.append(method)
            link.evidence.append(evidence)
        if status == "verified" and link.status != "verified":
            link.status, link.confidence = "verified", confidence
        elif status == "verified":
            link.confidence = max(link.confidence, confidence)

    by_story = {s.id: s for s in stories}
    if commit:
        message = commit.message
        for task in tasks:
            if _mentions(message, task.id):
                add("task", task, "verified", "commit_message_reference",
                    f"the message of commit {commit.sha[:7]} mentions {task.id}", RULE_CONFIDENCE["commit_message_reference"])
            if any(_same_commit(c, commit.sha) for c in task.commits):
                add("task", task, "verified", "task_commit_list",
                    f"task {task.id} lists commit {commit.sha[:7]}", RULE_CONFIDENCE["task_commit_list"])
        for story in stories:
            if _mentions(message, story.id):
                add("story", story, "verified", "commit_message_reference",
                    f"the message of commit {commit.sha[:7]} mentions {story.id}", RULE_CONFIDENCE["commit_message_reference"])
    for (kind, tid), link in list(links.items()):
        task = next((t for t in tasks if kind == "task" and t.id == tid), None)
        if task and task.story_id in by_story:
            add("story", by_story[task.story_id], "verified", "task_linked_story",
                f"task {task.id} belongs to {task.story_id}", RULE_CONFIDENCE["task_linked_story"])

    tokens = [t for t in (finding.function_or_endpoint, Path(finding.file_path).name if finding.file_path else None,
                          finding.file_path) if t]
    for kind, items in (("story", stories), ("task", tasks)):
        hits = [(i, t) for i in items for t in tokens if _mentions(i.text, t)]
        matched = {i.id: (i, t) for i, t in hits}
        if len(matched) == 1:
            (item, token), = matched.values()
            add(kind, item, "verified", "file_or_endpoint_mentioned", f"'{token}' appears in {kind} {item.id}",
                RULE_CONFIDENCE["file_or_endpoint_mentioned"])
        elif len(matched) > 1:
            notes.append(f"'{tokens[0] if tokens else ''}' appears in {len(matched)} {kind}s ({', '.join(sorted(matched))}): "
                         "too vague to verify")

    rejected: list[dict] = []
    if proposal is not None:
        for kind, pid, pool in (("story", proposal.story_id, by_story), ("task", proposal.task_id, {t.id: t for t in tasks})):
            if pid is None:
                continue
            if pid not in pool:
                rejected.append({"kind": kind, "id": pid, "reason": f"{kind} id does not exist in the {kind}s file"})
                continue
            add(kind, pool[pid], "candidate", "llm_proposal",
                f"proposed by the model ({', '.join(proposal.evidence_ids) or 'no evidence ids'}): {proposal.rationale}",
                proposal.confidence)
    if stories and not any(k == "story" for k, _ in links):
        notes.append("no matching story")
    return list(links.values()), rejected, notes


def pseudonymous_commit(commit: Commit | None, pseudo: Pseudonymizer, pii: PIIRedactor, note: str) -> dict | None:
    """The commit as it may appear in outputs: sha, date, personal-data-redacted subject, pseudonymous contributor."""
    if commit is None:
        return None
    pii.add_known_name(commit.author_name)  # so the author's name is also removed if it appears in the message
    return {"sha": commit.sha, "date": commit.date, "subject": redact_text(pii.redact_plain(commit.subject))[:200],
            "contributor": pseudo.id_for(commit.author_name, commit.author_email), "how_found": note}
