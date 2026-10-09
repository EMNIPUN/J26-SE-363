# Server Database & Migration Guide

This guide explains the database architecture, configuration, and migration commands for developers working on the SELVIA backend server.

See also: [DATABASE_SETUP_IMPLEMENTATION.md](./DATABASE_SETUP_IMPLEMENTATION.md) (what was built and how Supabase was set up) and [SCHEMA_CHANGE_GUIDE.md](./SCHEMA_CHANGE_GUIDE.md) (changing a table after setup).

---

## 1. Database Architecture & Dual-Port Strategy

The backend server connects to **Supabase Cloud PostgreSQL** using a dual-connection architecture:

```
                            ┌──────────────────────────────────────────────┐
                            │               SUPABASE CLOUD                 │
                            │                                              │
┌───────────────────────┐   │   ┌────────────────────────┐   ┌──────────┐  │
│ FastAPI Web Server    │───┼──▶│ Supavisor Pooler: 6543 │──▶│ Postgres │  │
│ (Runtime Queries)     │   │   │ (Transaction Mode)     │   │ Engine   │  │
└───────────────────────┘   │   └────────────────────────┘   └──────────┘  │
                            │                                      ▲       │
┌───────────────────────┐   │   ┌────────────────────────┐         │       │
│ Alembic Migrations    │───┼──▶│ Supavisor Pooler: 5432 │─────────┘       │
│ (Schema DDL & Locks)  │   │   │ (Session Mode)         │                 │
└───────────────────────┘   │   └────────────────────────┘                 │
                            └──────────────────────────────────────────────┘
```

* **Port `6543` (Transaction Pooler)** $\rightarrow$ Used by the **FastAPI Web Server** (`SERVER_DATABASE_URL`). Multiplexes thousands of concurrent API requests across shared connections to prevent connection exhaustion.
* **Port `5432` (Session Mode)** $\rightarrow$ Used by **Alembic Migrations** (`SERVER_DIRECT_URL`). Provides dedicated session-level locks required for DDL statements (`CREATE TABLE`, `ALTER TABLE`, index creation).

> [!NOTE]
> Developers **do not need to pick or swap ports manually**. Alembic automatically prioritizes `SERVER_DIRECT_URL` (Port 5432), while FastAPI automatically uses `SERVER_DATABASE_URL` (Port 6543).

---

## 2. Environment Configuration

Each service has its own gitignored `.env` file, copied from its own template. There is no shared
`backend/.env.example` any more:

