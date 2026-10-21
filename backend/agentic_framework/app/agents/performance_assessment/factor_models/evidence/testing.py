"""Small builders for tests: evidence with a few commits, in line-stats form."""


def stats(code=0, comment=0, blank=0, format_only=0, d_code=0, d_comment=0, d_blank=0, d_format=0):
    return {"added": {"code": code, "comment": comment, "blank": blank, "format_only": format_only},
            "deleted": {"code": d_code, "comment": d_comment, "blank": d_blank, "format_only": d_format}}


def file(path, **kw):
    s = stats(**kw)
    return {"path": path, "status": "M", "added": sum(s["added"].values()), "deleted": sum(s["deleted"].values()), "line_stats": s}


def commit(cid, at, files, is_merge=False, subject="work"):
    return {"id": cid, "authored_at": at, "is_merge": is_merge, "subject": subject, "files": files}


def evidence(commits, student="STU-001", start="2026-02-02", days=14, **extra):
    base = {"schema": "evidence/1", "student_id": student, "team_id": "T01",
            "sprint": {"id": "T01-S1", "start": start, "days": days}, "commits": commits}
    base.update(extra)
    return base
