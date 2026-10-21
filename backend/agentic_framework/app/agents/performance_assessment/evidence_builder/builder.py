"""Builds one ``evidence/1`` per student for a team and sprint from a repository (read-only workspace), the team's pull requests (GitHub) and its tasks (Scrum MCP).

    result = build_team_evidence(ws, repo_url, roster, sprint, tasks_by_student, github_prs=prs, token=token)
    result.evidence["STU-014"]   # evidence/1, validated
    result.quality               # what could not be attributed or measured, for the evidence gate and the lecturer

Same contract and the same clean line counting as the dataset build (evidence/lines.py, evidence/common.py, 07_code_ownership.summarize), so the numbers a factor sees
here are comparable with the numbers it was validated on. What differs from the dataset build, on purpose: identities come from the roster the lecturer gave (an unmapped author
is reported, never dropped silently); GitHub's ``merged_by`` replaces guessing from merge-commit subjects; sprint membership uses the author's own date (as in the dataset);
blame is taken at the last commit of the sprint.
"""
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from app.agents.performance_assessment.evidence_builder import gitlog
from app.agents.performance_assessment.evidence_builder.identity import Roster, is_bot
from app.agents.performance_assessment.evidence_builder.repo_graph import dependency_reach
from app.agents.performance_assessment.workspace import WorkspaceError

FACTOR_MODELS = Path(__file__).resolve().parents[1] / "factor_models"
MAX_BLAME_FILES = 40


def _fm():
    if str(FACTOR_MODELS) not in sys.path:
        sys.path.insert(0, str(FACTOR_MODELS))
    from evidence import common, lines, registry, schema
    return common, lines, registry, schema


@dataclass
class TeamEvidence:
    evidence: dict
    quality: dict
    rev: str | None = None
    notes: list = field(default_factory=list)
    patches: dict = field(default_factory=dict)  # {sha: {path: patch}} of the students' commits and of the commits linked to their tasks (for Requirement Fulfillment)


def _day(iso: str) -> date:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).date()


def _in_window(iso: str, start: date, end: date) -> bool:
    try:
        return start <= _day(iso) <= end
    except ValueError:
        return False


def _commit_evidence(c: dict, patches: dict, lines) -> dict:
    files = []
    for path, added, deleted in c["files"]:
        kind = lines.classify_path(path)
        a, d = added or 0, deleted or 0
        if kind in lines.SOURCE_KINDS:
            patch = (patches.get(c["sha"]) or {}).get(path)
            if patch:
                stats = lines.stats_from_patch(path, patch)
            else:  # binary, or no patch available: every counted line is code, as in the dataset build
                stats = {"added": {"code": a, "comment": 0, "blank": 0, "format_only": 0}, "deleted": {"code": d, "comment": 0, "blank": 0, "format_only": 0}}
        else:
            stats = {"added": {"code": a, "comment": 0, "blank": 0, "format_only": 0}, "deleted": {"code": d, "comment": 0, "blank": 0, "format_only": 0}}
        files.append({"path": path, "kind": kind, "added": a, "deleted": d, "line_stats": stats})
    return {"id": c["sha"], "authored_at": c["authored_at"], "is_merge": len(c["parents"]) > 1, "subject": c["subject"], "files": files}


def _format_only_commits(commits_evidence) -> set:
    """Commits that only re-formatted code (>= 30 lines and >= 80% of them format-only): blame ignores them, as in the dataset build."""
    out = set()
    for c in commits_evidence:
        total = fmt = 0
        for f in c["files"]:
            if f["kind"] in ("code", "test"):
                a = f["line_stats"]["added"]
                total += sum(a.values())
                fmt += a["format_only"]
        if total >= 30 and fmt >= 0.8 * total:
            out.add(c["id"])
    return out


