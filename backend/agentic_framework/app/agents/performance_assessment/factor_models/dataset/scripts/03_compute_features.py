"""Step 3: one row per student per sprint with the features of all seven factors.

Inputs: evidence/*.csv, scrum_board/*.csv, sprints.csv, the team rosters, and (for dependency
reach and code survival) the repositories. Output: features_real.csv. Every column is prefixed
with its factor (E_, C_, RF_, Co_, TC_, KO_); BP has no inputs of its own and is derived from the
factor scores in step 6.

Definitions are documented in README.md, section "Features".
"""

import csv
import json
import math
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from identity import DATASET, PRIVATE, opaque
from repo_analysis import SKIP as GENERATED, blame_owners, dependency_reach

E = DATASET / "evidence"
SPRINT_DAYS = 14
DEADLINE_DAYS = 3  # the last 3 of 14 days count as "near the deadline"
BULK_CAP = 800  # net lines one ordinary commit can contribute to LOC_net_capped
COUNTED = ("code", "test", "config_or_docs")
CODE_FILE = re.compile(r"\.(jsx?|tsx?|py|java|kt|dart|vue|go|cs|php)$")
APPROVAL_ONLY = re.compile(r"^\W*(lgtm|ok(ay)?|good|great|nice|done|approved?|well done|all good|looks good|thanks?|ty|\+1|👍)\W*$", re.I)
TECHNICAL = re.compile(r"`|\.(js|ts|jsx|tsx|java|py|css)\b|line \d+|function|endpoint|null|undefined|error|exception|query|index|validation|refactor|test", re.I)


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def substance(text):
    """0-1 substantiveness of a review or comment. Rule-based stand-in for the encoder score
    described in the proposal (3.1.5); approvals and one-word replies score 0."""
    text = (text or "").strip()
    words = len(text.split())
    if words < 3 or APPROVAL_ONLY.match(text):
        return 0.0
    return round(min(1.0, 0.2 + 0.6 * min(words, 40) / 40 + (0.2 if TECHNICAL.search(text) else 0.0)), 3)


def day_index(when, start):
    return (datetime.fromisoformat(when).date() - start).days


def longest_gap(active, days=SPRINT_DAYS):
    longest = run = 0
    for d in range(days):
        run = 0 if d in active else run + 1
        longest = max(longest, run)
    return longest


def bursts(active_days, churn_by_day, gap=4, share=0.2):
    """True when the work falls into two or more bursts separated by `gap`+ idle days, each
    holding at least `share` of the sprint's churn."""
    if len(active_days) < 2:
        return False
    days = sorted(active_days)
    groups, current = [], [days[0]]
    for d in days[1:]:
        if d - current[-1] > gap:
            groups.append(current)
            current = [d]
        else:
            current.append(d)
    groups.append(current)
    total = sum(churn_by_day.values()) or 1
    return sum(1 for g in groups if sum(churn_by_day.get(d, 0) for d in g) / total >= share) >= 2


