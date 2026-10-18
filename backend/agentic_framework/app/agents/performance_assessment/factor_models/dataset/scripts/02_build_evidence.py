"""Step 2: pseudonymised evidence tables from the private cache.

Writes ``evidence/*.csv``: commits, the files each commit touched, pull requests, reviews and
comments. Student ids replace people, opaque ids replace commit SHAs and PR numbers, and free
text is scrubbed of names, logins and emails. Nothing here can be traced back without
``private/``.

Each commit is placed in the sprint of its team whose window holds its author date (sprints.csv).
Commits outside every sprint window are kept with an empty sprint_id and are not scored.
"""

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path, PurePosixPath

from identity import DATASET, PRIVATE, Identities, opaque

EVIDENCE = DATASET / "evidence"
BOTS = {"copilot", "copilot-pull-request-reviewer", "github-actions", "vercel", "netlify"}


def is_bot(user):
    login = (user or {}).get("login", "").lower()
    return not login or login.endswith("[bot]") or login in BOTS

GENERATED = re.compile(
    r"(^|/)(node_modules|dist|build|out|\.next|coverage|vendor|target|\.gradle|__pycache__|\.idea|\.vscode|\.vs|bin|obj"
    r"|\.mvn|docker-data|postgres-data|pgdata|mongo-data|uploads)/"
    r"|(^|/)(mvnw|mvnw\.cmd|gradlew|gradlew\.bat|\.DS_Store)$|\.log$"
    r"|(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|composer\.lock|poetry\.lock|Pipfile\.lock)$"
    r"|\.min\.(js|css)$|\.map$",
    re.IGNORECASE,
)
ASSET = re.compile(r"\.(png|jpe?g|gif|svg|ico|webp|bmp|mp4|mp3|wav|woff2?|ttf|eot|otf|pdf|zip|jar|apk|psd)$", re.I)
DATA = re.compile(r"\.(csv|tsv|xlsx?|sqlite|db|geojson)$", re.I)
CODE = re.compile(r"\.(jsx?|tsx?|mjs|cjs|py|java|kt|dart|go|cs|php|rb|vue|svelte|swift|c|cpp|h|hpp|sql|html?|css|scss|sass|less)$", re.I)
BULK_FILES = 150
TEST = re.compile(r"(^|/)(tests?|__tests__|spec)/|\.(test|spec)\.\w+$", re.I)


def file_kind(path):
    if GENERATED.search(path):
        return "generated"
    if ASSET.search(path):
        return "asset"
    if DATA.search(path):
        return "data"
    if TEST.search(path):
        return "test"
    if CODE.search(path):
        return "code"
    return "config_or_docs"


def component(path):
    """The part of the system a file belongs to: the first meaningful directory."""
    parts = [p for p in PurePosixPath(path).parts[:-1] if p not in ("src", "app", "main", "java", "com", "lib")]
    return "/".join(parts[:2]) if parts else "(root)"


