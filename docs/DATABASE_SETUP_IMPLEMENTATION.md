# Database Setup: Implementation Report

What was built to run the SELVIA backend on Supabase PostgreSQL, how it is secured, how the
shared Supabase database was set up, and what is still open.

Related guides:

- [SERVER_DATABASE_GUIDE.md](./SERVER_DATABASE_GUIDE.md): day-to-day reference for configuration,
  migrations, the guards and every script option.
- [SCHEMA_CHANGE_GUIDE.md](./SCHEMA_CHANGE_GUIDE.md): how to change a table after this setup.

No credentials, connection URLs, host names or project references appear in this document. Use
the placeholders in the `.env.example` files.

---

## 1. Status

| Area | Status |
| --- | --- |
| Core API tables (6) on Supabase | Created by migration `c9da91ebdddb`; verified against the models |
| Public schema security | Migration `4f6d2a9c8e1b` applied; row level security on, browser roles revoked; verified |
| Job queue schema (Procrastinate 3.10.0) | Installed through the guarded script; verified |
| Job queue security | Row level security on, browser roles revoked; verified (all PASS) |
| TLS to Supabase | `sslmode=verify-full` with the committed Supabase CA certificate; verified on every connection |
| Final preflight after the queue hardening | **Pending**: the last run was interrupted at the URL prompt before connecting |
| Starting the Core API and the worker against Supabase | **Pending** (section 9) |
| Supabase dashboard: turn off the Data API, review the Security Advisor | **Pending** (section 11) |
| Changes committed to Git | **No**: all changes are in the working tree, including `backend/certs/supabase-ca.crt` |

---

## 2. Architecture

```text
                                  ┌──────────────── Supabase ────────────────┐
┌──────────────────────────┐      │  ┌───────────────────────────┐           │
│ Core API (FastAPI)       │──────┼─▶│ Transaction pooler :6543  │──┐        │
│ request queries          │      │  └───────────────────────────┘  │        │
│ SERVER_DATABASE_URL      │      │                                 ▼        │
└──────────────────────────┘      │                          ┌────────────┐  │
┌──────────────────────────┐      │  ┌───────────────────┐   │ PostgreSQL │  │
│ Core API job publishing  │──────┼─▶│ Session pooler    │──▶│ 17         │  │
│ Worker (agentic_fw)      │──────┼─▶│ :5432             │   │ database   │  │
│ Alembic, queue scripts,  │──────┼─▶│                   │   │ "postgres" │  │
│ preflight                │      │  └───────────────────┘   └────────────┘  │
│ SERVER_DIRECT_URL        │      │                                          │
└──────────────────────────┘      └──────────────────────────────────────────┘
        all connections: TLS, sslmode=verify-full, CA = backend/certs/supabase-ca.crt
```

| Component | Folder | Connects with | Port | Purpose |
| --- | --- | --- | --- | --- |
| Core API requests | `backend/server` | `SERVER_DATABASE_URL` (SQLAlchemy + psycopg) | 6543 | Short request queries; the transaction pooler shares a few server connections among many clients |
| Core API job publishing | `backend/server` | `SERVER_DIRECT_URL` (Procrastinate) | 5432 | Puts jobs on the queue |
| Agent worker | `backend/agentic_framework` | `SERVER_DIRECT_URL` (Procrastinate) | 5432 | Takes jobs off the queue; needs session features (LISTEN/NOTIFY, advisory locks) |
| Alembic | `backend/server` | `SERVER_DIRECT_URL` | 5432 | Schema changes need a stable session |
| Queue scripts, preflight | `backend/server` | `SERVER_DIRECT_URL` or a hidden prompt | 5432 | Install, secure and check the schema |

All of them connect as the Supabase `postgres` role, which owns the tables (section 4).

---

## 3. Database objects

### Core API tables (Alembic)

| Table | Holds |
| --- | --- |
| `users` | Keycloak subject (unique), role (`student`/`lecturer`/`admin`), name, optional unique student number |
| `groups` | Group code (unique) and name |
| `group_members` | User and group membership, each pair once |
| `projects` | Group, creating lecturer, title, description |
| `project_documents` | Project, file name, content type, storage key (the file lives in object storage) |
| `agent_runs` | Background orchestration runs: request id, action, requester, scope ids, status, JSON response and error |
| `alembic_version` | The applied migration revision |

| Revision | Name | Does |
| --- | --- | --- |
| `c9da91ebdddb` | create core tables | Creates the six tables with named primary keys, unique, foreign key and check constraints, and indexes |
| `4f6d2a9c8e1b` | secure public schema | Turns on row level security for the six tables and `alembic_version`; revokes all access from `anon`, `authenticated` and `service_role`; stops new objects that `postgres` creates in `public` from granting them access. Its downgrade deliberately does nothing |