| File | Template | Database variables |
| --- | --- | --- |
| `backend/server/.env` | `backend/server/.env.example` | `SERVER_DATABASE_URL`, `SERVER_DIRECT_URL`, or the `SERVER_POSTGRES_*` parts |
| `backend/agentic_framework/.env` | `backend/agentic_framework/.env.example` | `SERVER_DIRECT_URL` only (the worker's job queue); the AI Backend's own `AI_BACKEND_*` settings have no database |

```env
# backend/server/.env (placeholders only)

# --- Option A: Supabase ---
SERVER_DATABASE_URL=postgresql+psycopg://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=verify-full&sslrootcert=../certs/supabase-ca.crt
SERVER_DIRECT_URL=postgresql+psycopg://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=verify-full&sslrootcert=../certs/supabase-ca.crt

# --- Option B: local Docker PostgreSQL (port 5433) ---
# SERVER_DATABASE_URL=postgresql+psycopg://selvia_server_user:[YOUR_LOCAL_PASSWORD]@localhost:5433/selvia_server_db
# SERVER_DIRECT_URL=postgresql+psycopg://selvia_server_user:[YOUR_LOCAL_PASSWORD]@localhost:5433/selvia_server_db
```

**What each variable is for:**

| Variable | Used by | On Supabase |
| --- | --- | --- |
| `SERVER_DATABASE_URL` | Core API requests (SQLAlchemy). Also the last fallback for Alembic, the queue scripts and the job queue | Transaction pooler, port 6543 |
| `SERVER_DIRECT_URL` | Schema changes: Alembic, `scripts.install_queue_schema`, `scripts.secure_queue_schema`. Also the job queue (Core API publishing and the worker) | Session pooler, port 5432, or a direct connection if your project supports it. Never port 6543 |
| `SERVER_POSTGRES_*` | Builds `SERVER_DATABASE_URL` when it is unset or blank (host defaults to `localhost`, port to 5433) | Not used |
| `SERVER_TEST_DATABASE_URL` | Only the tests that need a real database, and only from the shell (section 5) | Never: it must be a local `*_test` database |

**Precedence, as implemented:**

- Core API requests: `SERVER_DATABASE_URL`, else the `SERVER_POSTGRES_*` parts (`app/core/config.py`).
- Alembic: `-x db_url=...`, then `SERVER_DIRECT_URL`, then `SERVER_DATABASE_URL` (`alembic/env.py`).
  The two queue scripts use the same order with `--db-url`. All three read the Core API settings,
  which load `backend/server/.env` by its absolute path, so the current folder doesn't matter.
- Job queue: `SERVER_DIRECT_URL`, then `SERVER_DATABASE_URL`, read from the process environment
  after loading `.env` from the **current folder** (`shared/queue.py`). Start the Core API from
  `backend/server/` and the worker from `backend/agentic_framework/`.
- Real environment variables beat the `.env` file everywhere. A blank value counts as unset.

`SERVER_DIRECT_URL` must be set explicitly before any remote schema change. If it is unset,
Alembic and the queue scripts would fall back to `SERVER_DATABASE_URL`; for a remote database
they refuse that fallback, and any URL on port 6543, even with the remote opt-in (section 3B).

### TLS for Supabase connections

Every Supabase URL, in both files, must end with
`?sslmode=verify-full&sslrootcert=../certs/supabase-ca.crt`:

- The Supabase CA certificate is committed at `backend/certs/supabase-ca.crt`, so the whole team
  uses the same file. It is public (it contains no key or password). It was downloaded from the
  Supabase dashboard (Project Settings → Database → SSL Configuration); replace it from there only,
  and only if Supabase rotates its CA.
- The relative path is resolved from the **current folder**. `backend/server/` (Core API, Alembic,
  scripts) and `backend/agentic_framework/` (worker) both sit next to `backend/certs/`, so the same
  path works in both `.env` files as long as each service starts from its own folder. Started from
  anywhere else, the checks below refuse the URL because the file isn't found.
- `sslrootcert=system` uses the operating system's trust store, which normally doesn't contain the
  Supabase CA.
- `sslmode=verify-full` makes libpq check that the server's certificate chains to that CA and was
  issued for the host in the URL. `require` only encrypts and `verify-ca` doesn't check the host
  name, so neither can tell the real server from an impostor.

The settings travel only in the URL. SQLAlchemy passes `sslmode` and `sslrootcert` to psycopg
unchanged, and the job queue gives the URL to libpq as is. Because both are in the URL,
`PGSSLMODE` and `PGSSLROOTCERT` never apply. Nothing in the code adds or overrides `sslmode`.

What is checked, before any connection is opened, for a URL whose host (including a `host` URL
parameter) ends in `.supabase.com` or `.supabase.co`:

| Where | Check | When it fails |
| --- | --- | --- |
| Core API (`get_engine`, `app/database/session.py`) | `sslmode=verify-full`, and `sslrootcert` is `system` or a readable file containing a PEM certificate | `DatabaseConfigurationError`; `/health` reports the database as not connected |
| Alembic, `scripts.install_queue_schema`, `scripts.secure_queue_schema` | Same check (`check_tls` in `app/database/safety.py`) | `UnsafeDatabaseTarget` / exit code 2 |
| Job queue (Core API startup and the worker, `shared/queue.py`) | `sslmode=verify-full` and a non-empty `sslrootcert`; libpq itself checks the file when connecting | `QueueConfigurationError`; the Core API or the worker doesn't start |
| Preflight (`scripts.supabase_preflight`) | Its own, stricter check (section 3G) | Exit code 2 |

Error messages never contain the URL, the host, the user name or the certificate path. The
health check logs only the exception class and SQLSTATE of a failed connection, never the
driver's message. Local and other non-Supabase databases keep whatever `sslmode` their URL sets.
This is a configuration check: only a real connection shows that the certificate actually
matches the server.

A missing or blank URL is an error, never a silent fallback to a default local database:

- The job queue (Core API startup and the worker) uses `SERVER_DIRECT_URL`, else
  `SERVER_DATABASE_URL`. If both are unset or blank, opening the queue raises
  `QueueConfigurationError` naming both variables.
- The Core API database session uses `SERVER_DATABASE_URL`, else the `SERVER_POSTGRES_*` parts.
  If neither is configured, `get_engine()` raises `DatabaseConfigurationError` and `/health`
  reports the database as not connected.

---

## 3. Database Migrations (Alembic)

All commands are executed from the `backend/server/` directory using `uv run` (the server has its own `pyproject.toml`, `uv.lock` and `.venv`; run `uv sync` there first).

| File | Purpose |
|---|---|
| `backend/server/alembic.ini` | Alembic settings (no database URL in it) |
| `backend/server/alembic/env.py` | Picks the target database and the models |
| `backend/server/alembic/versions/` | Migration scripts, one per schema change |
| `backend/server/app/models/` | SQLAlchemy models; every model is imported in `app/models/__init__.py` |
| `backend/server/app/database/migrations.py` | Filter that keeps Alembic away from tables it doesn't own |

### A. Tables managed by the Core API

The first migration (`create core tables`) creates:

| Table | Holds |
|---|---|
| `users` | Keycloak subject (`keycloak_sub`, unique), role (`student`/`lecturer`/`admin`), name, optional unique student number |
| `groups` | Stable group code (unique, e.g. `J26-SE-363`) and name |
| `group_members` | User ↔ group membership; each pair at most once |
| `projects` | Required group, creating lecturer, title (not unique), description |
| `project_documents` | Project, original filename, content type and a storage reference (`storage_key`); the file itself lives in object storage, never in the database |
| `agent_runs` | Background orchestration runs: request id, action, requester, scope ids, status (`queued`/`running`/`succeeded`/`failed`), JSON response and error |

The second migration (`secure public schema`) creates no tables; it locks the tables down (see F).

**Alembic never touches Procrastinate's tables** (`procrastinate_*`, the job queue in the same
database) or any other table without a model: `include_object` in
`app/database/migrations.py` filters them out, so autogenerate never creates, alters or drops them.
Procrastinate manages its own schema.

### B. Which database a command targets