def load_sprints():
    sprints = {}
    with open(DATASET / "sprints.csv", newline="") as f:
        for row in csv.DictReader(f):
            sprints.setdefault(row["team_id"], []).append(
                (row["sprint_id"], date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"]))
            )
    return sprints


def sprint_of(sprints, team, when):
    day = datetime.fromisoformat(when).date()
    for sprint_id, start, end in sprints.get(team, []):
        if start <= day <= end:
            return sprint_id
    return ""


def write(name, rows, header):
    with open(EVIDENCE / name, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def main():
    EVIDENCE.mkdir(exist_ok=True)
    ids = Identities()
    config = json.loads((PRIVATE / "teams_private.json").read_text(encoding="utf-8"))
    sprints = load_sprints()
    commits, files, pulls, reviews, comments = [], [], [], [], []
    seen = set()
    for team, info in config["teams"].items():
        members = set(info["members"])
        for repo_id in info["repos"]:
            raw = json.loads((PRIVATE / "raw" / f"{repo_id}.json").read_text(encoding="utf-8"))
            sha_to_id = {}
            for c in raw["commits"]:
                if c["student"] not in members or (team, c["sha"]) in seen:
                    continue  # people outside the team roster (e.g. a lecturer) are not assessed
                seen.add((team, c["sha"]))
                cid = opaque(c["sha"])
                sha_to_id[c["sha"]] = cid
                totals = {"code": [0, 0], "test": [0, 0], "config_or_docs": [0, 0], "generated": [0, 0], "asset": [0, 0], "data": [0, 0]}
                for path, add, delete in c["files"]:
                    kind = file_kind(path)
                    totals[kind][0] += add or 0
                    totals[kind][1] += delete or 0
                    files.append({
                        "commit_id": cid, "team_id": team, "repo_id": repo_id, "path": ids.scrub(path),
                        "component": ids.scrub(component(path)), "kind": kind,
                        "lines_added": "" if add is None else add, "lines_deleted": "" if delete is None else delete,
                    })
                counted = ("code", "test", "config_or_docs")
                commits.append({
                    "commit_id": cid, "team_id": team, "repo_id": repo_id,
                    "sprint_id": sprint_of(sprints, team, c["author_date"]), "student_id": c["student"],
                    "authored_at": c["author_date"], "is_merge": int(len(c["parents"]) > 1),
                    "subject": ids.scrub(c["subject"])[:200], "body_words": len(c["body"].split()),
                    "files_changed": len(c["files"]),
                    "files_counted": sum(1 for p, _, _ in c["files"] if file_kind(p) in counted),
                    "lines_added": sum(totals[k][0] for k in counted),
                    "lines_deleted": sum(totals[k][1] for k in counted),
                    "code_added": totals["code"][0], "code_deleted": totals["code"][1],
                    "test_added": totals["test"][0],
                    "excluded_lines": sum(totals[k][0] + totals[k][1] for k in ("generated", "asset", "data")),
                    # a re-upload of the whole project or a framework scaffold, not authored work
                    "is_bulk": int(sum(1 for p, _, _ in c["files"] if file_kind(p) in counted) > BULK_FILES),
                })
            for pr in (raw.get("github") or {}).get("pulls", []):
                author = ids.login(pr["user"]["login"])
                pid = opaque(f"{repo_id}#{pr['number']}")
                pulls.append({
                    "pr_id": pid, "team_id": team, "repo_id": repo_id, "author_id": author or "external",
                    "created_at": pr["created_at"], "merged_at": pr.get("merged_at") or "",
                    "closed_at": pr.get("closed_at") or "", "sprint_id": sprint_of(sprints, team, pr["created_at"]),
                    "title": ids.scrub(pr["title"])[:200], "body_words": len((pr.get("body") or "").split()),
                    "commits": len(pr["_commits"]),
                    "commit_ids": " ".join(sha_to_id.get(s) or opaque(s) for s in pr["_commits"]),
                })
                for r in pr["_reviews"]:
                    if is_bot(r.get("user")):
                        continue
                    reviews.append({
                        "pr_id": pid, "team_id": team, "reviewer_id": ids.login(r["user"]["login"]) or "external",
                        "pr_author_id": author or "external", "state": r["state"], "submitted_at": r.get("submitted_at") or "",
                        "sprint_id": sprint_of(sprints, team, r["submitted_at"]) if r.get("submitted_at") else "",
                        "body": ids.scrub(r.get("body") or "")[:1000], "body_words": len((r.get("body") or "").split()),
                    })
                for kind, items in (("review_comment", pr["_review_comments"]), ("discussion", pr["_issue_comments"])):
                    for m in items:
                        if is_bot(m.get("user")):
                            continue
                        comments.append({
                            "pr_id": pid, "team_id": team, "kind": kind, "author_id": ids.login(m["user"]["login"]) or "external",
                            "pr_author_id": author or "external", "created_at": m["created_at"],
                            "sprint_id": sprint_of(sprints, team, m["created_at"]),
                            "is_reply": int(bool(m.get("in_reply_to_id"))), "mentions": len(re.findall(r"@\w", m.get("body") or "")),
                            "body": ids.scrub(m.get("body") or "")[:1000], "body_words": len((m.get("body") or "").split()),
                        })
    write("commits.csv", commits, list(commits[0]))
    write("commit_files.csv", files, list(files[0]))
    write("pull_requests.csv", pulls, list(pulls[0]))
    write("pr_reviews.csv", reviews, list(reviews[0]))
    write("pr_comments.csv", comments, list(comments[0]))


if __name__ == "__main__":
    main()