Conventions: enums are stored as VARCHAR with a check constraint (`string_enum`), JSON as JSONB,
constraint names follow the naming convention in `app/database/base.py`, and columns have no
database-side defaults.

### Job queue (Procrastinate 3.10.0)

Four tables (`procrastinate_jobs`, `procrastinate_events`, `procrastinate_periodic_defers`,
`procrastinate_workers`), their four sequences, two enum types, one composite type and 17
functions, all in `public`. Alembic never touches them: `include_object` in
`app/database/migrations.py` filters them out of autogenerate.

---

## 4. Security design

### What it protects against

Supabase publishes the `public` schema through its Data API (PostgREST) to the roles `anon`
(anyone with the public key), `authenticated` (any signed-in Supabase user) and `service_role`.
Without protection, anyone holding the project's public key could read or change the backend's
tables directly, bypassing the Core API and its Keycloak authorisation.

### Database layer

| Measure | Applied by | Effect |
| --- | --- | --- |
| Row level security on, not forced, no policies | Migration `4f6d2a9c8e1b`, `secure_queue_schema --apply` | Roles that are subject to row level security see no rows. The owner (`postgres`) is not affected, so the backend keeps working |
| Revoke all privileges from `PUBLIC`, `anon`, `authenticated`, `service_role` | Same | Needed because `service_role` has BYPASSRLS, and row level security never covers TRUNCATE, REFERENCES or TRIGGER |
| Revoke default privileges for objects `postgres` creates in `public` | Migration `4f6d2a9c8e1b` | New tables, sequences and functions no longer grant the browser roles access automatically. This is why the queue tables had no browser grants straight after installation |
| Revoke EXECUTE on the 17 queue functions | `secure_queue_schema --apply` | PostgreSQL lets `PUBLIC` run every new function by default |

No policies and no `FORCE ROW LEVEL SECURITY` were added; that would need a separately reviewed
requirement.

### Connection guards

Every command that can change the schema (Alembic, `install_queue_schema`, `secure_queue_schema`)
runs these checks **before opening a connection**. They live in `app/database/safety.py`.

| Guard | Refuses |
| --- | --- |
| Remote opt-in | Any non-local host unless `-x allow_remote=true` (Alembic) or `--allow-remote` (scripts) is passed |
| Remote downgrade | `downgrade` on a remote host unless `-x allow_remote_downgrade=true` is also passed |
| Schema change source | A remote URL taken from `SERVER_DATABASE_URL`, which happens only when `SERVER_DIRECT_URL` is unset |
| Transaction pooler | Any remote URL on port 6543 |
| TLS | A Supabase URL without `sslmode=verify-full`, or without an `sslrootcert` that is `system` or a readable PEM certificate file |

At runtime, the Core API engine (`app/database/session.py`) and the job queue connector
(`shared/queue.py`) refuse a Supabase URL without verified TLS. The health check then reports the
database as not connected, and the queue refuses to start.

`procrastinate --app=shared.queue.app schema --apply` is disabled (`GuardedSchemaManager` in
`shared/queue.py`), because it had no target checks. The only supported install route is
`python -m scripts.install_queue_schema`.

### TLS

`sslmode=verify-full` makes libpq check that the server's certificate is signed by the trusted CA
and was issued for the host in the URL. `sslmode=require` only encrypts and cannot detect an
impostor, so it is refused.

Supabase signs its database certificates with its own CA, which the operating system doesn't
trust, so the CA certificate is committed to the repository:

- File: `backend/certs/supabase-ca.crt`, downloaded from the Supabase dashboard (Project
  Settings > Database > SSL Configuration). It is public and contains no key.
- URL setting: `sslrootcert=../certs/supabase-ca.crt`. The path is relative to the current folder,
  so the Core API, Alembic and the scripts must run from `backend/server`, and the worker from
  `backend/agentic_framework`. Started from anywhere else, the URL is refused because the file
  isn't found.

TLS settings travel only in the URL, so `PGSSLMODE` and `PGSSLROOTCERT` never apply, and nothing
in the code overrides them.

### Secrets

- `.env` files are gitignored; only `.env.example` files with placeholders are committed.
- Output from the guards, scripts and health check never includes passwords, user names,
  certificate paths or complete URLs. Database errors show only the error class and SQLSTATE.
- The preflight and the local test commands read URLs through hidden prompts.
- The test fixture for `SERVER_TEST_DATABASE_URL` reports an invalid value without a traceback,
  because pytest tracebacks print argument values.

---

## 5. Implementation files

### Core API (`backend/server`)

