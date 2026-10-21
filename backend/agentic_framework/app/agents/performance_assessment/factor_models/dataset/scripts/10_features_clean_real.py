"""Step 10: clean features for every real student-sprint, through the factor packages' own cleaning code.

Builds the raw evidence a student's sprint would have at run time (commits with clean line counts from step 9, tasks from the
Scrum board, pull requests, reviews, comments, clean blame from step 11, import-graph reach from the repository as it stood at
the sprint start with tests and generated code left out), hands it to each factor's `featurize`, and writes
``clean/features_real_clean.csv``. The old columns are kept beside the new ones with a `_raw` suffix for comparison.

    python scripts/10_features_clean_real.py
"""

import importlib.util
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FM = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(FM))

import repo_analysis as ra  # noqa: E402
from evidence.lines import classify_path, SOURCE_KINDS  # noqa: E402
from identity import DATASET, PRIVATE, Identities, opaque  # noqa: E402


def load(folder):
    spec = importlib.util.spec_from_file_location(f"clean_{folder}", FM / folder / "cleaning.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FACTORS = {name: load(folder) for name, folder in {
    "effort": "01_effort", "consistency": "02_consistency", "rf": "03_requirement_fulfillment",
    "collab": "04_collaboration", "tc": "05_task_complexity", "ko": "07_code_ownership"}.items()}

# the import graph for dependency reach is built from source files only: no tests, no generated code
_orig_source_files = ra.source_files
ra.source_files = lambda path, rev: [n for n in _orig_source_files(path, rev) if classify_path(n) == "code"]

E = DATASET / "evidence"
MERGE = re.compile(r"Merge pull request #(\d+) from ([^/\s]+)")


