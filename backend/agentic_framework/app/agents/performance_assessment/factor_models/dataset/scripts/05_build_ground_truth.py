"""Step 5: choose 20 records for human rating and write the evaluation form.

Selection (real records only, deterministic):
* stratified by provisional profile so every behaviour type is rated;
* at most two records per team and one per student, so no single team or person dominates;
* students listed in private/teams_private.json under "excluded_from_ground_truth" (conflict of
  interest) are never sampled;
* within a profile, records are spread across the effort range rather than picked at random.

The form shows the evidence a supervisor would look at on GitHub and the Scrum board - what the
student worked on, task status, when they worked, how they worked with others - written as plain
statements. It does not show the model's computed feature values, so the ratings stay independent
of the model inputs (proposal 3.1, "Ground truth").

    python scripts/05_build_ground_truth.py
"""

import csv
import json
import random
from collections import defaultdict
from datetime import date, datetime, timedelta

from identity import DATASET, PRIVATE

GT = DATASET / "ground_truth"
E = DATASET / "evidence"
TARGET = {"consistent_deep_contributor": 4, "last_minute_rusher": 3, "burst_worker": 2, "reviewer_coordinator": 2,
          "free_rider": 3, "no_specific_pattern": 6}
SEED = 20261018

CRITERIA = {
    "Effort": [("E_responsibility_engagement", "Responsibility engagement", "Took up and worked on the tasks assigned to them."),
               ("E_work_investment", "Work investment", "Amount and substance of the work, not just how often they committed."),
               ("E_responsibility_fulfillment", "Responsibility fulfilment", "Finished what they took on."),
               ("E_initiative", "Initiative", "Went beyond the assignment: picked up unowned work, unblocked others."),
               ("E_persistence", "Persistence", "Kept working through the sprint and through problems.")],
    "Consistency": [("C_steady_engagement", "Steady engagement", "Worked on many days, not one or two."),
                    ("C_early_contribution", "Early contribution", "Started early rather than near the deadline."),
                    ("C_continuity", "Continuity", "No long idle stretches inside the sprint."),
                    ("C_predictable_rhythm", "Predictable rhythm", "Similar amounts of work across the sprint rather than spikes.")],
    "Requirement fulfilment": [("RF_task_alignment", "Task alignment", "The work matches the tasks they were assigned."),
                               ("RF_acceptance_criteria", "Acceptance criteria", "The delivered work meets the stated criteria."),
                               ("RF_completeness", "Completeness", "Tasks are finished, not left partial or done by others.")],
    "Collaboration": [("Co_review_engagement", "Review engagement", "Reviewed or merged teammates' work."),
                      ("Co_discussion_substance", "Discussion substance", "Wrote useful comments, not just 'ok'."),
                      ("Co_team_interaction", "Team interaction", "Worked on shared parts of the code with others; integrated others' work."),
                      ("Co_follow_through", "Follow-through", "Got their own work reviewed and merged; resolved feedback.")],
    "Task complexity": [("TC_technical_difficulty", "Technical difficulty", "How hard the assigned work was to build."),
                        ("TC_scope_breadth", "Scope and breadth", "How many parts of the system it covered."),
                        ("TC_dependency_impact", "Dependency impact", "How much other code depends on what they changed."),
                        ("TC_architectural_impact", "Architectural impact", "Whether it shaped the structure others build on."),
                        ("TC_uncertainty", "Uncertainty", "How much had to be worked out rather than followed.")],
    "Code ownership": [("KO_authorship_depth", "Authorship depth", "Wrote substantial original code of their own."),
                       ("KO_code_durability", "Code durability", "Their code is still in the final product."),
                       ("KO_self_maintenance", "Self-maintenance", "They fixed and extended their own code; others did not have to rewrite it.")],
}
PATTERNS = ["consistent_deep_contributor", "last_minute_rusher", "burst_worker", "reviewer_coordinator", "free_rider", "no_specific_pattern"]


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def select(real, profiles):
    excluded = set(json.loads((PRIVATE / "teams_private.json").read_text(encoding="utf-8")).get("excluded_from_ground_truth", {}).get("students", []))
    rng = random.Random(SEED)
    prof = {p["record_id"]: p for p in profiles}
    chosen, per_team, students = [], defaultdict(int), set()
    for name, k in TARGET.items():
        pool = [r for r in real if prof[r["record_id"]]["profile"] == name and r["student_id"] not in excluded]
        pool.sort(key=lambda r: float(prof[r["record_id"]]["effort_index"]))
        rng.shuffle(pool) if name == "free_rider" else None
        picks = []
        # spread across the effort range: walk evenly spaced positions, skipping team/student repeats
        positions = [round(i * (len(pool) - 1) / max(1, k - 1)) for i in range(k)] if pool else []
        tried = set()
        for pos in positions + list(range(len(pool))):
            if len(picks) == k:
                break
            for r in pool[pos:] + pool[:pos]:
                if r["record_id"] in tried:
                    continue
                if per_team[r["team_id"]] >= 2 or r["student_id"] in students:
                    continue
                tried.add(r["record_id"])
                picks.append(r)
                per_team[r["team_id"]] += 1
                students.add(r["student_id"])
                break
        chosen += [(name, r) for r in picks]
    # scarce profiles may not fill their quota under the team/student limits: top up from the
    # largest pools so 20 records are always rated
    total = sum(TARGET.values())
    for name in ("no_specific_pattern", "consistent_deep_contributor", "last_minute_rusher"):
        pool = [r for r in real if prof[r["record_id"]]["profile"] == name and r["student_id"] not in excluded
                and r["record_id"] not in {x["record_id"] for _, x in chosen}]
        rng.shuffle(pool)
        for r in pool:
            if len(chosen) == total:
                return chosen
            if per_team[r["team_id"]] < 2 and r["student_id"] not in students:
                chosen.append((name, r))
                per_team[r["team_id"]] += 1
                students.add(r["student_id"])
    return chosen