| File | Purpose |
| --- | --- |
| `app/core/config.py` | Settings; loads `backend/server/.env` by its absolute path |
| `app/database/base.py` | Declarative base, naming convention, `string_enum`, `JSONType`, timestamps |
| `app/database/session.py` | Engine and sessions for `SERVER_DATABASE_URL`; TLS check before the engine exists; health check that hides driver messages |
| `app/database/safety.py` | All target and TLS guards (section 4) |
| `app/database/migrations.py` | `include_object`: Alembic only manages tables with a model |
| `app/models/` | `User`, `Group`, `GroupMember`, `Project`, `ProjectDocument`, `AgentRun` |
| `alembic/env.py` | Target selection (`-x db_url`, `SERVER_DIRECT_URL`, `SERVER_DATABASE_URL`) and the guards |
| `alembic/versions/` | `c9da91ebdddb` and `4f6d2a9c8e1b` |
| `scripts/supabase_preflight.py` | Read-only check of a Supabase database before and after migrating: identity, TLS, roles, tables against the models, Alembic state, row level security, grants, default privileges, queue, unexpected objects |
| `scripts/install_queue_schema.py` | Guarded install of Procrastinate's `schema.sql` in one transaction; does nothing if already installed |
| `scripts/secure_queue_schema.py` | `--check` (read-only report) and `--apply` (one transaction, re-verified before commit) for the queue objects |
| `conftest.py` | `test_database_url` fixture: only a local `*_test` database, never the application database |
| `.env.example` | Variables, precedence, guards and TLS, with placeholder URLs |

### Shared and worker

| File | Purpose |
| --- | --- |
| `backend/shared/src/shared/queue.py` | Procrastinate app: URL from `SERVER_DIRECT_URL`, else `SERVER_DATABASE_URL`; refuses an empty URL or unverified Supabase TLS; disables `schema --apply` |
| `backend/agentic_framework/worker.py` | Worker entry point |
| `backend/agentic_framework/.env.example` | The worker's `SERVER_DIRECT_URL`, with the TLS settings |
| `backend/certs/supabase-ca.crt` | Supabase CA certificate |

---

## 6. Configuration

| File | Variable | Value on Supabase |
| --- | --- | --- |
| `backend/server/.env` | `SERVER_DATABASE_URL` | Transaction pooler, port 6543 |
| `backend/server/.env` | `SERVER_DIRECT_URL` | Session pooler, port 5432 |
| `backend/agentic_framework/.env` | `SERVER_DIRECT_URL` | Session pooler, port 5432 |

URL format (placeholders only):

```text
postgresql+psycopg://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=verify-full&sslrootcert=../certs/supabase-ca.crt
```

- Special characters in the password must be URL-encoded (`@` becomes `%40`).
- Each URL sets `sslmode` and `sslrootcert` exactly once.
- Precedence: the Core API's requests use `SERVER_DATABASE_URL`. Alembic and the queue scripts
  use `-x db_url` or `--db-url`, then `SERVER_DIRECT_URL`, then `SERVER_DATABASE_URL`. The job queue
  uses `SERVER_DIRECT_URL`, then `SERVER_DATABASE_URL`. Real environment variables override `.env`.

---

## 7. Supabase setup: what was done

All commands ran from `backend/server`, against the session pooler on port 5432, with verified
TLS. Each phase started only after the previous one was verified.

| Phase | Command | Result |
| --- | --- | --- |
| A. Inspection | Code review, local test suite | Guards confirmed to run before any connection; Procrastinate's `schema.sql` matches the hardening script's table list |
| B. Read-only checks | `secure_queue_schema --check --allow-remote`, `alembic -x allow_remote=true current`, `supabase_preflight` | Fresh database: no Core API tables, no Alembic revision, no queue schema, nothing unexpected in `public`. Preflight: 13 PASS, 16 INFO, 0 WARN, 0 FAIL, 0 LIMITED |
| C. Migrations | `alembic -x allow_remote=true upgrade head` | Both revisions applied. `current` shows `4f6d2a9c8e1b (head)`. Preflight: 39 PASS, 11 INFO, 0 WARN, 0 FAIL, 0 LIMITED (tables match the models, row level security on, no browser-role access, default grants removed) |
| D. Queue install | `install_queue_schema --allow-remote` | First attempt refused with `permission denied` (see below); the check confirmed nothing had changed. After the fix: `Queue schema installed (Procrastinate 3.10.0)` |
| E. Queue hardening | `secure_queue_schema --apply --allow-remote`, then `--check` | Every line PASS, `Queue schema is secured`: row level security on all four tables, no browser-role privileges on tables or sequences, no EXECUTE on the 17 functions for `PUBLIC` or the browser roles, owner keeps full access |

### Issues found during setup

