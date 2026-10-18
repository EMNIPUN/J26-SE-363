"""Pseudonymisation shared by every dataset script.

Real names, emails and GitHub logins exist only in ``private/`` (git-ignored). Everything written
outside ``private/`` goes through :func:`scrub` and carries student ids such as ``STU-007``.
"""

import hashlib
import json
import re
from pathlib import Path

DATASET = Path(__file__).resolve().parents[1]
PRIVATE = DATASET / "private"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PROFANITY = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*)\b", re.IGNORECASE)
MENTION = re.compile(r"(?<![\w@])@[A-Za-z0-9-]{2,39}(?![\w/-])")  # not npm scopes like @scope/pkg
STUDENT_NUMBER = re.compile(r"\b[Ii][Tt]\d{8}\b")


class Identities:
    def __init__(self):
        data = json.loads((PRIVATE / "student_identity_map.json").read_text(encoding="utf-8"))
        self.by_email, self.by_login, self.by_name = {}, {}, {}
        self.tokens = []  # every alias, longest first, for scrubbing free text
        for sid, person in data["students"].items():
            for email in person["emails"]:
                self.by_email[email.lower()] = sid
            for login in person["logins"]:
                self.by_login[login.lower()] = sid
                self.tokens.append((login, sid))
            for name in person["names"] + [person["name"]]:
                self.by_name[name.lower()] = sid
                self.tokens.append((name, sid))
            for part in person["name"].split():
                if len(part) > 3 and part[0].isupper() and "." not in part:
                    self.tokens.append((part, sid))
        # names of people outside the rosters that appear in branch names
        self.tokens += [(name, "[name]") for name in data.get("other_names", [])]
        self.tokens.sort(key=lambda t: -len(t[0]))
        lookup = {token.lower(): sid for token, sid in self.tokens}
        alternation = "|".join(re.escape(token) for token, _ in self.tokens)
        # "-" and "_" count as separators, so "dev-<name>" branch names are caught too
        self._names = re.compile(rf"(?<![A-Za-z0-9])({alternation})(?![A-Za-z])", re.IGNORECASE)
        self._lookup = lookup

    def author(self, name, email):
        return self.by_email.get((email or "").lower()) or self.by_name.get((name or "").lower())

    def login(self, login):
        return self.by_login.get((login or "").lower())

    def scrub(self, text):
        """Free text without names, logins, emails or student numbers."""
        if not text:
            return ""
        text = EMAIL.sub("[email]", text)
        text = STUDENT_NUMBER.sub("[student-number]", text)
        text = PROFANITY.sub("[removed]", text)
        text = self._names.sub(lambda m: self._lookup[m.group(1).lower()], text)
        return MENTION.sub(lambda m: "@" + (self.login(m.group()[1:]) or "user"), text)


def opaque(value, length=10):
    """A stable id that cannot be looked up on GitHub (commit and pull request ids)."""
    return hashlib.sha256(f"selvia:{value}".encode()).hexdigest()[:length]
