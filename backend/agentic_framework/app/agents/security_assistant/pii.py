"""Redact personal data of students before text is sent to an external LLM (next to redaction.py, which handles
secrets). Placeholders are stable (the same person gets the same placeholder inside one redactor) and the mapping from
placeholder to original stays in memory / a local file; it is never put into a prompt or a report.

What it redacts, and what it deliberately does not:
- emails, phone numbers and student IDs (default format IT + 8 digits, configurable) in the text it is given;
- names: on labelled lines (Author:, @author, Copyright, Maintainer, Contact, Written by, Created by, ...), and every
  author or committer name of the repository's git history (`learn_git_names`, also in unlabelled text such as "ask Priya
  about this"). Incomplete by nature: a name that is on no label, not in the git history and not in the configured known
  names ("fixed by John", a classmate who never committed) is not found;
- in source code only comments and string literals are touched (see `redact_code`); identifiers and structure never are;
- file paths are kept, except a known person's name, email or student ID inside them, which gets a placeholder
  (`path_map` keeps redacted path -> original path so a finding stays traceable).
"""

import json
import os
import re
import subprocess
from pathlib import Path

DEFAULT_STUDENT_ID = r"\bIT\d{8}\b"

# the last label must be letters, so package versions such as flask@1.0 or lodash@4.17.15 are not emails
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_PHONE = re.compile(
    r"(?<![\w.])(?:\+\d{8,14}|\+\d{1,3}[ \t-]?(?:\(\d{2,4}\)|\d{2,4})[ \t.-]\d{3,4}[ \t.-]\d{3,4}|"
    r"(?:\(\d{2,4}\)|\d{2,4})[ \t.-]\d{3,4}[ \t.-]\d{3,4}|0\d{9})(?![\w.])"
)
_W = r"[^\W\d_][\w'’.\-]*"  # a word that starts with a letter
_NAMES = rf"(?P<n>{_W}(?:[ \t]+{_W}){{0,3}}(?:[ \t]*(?:,|&|\band\b)[ \t]*{_W}(?:[ \t]+{_W}){{0,3}})*)"
_LABELS = [
    re.compile(rf"(?i)\b(?:authors?|maintainers?|contacts?|owner|student(?:[ \t]+name)?|name|submitted[ \t]+by|"
               rf"signed-off-by|co-authored-by|reviewed-by|committer)[ \t]*:[ \t]*{_NAMES}"),
    re.compile(rf"(?i)@authors?\b[ \t]+{_NAMES}"),
    re.compile(rf"(?i)\b(?:written|created|developed|designed|maintained)[ \t]+by[ \t]*:?[ \t]*{_NAMES}"),
    re.compile(rf"(?i)\bcopyright(?:[ \t]*\(c\)|[ \t]*©)?[ \t]*(?:\d{{4}}(?:[ \t]*[-–][ \t]*\d{{4}})?[ \t,]*)?{_NAMES}"),
]
_STOP = {"all", "rights", "reserved", "licensed", "license", "under", "released", "this", "inc", "ltd", "llc", "the",
         "project", "university", "of", "for", "from", "on", "at", "is", "was", "date", "email", "e-mail", "phone",
         "tel", "id", "student", "version", "see", "to"}
MAX_GIT_COMMITS = 5000
MAX_GIT_NAMES = 200
_GENERIC_NAMES = {"demo", "unknown", "root", "admin", "user", "github", "git", "ci", "test", "tester", "student", "you", "me", "noreply"}
_GENERIC_IDENTITY = re.compile(r"(?i)\[bot\]|\bbot\b|\bnoreply\b|\bgithub[ -]actions?\b|\bdependabot\b|\brenovate\b")
_NUMBERED = re.compile(r"^([ >]\s*\d+ \| )(.*)$")
_SEPARATORS = (" ", "_", "-", ".", "")  # how a name is written inside a path: kasun perera, kasun_perera, KasunPerera, ...