def strip(active_days, start):
    cells = []
    for d in range(14):
        day = start + timedelta(days=d)
        cells.append(("■" if d in active_days else "·") + ("" if (d + 1) % 7 else " "))
    return "".join(cells).strip()


def size_words(lines):
    if lines <= 0:
        return "no code"
    if lines < 150:
        return "a small amount of code (under 150 lines)"
    if lines < 600:
        return "a moderate amount of code (a few hundred lines)"
    if lines < 2000:
        return "a substantial amount of code (around a thousand lines)"
    return "a large amount of code (several thousand lines)"


def share_words(x):
    if x is None:
        return None
    if x >= 0.8:
        return "nearly all of it"
    if x >= 0.6:
        return "most of it"
    if x >= 0.35:
        return "about half of it"
    if x > 0:
        return "only a small part of it"
    return "none of it"


def evidence(r, sprint, commits, board, pulls, reviews, team_commits):
    sid, student = r["sprint_id"], r["student_id"]
    start = date.fromisoformat(sprint["start_date"])
    mine = sorted([c for c in commits if c["sprint_id"] == sid and c["student_id"] == student], key=lambda c: c["authored_at"])
    work = [c for c in mine if c["is_merge"] == "0"]
    active = {(datetime.fromisoformat(c["authored_at"]).date() - start).days for c in work}
    tasks = [t for t in board if t["sprint_id"] == sid and t["assignee_id"] == student]
    team_work = [c for c in team_commits if c["sprint_id"] == sid and c["is_merge"] == "0"]
    share = len(work) / len(team_work) if team_work else 0
    lines = sum(int(c["lines_added"]) for c in work if c["is_bulk"] == "0")
    bulk = [c for c in work if c["is_bulk"] == "1"]
    own_prs = [p for p in pulls if p["sprint_id"] == sid and p["author_id"] == student]
    given = [x for x in reviews if x["sprint_id"] == sid and x["reviewer_id"] == student and x["pr_author_id"] != student]
    merged_others = [c for c in mine if c["is_merge"] == "1" and c["subject"].startswith("Merge pull request") and student not in c["subject"]]
    other_tasks = [t for t in board if t["sprint_id"] == sid and t["completed_by"] == student and t["assignee_id"] != student]
    lines_out = []
    # what they worked on
    lines_out.append("**Tasks on the sprint board**")
    if tasks:
        for t in tasks:
            by = "" if t["completed_by"] in (student, "") else f" — completed by a teammate ({t['completed_by']})"
            carried = " (carried over from the previous sprint)" if t["carried_over_from"] else ""
            note = f" — {t['notes']}" if t["notes"] else ""
            lines_out.append(f"- *{t['task_title']}* ({t['story_points']} pts){carried}: **{t['status']}**{by}. Criteria: {t['acceptance_criteria'] or 'none recorded'}.{note}")
    else:
        lines_out.append("- No tasks were assigned to this student.")
    if other_tasks:
        lines_out.append(f"- Also completed {len(other_tasks)} task(s) assigned to teammates: " + "; ".join(f"*{t['task_title']}*" for t in other_tasks) + ".")
    lines_out.append("")
    lines_out.append("**Activity in the repository**")
    if not work:
        lines_out.append("- No commits in this sprint." + (" Only merges." if mine else ""))
    else:
        lines_out.append(f"- Worked on {len(active)} of the 14 days: `{strip(active, start)}` (■ = day with commits, week 1 then week 2).")
        lines_out.append(f"- Wrote {size_words(lines)}; made {len(work)} of the team's {len(team_work)} commits this sprint ({share:.0%}).")
        if bulk:
            lines_out.append(f"- {len(bulk)} commit(s) re-uploaded or generated large numbers of files; those are not counted as written code.")
        sample = [c["subject"] for c in work if len(c["subject"]) > 3][:8]
        if sample:
            lines_out.append("- Example commit messages: " + "; ".join(f"“{s[:90]}”" for s in sample) + ".")
    lines_out.append("")
    lines_out.append("**Working with the team**")
    team_prs = [p for p in pulls if p["sprint_id"] == sid]
    if not team_prs:
        lines_out.append("- The team did not use pull requests this sprint; work was pushed or merged directly.")
    else:
        lines_out.append(f"- Opened {len(own_prs)} pull request(s); {sum(1 for p in own_prs if p['merged_at'])} merged.")
        lines_out.append(f"- Merged {len(merged_others)} pull request(s) or branches from teammates; wrote {len(given)} review(s).")
        texts = [x["body"] for x in given if x["body"]]
        if texts:
            lines_out.append("- Review text: " + "; ".join(f"“{t[:80]}”" for t in texts[:4]) + ".")
        else:
            lines_out.append("- No written review comments.")
    shared = float(r["Co_shared_file_ratio"] or 0)
    if work:
        lines_out.append("- " + ("Most of the files they changed were also changed by teammates in this sprint." if shared >= 0.5
                                 else "Some of the files they changed were also changed by teammates." if shared > 0.1
                                 else "They worked mostly in files nobody else touched this sprint."))
    lines_out.append("")
    lines_out.append("**Their code later on**")
    survival = float(r["KO_survival"]) if r["KO_survival"] else None
    owner = float(r["KO_primary_owner_share"]) if r["KO_primary_owner_share"] else None
    if survival is None:
        lines_out.append("- No source code to follow up.")
    else:
        lines_out.append(f"- Of the code they wrote this sprint, {share_words(survival)} is still in the final version of the project.")
        if owner is not None:
            owned = {"nearly all of it": "nearly all of the files", "most of it": "most of the files", "about half of it": "about half of the files",
                     "only a small part of it": "only a few of the files", "none of it": "none of the files"}[share_words(owner)]
            lines_out.append(f"- In the final version they are the main author of {owned} they worked on.")
    lines_out.append("- The comprehension interview could not be held for past students, so no answers are available.")
    return "\n".join(lines_out)