`alembic/env.py` uses, in order: `-x db_url=...` on the command line, then `SERVER_DIRECT_URL`,
then `SERVER_DATABASE_URL` from `backend/server/.env`. Every online command logs the target first
(host, port and database only; never the user name or password), for example:

```text
INFO  [alembic.env] Target database: postgresql localhost:5432/selvia_migration_test
```

**Remote databases are refused by default.** Online commands (`upgrade`, `downgrade`, `stamp`,
`current`, ...) only run against `localhost`, `127.0.0.1` or `::1`. Any other host, including
Supabase, stops with `UnsafeDatabaseTarget` before a connection is opened, whichever of the three
sources the URL came from. To deliberately change a remote database, add `-x allow_remote=true`:

```bash
uv run alembic -x allow_remote=true upgrade head
```

**`allow_remote=true` does not cover `downgrade`.** A downgrade drops tables and their data, so on
a remote database it is refused even with `allow_remote=true`. It needs a second, separate opt-in,
and the command logs a warning when it is used:

```bash
uv run alembic -x allow_remote=true -x allow_remote_downgrade=true downgrade -1
```

`allow_remote_downgrade=true` on its own is not enough either. Local databases need neither flag.

**Remote schema changes need the session URL.** Even with `allow_remote=true`, a remote target is
refused before connecting when:
- it came from `SERVER_DATABASE_URL`, which is only used when `SERVER_DIRECT_URL` is unset. That
  is the Core API's own URL, on Supabase the transaction pooler;
- or it uses port 6543, Supabase's transaction pooler, whichever source it came from. The pooler
  can hand each transaction to a different server session, which DDL (schema changes) can't rely on.

Set `SERVER_DIRECT_URL` to the session pooler URL (port 5432), or pass it with `-x db_url=...`.
Local databases are not affected.

**A Supabase target must verify TLS.** It is also refused before connecting unless the URL sets
`sslmode=verify-full` and a usable `sslrootcert` (section 2, "TLS for Supabase connections").

A URL without a host, or with a `host`/`hostaddr`/`service` query parameter pointing elsewhere,
counts as remote. `--sql` (offline SQL generation) never connects and is never blocked. A blank
value (`SERVER_DIRECT_URL=`) counts as unset, so the next source is used. The guard lives in
`app/database/safety.py`.

### C. Safe workflow on a local development database

1. Start the local server database (host port 5433; needs `SERVER_POSTGRES_DB`, `SERVER_POSTGRES_USER`
   and `SERVER_POSTGRES_PASSWORD` in the root `.env`):
   ```bash
   docker compose up -d server-postgres
   ```
2. Point `backend/server/.env` at it (Option B in section 2), or pass the URL for one command with
   `-x "db_url=postgresql+psycopg://<user>:<password>@localhost:5433/<db>"` (the password then
   ends up in your shell history, so prefer the `.env` file).
3. Preview the SQL without connecting to any database:
   ```bash
   uv run alembic upgrade head --sql
   ```
4. Check the target and current revision:
   ```bash
   uv run alembic current
   ```
5. Apply all migrations:
   ```bash
   uv run alembic upgrade head
   ```
6. Revert, **only on a disposable development database** (this deletes the tables and their data):
   ```bash
   uv run alembic downgrade -1     # undo the last migration
   uv run alembic downgrade base   # undo every Core API migration
   ```

Rules:

- Never run `downgrade` against the shared Supabase database. The guard refuses it unless
  `-x allow_remote_downgrade=true` is also passed; reserve that flag for an agreed recovery with a
  fresh backup.
- Apply `upgrade` to the shared Supabase database (`-x allow_remote=true`) only after the
  migration has been reviewed and the team has agreed.
- Never drop or recreate the database or the `public` schema to "fix" a migration; write a new
  migration instead.

### D. Generate a new migration

The full workflow, from changing a model to applying the migration on Supabase, with recipes for
common changes, is in [SCHEMA_CHANGE_GUIDE.md](./SCHEMA_CHANGE_GUIDE.md).

Run it against a local database that is already at `head`, then review the generated file before
committing:

```bash
uv run alembic revision --autogenerate -m "add sprints table"
```

Review checklist: one `ck_<table>_<column>` check constraint per enum column (autogenerate may
render a duplicate unnamed one; delete it), `postgresql.JSONB(astext_type=sa.Text())` rather than
`Text()`, and no operation on tables you didn't change. **A new table needs row level
security:** add `op.execute("ALTER TABLE <table> ENABLE ROW LEVEL SECURITY")` to the same
migration (autogenerate never adds it), and revoke browser-role access if the table was created
by a role whose default privileges still grant it (see F). Then run the migration tests
(section 5); `test_every_model_table_and_the_version_table_get_rls` fails for any model table
without an RLS statement.

### E. Status and history

```bash
uv run alembic current
uv run alembic history --verbose
```

### F. Database security: RLS, browser roles and the job queue

Supabase exposes the `public` schema through its Data API to the roles `anon`, `authenticated`
and `service_role`, and by default gives them full access to every new table. SELVIA doesn't use
the Data API (the frontend signs in with Keycloak and only calls the Core API), so these roles
must not be able to read or change anything.

**The `secure public schema` migration (`4f6d2a9c8e1b`)**, applied by `alembic upgrade head`:

