"""Step 1: collect the raw evidence for every team.

Reads each team's local git clones (all branches) and its GitHub pull requests, reviews and
comments, and caches them in ``private/raw/<repo>.json``. The cache keeps real identities, so it
stays in ``private/``; step 2 writes the pseudonymised evidence tables.

    python scripts/01_extract_evidence.py            # git + GitHub (uses GITHUB_TOKEN)
    python scripts/01_extract_evidence.py --no-github
"""

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from identity import PRIVATE, Identities

SEP = "\x1f"
RECORD = "\x1e"


def git_commits(path):
    fmt = SEP.join(["%H", "%P", "%aN", "%aE", "%aI", "%cI", "%s", "%b"]) + RECORD
    out = subprocess.run(
        ["git", "-C", str(path), "log", "--all", "--numstat", "--no-renames", f"--format={RECORD}{fmt}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout
    commits = {}
    # each commit is RECORD header RECORD numstat-lines
    parts = out.split(RECORD)
    i = 1
    while i < len(parts) - 1:
        header, stats = parts[i], parts[i + 1]
        i += 2
        fields = header.split(SEP)
        if len(fields) < 8:
            continue
        sha, parents, name, email, adate, cdate, subject, body = fields[:8]
        files = []
        for line in stats.strip().splitlines():
            cols = line.split("\t")
            if len(cols) == 3:
                add, delete, file = cols
                files.append([file, None if add == "-" else int(add), None if delete == "-" else int(delete)])
        commits[sha] = {
            "sha": sha, "parents": parents.split(), "author_name": name, "author_email": email,
            "author_date": adate, "committer_date": cdate, "subject": subject, "body": body.strip(),
            "files": files,
        }
    branches = subprocess.run(
        ["git", "-C", str(path), "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    return list(commits.values()), branches


class GitHub:
    def __init__(self, token):
        self.token = token

    def get(self, url):
        items, page = [], 1
        while True:
            sep = "&" if "?" in url else "?"
            request = urllib.request.Request(
                f"https://api.github.com/{url}{sep}per_page=100&page={page}",
                headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"},
            )
            try:
                with urllib.request.urlopen(request) as response:
                    data = json.load(response)
            except urllib.error.HTTPError as error:
                if error.code == 403:
                    time.sleep(30)
                    continue
                raise
            if isinstance(data, dict):
                return data
            items += data
            if len(data) < 100:
                return items
            page += 1

    def repo(self, slug):
        pulls = self.get(f"repos/{slug}/pulls?state=all")
        for pr in pulls:
            n = pr["number"]
            pr["_reviews"] = self.get(f"repos/{slug}/pulls/{n}/reviews")
            pr["_review_comments"] = self.get(f"repos/{slug}/pulls/{n}/comments")
            pr["_issue_comments"] = self.get(f"repos/{slug}/issues/{n}/comments")
            pr["_commits"] = [c["sha"] for c in self.get(f"repos/{slug}/pulls/{n}/commits")]
        issues = [i for i in self.get(f"repos/{slug}/issues?state=all") if "pull_request" not in i]
        for issue in issues:
            issue["_comments"] = self.get(f"repos/{slug}/issues/{issue['number']}/comments") if issue["comments"] else []
        return {"pulls": pulls, "issues": issues}


def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    config = json.loads((PRIVATE / "teams_private.json").read_text(encoding="utf-8"))
    env = Path(config["repos_dir"]) / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("GITHUB_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("Set GITHUB_TOKEN")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-github", action="store_true")
    args = parser.parse_args()
    config = json.loads((PRIVATE / "teams_private.json").read_text(encoding="utf-8"))
    ids = Identities()
    github = None if args.no_github else GitHub(token())
    unmapped = set()
    for team, info in config["teams"].items():
        for repo_id, (folder, slug) in info["repos"].items():
            commits, branches = git_commits(Path(config["repos_dir"]) / folder)
            for c in commits:
                c["student"] = ids.author(c["author_name"], c["author_email"])
                if not c["student"]:
                    unmapped.add(f"git {repo_id}: {c['author_name']} <{c['author_email']}>")
            raw = {"team": team, "repo": repo_id, "branches": branches, "commits": commits}
            cache = PRIVATE / "raw" / f"{repo_id}.json"
            if github:
                raw["github"] = github.repo(slug)
            elif cache.exists():
                raw["github"] = json.loads(cache.read_text(encoding="utf-8")).get("github")
            for pr in (raw.get("github") or {}).get("pulls", []):
                logins = [pr["user"]["login"]] + [r["user"]["login"] for r in pr["_reviews"] if r.get("user")]
                logins += [c["user"]["login"] for c in pr["_review_comments"] + pr["_issue_comments"] if c.get("user")]
                for login in logins:
                    if not ids.login(login) and not login.endswith("[bot]"):
                        unmapped.add(f"github {repo_id}: {login}")
            cache.write_text(json.dumps(raw), encoding="utf-8")
            print(f"{team} {repo_id}: {len(commits)} commits, {len((raw.get('github') or {}).get('pulls', []))} PRs")
    if unmapped:
        print("\nNot in student_identity_map.json:")
        print("\n".join(sorted(unmapped)))


if __name__ == "__main__":
    main()