def rating_line(code, label):
    return f"| {label} | `{code}` | [ ] 1 &nbsp; [ ] 2 &nbsp; [ ] 3 &nbsp; [ ] 4 &nbsp; [ ] 5 |"


def main():
    GT.mkdir(exist_ok=True)
    real = read(DATASET / "features_real.csv")
    profiles = read(DATASET / "features_real_profiles.csv")
    sprints = {s["sprint_id"]: s for s in read(DATASET / "sprints.csv")}
    commits = read(E / "commits.csv")
    board = [r for p in sorted((DATASET / "scrum_board").glob("T*.csv")) for r in read(p)]
    pulls, reviews = read(E / "pull_requests.csv"), read(E / "pr_reviews.csv")
    chosen = select(real, profiles)

    with open(GT / "samples.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["candidate", "record_id", "team_id", "sprint_id", "student_id", "selection_stratum"])
        order = list(chosen)
        random.Random(SEED + 1).shuffle(order)  # the rater does not see candidates grouped by profile
        for i, (name, r) in enumerate(order, 1):
            w.writerow([f"C{i:02d}", r["record_id"], r["team_id"], r["sprint_id"], r["student_id"], name])

    md = ["# Student Contribution Assessment — Evaluator Form", "",
          "**Purpose.** Your ratings are the independent reference for checking SELVIA's automatic assessment. "
          "Please rate what the evidence shows, not what the student might have done.", "",
          "**How to rate.** Read one candidate at a time. For each factor, rate every criterion from 1 to 5 using the scale below, "
          "then choose the behaviour pattern that fits best and give an overall mark out of 100. "
          "Students and teams are anonymised (STU-xxx, Txx). Candidates are in random order.", "",
          "| Score | Meaning |", "|---|---|",
          "| 1 | No evidence, or clearly inadequate |", "| 2 | Below what the team needed |", "| 3 | What a reasonable team member would do |",
          "| 4 | Clearly more than expected |", "| 5 | Exceptional; rare — reserve it for work that stands out across the whole cohort |", "",
          "Most students are 2–4 on most criteria. A student can be strong on one factor and weak on another.", "",
          "## Criteria", ""]
    for factor, items in CRITERIA.items():
        md.append(f"**{factor}**")
        md += [f"- *{label}* — {desc}" for _, label, desc in items]
        md.append("")
    md += ["**Behaviour pattern** (choose one): consistent deep contributor · last-minute rusher · burst worker · reviewer or coordinator · free rider · no specific pattern.", "",
           "**Overall mark** (0–100): your overall judgement of this student's contribution in this sprint.", "",
           "### Evaluator", "- Name or identifier: ____________________", "- Role: ____________________", "- Date: ____________________", "", "---", ""]
    by_id = {r["record_id"]: r for r in real}
    team_commits = defaultdict(list)
    for c in commits:
        team_commits[c["team_id"]].append(c)
    for i, (name, r) in enumerate(order, 1):
        s = sprints[r["sprint_id"]]
        md += [f"## Candidate C{i:02d}", "",
               f"**Student** {r['student_id']} · **Team** {r['team_id']} ({s['project_domain']}, {r['team_size']} members) · "
               f"**Sprint** {r['sprint_id'].split('-')[1]} ({s['start_date']} to {s['end_date']})", "",
               evidence(by_id[r["record_id"]], s, commits, board, pulls, reviews, team_commits[r["team_id"]]), ""]
        for factor, items in CRITERIA.items():
            md += [f"**{factor}**", "", "| Criterion | Code | Rating |", "|---|---|---|"] + [rating_line(c, l) for c, l, _ in items] + [""]
        md += ["**Behaviour pattern:** [ ] consistent deep contributor &nbsp; [ ] last-minute rusher &nbsp; [ ] burst worker &nbsp; "
               "[ ] reviewer or coordinator &nbsp; [ ] free rider &nbsp; [ ] no specific pattern", "",
               "**Overall mark (0–100):** ________ &nbsp;&nbsp; **Comment:** ____________________________________", "",
               "<div style='page-break-after: always;'></div>", ""]
    (GT / "EVALUATION_FORM.md").write_text("\n".join(md), encoding="utf-8")

    header = ["record_id", "candidate", "rater_id", "rater_type"] + [c for items in CRITERIA.values() for c, _, _ in items] + ["BP_pattern", "overall_mark", "comment"]
    template = GT / "human_ratings_template.csv"
    with open(template, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for i, (_, r) in enumerate(order, 1):
            w.writerow([r["record_id"], f"C{i:02d}"] + [""] * (len(header) - 2))
    print(f"selected {len(order)}:", {k: sum(1 for n, _ in order if n == k) for k in TARGET})
    print("teams:", sorted({r["team_id"] for _, r in order}), "students:", len({r["student_id"] for _, r in order}))


if __name__ == "__main__":
    main()
