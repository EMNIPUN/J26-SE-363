"""Build the limited, labelled evidence bundle for one finding.

E1 is always the finding metadata. E2 is the code snippet around the finding. E3.. are small context
snippets found by simple searches (where authorisation, sanitisers or usages of a package appear).
Everything is size-limited and redacted. The repository is only read, never executed.
"""

import re
from pathlib import Path

from app.agents.security_assistant.interpreter.models import EvidenceBundle, EvidenceItem
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.schemas import Category, Finding
from app.agents.security_assistant.tools.languages import walk_repo

SNIPPET_RADIUS = 8
MAX_CONTEXT_ITEMS = 3
MAX_ITEM_CHARS = 2500
MAX_FILE_BYTES = 1_000_000
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".java", ".kt", ".yml", ".yaml", ".properties", ".xml", ".gradle"}
LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "gradle.lockfile", "poetry.lock"}

# What to look for besides the snippet, per category: (label, regex)
CONTEXT_SEARCHES: dict[Category, tuple[str, re.Pattern]] = {
    Category.V1: ("places in the project that enforce authorisation (middleware, decorators, annotations, security config)",
                  re.compile(r"@PreAuthorize|@Secured|@RolesAllowed|SecurityFilterChain|requestMatchers|login_required|"
                             r"permission_required|current_user|get_jwt_identity|Depends\(|app\.use\(.*(auth|protect)|"
                             r"authenticate|requireAuth|isOwner", re.I)),
    Category.V2: ("places that sanitise, escape or validate input",
                  re.compile(r"escape|sanitiz|sanitis|bleach|DOMPurify|PreparedStatement|parameteri[sz]ed|"
                             r"allow[_-]?list|whitelist|shlex\.quote|validator|html\.escape", re.I)),
}


def _numbered(lines: list[str], first: int, mark: int | None = None) -> str:
    return "\n".join(f"{'>' if first + i == mark else ' '} {first + i:4d} | {ln}" for i, ln in enumerate(lines))


CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".kt", ".c", ".h", ".cpp", ".cs", ".go",
                 ".rb", ".php", ".rs", ".sh", ".sql", ".swift"}


def _pii_text(pii: PIIRedactor | None, path: Path, text: str) -> str:
    """Personal data out of a whole file before it is cut into lines: comments and strings only for source code (so
    identifiers are never touched), the whole text for prose and data files. The line count never changes."""
    if pii is None:
        return text
    return pii.redact_code(text) if path.suffix.lower() in CODE_SUFFIXES else pii.redact_plain(text)


def finding_item(f: Finding, id_: str = "E1", pii: PIIRedactor | None = None) -> EvidenceItem:
    parts = {
        "category": f.category.value, "rule_id": f.rule_id, "tool": f.tool, "cwe": f.cwe,
        "file_path": f.file_path, "line": f.line, "function_or_endpoint": f.function_or_endpoint,
        "source": f.source, "sink": f.sink, "severity_from_tool": f.severity_tool, "message": f.message,
    }
    if pii is not None:  # the path keeps its shape; a person's name inside it gets a placeholder
        parts["file_path"] = pii.redact_path(f.file_path)
        for key in ("function_or_endpoint", "source", "sink", "message"):
            parts[key] = pii.redact_plain(parts[key]) if parts[key] else parts[key]
    content = "\n".join(f"{k}: {v}" for k, v in parts.items() if v not in (None, ""))
    return EvidenceItem(id=id_, kind="finding", label="scanner finding", content=redact_text(content))


def _safe_file(repo: Path, rel: str | None) -> Path | None:
    if not rel:
        return None
    path = (repo / rel).resolve()
    try:
        path.relative_to(repo.resolve())  # no escaping the repository, symlinks included
    except ValueError:
        return None
    return path if path.is_file() and path.stat().st_size <= MAX_FILE_BYTES else None


def snippet_item(f: Finding, repo: Path, id_: str = "E2", radius: int = SNIPPET_RADIUS,
                 pii: PIIRedactor | None = None) -> EvidenceItem | None:
    path = _safe_file(repo, f.file_path)
    if path is None:
        return None
    lines = _pii_text(pii, path, path.read_text(encoding="utf-8", errors="replace")).splitlines()
    if f.line and 1 <= f.line <= len(lines):
        lo, hi = max(1, f.line - radius), min(len(lines), f.line + radius)
    else:
        lo, hi = 1, min(len(lines), 2 * radius + 1)
    text = redact_text(_numbered(lines[lo - 1:hi], lo, f.line))
    label = f"code around {pii.redact_path(f.file_path) if pii else f.file_path}:{f.line}"
    return EvidenceItem(id=id_, kind="code_snippet", label=label, content=text[:MAX_ITEM_CHARS])