def build_team_evidence(ws, repo_url, roster: Roster, sprint: dict, tasks_by_student: dict | None = None, github_prs: list | None = None, *, token=None,
                        run_blame: bool = True, with_reach: bool = True, progress=None) -> TeamEvidence:
    """sprint: {"id", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "days": 14}. tasks_by_student: {student_id: [task dict from the Scrum MCP, with "acceptance_criteria" list]}."""
    common, lines, registry, schema = _fm()
    say = progress or (lambda message: None)
    t0 = time.time()
    ko = registry.load_factors(["ko"])["ko"]
    start, end = date.fromisoformat(sprint["start"]), date.fromisoformat(sprint["end"])
    tasks_by_student = tasks_by_student or {}
    quality: dict = {"unmapped_authors": {}, "bot_commits": 0, "commits_in_sprint": 0, "commits_outside_sprint": 0, "github": github_prs is not None, "notes": []}

    ws.ensure_mirror(repo_url, token=token)
    say(f"repository fetched ({time.time() - t0:.0f} s)")
    try:
        rev = ws.resolve(repo_url, None, as_of=f"{sprint['end']}T23:59:59Z", token=token)
    except WorkspaceError:
        rev = None
        quality["notes"].append("the repository has no commit on or before the end of the sprint")
    all_commits = gitlog.fetch_commits(ws, repo_url, token=token)
    say(f"{len(all_commits)} commits read from the history ({time.time() - t0:.0f} s)")
    owner_of, window, unmapped = {}, [], {}
    for c in all_commits:
        who = roster.author(c["author_name"], c["author_email"])
        c["student"] = who
        if who:
            owner_of[c["sha"]] = who
        if is_bot(c["author_name"], c["author_email"]):
            quality["bot_commits"] += 1
            continue
        if _in_window(c["authored_at"], start, end):
            quality["commits_in_sprint"] += 1
            if who:
                window.append(c)
            else:
                key = f"{c['author_name']} <{c['author_email']}>"
                u = unmapped.setdefault(key, {"commits": 0, "lines": 0})
                u["commits"] += 1
                u["lines"] += sum((a or 0) for _, a, _d in c["files"])
        else:
            quality["commits_outside_sprint"] += 1
    quality["unmapped_authors"] = unmapped
    total_lines = sum(u["lines"] for u in unmapped.values()) + sum((a or 0) for c in window for _, a, _d in c["files"])
    quality["unmapped_share_of_added_lines"] = round(sum(u["lines"] for u in unmapped.values()) / total_lines, 4) if total_lines else 0.0

    patches = gitlog.fetch_patches(ws, repo_url, [c["sha"] for c in window if len(c["parents"]) <= 1], token=token)
    say(f"{sum(1 for c in window if len(c['parents']) <= 1)} diffs read ({time.time() - t0:.0f} s)")
    by_student: dict[str, list] = {sid: [] for sid in roster.ids}
    for c in window:
        by_student[c["student"]].append(_commit_evidence(c, patches, lines))

    # tasks: linked commit prefixes -> real SHAs of this repository
    all_shas = [c["sha"] for c in all_commits]
    evidence_tasks, extra_shas = {}, set()
    for sid in roster.ids:
        tl = []
        for t in tasks_by_student.get(sid, []):
            ids = []
            for p in t.get("linked_commits") or []:
                hits = [s for s in all_shas if s.startswith(p.lower())]
                if len(hits) == 1:
                    ids.append(hits[0])
                else:
                    quality["notes"].append(f"task {t.get('task_id')}: linked commit {p!r} matched {len(hits)} commits (ignored)")
            tl.append({"id": t["task_id"], "title": t.get("title", ""), "description": t.get("description", ""), "acceptance_criteria": t.get("acceptance_criteria", []),
                       "story_points": t.get("story_points", 0), "subtask_count": t.get("subtask_count", 0), "assignee": sid, "status": t.get("status", ""),
                       "completed_by": t.get("completed_by"), "carried_over_from": t.get("carried_over_from"), "commit_ids": ids})

            extra_shas.update(ids)
        evidence_tasks[sid] = tl
    mine = {c["sha"] for c in window}
    needed = sorted(s for s in extra_shas if s not in mine)
    extra_patches = gitlog.fetch_patches(ws, repo_url, needed, token=token) if needed else {}
    by_sha = {c["sha"]: c for c in all_commits}
    task_commits = {sid: [_commit_evidence(by_sha[s], {**patches, **extra_patches}, lines) for s in sorted({i for t in evidence_tasks[sid] for i in t["commit_ids"]})
                          if s in by_sha and by_sha[s]["student"] != sid and len(by_sha[s]["parents"]) <= 1] for sid in roster.ids}

    reach = {}
    if with_reach:
        try:
            with ws.worktree(repo_url, as_of=f"{sprint['start']}T00:00:00Z", token=token) as wt:
                reach = dependency_reach(wt.path, lines.classify_path)
        except WorkspaceError as e:
            quality["notes"].append(f"dependency reach not computed: {e}")

    say(f"dependency reach computed ({time.time() - t0:.0f} s)")
    # pull requests, reviews, comments
    per_github = _github_parts(github_prs, roster, start, end, owner_of) if github_prs is not None else None

    # ownership by blame at the end of the sprint
    ignore_file = None
    ignore = _format_only_commits([ce for ces in by_student.values() for ce in ces])
    if run_blame and rev:
        if ignore:
            ignore_file = ws.root / "tmp" / f"ignore-{sprint['id']}.txt"
            ignore_file.parent.mkdir(parents=True, exist_ok=True)
            ignore_file.write_text("\n".join(sorted(ignore)) + "\n", encoding="utf-8")
    blame_cache: dict[str, dict] = {}

    def blame_counts(path):
        if path not in blame_cache:
            args = ["blame", "--line-porcelain", "-w"] + (["--ignore-revs-file", str(ignore_file)] if ignore_file else []) + [rev, "--", path]
            try:
                blame_cache[path] = ko.meaningful_blame_counts(ws.read(repo_url, *args, token=token), path)
            except WorkspaceError:
                blame_cache[path] = {}  # file missing at that revision
        return blame_cache[path]

    result: dict[str, dict] = {}
    for sid in roster.ids:
        ev = {"schema": "evidence/1", "student_id": sid, "team_id": sprint.get("team_id"), "sprint": {"id": sprint["id"], "start": sprint["start"], "days": sprint["days"]},
              "commits": by_student[sid], "tasks": evidence_tasks[sid], "task_commits": task_commits[sid], "repo": {"reach_before": reach}}
        if per_github is not None:
            g = per_github[sid]
            ev.update({"pull_requests": g["pull_requests"], "reviews": g["reviews"], "comments": g["comments"], "merged_for_others": g["merged_for_others"],
                       "team": {"reviews_and_comments": per_github["_team_count"]}})
        counted = common.meaningful_commits(ev)
        added = sum(s["added"] for _, s in counted)
        if run_blame and rev and counted:
            shas = [c["id"] for c, _ in counted]
            touched = {}
            for c, _s in counted:
                for f in c["files"]:
                    if f["kind"] in lines.SOURCE_KINDS and f["added"] > 0:
                        touched[f["path"]] = touched.get(f["path"], 0) + f["added"]
            files = [p for p, _n in sorted(touched.items(), key=lambda kv: -kv[1])[:MAX_BLAME_FILES]]
            if len(touched) > MAX_BLAME_FILES:
                quality["notes"].append(f"{sid}: blame limited to the {MAX_BLAME_FILES} files with most added lines (of {len(touched)})")
            per_file = {p: blame_counts(p) for p in files}
            own = ko.summarize(per_file, shas, 0, owner_of=owner_of, me=sid)
            own["added_lines"] = added
            ev["ownership"] = own
            say(f"{sid}: blame of {len(files)} files done ({time.time() - t0:.0f} s)")
        elif run_blame:
            ev["ownership"] = {"added_lines": 0, "surviving_lines": 0, "files": 0, "primary_files": 0, "owned_files": 0}
        schema.validate(ev)
        result[sid] = ev
    return TeamEvidence(result, quality, rev, patches={**patches, **extra_patches})


