"""An in-memory stand-in for ``shared.performance.PerformanceStore`` (same method names and shapes for what the graph uses), for tests and for running the agent without a database."""
import itertools
import threading
import uuid
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


class MemoryStore:
    def __init__(self):
        self.runs, self.events, self.factor_results, self.results, self.snapshots, self.reviews, self.quizzes = {}, {}, {}, {}, [], {}, {}
        self._lock = threading.Lock()
        self.teams = {}

    # runs
    def create_run(self, team_ref, sprint_id, mode, requested_by=None, job_id=None):
        rid = str(uuid.uuid4())
        self.runs[rid] = {"id": rid, "team_ref": team_ref, "sprint_id": sprint_id, "mode": mode, "status": "queued", "thread_id": f"team:{team_ref}:sprint:{sprint_id}", "current_node": None,
                          "requested_by": requested_by, "job_id": job_id, "error": None, "summary": {}, "created_at": _now(), "started_at": None, "finished_at": None}
        self.events[rid] = []
        return self.runs[rid]

    def get_run(self, run_id):
        return self.runs.get(run_id)

    def update_run(self, run_id, *, status=None, current_node=None, error=None, summary=None, job_id=None):
        r = self.runs[run_id]
        for k, v in (("status", status), ("current_node", current_node), ("error", error), ("summary", summary), ("job_id", job_id)):
            if v is not None:
                r[k] = v
        if status == "running" and r["started_at"] is None:
            r["started_at"] = _now()
        if status in ("succeeded", "failed", "cancelled"):
            r["finished_at"] = _now()
        return r

    # events
    def add_event(self, run_id, type, message="", *, node_path="", level="info", payload=None):
        with self._lock:
            seq = len(self.events[run_id]) + 1
            self.events[run_id].append({"seq": seq, "ts": _now(), "node_path": node_path, "type": type, "level": level, "message": message, "payload": payload or {}})
            return seq

    def list_events(self, run_id, after=0, limit=500, node_path=None):
        return [e for e in self.events[run_id] if e["seq"] > after and (node_path is None or e["node_path"] == node_path or e["node_path"].startswith(node_path + "/"))][:limit]

    # results
    def save_factor_result(self, run_id, student_id, factor, *, score, status, interval=None, provisional=False, features=None, warnings=None, versions=None, audit=None):
        row = {"run_id": run_id, "student_id": student_id, "factor": factor, "score": score, "status": status, "interval": interval, "provisional": provisional, "features": features or {},
               "warnings": warnings or [], "versions": versions or {}, "audit": audit or {}}
        self.factor_results[(run_id, student_id, factor)] = row
        return row

    def list_factor_results(self, run_id, student_id=None):
        return [r for (rid, sid, _f), r in sorted(self.factor_results.items()) if rid == run_id and (student_id is None or sid == student_id)]

    def save_assessment_result(self, run_id, team_ref, sprint_id, student_id, *, mark, status, mark_interval=None, factors=None, justification=None, flags=None):
        row = {"id": str(uuid.uuid4()), "run_id": run_id, "team_ref": team_ref, "sprint_id": sprint_id, "student_id": student_id, "mark": mark, "mark_interval": mark_interval, "status": status,
               "factors": factors or {}, "justification": justification or {}, "flags": flags or [], "override": None, "created_at": _now()}
        self.results[(run_id, student_id)] = row
        return row

    def latest_results(self, team_ref, sprint_id):
        best = {}
        for r in self.results.values():
            if r["team_ref"] == team_ref and r["sprint_id"] == sprint_id:
                cur = best.get(r["student_id"])
                if cur is None or (r["status"] == "final", r["created_at"]) > (cur["status"] == "final", cur["created_at"]):
                    best[r["student_id"]] = r
        return sorted(best.values(), key=lambda r: r["student_id"])

    def set_override(self, run_id, student_id, override):
        r = self.results.get((run_id, student_id))
        if r:
            r["override"] = override
        return r

    # snapshots
    def add_snapshot(self, team_ref, sprint_id, student_id, as_of, sprint_elapsed, *, mark, mark_interval=None, factors=None):
        self.snapshots.append({"team_ref": team_ref, "sprint_id": sprint_id, "student_id": student_id, "as_of": as_of, "sprint_elapsed": sprint_elapsed, "mark": mark, "mark_interval": mark_interval,
                               "factors": factors or {}})

    def trajectory(self, team_ref, sprint_id, student_id):
        return sorted((s for s in self.snapshots if (s["team_ref"], s["sprint_id"], s["student_id"]) == (team_ref, sprint_id, student_id)), key=lambda s: s["as_of"])

    # reviews
    def create_review(self, run_id, kind, reason, *, student_id=None, evidence=None):
        rid = str(uuid.uuid4())
        self.reviews[rid] = {"id": rid, "run_id": run_id, "student_id": student_id, "kind": kind, "reason": reason, "evidence": evidence or {}, "status": "open", "decision": None}
        return self.reviews[rid]

    def list_reviews(self, status="open", run_id=None):
        return [r for r in self.reviews.values() if (status is None or r["status"] == status) and (run_id is None or r["run_id"] == run_id)]

    def decide_review(self, review_id, decision, decided_by=None):
        r = self.reviews.get(review_id)
        if not r or r["status"] != "open":
            return None
        r.update({"status": "decided", "decision": decision, "decided_by": decided_by})
        return r

    # quizzes
    def get_quiz(self, team_ref, sprint_id, student_id):
        return self.quizzes.get((team_ref, sprint_id, student_id))

    def create_quiz(self, team_ref, sprint_id, student_id, *, question, snippet, file_path, line_range, meta, deadline_at, run_id=None):
        key = (team_ref, sprint_id, student_id)
        if key not in self.quizzes:
            self.quizzes[key] = {"id": str(uuid.uuid4()), "team_ref": team_ref, "sprint_id": sprint_id, "student_id": student_id, "run_id": run_id, "question": question, "snippet": snippet, "file_path": file_path,
                                 "line_range": line_range, "meta": meta, "status": "open", "deadline_at": deadline_at, "extended_until": None, "answer": None, "answered_at": None, "in_extension": False, "result": None}
        return self.quizzes[key]

    def list_student_quizzes(self, student_id, status=None):
        return [q for q in self.quizzes.values() if q["student_id"] == student_id and (status is None or q["status"] == status)]

    def submit_quiz_answer(self, quiz_id, answer, now=None):
        now = now or _now()
        for q in self.quizzes.values():
            if q["id"] == quiz_id and q["status"] in ("open", "extended") and now <= (q["extended_until"] or q["deadline_at"]):
                q.update({"answer": answer, "answered_at": now, "in_extension": q["status"] == "extended", "status": "answered"})
                return q
        return None

    def set_quiz_result(self, quiz_id, result):
        for q in self.quizzes.values():
            if q["id"] == quiz_id:
                q["result"] = result
                return q
        return None

    def advance_quiz_windows(self, extra_hours, now=None):
        from datetime import timedelta
        now, changed = now or _now(), []
        for q in self.quizzes.values():
            if q["status"] == "open" and q["deadline_at"] < now:
                q.update({"status": "extended", "extended_until": q["deadline_at"] + timedelta(hours=extra_hours)})
                changed.append(q)
            elif q["status"] == "extended" and q["extended_until"] < now:
                q["status"] = "expired"
                changed.append(q)
        return changed

    # tracked teams
    def upsert_tracked_team(self, team_ref, repo_url, board_ref=None, config=None, created_by=None):
        self.teams[team_ref] = {"team_ref": team_ref, "repo_url": repo_url, "board_ref": board_ref, "config": config or {}, "status": "active", "created_by": created_by}
        return self.teams[team_ref]

    def get_tracked_team(self, team_ref):
        return self.teams.get(team_ref)

    def list_runs(self, team_ref=None, sprint_id=None, limit=50):
        rows = [r for r in self.runs.values() if (team_ref is None or r["team_ref"] == team_ref) and (sprint_id is None or r["sprint_id"] == sprint_id)]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)[:limit]