- enables row level security on the six Core API tables and `alembic_version`, without
  `FORCE` and without policies. With no policy, a role that has privileges on a table still sees
  no rows, unless it owns the table, is a superuser or has the `BYPASSRLS` attribute. The
  backend connects as the owner, so it keeps working. **Keep it that way:** the tables must stay
  owned by the role the backend and migrations connect as;
- revokes all table privileges from `anon`, `authenticated` and `service_role`. Each revoke is
  skipped when the role doesn't exist, so on plain local PostgreSQL only RLS is enabled;
- revokes the default privileges those roles would get on future tables, sequences and functions
  that the migrating role creates in `public`;
- never touches other schemas, the backend role or Procrastinate's objects, and does nothing on
  SQLite;
- has a downgrade that deliberately does nothing: `downgrade` past it neither turns RLS off nor
  gives access back. Undoing it needs a new, reviewed migration.

**What RLS does not cover.** RLS is one layer, not a complete access control:

- Superusers and roles with `BYPASSRLS` ignore it completely. Supabase's `service_role` is
  expected to have `BYPASSRLS`, but this project's actual role settings have **not been
  verified yet**; check `rolbypassrls` in `pg_roles` before relying on anything. For such roles
  only the revoked privileges keep them out.
- RLS filters rows for `SELECT`, `INSERT`, `UPDATE` and `DELETE` only. It does not restrict
  `TRUNCATE`, `REFERENCES` or `TRIGGER`; only privileges (grants and revokes) do.
- RLS says nothing about who may call the Core API: that is the application's authorization
  (Keycloak roles checked by the API). Which schemas Supabase exposes over HTTP is a separate
  setting (the Data API).

So the protection is the combination: RLS, revoked privileges for the browser roles,
application authorization, and turning off the Data API. None of them alone secures every access
path.

After this, the Supabase `service_role` key can't reach these tables through Supabase client
libraries either, because its privileges are revoked. Nothing in SELVIA uses it today; use the
Core API instead.

**The job queue is secured separately.** Alembic never manages Procrastinate's objects, so
`scripts/secure_queue_schema.py` does it: RLS (not forced, no policies) on the four
`procrastinate_*` tables, all privileges on those tables and their sequences revoked from
`PUBLIC` and the three browser roles, and `EXECUTE` on the `procrastinate_*` functions revoked
from the same grantees. Revoking from `PUBLIC` as well as the browser roles is intentional and
approved: every role is a member of `PUBLIC`, so a `PUBLIC` grant would otherwise reopen access.
The owner, which the Core API and the worker connect as, keeps full access. It refuses to change anything if the queue tables are missing, if it finds objects it
doesn't expect (views, extra tables, policies, forced RLS, `SECURITY DEFINER` functions, objects
owned by another role) or if it is connected as a browser role. `--apply` runs in one
transaction, re-checks everything before committing, and rolls back if a check fails; running it
again changes nothing. A missing permission record for an existing browser role counts as a
FAIL, never as "no access". Database errors are reported as the error class and SQLSTATE only;
server messages are never printed because they can contain the user name or host.

It uses the same target as Alembic (`--db-url`, then `SERVER_DIRECT_URL`, then
`SERVER_DATABASE_URL`), prints the target without credentials, and refuses non-local databases
unless `--allow-remote` is passed, in both modes. Like Alembic, it also refuses a remote target
that came from `SERVER_DATABASE_URL` or uses port 6543, even with `--allow-remote`, and a
Supabase URL without `sslmode=verify-full` and `sslrootcert`:

```bash
uv run python -m scripts.secure_queue_schema --check     # read-only PASS/FAIL report, exit 1 on any FAIL
uv run python -m scripts.secure_queue_schema --apply     # secure the queue objects
uv run python -m scripts.secure_queue_schema --check --allow-remote   # same, on Supabase
```

**Installing the queue schema: `scripts.install_queue_schema` only.** This is the only supported
way to create Procrastinate's tables, functions and types:

```bash
uv run python -m scripts.install_queue_schema                  # local database
uv run python -m scripts.install_queue_schema --allow-remote   # Supabase, only with approval (section 3H)
```

- **Target:** `--db-url`, then `SERVER_DIRECT_URL`, then `SERVER_DATABASE_URL` from the Core API
  settings, as for Alembic. The current folder doesn't choose the credentials.
- **Checks before connecting** (exit code 2, nothing opened): the URL must be PostgreSQL; a
  non-local database needs `--allow-remote`; a remote URL that came from `SERVER_DATABASE_URL` or
  uses port 6543 is refused even with `--allow-remote`; a Supabase URL needs
  `sslmode=verify-full` and a usable `sslrootcert`. These are the same helpers Alembic uses.
- **Install:** in one transaction, with `search_path` set to `public` and a 10 s lock timeout,
  it runs the `schema.sql` of the installed Procrastinate version. If
  `public.procrastinate_jobs` already exists it changes nothing and exits 0. A database error
  rolls everything back and prints only the error class and SQLSTATE (exit code 1).
- **Output:** the target without credentials and where it came from, for example
  `Target database: postgresql localhost:5432/selvia_migration_test (from --db-url)`.