def _package_name(f: Finding) -> str | None:
    """'lodash 4.17.15' / 'lodash@4.17.15' / 'requests==2.19.0' / 'g:a@1.0 (Maven)' -> 'lodash' / 'a'."""
    m = re.match(r"([A-Za-z0-9_.\-@/:]+?)(?:[ @=]|$)", (f.sink or "").split(" (")[0])
    name = m.group(1).split(":")[-1].split("/")[-1] if m else None
    return name or None


def _search(repo: Path, pattern: re.Pattern, skip: Path | None, limit: int, radius: int = 2,
            pii: PIIRedactor | None = None) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    scanned = 0
    for directory, names in walk_repo(repo):
        for name in sorted(names):
            p = directory / name
            if p.suffix.lower() not in SOURCE_SUFFIXES or name in LOCKFILES or p == skip:
                continue
            scanned += 1
            if scanned > 400 or len(hits) >= limit:
                return hits
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
                lines = _pii_text(pii, p, p.read_text(encoding="utf-8", errors="replace")).splitlines()
            except OSError:
                continue
            for no, line in enumerate(lines, 1):
                if pattern.search(line):
                    lo, hi = max(1, no - radius), min(len(lines), no + radius)
                    rel = p.relative_to(repo).as_posix()
                    rel = pii.redact_path(rel) if pii else rel
                    hits.append((f"{rel}:{no}", redact_text(_numbered(lines[lo - 1:hi], lo, no))))
                    break  # one hit per file keeps the bundle small and varied
    return hits


def redact_bundle(bundle: EvidenceBundle, pii: PIIRedactor) -> EvidenceBundle:
    """Personal data out of every item (idempotent). Code items are redacted as code: comments and strings only."""
    items = []
    for it in bundle.items:
        content = pii.redact_plain(it.content) if it.kind == "finding" else pii.redact_numbered(it.content)
        items.append(it.model_copy(update={"content": content, "label": pii.redact_plain(it.label)}))
    return EvidenceBundle(items=items)


def build_bundle(f: Finding, repo: Path | None = None, extra: list[EvidenceItem] | None = None,
                 pii: PIIRedactor | None = None) -> EvidenceBundle:
    """E1 finding, E2 snippet, then up to three context items from simple searches, then `extra`.

    Secrets and personal data are replaced by placeholders here. `pii` keeps the placeholder -> original mapping
    (pass the same redactor for a whole run so placeholders stay stable); the mapping is never part of the bundle."""
    pii = pii if pii is not None else PIIRedactor.from_env()
    target = None
    if repo is not None:
        repo = Path(repo)
        target = _safe_file(repo, f.file_path)
        if target is not None:  # learn the names written in this file first, so its path and every item use them
            _pii_text(pii, target, target.read_text(encoding="utf-8", errors="replace"))
    items = [finding_item(f, pii=pii)]
    if repo is not None:
        snippet = snippet_item(f, repo, pii=pii)
        if snippet:
            items.append(snippet)
        skip = target
        if f.category in CONTEXT_SEARCHES:
            label, pattern = CONTEXT_SEARCHES[f.category]
            hits = _search(repo, pattern, skip, MAX_CONTEXT_ITEMS, pii=pii)
            body = "\n\n".join(f"{where}\n{text}" for where, text in hits) if hits else "(no matches found)"
            items.append(EvidenceItem(id=f"E{len(items) + 1}", kind="context", label=label, content=body[:MAX_ITEM_CHARS]))
        elif f.category is Category.V5 and (name := _package_name(f)):
            hits = _search(repo, re.compile(rf"(?<![\w.-]){re.escape(name)}(?![\w-])"), skip, MAX_CONTEXT_ITEMS, pii=pii)
            body = "\n\n".join(f"{where}\n{text}" for where, text in hits) if hits else "(no source file mentions it)"
            items.append(EvidenceItem(id=f"E{len(items) + 1}", kind="context",
                                      label=f"where the package '{name}' is used in the project", content=body[:MAX_ITEM_CHARS]))
    for item in extra or []:
        items.append(EvidenceItem(id=f"E{len(items) + 1}", kind=item.kind, label=item.label,
                                  content=redact_text(item.content)[:MAX_ITEM_CHARS]))
    # second pass: a name learned while reading a later file also applies to the items built before it
    return redact_bundle(EvidenceBundle(items=items), pii)