def main():
    config = json.loads((PRIVATE / "teams_private.json").read_text(encoding="utf-8"))
    sprints = pd.read_csv(DATASET / "sprints.csv")
    commits = pd.read_csv(E / "commits.csv").fillna("")
    cfiles = pd.read_csv(E / "commit_files.csv").fillna("")
    stats = pd.read_csv(DATASET / "clean" / "commit_file_stats.csv").fillna("")
    board = pd.read_csv(DATASET / "scrum_board.csv").fillna("")
    pulls = pd.read_csv(E / "pull_requests.csv").fillna("")
    reviews = pd.read_csv(E / "pr_reviews.csv").fillna("")
    comments = pd.read_csv(E / "pr_comments.csv").fillna("")
    old = pd.read_csv(DATASET / "features_real.csv").set_index("record_id")
    scrubber = Identities()

    files_by_commit = defaultdict(list)
    for r in cfiles.to_dict("records"):
        files_by_commit[r["commit_id"]].append(r)
    stats_by = {(r["commit_id"], r["path"]): r for r in stats.to_dict("records")}

    # real commit ids and authors, for blame
    real_sha, author_of, raw_files, repo_dir = {}, {}, {}, {}
    for team, info in config["teams"].items():
        for repo_id, (folder, _) in info["repos"].items():
            repo_dir[repo_id] = Path(config["repos_dir"]) / folder
            raw = json.loads((PRIVATE / "raw" / f"{repo_id}.json").read_text(encoding="utf-8"))
            for c in raw["commits"]:
                cid = opaque(c["sha"])
                real_sha[cid] = c["sha"]
                author_of[c["sha"]] = c["student"]
                raw_files[cid] = c["files"]
    blame = {repo_id: json.loads((PRIVATE / "cache" / f"blame_clean_{repo_id}.json").read_text(encoding="utf-8")) for repo_id in repo_dir}
    pr_by_id = {r["pr_id"]: r for r in pulls.to_dict("records")}

    def evidence_commit(row):
        cid = row["commit_id"]
        files, fallbacks = [], 0
        for f in files_by_commit.get(cid, []):
            kind = classify_path(f["path"])
            a = int(f["lines_added"]) if f["lines_added"] != "" else 0
            d = int(f["lines_deleted"]) if f["lines_deleted"] != "" else 0
            if kind in SOURCE_KINDS:
                s = stats_by.get((cid, f["path"]))
                if s:
                    ls = {"added": {k[2:]: int(v) for k, v in s.items() if k.startswith("a_")}, "deleted": {k[2:]: int(v) for k, v in s.items() if k.startswith("d_")}}
                else:  # no diff was read for this file (for example a binary change): fall back to the plain counts
                    ls = {"added": {"code": a, "comment": 0, "blank": 0, "format_only": 0}, "deleted": {"code": d, "comment": 0, "blank": 0, "format_only": 0}}
                    fallbacks += 1
            else:
                ls = {"added": {"code": a, "comment": 0, "blank": 0, "format_only": 0}, "deleted": {"code": d, "comment": 0, "blank": 0, "format_only": 0}}
            files.append({"path": f["path"], "kind": kind, "added": a, "deleted": d, "line_stats": ls})
        return {"id": cid, "authored_at": row["authored_at"], "is_merge": bool(int(row["is_merge"])), "subject": row["subject"], "files": files}, fallbacks

    commit_rows = {r["commit_id"]: r for r in commits.to_dict("records")}
    out, fallback_total = [], 0
    roster = pd.read_csv(DATASET / "roster.csv")
    for team, info in config["teams"].items():
        members = list(info["members"])
        for s in sprints[sprints.team_id == team].to_dict("records"):
            sid, start = s["sprint_id"], s["start_date"]
            reach = {}
            for repo_id in info["repos"]:
                r = ra.dependency_reach(repo_dir[repo_id], start, f"clean_{repo_id}_{start}")
                reach.update({scrubber.scrub(p): n for p, n in r.items()})  # evidence paths are scrubbed, so the keys are too
            sprint_commits = commits[commits.sprint_id == sid]
            team_board = board[board.sprint_id == sid]
            prs = pulls[pulls.sprint_id == sid]
            for student in members:
                mine = sprint_commits[sprint_commits.student_id == student]
                ev_commits, fb = [], 0
                for row in mine.to_dict("records"):
                    c, n = evidence_commit(row)
                    ev_commits.append(c)
                    fb += n
                fallback_total += fb
                # tasks and the commits that implement them
                tasks, task_commit_ids = [], set()
                prefix = {cid for cid in commit_rows if commit_rows[cid]["team_id"] == team}
                for t in team_board[team_board.assignee_id == student].to_dict("records"):
                    ids = [next(iter([c for c in prefix if c.startswith(p)]), None) for p in str(t["linked_commits"]).split()]
                    ids = [i for i in ids if i]
                    task_commit_ids.update(ids)
                    crit = [x for x in re.split(r";\s*(?=\d+\.)", t["acceptance_criteria"]) if x] if t["acceptance_criteria"] else []
                    if len(crit) != int(t["ac_total"]):
                        crit = ["criterion"] * int(t["ac_total"])
                    tasks.append({"id": t["task_id"], "title": t["task_title"], "story_points": int(t["story_points"]), "subtask_count": int(t["subtask_count"]),
                                  "assignee": student, "status": t["status"], "completed_by": t["completed_by"] or None,
                                  "carried_over_from": t["carried_over_from"] or None, "commit_ids": ids, "acceptance_criteria": crit,
                                  "criteria_met": int(t["ac_met"]), "llm_rating": int(t["llm_fulfilment_rating"])})
                mine_ids = {c["id"] for c in ev_commits}
                task_commits = []
                for cid in task_commit_ids - mine_ids:
                    c, n = evidence_commit(commit_rows[cid])
                    task_commits.append(c)
                # pull requests, reviews, comments
                my_prs = [{"id": p["pr_id"], "author": p["author_id"], "created_at": p["created_at"], "merged_at": p["merged_at"] or None, "closed_at": p["closed_at"] or None}
                          for p in prs.to_dict("records") if p["author_id"] == student]
                my_reviews = [{"pr_id": r["pr_id"], "reviewer": r["reviewer_id"], "pr_author": r["pr_author_id"], "state": r["state"], "body": r["body"], "at": r["submitted_at"]}
                              for r in reviews[(reviews.sprint_id == sid) & (reviews.reviewer_id == student)].to_dict("records")]
                my_comments = [{"pr_id": m["pr_id"], "author": m["author_id"], "pr_author": m["pr_author_id"], "kind": m["kind"], "body": m["body"], "at": m["created_at"],
                                "is_reply": bool(int(m["is_reply"])), "mentions": int(m["mentions"])}
                               for m in comments[(comments.sprint_id == sid) & (comments.author_id == student)].to_dict("records")]
                merged_for_others = set()
                for row in mine.to_dict("records"):
                    m = MERGE.match(row["subject"])
                    if row["is_merge"] and m:
                        pr = pr_by_id.get(opaque(f"{row['repo_id']}#{m.group(1)}"))
                        if pr and pr["author_id"] not in (student, "external"):
                            merged_for_others.add(pr["pr_id"])

                # ownership: the student's counted commits in the sprint, blame on counted lines at the final version
                counted = []
                for c in ev_commits:
                    row = commit_rows[c["id"]]
                    if c["is_merge"] or row["is_bulk"] == 1:
                        continue
                    if any(f["kind"] in SOURCE_KINDS and (f["line_stats"]["added"]["code"] or f["line_stats"]["deleted"]["code"]) for f in c["files"]):
                        counted.append(c)
                added_lines = sum(f["line_stats"]["added"]["code"] for c in counted for f in c["files"] if f["kind"] in SOURCE_KINDS)
                shas_by_repo = defaultdict(set)
                touched = defaultdict(set)
                for c in counted:
                    repo_id = commit_rows[c["id"]]["repo_id"]
                    shas_by_repo[repo_id].add(real_sha[c["id"]])
                    for p, a, _ in raw_files[c["id"]]:
                        if a and classify_path(p) in SOURCE_KINDS:
                            touched[repo_id].add(p)
                summary = {"added_lines": 0, "surviving_lines": 0, "files": 0, "primary_files": 0, "owned_files": 0}
                for repo_id, shas in shas_by_repo.items():
                    per_file = {f: blame[repo_id].get(f, {}) for f in touched[repo_id]}
                    one = FACTORS["ko"].summarize(per_file, shas, 0, owner_of=author_of, me=student)
                    for k in ("surviving_lines", "files", "primary_files", "owned_files"):
                        summary[k] += one[k]
                summary["added_lines"] = added_lines

                evidence = {"schema": "evidence/1", "student_id": student, "team_id": team,
                            "sprint": {"id": sid, "start": start, "days": int(s["length_days"])},
                            "commits": ev_commits, "task_commits": task_commits, "tasks": tasks, "pull_requests": my_prs,
                            "reviews": my_reviews, "comments": my_comments, "merged_for_others": len(merged_for_others),
                            "repo": {"reach_before": reach}, "ownership": summary}
                row = {"record_id": f"{sid}-{student}", "team_id": team, "sprint_id": sid, "student_id": student,
                       "project_domain": s["project_domain"], "team_size": len(members)}
                removed = {}
                for name, mod in FACTORS.items():
                    res = mod.featurize(evidence)
                    row.update(res["features"])
                    if name == "effort":
                        removed = res["removed"]
                row["Co_team_uses_prs"] = int(len(prs) > 0)
                for k in ("comment", "blank", "format_only", "docs_or_config", "generated_or_data"):
                    row[f"removed_{k}"] = removed.get(k, 0)
                for k in ("E_CC", "E_LOC_net", "E_LOC_net_capped", "E_FC", "C_AWR", "C_DC", "C_LI_norm", "C_CV_norm", "TC_FI", "TC_DR", "TC_CB",
                          "KO_survival", "KO_primary_owner_share", "KO_snippet_candidates"):
                    row[f"{k}_raw"] = old.loc[row["record_id"], k] if row["record_id"] in old.index else ""
                out.append(row)
    df = pd.DataFrame(out)
    (DATASET / "clean").mkdir(exist_ok=True)
    df.to_csv(DATASET / "clean" / "features_real_clean.csv", index=False)
    print(f"features_real_clean.csv: {len(df)} records, {df.shape[1]} columns; files without a diff (plain counts used): {fallback_total}")


if __name__ == "__main__":
    main()
