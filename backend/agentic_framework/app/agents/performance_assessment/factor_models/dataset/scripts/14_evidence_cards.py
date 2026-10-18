"""Step 14: evidence cards, one per student-sprint, for rating against the rubric (ground_truth/EVALUATION_FORM.md).

A card holds the raw evidence a rater would read: the commits (date, message, size, parts of the system), the tasks with their
status, pull requests, reviews and comments, and the share of the code that survives. It holds none of the engineered
feature values and, for simulated students, nothing about how they were written (no behaviour class, no scenario).

    python scripts/14_evidence_cards.py real 0 15      # cards 0-14 of the real records that have no rating
    python scripts/14_evidence_cards.py sim 0 15       # cards 0-14 of the simulated records
    python scripts/14_evidence_cards.py list real      # how many cards there are
"""

import csv
import json
import sys
from collections import defaultdict

import pandas as pd

from identity import DATASET

sys.stdout.reconfigure(encoding="utf-8")
E = DATASET / "evidence"
SIM = DATASET / "synthetic_students" / "out"
MAX_COMMITS = 28


def short(text, n=100):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def unrated_real():
    final = pd.read_csv(DATASET / "clean" / "final_dataset_clean.csv", low_memory=False)
    rated = set(pd.read_csv(DATASET / "ground_truth" / "human_ratings.csv").record_id)
    return [r for r in final[final.source == "real"].record_id if r not in rated]


def sim_records():
    return list(pd.read_csv(SIM / "features_simulated.csv").record_id)


def real_cards(ids):
    commits = pd.read_csv(E / "commits.csv").fillna("")
    cfiles = pd.read_csv(E / "commit_files.csv").fillna("")
    board = pd.read_csv(DATASET / "scrum_board.csv").fillna("")
    pulls = pd.read_csv(E / "pull_requests.csv").fillna("")
    reviews = pd.read_csv(E / "pr_reviews.csv").fillna("")
    comments = pd.read_csv(E / "pr_comments.csv").fillna("")
    feats = pd.read_csv(DATASET / "features_real.csv").set_index("record_id")
    sprints = pd.read_csv(DATASET / "sprints.csv").set_index("sprint_id")
    comps = cfiles[cfiles.kind.isin(["code", "test", "config_or_docs"])].groupby("commit_id").component.agg(lambda s: sorted(set(s)))
    out = []
    for rid in ids:
        f = feats.loc[rid]
        sid, stu = f.sprint_id, f.student_id
        sp = sprints.loc[sid]
        mine = commits[(commits.sprint_id == sid) & (commits.student_id == stu)].sort_values("authored_at")
        lines = [f"=== {rid} | {sid} {sp.start_date}..{sp.end_date} | {sp.project_domain} | team of {int(f.team_size)} | student {stu}"]
        if not len(mine):
            lines.append("COMMITS: none in this sprint")
        else:
            lines.append(f"COMMITS: {len(mine)}")
            for c in mine.head(MAX_COMMITS).itertuples():
                tag = "MERGE " if c.is_merge == 1 else ""
                lines.append(f"  {c.authored_at[:10]} {tag}+{c.lines_added}/-{c.lines_deleted} {c.files_counted}f | {short(c.subject, 70)} | {','.join(comps.get(c.commit_id, []))[:50]}")
            if len(mine) > MAX_COMMITS:
                rest = mine.iloc[MAX_COMMITS:]
                lines.append(f"  … {len(rest)} more commits, dates {rest.authored_at.str[:10].min()}..{rest.authored_at.str[:10].max()}, +{int(rest.lines_added.sum())} lines")
        t = board[(board.sprint_id == sid) & (board.assignee_id == stu)]
        if len(t):
            lines.append("TASKS:")
            for x in t.itertuples():
                by = f" (finished by a teammate)" if x.completed_by not in ("", stu) else ""
                carried = " (carried over)" if x.carried_over_from else ""
                lines.append(f"  [{x.status}{by}{carried}] {short(x.task_title, 60)} | {x.story_points}sp {x.subtask_count} subtasks | criteria met {x.ac_met}/{x.ac_total} | {short(x.description, 110)}")
        else:
            lines.append("TASKS: none assigned")
        pr = pulls[(pulls.sprint_id == sid) & (pulls.author_id == stu)]
        lines.append("PULL REQUESTS opened: " + (", ".join(f"{'merged' if p.merged_at else 'open'}: {short(p.title, 50)}" for p in pr.itertuples()) or "none"))
        rv = reviews[(reviews.sprint_id == sid) & (reviews.reviewer_id == stu)]
        cm = comments[(comments.sprint_id == sid) & (comments.author_id == stu)]
        merged_others = int(f.Co_prs_merged_for_others)
        lines.append(f"REVIEWS given: {len(rv)}; comments: {len(cm)}; merged others' pull requests: {merged_others}")
        for r in rv.itertuples():
            lines.append(f"  review ({r.state}): {short(r.body, 140)}")
        for m in cm.itertuples():
            lines.append(f"  comment: {short(m.body, 140)}")
        lines.append(f"TEAM USED PULL REQUESTS THIS SPRINT: {'yes' if int(f.Co_team_uses_prs) else 'no'}")
        surv = f.KO_survival if str(f.KO_survival) != "nan" else None
        own = f.KO_primary_owner_share if str(f.KO_primary_owner_share) != "nan" else None
        lines.append("CODE AT THE FINAL VERSION: " + (f"{surv:.0%} of the lines they added still survive; main author of {own:.0%} of the files they touched" if surv is not None else "no code of theirs to trace"))
        out.append("\n".join(lines))
    return out