class PIIRedactor:
    def __init__(self, student_id_pattern: str | None = None, known_names: tuple[str, ...] | list[str] = ()):
        self.student_id = re.compile(student_id_pattern or DEFAULT_STUDENT_ID, re.I)
        self.mapping: dict[str, str] = {}  # placeholder -> original; never sent, never in a report
        self.path_map: dict[str, str] = {}  # redacted path -> original path
        self._by_original: dict[tuple[str, str], str] = {}
        self._counts: dict[str, int] = {}
        self._names: dict[str, str] = {}  # lower case name or name token -> the person's full name
        for name in known_names:
            self.add_known_name(name)

    @classmethod
    def from_env(cls, repo: Path | str | None = None) -> "PIIRedactor":
        """SECURITY_ASSISTANT_STUDENT_ID_REGEX and SECURITY_ASSISTANT_PII_KNOWN_NAMES (comma separated). With `repo`, the
        author and committer names of its git history are learned as known names (see `learn_git_names`)."""
        names = [n.strip() for n in os.environ.get("SECURITY_ASSISTANT_PII_KNOWN_NAMES", "").split(",") if n.strip()]
        redactor = cls(os.environ.get("SECURITY_ASSISTANT_STUDENT_ID_REGEX") or None, names)
        if repo is not None:
            redactor.learn_git_names(repo)
        return redactor

    # ---- placeholders and known names ---------------------------------------------------------------------------
    def placeholder(self, kind: str, original: str) -> str:
        key = (kind, " ".join(original.lower().split()))
        if key not in self._by_original:
            self._counts[kind] = self._counts.get(kind, 0) + 1
            ph = f"<{kind}_{self._counts[kind]}>"
            self._by_original[key] = ph
            self.mapping[ph] = original
        return self._by_original[key]

    def learn_git_names(self, repo: Path | str) -> int:
        """Learn the author and committer names of the repository's git history as known names, so a name written
        without a label ("ask Priya about this") is replaced too. Read-only `git log`; the names stay in this object and in
        the local mapping file, never in a prompt or report. Generic or automated identities (a bot, "root", "demo") are
        skipped. Returns how many names were learned; 0 when there is no usable git history."""
        repo = Path(repo)
        if not (repo / ".git").exists():
            return 0
        from app.agents.security_assistant.tools.base import child_env

        env = {**child_env(), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"}
        try:
            done = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(repo), "log", "--all", f"-n{MAX_GIT_COMMITS}",
                                   "--format=%an%x1f%cn"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  timeout=30, env=env)
        except (OSError, subprocess.TimeoutExpired):
            return 0
        if done.returncode != 0:
            return 0
        names = {n.strip() for line in done.stdout.splitlines() for n in line.split("\x1f")}
        learned = 0
        for name in sorted(names)[:MAX_GIT_NAMES]:
            if name and not _GENERIC_IDENTITY.search(name) and name.lower() not in _GENERIC_NAMES:
                before = len(self._names)
                self.add_known_name(name)
                learned += len(self._names) > before
        return learned

    def add_known_name(self, name: str) -> None:
        name = " ".join(name.split()).strip(" ,.")
        if len(name) < 3:
            return
        self._names.setdefault(name.lower(), name)
        for token in re.split(r"[\s,]+", name):
            if len(token.strip(".")) >= 4:  # a first or last name on its own, longer than 3 letters
                self._names.setdefault(token.lower(), name)

    def _split_names(self, raw: str) -> tuple[str, str]:
        """'Kasun Perera, Jane Roe All rights' -> ('Kasun Perera, Jane Roe', 'All rights')."""
        tokens = re.split(r"(\s+)", raw)
        for i, tok in enumerate(tokens):
            if tok.strip() and tok.strip(".,&").lower() in _STOP:
                return "".join(tokens[:i]).rstrip(), "".join(tokens[i:])
        return raw, ""

    def learn(self, text: str) -> None:
        """Remember the names on labelled lines (without changing the text)."""
        for label in _LABELS:
            for m in label.finditer(text):
                names, _rest = self._split_names(m.group("n"))
                for part in re.split(r"\s*(?:,|&|\band\b)\s*", names):
                    self.add_known_name(part)

    # ---- text ---------------------------------------------------------------------------------------------------------
    def _label_sub(self, m: re.Match) -> str:
        names, rest = self._split_names(m.group("n"))
        if not names.strip():
            return m.group(0)
        redacted = re.sub(r"[^,&]+?(?=\s*(?:,|&|\band\b)|$)",
                          lambda p: self._name_part(p.group(0)), names)
        start, end = m.span("n")
        tail = (" " + rest) if rest else ""
        return m.group(0)[: start - m.start()] + redacted + tail + m.group(0)[end - m.start():]

    def _name_part(self, part: str) -> str:
        stripped = part.strip(" .")
        if not stripped or stripped.lower() == "and":
            return part
        self.add_known_name(stripped)
        lead = part[: len(part) - len(part.lstrip())]
        trail = part[len(part.rstrip(" .")):]  # keep the full stop after a name
        return lead + self.placeholder("NAME", self._names.get(stripped.lower(), stripped)) + trail

    def _known_names_sub(self, text: str) -> str:
        for name, display in sorted(self._names.items(), key=lambda kv: len(kv[0]), reverse=True):
            for variant in sorted({name} | {name.replace(" ", sep) for sep in _SEPARATORS}, key=len, reverse=True):
                pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(variant)}(?![A-Za-z0-9])", re.I)
                text = pattern.sub(lambda _m, d=display: self.placeholder("NAME", d), text)
        return text

    def redact_plain(self, text: str) -> str:
        """For metadata, messages, commit messages and prose: the whole text is eligible."""
        if not text:
            return text
        text = _EMAIL.sub(lambda m: self.placeholder("EMAIL", m.group(0)), text)
        text = self.student_id.sub(lambda m: self.placeholder("STUDENT_ID", m.group(0)), text)
        for label in _LABELS:
            text = label.sub(self._label_sub, text)
        text = self._known_names_sub(text)
        return _PHONE.sub(lambda m: self.placeholder("PHONE", m.group(0))
                          if sum(c.isdigit() for c in m.group(0)) >= 9 else m.group(0), text)

    def redact_code(self, text: str) -> str:
        """For source code: only comments and string literals are redacted; identifiers and structure are not."""
        if not text:
            return text
        spans = _protected_spans(text)
        self.learn("\n".join(text[a:b] for a, b in spans))
        out, last = [], 0
        for a, b in spans:
            out.append(text[last:a])
            out.append(self.redact_plain(text[a:b]))
            last = b
        out.append(text[last:])
        return "".join(out)

    def redact_numbered(self, text: str, code: bool = True) -> str:
        """A snippet whose lines look like '>   22 | code'. The prefix is kept and each run of numbered lines is
        redacted as one piece of code; other lines (such as 'path:line' headers) are redacted as metadata."""
        out, run = [], []

        def flush():
            if run:
                body = "\n".join(c for _p, c in run)
                new = (self.redact_code(body) if code else self.redact_plain(body)).split("\n")
                out.extend(p + n for (p, _c), n in zip(run, new))
                run.clear()

        for line in text.split("\n"):
            m = _NUMBERED.match(line)
            if m:
                run.append((m.group(1), m.group(2)))
            else:
                flush()
                out.append(self.redact_plain(line))
        flush()
        return "\n".join(out)

    def redact_path(self, path: str | None) -> str | None:
        """Keep the path, but replace a known name, an email or a student ID inside it."""
        if not path:
            return path
        new = _EMAIL.sub(lambda m: self.placeholder("EMAIL", m.group(0)), path)
        new = self.student_id.sub(lambda m: self.placeholder("STUDENT_ID", m.group(0)), new)
        new = self._known_names_sub(new)
        if new != path:
            self.path_map[new] = path
        return new

    def redact_git_metadata(self, author_name: str | None = None, author_email: str | None = None,
                            message: str | None = None) -> dict[str, str | None]:
        """Commit author, email and message as they may be added to a bundle."""
        if author_name:
            self.add_known_name(author_name)
        return {"author": self.placeholder("NAME", author_name) if author_name else None,
                "email": self.placeholder("EMAIL", author_email) if author_email else None,
                "message": self.redact_plain(message) if message else message}

    def save_mapping(self, path: Path) -> Path | None:
        """Write the local-only mapping (placeholder -> original, redacted path -> original path). Do not share it."""
        if not self.mapping and not self.path_map:
            return None
        path = Path(path)
        path.write_text(json.dumps(
            {"WARNING": "local only: holds the personal data removed from prompts; do not share or commit",
             "placeholders": self.mapping, "paths": self.path_map}, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


def _protected_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of every comment and string literal in `text`: a small language-agnostic scanner for
    // # /* */ <!-- --> and quotes. Strings other than triple quoted and backtick end at the line end, so a wrong guess
    stays local. A line that starts with ' * ' counts as a block comment line (also in a window cut out of a comment)."""
    spans, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith(('"""', "'''"), i):
            end = text.find(text[i:i + 3], i + 3)
            end = n if end == -1 else end + 3
            spans.append((i, end))
            i = end
        elif c in "\"'`":
            j = i + 1
            while j < n and text[j] != c and (text[j] != "\n" or c == "`"):
                j += 2 if text[j] == "\\" else 1
            spans.append((i, min(j + 1, n)))
            i = min(j + 1, n)
        elif text.startswith("//", i) or c == "#" or (
                c == "*" and not text[text.rfind("\n", 0, i) + 1:i].strip() and text[i + 1:i + 2] in (" ", "\t", "@")):
            end = text.find("\n", i)
            end = n if end == -1 else end
            spans.append((i, end))
            i = end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            spans.append((i, end))
            i = end
        elif text.startswith("<!--", i):
            end = text.find("-->", i + 4)
            end = n if end == -1 else end + 3
            spans.append((i, end))
            i = end
        else:
            i += 1
    return spans
