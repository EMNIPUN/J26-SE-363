"""performance assessment tables

Tracked teams, assessment runs, the run event log (live pipeline), factor and assessment results, daily snapshots and lecturer reviews. The DDL lives in one file shared with the
AI backend worker (backend/shared/src/shared/performance/schema.sql) so the worker and the API cannot disagree about the tables. No existing table or row changes.

Revision ID: a7c3d5e91f02
Revises: f2a6c4b8d150
Create Date: 2026-10-20 09:00:00.000000

"""
import importlib.util
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# Found without importing shared.performance: that package opens the job queue module, which reads the service's .env file, and migrations must not.
SCHEMA_SQL = Path(importlib.util.find_spec("shared").submodule_search_locations[0]) / "performance" / "schema.sql"

# revision identifiers, used by Alembic.
revision: str = 'a7c3d5e91f02'
down_revision: Union[str, Sequence[str], None] = 'f2a6c4b8d150'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BROWSER_ROLES = ("anon", "authenticated", "service_role")
TABLES = ("perf_tracked_teams", "perf_runs", "perf_run_events", "perf_factor_results", "perf_assessment_results", "perf_snapshots", "perf_reviews", "perf_quizzes")


def upgrade() -> None:
    """Upgrade schema."""
    if op.get_context().dialect.name != "postgresql":
        return  # these tables use PostgreSQL types (jsonb, uuid, timestamptz); the SQLite test database does not need them
    op.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
    # Same lock-down as the other Core API tables (row level security is enabled by the DDL file): browser roles get nothing.
    table_list = ", ".join(TABLES)
    for role in BROWSER_ROLES:
        op.execute(
            "DO $$\n"
            "BEGIN\n"
            f"    IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{role}')\n"
            f"       AND current_user <> '{role}' THEN\n"
            f"        REVOKE ALL ON TABLE {table_list} FROM {role};\n"
            "    END IF;\n"
            "END\n"
            "$$"
        )


def downgrade() -> None:
    """Downgrade schema."""
    if op.get_context().dialect.name != "postgresql":
        return
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