def _github_parts(prs: list, roster: Roster, start: date, end: date, owner_of) -> dict:
    """Per student pull requests, reviews, comments and merges, and the number of reviews and comments by anyone on other people's pull requests (the team gate)."""
    out = {sid: {"pull_requests": [], "reviews": [], "comments": [], "merged_for_others": 0} for sid in roster.ids}
    team = 0
    for p in prs:
        n = str(p["number"])
        author_login = (p.get("user") or {}).get("login", "")
        pr_author = roster.login(author_login) or ("external" if author_login else "external")
        if pr_author in out and _in_window(p.get("created_at", ""), start, end):
            out[pr_author]["pull_requests"].append({"id": n, "author": pr_author, "created_at": p["created_at"], "merged_at": p.get("merged_at"), "closed_at": p.get("closed_at")})
        merger = roster.login(p.get("merged_by") or "")
        if merger in out and pr_author != merger and p.get("merged_at") and _in_window(p["merged_at"], start, end):
            out[merger]["merged_for_others"] += 1
        for r in p.get("_reviews", []):
            login = (r.get("user") or {}).get("login", "")
            if is_bot(login) or not _in_window(r.get("submitted_at") or "", start, end) or login == author_login:
                continue
            team += 1
            who = roster.login(login)
            if who in out:
                out[who]["reviews"].append({"pr_id": n, "reviewer": who, "pr_author": pr_author, "state": r.get("state", "COMMENTED"), "body": r.get("body") or "", "at": r["submitted_at"]})
        for kind, key in (("review_comment", "_review_comments"), ("discussion", "_issue_comments")):
            for cm in p.get(key, []):
                login = (cm.get("user") or {}).get("login", "")
                if is_bot(login) or not _in_window(cm.get("created_at", ""), start, end) or login == author_login:
                    continue
                team += 1
                who = roster.login(login)
                if who in out:
                    body = cm.get("body") or ""
                    out[who]["comments"].append({"pr_id": n, "author": who, "pr_author": pr_author, "kind": kind, "body": body, "at": cm["created_at"],
                                                 "is_reply": cm.get("in_reply_to_id") is not None, "mentions": body.count("@")})
    out["_team_count"] = team
    return out
