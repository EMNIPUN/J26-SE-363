"""Print one team's sprint evidence, student by student, for reading (used to reconstruct the
Scrum board by hand). Reads only pseudonymised evidence.

    python scripts/digest.py T03            # every sprint
    python scripts/digest.py T03 T03-S2     # one sprint
"""

import csv
import sys
from collections import defaultdict

from identity import DATASET

E = DATASET / "evidence"


def rows(name):
    with open(E / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    team = sys.argv[1]
    only = sys.argv[2] if len(sys.argv) > 2 else None
    files = defaultdict(list)
    for f in rows("commit_files.csv"):
        if f["team_id"] == team and f["kind"] in ("code", "test", "config_or_docs"):
            files[f["commit_id"]].append(f)
    by = defaultdict(list)
    for c in rows("commits.csv"):
        if c["team_id"] == team and (not only or c["sprint_id"] == only):
            by[(c["sprint_id"] or "(outside sprints)", c["student_id"])].append(c)
    prs = defaultdict(list)
    for p in rows("pull_requests.csv"):
        if p["team_id"] == team:
            prs[(p["sprint_id"], p["author_id"])].append(p)
    for (sprint, student), commits in sorted(by.items()):
        commits.sort(key=lambda c: c["authored_at"])
        add = sum(int(c["lines_added"]) for c in commits)
        print(f"\n### {sprint} {student}: {len(commits)} commits, +{add} lines, "
              f"{len({c['authored_at'][:10] for c in commits})} active days")
        for c in commits:
            comps = sorted({f["component"] for f in files[c["commit_id"]]})
            print(f"  {c['authored_at'][:10]} {c['commit_id'][:7]} {'M ' if c['is_merge'] == '1' else ''}"
                  f"+{c['lines_added']}/-{c['lines_deleted']} f{c['files_counted']} | {c['subject'][:90]} | {', '.join(comps)[:80]}")
        for p in prs.get((sprint, student), []):
            print(f"  PR {p['created_at'][:10]} {'merged' if p['merged_at'] else 'not merged'}: {p['title'][:90]}")


if __name__ == "__main__":
    main()