**`procrastinate --app=shared.queue.app schema --apply` is disabled.** The shared app's schema
manager (`shared/queue.py`) refuses to apply the schema, whether through the Procrastinate CLI or
code calling `app.schema_manager.apply_schema()`. The command exits with code 1 and a message
pointing to `scripts.install_queue_schema`. `schema --read` and `schema --migrations-path` still
work. Remaining limitations:

- The Procrastinate CLI opens the app's normal queue connection, the same one the worker uses,
  before it reaches the schema command. So a direct invocation still connects to whatever the
  current folder's `.env` points at, and libpq connection errors are printed by Procrastinate
  unfiltered. No schema statement is sent.
- The guard only covers the `shared.queue.app` app. Applying `procrastinate schema --read` output
  with `psql`, another Procrastinate app, or `SchemaManager` on a hand-made connector bypasses
  it (the job API test does this, on the disposable test database only). Don't do that against a
  shared database.

**Rerun `scripts.secure_queue_schema` after every Procrastinate upgrade** (and after any
Procrastinate schema migration): new versions can add functions or tables that start with the
default grants. If an upgrade adds objects the script doesn't know, `--apply` refuses; update
`QUEUE_TABLES` in the script after reviewing the new schema. Procrastinate's upgrade migrations
(`procrastinate schema --migrations-path`) aren't covered by `scripts.install_queue_schema`;
review and apply them like any other remote schema change.

**Order on a new local database** (from `backend/server/`): `uv run alembic upgrade head`, then
`uv run python -m scripts.install_queue_schema`, then `uv run python -m scripts.secure_queue_schema
--check`, `--apply` and `--check` again. For Supabase, follow section 3H.

**Turning off the Data API is not a substitute for RLS and the revokes.** The toggle only
stops PostgREST from serving the schema; the browser roles keep their privileges in the database,
and anyone who later re-enables the API, exposes another schema or connects as one of those roles
would get them back. The revokes and RLS protect the data inside the database; turning off the
Data API is an extra layer on top, and application authorization in the Core API is still
required.

### G. Read-only preflight before migrating Supabase

`scripts/supabase_preflight.py` inspects the target database and changes nothing. Run it with the
URL that `alembic upgrade` will use (the session pooler, port 5432), and type the URL and the
project reference at the hidden prompts:

```powershell
cd backend/server
uv run python -m scripts.supabase_preflight
```

> [!IMPORTANT]
> Don't type `$env:SELVIA_PREFLIGHT_DATABASE_URL = "postgresql://..."` in PowerShell: PSReadLine
> saves every command line, password included, to its history file
> (`(Get-PSReadLineOption).HistorySavePath`). Use the hidden prompt. If you need the variable,
> for example to run the script twice, read it without echoing and remove it afterwards:
>
> ```powershell
> $env:SELVIA_PREFLIGHT_DATABASE_URL = [Net.NetworkCredential]::new('', (Read-Host 'Database URL' -AsSecureString)).Password
> uv run python -m scripts.supabase_preflight
> Remove-Item Env:SELVIA_PREFLIGHT_DATABASE_URL
> ```

#### Connection and TLS

- **Target input:** the URL comes only from `SELVIA_PREFLIGHT_DATABASE_URL` or, when that is
  unset, a hidden prompt. The expected project reference comes from
  `SELVIA_PREFLIGHT_EXPECTED_PROJECT_REF` or a hidden prompt. There is no fallback to
  `SERVER_DIRECT_URL`, `SERVER_DATABASE_URL` or any `.env` file. The script never imports the Core
  API settings.
- **Target checks before connecting:** every host, including any `host` or `hostaddr` URL
  parameter, must be a Supabase host, and the project reference must match the expected one.
  Otherwise the script exits with code 2. A refused host is never printed, since a malformed one
  can contain the project reference or a private IP address: the message only says that a host in
  the URL is not an accepted Supabase host and that host details are omitted.
- **TLS:** add the committed CA certificate (`backend/certs/supabase-ca.crt`, section 2) to the
  Session pooler connection string copied from the dashboard's **Connect** panel (port 5432), and
  run the script from `backend/server/` so the relative path resolves:

  ```text
  postgresql://postgres.[PROJECT_REF]:[PASSWORD]@[SESSION_POOLER_HOST]:5432/postgres?sslmode=verify-full&sslrootcert=../certs/supabase-ca.crt
  ```

  Before connecting,
  the script checks that the file exists, can be read, and contains a PEM certificate (a
  `-----BEGIN CERTIFICATE-----` line, the only format libpq reads). The path and the file's
  contents are never printed.

  | `sslmode` | Result |
  | --- | --- |
  | `verify-full` with `sslrootcert` | PASS: the certificate chain and the host name are verified |
  | `verify-ca` | Refused. With `--allow-unverified-tls`, accepted as a WARN: the chain is verified, but not the host name, so any server holding a certificate from the same CA would be accepted |
  | `require` | Refused. With `--allow-unverified-tls`, accepted as a WARN: the connection is encrypted but the server isn't authenticated |
  | anything else, or missing | Refused |

  `sslmode` and `sslrootcert` are handed to libpq unchanged; the script does no TLS itself. With
  `verify-full`, libpq checks during the connection that the server's certificate chains to
  `sslrootcert` and was issued for the host in the URL. If either check fails, the connection
  fails before libpq sends its startup packet, so the password is never sent. The script then
  prints `the server certificate could not be verified ... while connecting` and exits with code
  1. Don't fall back to `verify-ca` or `require`: check that the host was copied from the
  dashboard and that the certificate is the project's current CA.
  `tests/test_supabase_preflight.py` exercises this against a local fake TLS server, with a
  certificate from another CA, a certificate for another host name, and a correct one.

  `sslrootcert=system` uses the operating system's trust store. It only works if that store
  contains the Supabase CA, which it normally doesn't.