def sim_cards(ids):
    commits = pd.read_csv(SIM / "commits_simulated.csv").fillna("")
    board = pd.read_csv(SIM / "scrum_board_simulated.csv").fillna("")
    reviews = pd.read_csv(SIM / "reviews_simulated.csv").fillna("")
    comments = pd.read_csv(SIM / "comments_simulated.csv").fillna("")
    prs = pd.read_csv(SIM / "pull_requests_simulated.csv").fillna("")
    quiz = pd.read_csv(SIM / "quiz_simulated.csv").fillna("")
    feats = pd.read_csv(SIM / "features_simulated.csv").set_index("record_id")
    code = {}
    for line in open(SIM / "code_examples.jsonl", encoding="utf-8"):
        r = json.loads(line)
        code[r["task_id"]] = r
    out = []
    for rid in ids:
        f = feats.loc[rid]
        sid, stu = f.sprint_id, f.student_id
        mine = commits[(commits.sprint_id == sid) & (commits.student_id == stu)].sort_values("authored_at")
        lines = [f"=== {rid} | {sid} | {f.project_domain} | team of {int(f.team_size)} | student {stu}"]
        if not len(mine):
            lines.append("COMMITS: none in this sprint")
        else:
            lines.append(f"COMMITS: {len(mine)}")
            for c in mine.head(MAX_COMMITS).itertuples():
                nf = len(str(c.files).split("; ")) if c.files else 0
                lines.append(f"  {c.authored_at[:10]} +{c.lines_added}/-{c.lines_deleted} {nf}f | {short(c.subject, 70)} | {short(str(c.files).split('; ')[0], 45)}")
            if len(mine) > MAX_COMMITS:
                rest = mine.iloc[MAX_COMMITS:]
                lines.append(f"  … {len(rest)} more commits, dates {rest.authored_at.str[:10].min()}..{rest.authored_at.str[:10].max()}, +{int(rest.lines_added.sum())} lines")
        t = board[(board.sprint_id == sid) & (board.assignee_id == stu)]
        lines.append("TASKS:" if len(t) else "TASKS: none assigned")
        for x in t.itertuples():
            by = " (finished by a teammate)" if x.completed_by not in ("", stu) else ""
            carried = " (carried over)" if x.carried_over_from else ""
            lines.append(f"  [{x.status}{by}{carried}] {short(x.task_title, 60)} | {x.story_points}sp {x.subtask_count} subtasks | criteria met {x.ac_met}/{x.ac_total}")
            lines.append(f"      description: {short(x.description, 130)}")
            lines.append(f"      criteria: {short(x.acceptance_criteria, 230)}")
            c = code.get(x.task_id)
            if c and c["code"].strip():
                snippet = " ⏎ ".join(l.strip() for l in c["code"].strip().splitlines()[:6])
                lines.append(f"      code excerpt: {short(snippet, 260)}")
        pr = prs[(prs.sprint_id == sid) & (prs.author_id == stu)]
        lines.append("PULL REQUESTS opened: " + (", ".join(f"{'merged' if p.merged else 'open'}: {short(p.title, 50)}" for p in pr.itertuples()) or "none"))
        rv = reviews[(reviews.sprint_id == sid) & (reviews.reviewer_id == stu)]
        cm = comments[(comments.sprint_id == sid) & (comments.author_id == stu)]
        lines.append(f"REVIEWS given: {len(rv)}; comments: {len(cm)}; merged others' pull requests: {int(f.Co_prs_merged_for_others)}")
        for r in rv.itertuples():
            lines.append(f"  review ({r.state}): {short(r.body, 170)}")
        for m in cm.itertuples():
            lines.append(f"  comment: {short(m.body, 140)}")
        lines.append(f"TEAM USED PULL REQUESTS THIS SPRINT: {'yes' if int(f.Co_team_uses_prs) else 'no'}")
        surv = f.KO_survival if str(f.KO_survival) != "nan" else None
        own = f.KO_primary_owner_share if str(f.KO_primary_owner_share) != "nan" else None
        lines.append("CODE AT THE FINAL VERSION: " + (f"{surv:.0%} of the lines they added still survive; main author of {own:.0%} of the files they touched" if surv is not None else "no code of theirs to trace"))
        q = quiz[(quiz.sprint_id == sid) & (quiz.student_id == stu)]
        for x in q.itertuples():
            lines.append(f"CODE QUESTION: {short(x.question, 120)} -> ANSWER: {short(x.answer, 200)}")
        out.append("\n".join(lines))
    return out


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "list":
        print(len(unrated_real() if sys.argv[2] == "real" else sim_records()))
    else:
        ids = unrated_real() if mode == "real" else sim_records()
        a, b = int(sys.argv[2]), int(sys.argv[3])
        print("\n\n".join((real_cards if mode == "real" else sim_cards)(ids[a:b])))
