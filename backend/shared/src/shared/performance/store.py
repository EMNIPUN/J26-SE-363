"""Reading and writing the performance assessment tables (see schema.sql).

Used by the AI backend worker (writes runs, events, results) and by the Core API (reads them for the endpoints and the live stream). Plain psycopg with a small
connection pool; every method returns plain dicts (JSON columns already decoded).
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from shared.queue import get_dsn

SCHEMA_SQL = Path(__file__).resolve().parent / "schema.sql"
RUN_STATUSES = ("queued", "running", "waiting_human", "succeeded", "failed", "cancelled")
ACTIVE_STATUSES = ("queued", "running", "waiting_human")


class RunAlreadyActive(RuntimeError):
    """A run for the same team, sprint and mode is already queued or running."""

    def __init__(self, run: dict):
        super().__init__(f"run {run['id']} is already {run['status']}")
        self.run = run


def thread_id_for(team_ref: str, sprint_id: str) -> str:
    return f"team:{team_ref}:sprint:{sprint_id}"


def _j(value: Any) -> Jsonb | None:
    return None if value is None else Jsonb(value)


class PerformanceStore:
    def __init__(self, dsn: str | None = None, *, max_size: int = 3):
        self.dsn = dsn or get_dsn()
        if not self.dsn:
            raise RuntimeError("no database URL configured (SERVER_DIRECT_URL / SERVER_DATABASE_URL)")
        self._pool: ConnectionPool | None = None
        self._max = max_size
        self._guard = threading.Lock()

    # ---- plumbing ---------------------------------------------------------------------------------------------------------------------
    def pool(self) -> ConnectionPool:
        with self._guard:
            if self._pool is None:
                self._pool = ConnectionPool(self.dsn, min_size=1, max_size=self._max, kwargs={"autocommit": True, "row_factory": dict_row}, open=True)
            return self._pool

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    def _one(self, sql: str, params: tuple | dict = ()) -> dict | None:
        with self.pool().connection() as c:
            return c.execute(sql, params).fetchone()

    def _all(self, sql: str, params: tuple | dict = ()) -> list[dict]:
        with self.pool().connection() as c:
            return c.execute(sql, params).fetchall()

    def ensure_schema(self) -> None:
        """Create the tables if they do not exist (tests and local development; production uses the alembic migration)."""
        with psycopg.connect(self.dsn, autocommit=True) as c:
            c.execute(SCHEMA_SQL.read_text(encoding="utf-8"))

    # ---- tracked teams ----------------------------------------------------------------------------------------------------------------
    def upsert_tracked_team(self, team_ref: str, repo_url: str, board_ref: str | None = None, config: dict | None = None, created_by: str | None = None) -> dict:
        return self._one(
            """INSERT INTO perf_tracked_teams (team_ref, repo_url, board_ref, config, created_by) VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (team_ref) DO UPDATE SET repo_url = EXCLUDED.repo_url, board_ref = EXCLUDED.board_ref, config = EXCLUDED.config, status = 'active', updated_at = now()
               RETURNING *""", (team_ref, repo_url, board_ref, Jsonb(config or {}), created_by))

    def get_tracked_team(self, team_ref: str) -> dict | None:
        return self._one("SELECT * FROM perf_tracked_teams WHERE team_ref = %s", (team_ref,))

    def update_tracked_config(self, team_ref: str, config: dict) -> dict | None:
        """Replace the team's config (roster, sprints, sync state) without touching its tracking status."""
        return self._one("UPDATE perf_tracked_teams SET config = %s, updated_at = now() WHERE team_ref = %s RETURNING *", (Jsonb(config), team_ref))

    def list_tracked_teams(self, status: str | None = None) -> list[dict]:
        return self._all("SELECT * FROM perf_tracked_teams WHERE (%s::text IS NULL OR status = %s) ORDER BY team_ref", (status, status))

    def set_tracking_status(self, team_ref: str, status: str) -> dict | None:
        return self._one("UPDATE perf_tracked_teams SET status = %s, updated_at = now() WHERE team_ref = %s RETURNING *", (status, team_ref))

    # ---- runs -------------------------------------------------------------------------------------------------------------------------
    def create_run(self, team_ref: str, sprint_id: str, mode: str, requested_by: str | None = None, job_id: int | None = None) -> dict:
        """New run in status queued. Raises RunAlreadyActive when the same team, sprint and mode is already queued, running or waiting for a human."""
        with self.pool().connection() as c:
            with c.transaction():
                c.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"run:{team_ref}:{sprint_id}:{mode}",))
                active = c.execute("SELECT * FROM perf_runs WHERE team_ref = %s AND sprint_id = %s AND mode = %s AND status = ANY(%s) ORDER BY created_at DESC LIMIT 1",
                                   (team_ref, sprint_id, mode, list(ACTIVE_STATUSES))).fetchone()
                if active:
                    raise RunAlreadyActive(active)
                return c.execute("INSERT INTO perf_runs (team_ref, sprint_id, mode, thread_id, requested_by, job_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING *",
                                 (team_ref, sprint_id, mode, thread_id_for(team_ref, sprint_id), requested_by, job_id)).fetchone()

    def get_run(self, run_id: str) -> dict | None:
        return self._one("SELECT * FROM perf_runs WHERE id = %s", (run_id,))

    def list_runs(self, team_ref: str | None = None, sprint_id: str | None = None, limit: int = 50) -> list[dict]:
        return self._all("SELECT * FROM perf_runs WHERE (%s::text IS NULL OR team_ref = %s) AND (%s::text IS NULL OR sprint_id = %s) ORDER BY created_at DESC LIMIT %s",
                         (team_ref, team_ref, sprint_id, sprint_id, limit))

    def update_run(self, run_id: str, *, status: str | None = None, current_node: str | None = None, error: dict | None = None, summary: dict | None = None, job_id: int | None = None) -> dict | None:
        if status is not None and status not in RUN_STATUSES:
            raise ValueError(f"unknown run status {status!r}")
        return self._one(
            """UPDATE perf_runs SET
                   status = COALESCE(%s, status), current_node = COALESCE(%s, current_node), error = COALESCE(%s, error), summary = COALESCE(%s, summary), job_id = COALESCE(%s, job_id),
                   started_at = CASE WHEN %s = 'running' AND started_at IS NULL THEN now() ELSE started_at END,
                   finished_at = CASE WHEN %s IN ('succeeded', 'failed', 'cancelled') THEN now() ELSE finished_at END, updated_at = now()
               WHERE id = %s RETURNING *""", (status, current_node, _j(error), _j(summary), job_id, status, status, run_id))

    # ---- events -----------------------------------------------------------------------------------------------------------------------
    def add_event(self, run_id: str, type: str, message: str = "", *, node_path: str = "", level: str = "info", payload: dict | None = None) -> int:
        """Append an event to a run's log and wake listeners (NOTIFY perf_events). Returns its sequence number."""
        return self.add_events(run_id, [{"type": type, "message": message, "node_path": node_path, "level": level, "payload": payload or {}}])[-1]

    def add_events(self, run_id: str, events: list[dict]) -> list[int]:
        """Append several events in order with one round trip (the database may be far away: one event per round trip made a run's log slower than its work). Returns their sequence numbers."""
        if not events:
            return []
        rows = [(e.get("node_path", ""), e["type"], e.get("level", "info"), e.get("message", ""), Jsonb(e.get("payload") or {})) for e in events]
        values = ", ".join(["(%s, %s, %s, %s, %s)"] * len(rows))
        sql = f"""WITH base AS (SELECT coalesce(max(seq), 0) AS n FROM perf_run_events WHERE run_id = %s),
                  new AS (SELECT row_number() OVER () AS i, v.* FROM (VALUES {values}) AS v(node_path, type, level, message, payload)),
                  ins AS (INSERT INTO perf_run_events (run_id, seq, node_path, type, level, message, payload)
                          SELECT %s, base.n + new.i, new.node_path, new.type, new.level, new.message, new.payload::jsonb FROM new, base RETURNING seq)
                  SELECT seq, pg_notify('perf_events', %s || ':' || seq) FROM ins ORDER BY seq"""
        params = [run_id] + [x for r in rows for x in (r[0], r[1], r[2], r[3], r[4])] + [run_id, run_id]
        for attempt in range(8):  # two writers can pick the same next number: the unique key refuses the second, which then looks again
            try:
                with self.pool().connection() as c:
                    return [r["seq"] for r in c.execute(sql, params).fetchall()]
            except psycopg.errors.UniqueViolation:
                if attempt == 7:
                    raise
                time.sleep(0.01 * (attempt + 1))
        return []

    def list_events(self, run_id: str, after: int = 0, limit: int = 500, node_path: str | None = None) -> list[dict]:
        return self._all("SELECT seq, ts, node_path, type, level, message, payload FROM perf_run_events WHERE run_id = %s AND seq > %s AND (%s::text IS NULL OR node_path = %s OR node_path LIKE %s) ORDER BY seq LIMIT %s",
                         (run_id, after, node_path, node_path, (node_path or "") + "/%", limit))

    # ---- factor results and assessment results ----------------------------------------------------------------------------------------
    def save_factor_result(self, run_id: str, student_id: str, factor: str, *, score: float | None, status: str, interval: list | None = None, provisional: bool = False,
                           features: dict | None = None, warnings: list | None = None, versions: dict | None = None, audit: dict | None = None) -> dict:
        return self._one(
            """INSERT INTO perf_factor_results (run_id, student_id, factor, score, interval, status, provisional, features, warnings, versions, audit)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (run_id, student_id, factor) DO UPDATE SET score = EXCLUDED.score, interval = EXCLUDED.interval, status = EXCLUDED.status, provisional = EXCLUDED.provisional,
                   features = EXCLUDED.features, warnings = EXCLUDED.warnings, versions = EXCLUDED.versions, audit = EXCLUDED.audit RETURNING *""",
            (run_id, student_id, factor, score, _j(interval), status, provisional, Jsonb(features or {}), Jsonb(warnings or []), Jsonb(versions or {}), Jsonb(audit or {})))

    def list_factor_results(self, run_id: str, student_id: str | None = None) -> list[dict]:
        return self._all("SELECT * FROM perf_factor_results WHERE run_id = %s AND (%s::text IS NULL OR student_id = %s) ORDER BY student_id, factor", (run_id, student_id, student_id))

    def save_assessment_result(self, run_id: str, team_ref: str, sprint_id: str, student_id: str, *, mark: float | None, status: str, mark_interval: list | None = None,
                               factors: dict | None = None, justification: dict | None = None, flags: list | None = None) -> dict:
        return self._one(
            """INSERT INTO perf_assessment_results (run_id, team_ref, sprint_id, student_id, mark, mark_interval, status, factors, justification, flags)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (run_id, student_id) DO UPDATE SET mark = EXCLUDED.mark, mark_interval = EXCLUDED.mark_interval, status = EXCLUDED.status, factors = EXCLUDED.factors,
                   justification = EXCLUDED.justification, flags = EXCLUDED.flags, updated_at = now() RETURNING *""",
            (run_id, team_ref, sprint_id, student_id, mark, _j(mark_interval), status, Jsonb(factors or {}), Jsonb(justification or {}), Jsonb(flags or [])))

    def latest_results(self, team_ref: str, sprint_id: str) -> list[dict]:
        """The most recent result of each student of a team-sprint (final results win over provisional ones of the same age)."""
        return self._all(
            """SELECT DISTINCT ON (student_id) * FROM perf_assessment_results WHERE team_ref = %s AND sprint_id = %s
               ORDER BY student_id, (status = 'final') DESC, created_at DESC""", (team_ref, sprint_id))

    def set_override(self, run_id: str, student_id: str, override: dict) -> dict | None:
        return self._one("UPDATE perf_assessment_results SET override = %s, updated_at = now() WHERE run_id = %s AND student_id = %s RETURNING *", (Jsonb(override), run_id, student_id))

    # ---- snapshots (day-by-day development) -------------------------------------------------------------------------------------------
    def add_snapshot(self, team_ref: str, sprint_id: str, student_id: str, as_of, sprint_elapsed: float, *, mark: float | None, mark_interval: list | None = None, factors: dict | None = None) -> dict:
        return self._one(
            """INSERT INTO perf_snapshots (team_ref, sprint_id, student_id, as_of, sprint_elapsed, mark, mark_interval, factors) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (team_ref, sprint_id, student_id, as_of) DO UPDATE SET sprint_elapsed = EXCLUDED.sprint_elapsed, mark = EXCLUDED.mark, mark_interval = EXCLUDED.mark_interval,
                   factors = EXCLUDED.factors RETURNING *""", (team_ref, sprint_id, student_id, as_of, sprint_elapsed, mark, _j(mark_interval), Jsonb(factors or {})))

    def trajectory(self, team_ref: str, sprint_id: str, student_id: str) -> list[dict]:
        return self._all("SELECT as_of, sprint_elapsed, mark, mark_interval, factors FROM perf_snapshots WHERE team_ref = %s AND sprint_id = %s AND student_id = %s ORDER BY as_of",
                         (team_ref, sprint_id, student_id))

    # ---- reviews ----------------------------------------------------------------------------------------------------------------------
    def create_review(self, run_id: str, kind: str, reason: str, *, student_id: str | None = None, evidence: dict | None = None) -> dict:
        return self._one("INSERT INTO perf_reviews (run_id, student_id, kind, reason, evidence) VALUES (%s, %s, %s, %s, %s) RETURNING *", (run_id, student_id, kind, reason, Jsonb(evidence or {})))

    def list_reviews(self, status: str | None = "open", run_id: str | None = None) -> list[dict]:
        return self._all("SELECT * FROM perf_reviews WHERE (%s::text IS NULL OR status = %s) AND (%s::uuid IS NULL OR run_id = %s) ORDER BY created_at", (status, status, run_id, run_id))

    def decide_review(self, review_id: str, decision: dict, decided_by: str | None = None) -> dict | None:
        return self._one("UPDATE perf_reviews SET status = 'decided', decision = %s, decided_by = %s, decided_at = now() WHERE id = %s AND status = 'open' RETURNING *", (Jsonb(decision), decided_by, review_id))

    # ---- quizzes (Code Ownership) ----------------------------------------------------------------------------------------------------
    def get_quiz(self, team_ref: str, sprint_id: str, student_id: str) -> dict | None:
        return self._one("SELECT * FROM perf_quizzes WHERE team_ref = %s AND sprint_id = %s AND student_id = %s", (team_ref, sprint_id, student_id))

    def create_quiz(self, team_ref: str, sprint_id: str, student_id: str, *, question: str, snippet: str, file_path: str | None, line_range: list | None, meta: dict, deadline_at, run_id: str | None = None) -> dict:
        """The quiz of a student for a sprint; created once (a second call returns the existing one unchanged)."""
        return self._one(
            """INSERT INTO perf_quizzes (team_ref, sprint_id, student_id, run_id, question, snippet, file_path, line_range, meta, deadline_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (team_ref, sprint_id, student_id) DO UPDATE SET team_ref = EXCLUDED.team_ref RETURNING *""",
            (team_ref, sprint_id, student_id, run_id, question, snippet, file_path, _j(line_range), Jsonb(meta), deadline_at))

    def list_student_quizzes(self, student_id: str, status: str | None = None) -> list[dict]:
        return self._all("SELECT * FROM perf_quizzes WHERE student_id = %s AND (%s::text IS NULL OR status = %s) ORDER BY created_at DESC", (student_id, status, status))

    def submit_quiz_answer(self, quiz_id: str, answer: str, now=None) -> dict | None:
        """Record the answer if the quiz is open or extended and its window has not passed; ``in_extension`` is set when it comes in the second window."""
        return self._one(
            """UPDATE perf_quizzes SET answer = %s, answered_at = COALESCE(%s::timestamptz, now()), in_extension = (status = 'extended'), status = 'answered'
               WHERE id = %s AND status IN ('open', 'extended') AND COALESCE(%s::timestamptz, now()) <= COALESCE(extended_until, deadline_at) RETURNING *""",
            (answer, now, quiz_id, now))

    def set_quiz_result(self, quiz_id: str, result: dict) -> dict | None:
        return self._one("UPDATE perf_quizzes SET result = %s WHERE id = %s RETURNING *", (Jsonb(result), quiz_id))

    def advance_quiz_windows(self, extra_hours: float, now=None) -> list[dict]:
        """Quizzes whose first window passed unanswered become 'extended' (a second window of extra_hours); those whose second window passed become 'expired'. Returns the changed rows."""
        with self.pool().connection() as c:
            with c.transaction():
                cur = c.cursor(row_factory=dict_row)
                ext = cur.execute("UPDATE perf_quizzes SET status = 'extended', extended_until = deadline_at + make_interval(hours => %s) WHERE status = 'open' AND deadline_at < COALESCE(%s::timestamptz, now()) RETURNING *", (extra_hours, now)).fetchall()
                exp = cur.execute("UPDATE perf_quizzes SET status = 'expired' WHERE status = 'extended' AND extended_until < COALESCE(%s::timestamptz, now()) RETURNING *", (now,)).fetchall()
        return ext + exp