| Issue | Cause | Fix |
| --- | --- | --- |
| Connections refused with `sslmode=require` | The guard requires verified TLS | URLs switched to `sslmode=verify-full` with `sslrootcert` |
| `sslrootcert` file not found | Each person would need their own absolute path | The CA certificate is committed at `backend/certs/supabase-ca.crt` and referenced by a relative path |
| Queue install: `permission denied` (SQLSTATE 42501) | The installer set `search_path = pg_catalog, public`. PostgreSQL creates unqualified objects in the first listed schema, so Procrastinate's first `CREATE TYPE` targeted the system catalog, which only superusers can write | `search_path = public`; `pg_catalog` is still searched first implicitly, so built-ins can't be shadowed. Proven on the local non-superuser test database (19 passed) before retrying. The integration test now also checks that the queue types land in `public` |
| Local test URL rejected, and pytest printed it in a traceback | The URL was missing the scheme and credentials; the fixture failure included a traceback | The fixture now fails without a traceback |

---

## 8. Team onboarding

For a teammate joining after this setup:

1. Pull the repository. The CA certificate comes with it.
2. In `backend/server` and `backend/agentic_framework`, run `uv sync`.
3. Copy each `.env.example` to `.env` in the same folder and fill in the Supabase password and
   project reference. Get these from the project owner through a private channel, never through
   Git or a group chat.
4. Keep `sslrootcert=../certs/supabase-ca.crt` exactly as in the template.
5. Always start the Core API from `backend/server` and the worker from `backend/agentic_framework`.
6. Check the connection from `backend/server`:

   ```powershell
   uv run python -c "from app.database import check_db_connection; print('Connected:', check_db_connection())"
   ```

Teammates never run migrations or queue scripts against Supabase. Schema changes go through
[SCHEMA_CHANGE_GUIDE.md](./SCHEMA_CHANGE_GUIDE.md).

---

## 9. Running against Supabase (Phase F, pending)

1. Final read-only check, from `backend/server`, on its own line:

   ```powershell
   uv run python -m scripts.supabase_preflight
   ```

   Expected: 0 WARN, 0 FAIL, 0 LIMITED, with the queue reported as installed and secured.

2. Start the Core API from `backend/server`:

   ```powershell
   uv run uvicorn app.main:app --reload --port 8002
   ```

   `GET http://localhost:8002/health` must return `"database_connected": true`.

3. Start the worker from `backend/agentic_framework`:

   ```powershell
   uv run python -m worker
   ```

   It must log `Starting Procrastinate worker` and keep running without errors.

4. Run one job end to end through the Core API and check that it reaches `succeeded` in
   `agent_runs`.

What to watch for: the Core API's requests go through the transaction pooler (port 6543), where
each transaction may land on a different server connection. If intermittent errors about
prepared statements appear, psycopg's automatic prepared statements need to be turned off for
that engine. Report it rather than switching the URL to port 5432.

---

## 10. Testing

| Suite | Command (from the service folder) | Result |
| --- | --- | --- |
| Core API, no database | `uv run pytest -q` in `backend/server` | 597 passed, 6 skipped |
| Queue install on real PostgreSQL | `tests/test_install_queue_schema.py` with `SERVER_TEST_DATABASE_URL` | 19 passed, 0 skipped |
| Migration round trip and job API on real PostgreSQL | `tests/test_migrations.py`, `tests/test_jobs_api.py` with `SERVER_TEST_DATABASE_URL` | Not yet run against the local test database |

The six skipped tests need `SERVER_TEST_DATABASE_URL`: a local, disposable `*_test` database on
`localhost`. They never fall back to the application database. Most of the guard tests use fake
engines, and the TLS tests include a local fake TLS server to prove that `verify-full` rejects a
certificate from another CA or for another host.

---

## 11. Open items

1. **Final preflight** after Phase E (section 9, step 1).
2. **Phase F**: start the Core API and the worker against Supabase and run one job end to end.
3. **Supabase dashboard**: turn off the Data API if the frontend doesn't use it (the backend
   doesn't), and review the Security Advisor.
4. **Real-database tests**: run the migration round trip and the job API test against the local
   test database.
5. **Commit** the changes, including `backend/certs/supabase-ca.crt`, after review.
6. **Least privilege (future)**: the Core API, the worker and the migrations all connect as
   `postgres`, which owns the tables and has BYPASSRLS. A separate runtime role with only the
   privileges the backend needs would reduce the impact of a leaked runtime password.
7. **`supabase_admin` default privileges**: objects that `supabase_admin` creates in `public` still
   grant the browser roles access by default. Only Supabase can change this. It doesn't affect
   this project's objects, which `postgres` creates.
8. **Working folder**: the relative certificate path ties each service to its own folder. Running
   from elsewhere, for example in a container with another layout, needs an absolute path in that
   environment's `.env`.