- **libpq environment variables:** the script refuses to run while `PGHOSTADDR` (connects to
  another IP address), `PGSERVICE`, `PGSERVICEFILE` (apply service-file settings) or `PGOPTIONS`
  (changes session settings such as `search_path` or the role) is set, and when the URL sets
  `service` or `options`. It names the variable but never prints its value. Unset it in that shell
  only (`Remove-Item Env:PGOPTIONS`).

  Other libpq variables still apply to anything the URL leaves out. The URL must contain a host,
  `sslmode` and `sslrootcert`, so `PGHOST`, `PGSSLMODE` and `PGSSLROOTCERT` never apply. But if the
  URL has no port, user, database or password, libpq takes them from `PGPORT`, `PGUSER`,
  `PGDATABASE`, `PGPASSWORD` or the `.pgpass` file:
  - a database from `PGDATABASE` is caught by the identity check;
  - a user from `PGUSER` shows up as the role you're asked to confirm;
  - a port from `PGPORT`, such as the transaction pooler's 6543, isn't noticed, because the pooler
    warning only looks at the URL.

  So write the port (5432), user and database explicitly in the URL, and before running check that
  `Get-ChildItem Env:PG* | Select-Object Name` lists nothing (it shows names, not values).
- **Identity:** in a `READ ONLY` transaction, it prints and checks the database name (`postgres`
  unless `--expect-database` says otherwise), the role, the server version, the current schema,
  the `search_path` (refused if `pg_catalog` comes after another schema, since objects there could
  replace built-in operators and types), and Supabase's `auth`/`storage` schemas and browser
  roles. Then it asks you to confirm. `--yes` skips only the question. The second transaction
  re-reads the identity and stops if anything changed.
  - The connected database role (`current_user`) and the session role are printed on purpose, so
    you can confirm them. On a direct connection the role usually has the same name as the URL's
    user; the URL itself and its user field (on the pooler, `postgres.<project-ref>`) are never
    printed.
  - The `search_path` is checked after the identity values are read, but before anything else. Those
    first reads use unqualified operators, so a hostile `search_path` set on the role could falsify
    the printed identity values (inside the read-only transaction) before it is refused.

#### What is checked

A second `READ ONLY` transaction, rolled back at the end, reads only the PostgreSQL catalog and
`public.alembic_version`. Catalog functions are called as `pg_catalog.<function>`. Below, "browser
roles" means `anon`, `authenticated` and `service_role` plus every other role the Data API can
switch to (see the next point), and every access check covers all of them.

- **Roles the Data API can switch to:** the Data API logs in as `authenticator` and runs each
  request after `SET ROLE` to the role named in the JWT. The script reads every grant in
  `pg_auth_members` and follows them from `authenticator`, through nested memberships, to every
  role it can `SET ROLE` to. From PostgreSQL 16 each grant in the chain must have the `SET` option;
  before 16 any membership counts. Roles that `authenticator` can't reach aren't treated as browser
  roles, whatever privileges they have.
  - PASS when it reaches no role besides the three above; INFO listing any others, which are then
    checked like them.
  - FAIL when `authenticator` is a superuser (it could switch to any role), when it reaches a
    superuser, or when it reaches the connection, Core API or worker role. WARN when it reaches a
    role with `BYPASSRLS`.
  - LIMITED (blocking) when the memberships can't be read, or when `authenticator` doesn't exist
    although the browser roles do: the role set is then unknown. Without `authenticator` and
    without browser roles (not a Supabase database, such as `--local-test`) this is only an INFO.
- **Roles:** for the connected role, `--app-role` and `--worker-role` (all default to the connected
  role) and the browser roles: superuser, `BYPASSRLS`, login, `USAGE`/`CREATE` on schema `public`,
  and whether a role can act as a table owner.
- **Core API tables and `alembic_version`:**
  - definitions against the models: column types, nullability and defaults (none expected);
    identity and generated columns; primary key, unique and foreign key columns; foreign key
    targets, `ON DELETE`/`ON UPDATE` and `MATCH`; check constraint values; `DEFERRABLE` and `NOT
    VALID`; index columns, uniqueness, method, expressions, partial-index conditions and validity;
  - owner, RLS on, `FORCE ROW LEVEL SECURITY` off, and policies (none expected);
  - direct table and column grants to every grantee, including `PUBLIC`;
  - effective privileges, including those inherited through membership and `PUBLIC`: `SELECT`,
    `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES` and `TRIGGER` on the table, and `SELECT`,
    `INSERT`, `UPDATE` and `REFERENCES` on any column;
  - the recorded revision against this repository.
- **Procrastinate:**
  - tables, functions, types, triggers and indexes against the installed version's `schema.sql`
    (by name);
  - the tables' RLS, policies and privileges, as above;
  - `USAGE`, `SELECT` and `UPDATE` on sequences owned by a queue table or named `procrastinate_*`;
  - `EXECUTE` on every `procrastinate_*` routine for `PUBLIC` and the browser roles, and whether
    the worker role can execute them;
  - `SECURITY DEFINER` routines (Procrastinate 3.10 defines none).
