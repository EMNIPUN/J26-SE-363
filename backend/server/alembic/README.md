# Alembic Database Migrations

Migration scripts and version tracking for the Core API database. Configuration is in
`backend/server/alembic.ini` and `env.py`; scripts are in `versions/`. Procrastinate's
`procrastinate_*` tables are never managed here.

How to apply, revert and generate migrations safely: `docs/SERVER_DATABASE_GUIDE.md`, section 3.
The `secure public schema` migration and securing the job queue with
`scripts/secure_queue_schema.py`: section 3F.
