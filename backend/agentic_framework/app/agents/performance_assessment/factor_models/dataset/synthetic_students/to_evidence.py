"""Turns a simulated student's sprint into raw evidence (evidence/1), so it goes through the same factor `featurize` code as
the real students.

The only thing evidence needs that the hand-written commits do not state is how each file's added and deleted lines divide
into code, comment, blank and format-only lines. That split comes from the real repositories: `Splitter` reads
``dataset/clean/commit_file_stats.csv`` and uses, for each file type, the shares measured there. File types with too few real
lines fall back to the shares of all source files (the fallbacks used are listed in ``out/split_fallbacks.txt``). This is an
assumption about the simulated code, stated here and in the README, and it is the same on every simulated student.
"""

import hashlib
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1]))  # factor_models/

from evidence.lines import SOURCE_KINDS, classify_path  # noqa: E402

MIN_LINES_FOR_OWN_RATIO = 300
PARTS = ("code", "comment", "blank", "format_only")


def _shares(df, prefix):
    totals = {p: df[f"{prefix}_{p}"].sum() for p in PARTS}
    n = sum(totals.values())
    return {p: totals[p] / n for p in PARTS} if n else None


class Splitter:
    def __init__(self):
        stats = pd.read_csv(HERE.parent / "clean" / "commit_file_stats.csv")
        stats["ext"] = stats.path.str.extract(r"\.([A-Za-z0-9]+)$")[0].str.lower().fillna("")
        self.table = {}
        for (kind, ext), g in stats.groupby(["kind", "ext"]):
            if g.a_code.sum() + g.a_comment.sum() + g.a_blank.sum() + g.a_format_only.sum() >= MIN_LINES_FOR_OWN_RATIO:
                self.table[(kind, ext)] = {"a": _shares(g, "a"), "d": _shares(g, "d")}
        self.overall = {"a": _shares(stats, "a"), "d": _shares(stats, "d")}
        self.fallbacks = Counter()

    def shares(self, path, kind):
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        hit = self.table.get((kind, ext))
        if not hit:
            self.fallbacks[(kind, ext)] += 1
            hit = self.overall
        return hit

    @staticmethod
    def _apportion(n, shares):
        """n lines divided by shares, whole numbers that add up to n (largest remainder)."""
        raw = {p: n * shares[p] for p in PARTS}
        out = {p: int(raw[p]) for p in PARTS}
        for p in sorted(PARTS, key=lambda q: -(raw[q] - out[q]))[: n - sum(out.values())]:
            out[p] += 1
        return out

    def line_stats(self, path, kind, added, deleted):
        if kind not in SOURCE_KINDS:
            return {"added": {"code": added, "comment": 0, "blank": 0, "format_only": 0}, "deleted": {"code": deleted, "comment": 0, "blank": 0, "format_only": 0}}
        s = self.shares(path, kind)
        return {"added": self._apportion(added, s["a"]), "deleted": self._apportion(deleted, s["d"])}


def sha(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def build(team, student, sprint, rec, label, tc_info, splitter, sprint_has_prs):
    """Evidence for one simulated student in one sprint. `rec['commits']` are the volume-scaled commits."""
    start = date.fromisoformat(team["sprint_starts"][sprint])
    commits, source_added = [], defaultdict(int)
    for d, h, msg, task, files in rec["commits"]:
        entries = []
        for path, _, a, dl in files:
            kind = classify_path(path)
            stats = splitter.line_stats(path, kind, a, dl)
            entries.append({"path": path, "kind": kind, "added": a, "deleted": dl, "line_stats": stats})
            if kind in SOURCE_KINDS:
                source_added[path] += stats["added"]["code"]
        commits.append({"id": sha(label, d, h, msg), "authored_at": f"{start + timedelta(days=d)}T{h:02d}:00:00+05:30",
                        "is_merge": False, "subject": msg, "files": entries})

    tasks = []
    for t in rec["tasks"]:
        full = f"{sprint}-{student}-{t['key']}"
        info = tc_info.get(full)
        tasks.append({"id": full, "title": t["title"], "story_points": t["sp"], "subtask_count": t["sub"], "assignee": student,
                      "status": t["status"], "completed_by": t.get("by") or (student if t["status"] == "Done" else None),
                      "carried_over_from": t.get("carried") or None,
                      "commit_ids": [sha(label, c[0], c[1], c[2]) for c in rec["commits"] if c[3] == t["key"]],
                      "acceptance_criteria": list(t["ac"]), "criteria_met": sum(t["met"]), "llm_rating": t["rating"],
                      "footprint": info["footprint"] if info else []})

    reviews, comments, prs = [], [], []
    for i, (d, author, state, text, tier) in enumerate(rec.get("reviews", [])):
        reviews.append({"pr_id": f"{sprint}-{author}-r{i}", "reviewer": student, "pr_author": author, "state": state, "body": text,
                        "at": f"{start + timedelta(days=d)}T12:00:00+05:30"})
    for i, (d, author, text, is_reply, mentions) in enumerate(rec.get("comments", [])):
        comments.append({"pr_id": f"{sprint}-{author}-c{i}", "author": student, "pr_author": author, "kind": "discussion", "body": text,
                         "at": f"{start + timedelta(days=d)}T13:00:00+05:30", "is_reply": bool(is_reply), "mentions": int(mentions)})
    for i, (d, title, merged) in enumerate(rec["prs"]):
        at = f"{start + timedelta(days=d)}T15:00:00+05:30"
        prs.append({"id": f"{sprint}-{student}-p{i}", "author": student, "created_at": at, "merged_at": at if merged else None, "closed_at": at if merged else None})

    # ownership: survival and primary-owner share are set per student and sprint (ownership.py); they apply to counted lines
    ko = rec["ko"]
    added_lines = sum(source_added.values())
    files = [p for p, n in source_added.items() if n > 0]
    ownership = {"added_lines": added_lines, "surviving_lines": round(added_lines * ko["survival"]), "files": len(files),
                 "primary_files": round(len(files) * ko["primary_owner"]),
                 "owned_files": sum(1 for p in files if source_added[p] * ko["survival"] >= 20)}
    return {"schema": "evidence/1", "student_id": student, "team_id": team["team"],
            "sprint": {"id": sprint, "start": str(start), "days": 14}, "commits": commits, "tasks": tasks, "pull_requests": prs,
            "reviews": reviews, "comments": comments, "merged_for_others": rec.get("merged_for_others", 0),
            "ownership": ownership, "quiz": {"score": round((rec["quiz"]["rating"] - 1) / 4, 4)}}