- **Every other relation in `public`** (tables, partitioned tables, views, materialized views,
  foreign tables and sequences): direct grants to `PUBLIC`, and effective table, column and
  sequence privileges of the browser roles.
- **Every other routine in `public`** (functions, procedures, aggregates and window functions):
  `EXECUTE` for `PUBLIC` (from the routine's ACL, including PostgreSQL's default) and for the
  browser roles, and `SECURITY DEFINER`.
- **Default privileges:** `ALTER DEFAULT PRIVILEGES` entries that give `PUBLIC` or the browser roles
  access to new tables, sequences, functions, types or schemas.
- **Other objects:** any relation, routine or type in `public` that the project didn't create. A
  name is treated as the project's only when the object is also of the expected kind: a table for
  the Core API, `alembic_version` and queue tables, and a sequence for the queue's sequences. A
  view or other object that reuses one of those names is reported here and graded for access like
  any other relation.

Access by `PUBLIC` or a browser role is graded as follows. Anything listed as a FAIL blocks the
migration.

| Object | FAIL | WARN (justified exception, review it) |
| --- | --- | --- |
| Core API tables, `alembic_version` | any access once the security migration is recorded; any `PUBLIC` grant | access before the security migration, which revokes it |
| Procrastinate tables, sequences and functions | any access once every queue table has RLS on (the queue was secured) | access before `scripts.secure_queue_schema --apply`, which revokes it |
| Views | a view without `security_invoker`, which reads its tables with the owner's privileges | a `security_invoker` view: the caller's privileges and RLS apply |
| Materialized views, foreign tables | always: RLS doesn't apply | none |
| Sequences | owned by a Core API table | other sequences: callers can read and advance them |
| Other tables | RLS off | RLS on: the policies decide which rows are visible |
| Routines | `SECURITY DEFINER` and executable by `PUBLIC` or a browser role | executable with the caller's privileges (the Data API exposes it as an RPC); `SECURITY DEFINER` but not executable by them |
| Extension members | none | exposed relations, and `SECURITY DEFINER` routines that are executable |

A missing permission record for a role that exists is a FAIL, never "no access".

#### Not checked

- Procrastinate's column, constraint and function definitions: only the object names are
  compared.
- Collations, operator classes, rules, publications, event triggers, and the definitions of
  triggers and policies (only whether policies exist).
- Schemas other than `public`, including any other schema the Data API exposes.
- Data API roles beyond what `authenticator` can reach: the script assumes the Data API logs in as
  a role named `authenticator` and doesn't read the Data API's configuration. Roles reached from
  other login roles (for example direct database connections by other users) aren't treated as
  browser roles. `authenticator`'s own privileges aren't checked, because requests run after
  `SET ROLE`. When `authenticator` is a superuser, the roles it could switch to aren't listed one by
  one; the FAIL covers them.
- The `MAINTAIN` privilege (PostgreSQL 17) and large objects.
- Supabase project settings: the Data API's exposed schemas, network restrictions, SSL
  enforcement, and authentication settings.
- Channel binding or `require_auth`: the script relies on TLS server verification.
- Temporary objects: type names in casts are resolved through `search_path`, so a temporary type
  created earlier in the same server session could shadow them. A fresh session has none.

A preflight without blocking findings is not a substitute for reviewing the Data API settings
(exposed schemas) and the Security Advisor in the Supabase dashboard before migrating.

#### Failures and output

- **Failed queries:** a query that fails, for example for lack of permission, is reported as
  LIMITED instead of guessed around, and the other sections still run. If the role query fails or
  misses a role seen at connect time, the role, RLS, queue and object checks report only LIMITED.
  If `authenticator`'s memberships can't be read, the RLS, queue, object and default-privilege
  checks report only LIMITED, since they might miss a role.
- **Database errors:** printed as the driver's exception class, the SQLSTATE and a fixed hint,
  never the server's message, which can name the user, host or project. The line ends with the
  stage: `while connecting` (no session was established) or `after connecting`.
  - psycopg gives no SQLSTATE for failures while connecting, so those show `SQLSTATE unknown` and a
    fixed hint chosen from libpq's English message. The hints cover a wrong password, no password,
    no `pg_hba.conf` entry, a missing certificate file, a missing database or role, a refused
    connection, a timeout, an unresolvable host name, certificate verification and TLS failures.
  - Anything else gets `details hidden`. A hint is a best guess from the message text, not a
    diagnosis.
- **Lost connection:** the inspection stops at once with the error class and SQLSTATE, prints no
  report, and exits with code 1. It doesn't continue on a new connection outside the read-only
  transaction.
- **Unexpected errors:** reported as the exception class and where it was raised, never its
  message, with exit code 1.
- **Ctrl+C:** not caught. Python prints its standard traceback instead of the sanitised error line
  and exits with its own interrupt status. Closing the connection rolls back any open transaction,
  and no transaction is open while the script waits for confirmation.