def main():
    config = json.loads((PRIVATE / "teams_private.json").read_text(encoding="utf-8"))
    sprints = {r["sprint_id"]: r for r in rows(DATASET / "sprints.csv")}
    commits = rows(E / "commits.csv")
    files = defaultdict(list)
    for f in rows(E / "commit_files.csv"):
        files[f["commit_id"]].append(f)
    pulls = rows(E / "pull_requests.csv")
    reviews = rows(E / "pr_reviews.csv")
    comments = rows(E / "pr_comments.csv")
    board = [r for p in sorted((DATASET / "scrum_board").glob("T*.csv")) for r in rows(p)]

    # real SHAs and paths for repository measurements (never written out)
    raw_files, real_sha, repo_dir = {}, {}, {}
    for team, info in config["teams"].items():
        for repo_id, (folder, _) in info["repos"].items():
            repo_dir[repo_id] = Path(config["repos_dir"]) / folder
            raw = json.loads((PRIVATE / "raw" / f"{repo_id}.json").read_text(encoding="utf-8"))
            for c in raw["commits"]:
                cid = opaque(c["sha"])
                real_sha[cid] = c["sha"]
                raw_files[cid] = c["files"]

    by_team_commit = defaultdict(dict)
    for c in commits:
        by_team_commit[c["team_id"]][c["commit_id"]] = c

    def resolve(team, prefix):
        hits = [cid for cid in by_team_commit[team] if cid.startswith(prefix)]
        return hits[0] if len(hits) == 1 else None

    task_commits = {}
    linked = defaultdict(set)
    for t in board:
        ids = [resolve(t["team_id"], p) for p in t["linked_commits"].split()]
        task_commits[t["task_id"]] = [i for i in ids if i]
        for i in task_commits[t["task_id"]]:
            linked[t["team_id"]].add(i)

    # PR number -> PR, for "Merge pull request #n" commits (merging a teammate's PR)
    pr_by_key = {}
    for p in pulls:
        pr_by_key[p["pr_id"]] = p

    # dependency reach at each sprint start, per repo
    reach = {}
    for sid, s in sprints.items():
        for repo_id in config["teams"][s["team_id"]]["repos"]:
            reach[(sid, repo_id)] = dependency_reach(repo_dir[repo_id], s["start_date"], f"{repo_id}_{s['start_date']}")

    # blame at the final version, per repo, for every file a member touched
    owners = {}
    for team, info in config["teams"].items():
        for repo_id in info["repos"]:
            touched = {p for c in commits if c["repo_id"] == repo_id and c["is_bulk"] == "0"
                       for p, a, _ in raw_files.get(c["commit_id"], []) if a and CODE_FILE.search(p) and not GENERATED.search(p)}
            owners[repo_id] = blame_owners(repo_dir[repo_id], touched, repo_id)
    sha_student = {real_sha[c["commit_id"]]: c["student_id"] for c in commits if c["commit_id"] in real_sha}

    out = []
    for team, info in config["teams"].items():
        team_sprints = [s for s in sprints.values() if s["team_id"] == team]
        for s in team_sprints:
            sid, start = s["sprint_id"], date.fromisoformat(s["start_date"])
            sprint_commits = [c for c in commits if c["sprint_id"] == sid]
            team_files = defaultdict(set)  # file -> students touching it this sprint
            for c in sprint_commits:
                if c["is_merge"] == "0" and c["is_bulk"] == "0":
                    for f in files[c["commit_id"]]:
                        if f["kind"] in COUNTED:
                            team_files[(c["repo_id"], f["path"])].add(c["student_id"])
            team_has_prs = any(p["sprint_id"] == sid for p in pulls)
            for student in info["members"]:
                mine = [c for c in sprint_commits if c["student_id"] == student]
                work = [c for c in mine if c["is_merge"] == "0"]
                ordinary = [c for c in work if c["is_bulk"] == "0"]
                row = {"record_id": f"{sid}-{student}", "team_id": team, "sprint_id": sid, "student_id": student,
                       "project_domain": s["project_domain"], "team_size": len(info["members"])}

                # --- Effort ---------------------------------------------------------------------
                added = sum(int(c["lines_added"]) for c in ordinary)
                deleted = sum(int(c["lines_deleted"]) for c in ordinary)
                touched = {(c["repo_id"], f["path"]) for c in ordinary for f in files[c["commit_id"]] if f["kind"] in COUNTED}
                my_tasks = [t for t in board if t["sprint_id"] == sid and t["assignee_id"] == student]
                done_self = [t for t in my_tasks if t["status"] == "Done" and t["completed_by"] == student]
                given = [r for r in reviews if r["sprint_id"] == sid and r["reviewer_id"] == student and r["pr_author_id"] != student]
                said = [m for m in comments if m["sprint_id"] == sid and m["author_id"] == student and m["pr_author_id"] != student]
                merged_for_others = set()
                for c in mine:
                    m = re.match(r"Merge pull request #(\d+) from ([^/\s]+)", c["subject"])
                    if c["is_merge"] == "1" and m:
                        pr = pr_by_key.get(opaque(f"{c['repo_id']}#{m.group(1)}"))
                        if pr and pr["author_id"] not in (student, "external"):
                            merged_for_others.add(pr["pr_id"])
                row.update({
                    "E_CC": len(work),
                    "E_LOC_net": added - deleted,
                    "E_LOC_added": added,
                    "E_LOC_deleted": deleted,
                    "E_LOC_net_capped": sum(max(-BULK_CAP, min(BULK_CAP, int(c["lines_added"]) - int(c["lines_deleted"]))) for c in ordinary),
                    "E_FC": len(touched),
                    "E_CT": len(done_self),
                    "E_RD": len(given) + len(said) + len(merged_for_others),
                    "E_merge_commits": len(mine) - len(work),
                    "E_bulk_commits": len(work) - len(ordinary),
                    "E_bulk_lines": sum(int(c["lines_added"]) for c in work if c["is_bulk"] == "1"),
                    "E_test_lines": sum(int(c["test_added"]) for c in ordinary),
                })

                # --- Consistency --------------------------------------------------------------------
                churn = defaultdict(int)
                for c in ordinary:
                    churn[day_index(c["authored_at"], start)] += min(BULK_CAP, int(c["lines_added"]) + int(c["lines_deleted"])) or 1
                active = {day_index(c["authored_at"], start) for c in work}
                daily = [churn.get(d, 0) for d in range(SPRINT_DAYS)]
                total = sum(daily)
                if work:
                    mean = total / SPRINT_DAYS
                    cv = statistics.pstdev(daily) / mean if mean else 0
                    row.update({
                        "C_AWR": round(len(active) / SPRINT_DAYS, 4),
                        "C_DC": round(sum(daily[-DEADLINE_DAYS:]) / total, 4) if total else 1.0,
                        "C_LI_norm": round(longest_gap(active) / SPRINT_DAYS, 4),
                        "C_CV_norm": round(min(1.0, cv / math.sqrt(SPRINT_DAYS - 1)), 4),
                        "C_first_active_day": min(active),
                        "C_bimodal": int(bursts(active, churn)),
                        "C_no_activity": 0,
                    })
                else:
                    row.update({"C_AWR": 0.0, "C_DC": 1.0, "C_LI_norm": 1.0, "C_CV_norm": 1.0,
                                "C_first_active_day": "", "C_bimodal": 0, "C_no_activity": 1})

                # --- Requirement Fulfillment --------------------------------------------------------
                n = len(my_tasks)
                ac_total = sum(int(t["ac_total"]) for t in my_tasks)
                ac_met = sum(int(t["ac_met"]) for t in my_tasks if t["completed_by"] in (student, ""))
                untracked = [c for c in work if c["commit_id"] not in linked[team]]
                row.update({
                    "RF_tasks_assigned": n,
                    "RF_tasks_done": len(done_self),
                    "RF_tasks_partial": sum(1 for t in my_tasks if t["status"] in ("Partially Done", "In Progress")),
                    "RF_tasks_not_started": sum(1 for t in my_tasks if t["status"] == "To Do"),
                    "RF_done_by_teammate": sum(1 for t in my_tasks if t["completed_by"] not in (student, "")),
                    "RF_completion_rate": round(len(done_self) / n, 4) if n else "",
                    "RF_ac_total": ac_total,
                    "RF_ac_met": ac_met,
                    "RF_ac_ratio": round(ac_met / ac_total, 4) if ac_total else "",
                    "RF_llm_score": round(statistics.mean((int(t["llm_fulfilment_rating"]) - 1) / 4 for t in my_tasks), 4) if n else "",
                    "RF_carried_over": sum(1 for t in my_tasks if t["carried_over_from"]),
                    "RF_untracked_ratio": round(len(untracked) / len(work), 4) if work else "",
                })

                # --- Collaboration ------------------------------------------------------------------
                review_texts = [r["body"] for r in given if r["body"]] + [m["body"] for m in said if m["kind"] == "review_comment"]
                discussion = [m["body"] for m in said if m["kind"] == "discussion"]
                reviewed_prs = {r["pr_id"] for r in given} | {m["pr_id"] for m in said} | merged_for_others
                own_prs = [p for p in pulls if p["sprint_id"] == sid and p["author_id"] == student]
                resolved = [p for p in own_prs if p["merged_at"] or p["closed_at"]]
                merged_by_others = [p for p in own_prs if p["merged_at"]]
                shared = [f for f in touched if len(team_files[f] - {student}) > 0]
                row.update({
                    "Co_PRC_depth": round(statistics.mean(substance(t) for t in review_texts), 4) if review_texts else 0.0,
                    "Co_IC_depth": round(statistics.mean(substance(t) for t in discussion), 4) if discussion else 0.0,
                    "Co_MC": sum(int(m["is_reply"]) + min(1, int(m["mentions"])) for m in said),
                    "Co_PCount": len(reviewed_prs),
                    "Co_CCount": len(said) + sum(1 for r in given if r["body"]),
                    "Co_IR": round(len(resolved) / len(own_prs), 4) if own_prs else "",
                    "Co_prs_opened": len(own_prs),
                    "Co_prs_merged": len(merged_by_others),
                    "Co_prs_merged_for_others": len(merged_for_others),
                    "Co_shared_file_ratio": round(len(shared) / len(touched), 4) if touched else 0.0,
                    "Co_team_uses_prs": int(team_has_prs),
                })

                # --- Task Complexity ----------------------------------------------------------------
                fi, dr, cb = [], [], []
                for t in my_tasks:
                    ids = task_commits[t["task_id"]]
                    if not ids:
                        continue
                    paths = {(by_team_commit[team][i]["repo_id"], p) for i in ids for p, *_ in raw_files.get(i, [])
                             if any(f["path"] and f["kind"] in COUNTED for f in files[i])}
                    counted = {(by_team_commit[team][i]["repo_id"], f["path"]) for i in ids for f in files[i] if f["kind"] in COUNTED}
                    comps = {f["component"] for i in ids for f in files[i] if f["kind"] in COUNTED}
                    fi.append(len(counted))
                    cb.append(len(comps))
                    dr.append(sum(reach[(sid, repo)].get(p, 0) for repo, p in paths))
                sp = [int(t["story_points"]) for t in my_tasks]
                row.update({
                    "TC_SP": round(statistics.mean(sp), 3) if sp else "",
                    "TC_SP_total": sum(sp),
                    "TC_SC": round(statistics.mean(int(t["subtask_count"]) for t in my_tasks), 3) if my_tasks else "",
                    "TC_FI": round(statistics.mean(fi), 3) if fi else "",
                    "TC_DR": round(statistics.mean(dr), 3) if dr else "",
                    "TC_CB": round(statistics.mean(cb), 3) if cb else "",
                })

                # --- Code Ownership (passive part; the comprehension quiz needs the live student) ---
                added_code, surviving, files_with_lines, primary, owned_candidates = 0, 0, 0, 0, 0
                mine_real = {real_sha[c["commit_id"]] for c in ordinary if c["commit_id"] in real_sha}
                seen_files = set()
                for c in ordinary:
                    for p, a, _ in raw_files.get(c["commit_id"], []):
                        if a and CODE_FILE.search(p) and not GENERATED.search(p):
                            added_code += a
                            seen_files.add((c["repo_id"], p))
                for repo, p in seen_files:
                    counts = owners.get(repo, {}).get(p)
                    if not counts:
                        continue
                    files_with_lines += 1
                    mine_now = sum(n for sha, n in counts.items() if sha in mine_real)
                    surviving += mine_now
                    if mine_now >= 20:
                        owned_candidates += 1
                    per_student = defaultdict(int)
                    for sha, n in counts.items():
                        per_student[sha_student.get(sha, "other")] += n
                    if max(per_student, key=per_student.get) == student:
                        primary += 1
                row.update({
                    "KO_lines_added_code": added_code,
                    "KO_survival": round(min(1.0, surviving / added_code), 4) if added_code else "",
                    "KO_primary_owner_share": round(primary / files_with_lines, 4) if files_with_lines else "",
                    "KO_snippet_candidates": owned_candidates,
                    "KO_quiz_score": "",
                })
                out.append(row)

    with open(DATASET / "features_real.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    with open(DATASET / "scrum_board.csv", "w", newline="", encoding="utf-8") as f:  # all teams in one file
        writer = csv.DictWriter(f, fieldnames=list(board[0]))
        writer.writeheader()
        writer.writerows(board)
    with open(DATASET / "roster.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["team_id", "student_id"])
        for team, info in config["teams"].items():
            for student in info["members"]:
                writer.writerow([team, student])
    print(f"features_real.csv: {len(out)} student-sprints, {len(out[0])} columns")


if __name__ == "__main__":
    main()
