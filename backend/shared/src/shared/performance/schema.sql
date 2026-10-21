-- Performance assessment tables (one source of truth). Applied by the Core API's alembic migration and, in tests, by PerformanceStore.ensure_schema().
-- Idempotent: every statement can run twice. No foreign keys to users/groups: a run is a record of what was assessed and must survive changes to those rows.

CREATE TABLE IF NOT EXISTS perf_tracked_teams (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_ref    text NOT NULL UNIQUE,
    repo_url    text NOT NULL,
    board_ref   text,
    status      text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'stopped')),
    config      jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_by  text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS perf_runs (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_ref      text NOT NULL,
    sprint_id     text NOT NULL,
    mode          text NOT NULL CHECK (mode IN ('snapshot', 'final')),
    status        text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'waiting_human', 'succeeded', 'failed', 'cancelled')),
    thread_id     text NOT NULL,
    current_node  text,
    requested_by  text,
    job_id        bigint,
    error         jsonb,
    summary       jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at    timestamptz NOT NULL DEFAULT now(),
    started_at    timestamptz,
    finished_at   timestamptz,
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_perf_runs_team_sprint ON perf_runs (team_ref, sprint_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_perf_runs_status ON perf_runs (status);

CREATE TABLE IF NOT EXISTS perf_run_events (
    id         bigserial PRIMARY KEY,
    run_id     uuid NOT NULL REFERENCES perf_runs (id) ON DELETE CASCADE,
    seq        integer NOT NULL,
    ts         timestamptz NOT NULL DEFAULT now(),
    node_path  text NOT NULL DEFAULT '',
    type       text NOT NULL,
    level      text NOT NULL DEFAULT 'info',
    message    text NOT NULL DEFAULT '',
    payload    jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (run_id, seq)
);

CREATE TABLE IF NOT EXISTS perf_factor_results (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      uuid NOT NULL REFERENCES perf_runs (id) ON DELETE CASCADE,
    student_id  text NOT NULL,
    factor      text NOT NULL,
    score       double precision,
    interval    jsonb,
    status      text NOT NULL CHECK (status IN ('completed', 'not_available', 'fallback', 'pending')),
    provisional boolean NOT NULL DEFAULT false,
    features    jsonb NOT NULL DEFAULT '{}'::jsonb,
    warnings    jsonb NOT NULL DEFAULT '[]'::jsonb,
    versions    jsonb NOT NULL DEFAULT '{}'::jsonb,
    audit       jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, student_id, factor)
);

CREATE TABLE IF NOT EXISTS perf_assessment_results (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id         uuid NOT NULL REFERENCES perf_runs (id) ON DELETE CASCADE,
    team_ref       text NOT NULL,
    sprint_id      text NOT NULL,
    student_id     text NOT NULL,
    mark           double precision,
    mark_interval  jsonb,
    status         text NOT NULL CHECK (status IN ('provisional', 'final', 'pending_review')),
    factors        jsonb NOT NULL DEFAULT '{}'::jsonb,
    justification  jsonb NOT NULL DEFAULT '{}'::jsonb,
    flags          jsonb NOT NULL DEFAULT '[]'::jsonb,
    override       jsonb,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, student_id)
);
CREATE INDEX IF NOT EXISTS ix_perf_results_team_sprint ON perf_assessment_results (team_ref, sprint_id, student_id, created_at DESC);

CREATE TABLE IF NOT EXISTS perf_snapshots (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_ref        text NOT NULL,
    sprint_id       text NOT NULL,
    student_id      text NOT NULL,
    as_of           timestamptz NOT NULL,
    sprint_elapsed  double precision NOT NULL,
    mark            double precision,
    mark_interval   jsonb,
    factors         jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (team_ref, sprint_id, student_id, as_of)
);

CREATE TABLE IF NOT EXISTS perf_reviews (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      uuid NOT NULL REFERENCES perf_runs (id) ON DELETE CASCADE,
    student_id  text,
    kind        text NOT NULL,
    reason      text NOT NULL,
    title       text NOT NULL DEFAULT '',
    summary     text NOT NULL DEFAULT '',
    severity    text NOT NULL DEFAULT 'warn' CHECK (severity IN ('info', 'warn', 'critical')),
    form        jsonb NOT NULL DEFAULT '{}'::jsonb,
    answers     jsonb,
    evidence    jsonb NOT NULL DEFAULT '{}'::jsonb,
    status      text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'decided')),
    decision    jsonb,
    decided_by  text,
    decided_at  timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_perf_reviews_status ON perf_reviews (status, created_at);

CREATE TABLE IF NOT EXISTS perf_quizzes (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_ref        text NOT NULL,
    sprint_id       text NOT NULL,
    student_id      text NOT NULL,
    run_id          uuid REFERENCES perf_runs (id) ON DELETE SET NULL,
    n               integer NOT NULL DEFAULT 1 CHECK (n > 0),
    of              integer NOT NULL DEFAULT 1 CHECK (of > 0),
    type            text NOT NULL DEFAULT 'explain_behaviour',
    batch_id        text,
    question        text NOT NULL,
    snippet         text NOT NULL,
    file_path       text,
    line_range      jsonb,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    status          text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'extended', 'answered', 'expired')),
    deadline_at     timestamptz NOT NULL,
    extended_until  timestamptz,
    answer          text,
    answered_at     timestamptz,
    in_extension    boolean NOT NULL DEFAULT false,
    result          jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (team_ref, sprint_id, student_id, n)
);
CREATE INDEX IF NOT EXISTS ix_perf_quizzes_student ON perf_quizzes (student_id, status);

-- Same protection as the other Core API tables: the backend role owns them, browser roles get nothing.
ALTER TABLE perf_tracked_teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE perf_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE perf_run_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE perf_factor_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE perf_assessment_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE perf_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE perf_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE perf_quizzes ENABLE ROW LEVEL SECURITY;
