"""Builds evidence/1 payloads (one per student and sprint) for the real and the simulated students, for the Collaboration audit.

Only the fields Collaboration reads are filled: reviews, comments, pull requests, and the team's review activity count (``evidence["team"]``).
``merged_for_others`` is 0 for real students because the collected data does not say who merged a pull request; this understates the
"reviewed pull requests" measure for them, and is stated in the notebook.
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FM = HERE.parents[2]
sys.path.insert(0, str(FM))
from evidence.testing import evidence  # noqa: E402

EVID = FM / "dataset" / "evidence"
SIM = FM / "dataset" / "synthetic_students" / "out"


def _rows(d):
    return [] if d is None else d.to_dict("records")


def _build(student, team, sprint, start, days, reviews, comments, prs, team_activity):
    e = evidence([], student=student, start=start, days=days,
                    reviews=[{"pr_id": str(r["pr_id"]), "reviewer": r["reviewer"], "pr_author": r["pr_author"], "state": r["state"], "body": r["body"]} for r in reviews],
                    comments=[{"pr_id": str(c["pr_id"]), "author": c["author"], "pr_author": c["pr_author"], "kind": "discussion", "body": c["body"],
                               "is_reply": bool(c["is_reply"]), "mentions": int(c["mentions"])} for c in comments],
                    pull_requests=[{"id": str(p["id"]), "author": student, "created_at": None, "merged_at": p["merged_at"], "closed_at": p["closed_at"]} for p in prs],
                    merged_for_others=0, team={"reviews_and_comments": int(team_activity)})
    e["team_id"], e["sprint"]["id"] = team, sprint
    return e


def real():
    """List of (meta, evidence) for every real student-sprint."""
    sprints = pd.read_csv(FM / "dataset" / "sprints.csv")
    roster = pd.read_csv(FM / "dataset" / "roster.csv")
    rv = pd.read_csv(EVID / "pr_reviews.csv").fillna("")
    cm = pd.read_csv(EVID / "pr_comments.csv").fillna("")
    pr = pd.read_csv(EVID / "pull_requests.csv").fillna("")
    out = []
    for s in sprints.itertuples():
        rvs, cms, prs = rv[rv.sprint_id == s.sprint_id], cm[cm.sprint_id == s.sprint_id], pr[pr.sprint_id == s.sprint_id]
        team_activity = int((rvs.reviewer_id != rvs.pr_author_id).sum() + (cms.author_id != cms.pr_author_id).sum())
        for stu in roster[roster.team_id == s.team_id].student_id:
            reviews = [{"pr_id": r.pr_id, "reviewer": r.reviewer_id, "pr_author": r.pr_author_id, "state": r.state, "body": r.body} for r in rvs[rvs.reviewer_id == stu].itertuples()]
            comments = [{"pr_id": c.pr_id, "author": c.author_id, "pr_author": c.pr_author_id, "body": c.body, "is_reply": c.is_reply, "mentions": c.mentions}
                        for c in cms[cms.author_id == stu].itertuples()]
            own = [{"id": p.pr_id, "merged_at": p.merged_at or None, "closed_at": p.closed_at or None} for p in prs[prs.author_id == stu].itertuples()]
            meta = {"source": "real", "student": stu, "team": s.team_id, "sprint": s.sprint_id}
            out.append((meta, _build(stu, s.team_id, s.sprint_id, str(s.start_date), int(s.length_days), reviews, comments, own, team_activity)))
    return out


def simulated():
    """List of (meta, evidence) for every simulated student-sprint."""
    students = pd.read_csv(SIM / "students_simulated.csv")
    rv = pd.read_csv(SIM / "reviews_simulated.csv").fillna("")
    cm = pd.read_csv(SIM / "comments_simulated.csv").fillna("")
    pr = pd.read_csv(SIM / "pull_requests_simulated.csv").fillna("")
    out = []
    for s in students.itertuples():
        for k in range(1, int(s.sprints) + 1):
            sprint = f"{s.team_id}-S{k}"
            rvs, cms, prs = rv[rv.sprint_id == sprint], cm[cm.sprint_id == sprint], pr[pr.sprint_id == sprint]
            team_activity = int((rvs.reviewer_id != rvs.pr_author_id).sum() + (cms.author_id != cms.pr_author_id).sum())
            reviews = [{"pr_id": f"{sprint}-{r.pr_author_id}-r{i}", "reviewer": r.reviewer_id, "pr_author": r.pr_author_id, "state": r.state, "body": r.body}
                       for i, r in enumerate(rvs[rvs.reviewer_id == s.student_id].itertuples())]
            comments = [{"pr_id": f"{sprint}-{c.pr_author_id}-c{i}", "author": c.author_id, "pr_author": c.pr_author_id, "body": c.body, "is_reply": c.is_reply, "mentions": c.mentions}
                        for i, c in enumerate(cms[cms.author_id == s.student_id].itertuples())]
            own = [{"id": f"{sprint}-own{i}", "merged_at": "t" if p.merged else None, "closed_at": "t" if p.merged else None}
                   for i, p in enumerate(prs[prs.author_id == s.student_id].itertuples())]
            meta = {"source": "simulated", "student": s.student_id, "team": s.team_id, "sprint": sprint, "behaviour": s.behaviour_class}
            out.append((meta, _build(s.student_id, s.team_id, sprint, "2026-01-05", 14, reviews, comments, own, team_activity)))
    return out