- **Timeouts:**
  - Connecting: 10 s (`connect_timeout`, which replaces any value in the URL). libpq applies it to
    each address it tries, so a host name with several addresses can take longer.
  - Once connected, each transaction sets a 30 s `statement_timeout` and a 5 s `lock_timeout`.
    Both are enforced by the server. The client sets no read timeout or keepalive tuning, so if the
    network drops silently mid-query, the script can wait well past 30 s; press Ctrl+C. The server
    ends the read-only transaction when it notices the connection is gone.
- **Output:** PASS, INFO, WARN, FAIL and LIMITED lines. The identity block prints the connected
  database role for confirmation (see Identity above). The output never contains the URL, its user
  field, the password, the project reference, the certificate path, a refused host, or the value of
  a refused environment variable.
- **Exit codes:**

  | Code | Meaning |
  | --- | --- |
  | 0 | no FAIL or LIMITED finding; WARNs still need review |
  | 1 | at least one FAIL or LIMITED finding, a database error (including a failed or lost connection), or an unexpected error |
  | 2 | refused: a missing or invalid URL or project reference, the target or TLS checks, a libpq environment variable or URL parameter, the identity checks, an identity change between the transactions, a transaction that isn't read-only, or no confirmation |
  | other | interrupted with Ctrl+C (Python's own status) |

`--local-test` points the same checks at a local `*_test` database. The tests in
`tests/test_supabase_preflight.py` use it.

### H. Order for setting up Supabase

Run everything from `backend/server/`, with `SERVER_DIRECT_URL` set to the session pooler URL
(port 5432) including `sslmode=verify-full&sslrootcert=...` (section 2). Every remote change needs
an explicit opt-in flag, and each step only starts after the previous one succeeded:

1. **Read-only preflight** against the same session pooler URL: `uv run python -m
   scripts.supabase_preflight` (section 3G). It changes nothing.
2. **Review and verify the target.** Resolve every FAIL and LIMITED finding and review every WARN.
   Without the opt-in flags, `uv run alembic current` and `uv run python -m
   scripts.secure_queue_schema --check` refuse the remote target before connecting. Their error
   message shows the host, port and database they would use, so you can confirm it's
   `...pooler.supabase.com:5432/postgres` and not port 6543.
3. **Get explicit approval** from the team (and the database owner) before any remote change.
   The opt-in flags below are that approval written down; never put them in scripts or aliases.
   Stop the worker so it doesn't hold locks on the queue tables.
4. **Migrations:** `uv run alembic -x allow_remote=true upgrade head`. This creates the Core API
   tables and, in the same run, the security migration (RLS, revoked browser-role privileges
   and default privileges).
5. **Queue schema, through the guarded entry point:** `uv run python -m
   scripts.install_queue_schema --allow-remote`. Never use `procrastinate schema --apply`.
6. **Queue hardening:** `uv run python -m scripts.secure_queue_schema --check --allow-remote`,
   verify the printed target, then `--apply --allow-remote`, then `--check --allow-remote` again.
   It must report only PASS.
7. **Verify:** rerun the preflight (it must report the security migration as recorded, RLS on,
   and no access for `PUBLIC` or the browser roles). Turn off the Data API in the Supabase
   dashboard and check the Security Advisor. Start the Core API (`/health` must report the
   database as connected) and the worker, and run one job end to end.

`downgrade` against Supabase is never part of this workflow (section 3C).

---

## 4. Running the Web Server

### Start the FastAPI Development Server
```bash
# From backend/server/ directory:
uv run uvicorn app.main:app --reload --port 8002
```

### Quick Database Health Check
To verify that your local environment connects successfully to Supabase:
```bash
# From backend/server/ directory:
uv run python -c "from app.database import check_db_connection; print('Connected:', check_db_connection())"
```

---

## 5. Running Automated Tests

The server and the agentic framework have separate environments, so run each test suite from its own folder:
```bash
# Server tests (from backend/server/):
uv run pytest

# Agent + worker tests (from backend/agentic_framework/):
uv run pytest
```

Without extra setup the Core API suite never writes to a real database: model and migration
tests use SQLite and render the PostgreSQL SQL offline, and the other tests use an in-memory
job queue.

Three tests need a real PostgreSQL database: the migration round trip in `tests/test_migrations.py`
(runs `upgrade head` and `downgrade base`), the job API test in `tests/test_jobs_api.py`
(applies Procrastinate's schema if missing and enqueues jobs on its own `selvia_test_jobs_api`
queue, deleting them afterwards), and the install test in `tests/test_install_queue_schema.py`
(runs `scripts.install_queue_schema` twice: it installs the queue schema if missing, then must
change nothing). All three use only `SERVER_TEST_DATABASE_URL`:

- not set: these tests are **skipped**; they never fall back to `SERVER_DIRECT_URL` or
  `SERVER_DATABASE_URL`;
- set: it must be a PostgreSQL URL on `localhost`/`127.0.0.1`/`::1`, the database name must end in
  `_test`, and it must not be the database in `SERVER_DIRECT_URL`/`SERVER_DATABASE_URL`;
  otherwise they fail before connecting.

The migration round trip also needs the database to be unmigrated (no Core API tables, no
applied revision):

```powershell
$env:SERVER_TEST_DATABASE_URL = "postgresql+psycopg://<user>:<password>@localhost:5432/selvia_migration_test"
uv run pytest tests/test_migrations.py tests/test_jobs_api.py tests/test_install_queue_schema.py
Remove-Item Env:SERVER_TEST_DATABASE_URL
```
