# Server Database & Migration Guide

This guide explains the database architecture, configuration, and migration commands for developers working on the SELVIA backend server.

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

All server database secrets are stored strictly in `backend/.env` (which is gitignored):

```env
# backend/.env

APP_NAME=SELVIA Server
APP_ENV=development
DEBUG=true

# --- Option A: Supabase Cloud PostgreSQL (Default) ---
SERVER_DATABASE_URL=postgresql+psycopg://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
SERVER_DIRECT_URL=postgresql+psycopg://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require

# --- Option B: Optional Local Docker PostgreSQL (Port 5433) ---
# SERVER_DATABASE_URL=postgresql+psycopg://selvia_server_user:your_local_password@localhost:5433/selvia_server_db
# SERVER_DIRECT_URL=postgresql+psycopg://selvia_server_user:your_local_password@localhost:5433/selvia_server_db

# Supabase Storage & API Credentials
SUPABASE_URL=https://[PROJECT_REF].supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

---

## 3. Database Migration Commands (Alembic)

All commands are executed from the `backend/` or `backend/server/` directory using `uv run`.

### A. Apply All Migrations
Applies all pending schema migrations up to the latest revision:
```bash
uv run alembic upgrade head
```

### B. Generate a New Migration
Automatically compares your SQLAlchemy models (`backend/server/app/models/`) with the live database schema and generates a new migration script:
```bash
uv run alembic revision --autogenerate -m "create_batches_and_teams_tables"
```

### C. Roll Back the Last Migration
Reverts the most recent migration step:
```bash
uv run alembic downgrade -1
```

### D. Check Migration Status
View the current revision applied to the database:
```bash
uv run alembic current
```

View migration history:
```bash
uv run alembic history --verbose
```

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

Run the full backend test suite:
```bash
# From repository root:
uv run pytest backend/
```
