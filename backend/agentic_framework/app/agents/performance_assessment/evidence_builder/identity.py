"""Who is who: git authors and GitHub logins mapped to the course roster.

The roster comes from the tracking record (the lecturer enters each student's GitHub login and commit e-mails; the platform's user table has the login). Nothing is guessed:
an author that matches nobody is reported as unmapped, never silently attributed or dropped, and the run asks the lecturer (identity gate).
"""
import re
from dataclasses import dataclass, field

BOT = re.compile(r"(\[bot\]$|^dependabot|^renovate|^github-actions|^copilot|^vercel|^netlify|^greenkeeper|^snyk)", re.I)
NOREPLY = re.compile(r"^(?:\d+\+)?([A-Za-z0-9-]+)@users\.noreply\.github\.com$", re.I)


def is_bot(name: str = "", email: str = "") -> bool:
    return bool(BOT.search((name or "").strip()) or BOT.search((email or "").split("@")[0]))


@dataclass
class Roster:
    """students: [{"student_id": "STU-014", "emails": [...], "logins": [...], "names": [...]}]"""
    students: list
    by_email: dict = field(default_factory=dict)
    by_login: dict = field(default_factory=dict)
    by_name: dict = field(default_factory=dict)

    def __post_init__(self):
        for s in self.students:
            sid = s["student_id"]
            for e in s.get("emails", []):
                self.by_email[e.strip().lower()] = sid
            for l in s.get("logins", []):
                self.by_login[l.strip().lower()] = sid
            for n in s.get("names", []):
                self.by_name[n.strip().lower()] = sid

    @property
    def ids(self):
        return [s["student_id"] for s in self.students]

    def login_of(self, student_id):
        for s in self.students:
            if s["student_id"] == student_id and s.get("logins"):
                return s["logins"][0]
        return None

    def author(self, name: str, email: str):
        """Student id for a git author, or None. E-mail first, then the login hidden in a GitHub noreply address, then the exact name."""
        e = (email or "").strip().lower()
        if e in self.by_email:
            return self.by_email[e]
        m = NOREPLY.match(e)
        if m and m.group(1).lower() in self.by_login:
            return self.by_login[m.group(1).lower()]
        return self.by_name.get((name or "").strip().lower())

    def login(self, login: str):
        return self.by_login.get((login or "").strip().lower())
