"""secure public schema

Enables row level security (without FORCE and without policies) on the Core API tables and the
Alembic version table, and takes away the Supabase browser roles' access to them. The backend
connects as the role that owns these tables, and table owners bypass RLS unless it is forced, so
the backend keeps working. Superusers and BYPASSRLS roles (Supabase's service_role is expected to
be one) also ignore RLS, and RLS never restricts TRUNCATE, REFERENCES or TRIGGER, so the revokes
below are what keep the browser roles out.

The browser roles (anon, authenticated, service_role) only exist on Supabase; each revoke is
skipped when the role is missing, so the migration also runs on plain PostgreSQL. Default
privileges are changed only for objects the migrating role creates in the public schema.

Procrastinate's procrastinate_* objects are not touched here: secure them with
scripts/secure_queue_schema.py after installing the queue schema.

Revision ID: 4f6d2a9c8e1b
Revises: c9da91ebdddb
Create Date: 2026-10-09 20:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f6d2a9c8e1b"
down_revision: str | Sequence[str] | None = "c9da91ebdddb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_TABLES = ("users", "groups", "group_members", "projects", "project_documents", "agent_runs")
BROWSER_ROLES = ("anon", "authenticated", "service_role")


def upgrade() -> None:
    context = op.get_context()
    if context.dialect.name != "postgresql":
        return

    quote = context.dialect.identifier_preparer.quote
    version_table = quote(context.version_table)
    if context.version_table_schema:
        version_table = f"{quote(context.version_table_schema)}.{version_table}"
    tables = [quote(name) for name in APP_TABLES] + [version_table]

    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    table_list = ", ".join(tables)
    for role in BROWSER_ROLES:
        grantee = quote(role)
        op.execute(
            "DO $$\n"
            "BEGIN\n"
            f"    IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{role}')\n"
            f"       AND current_user <> '{role}' THEN\n"
            f"        REVOKE ALL ON TABLE {table_list} FROM {grantee};\n"
            f"        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {grantee};\n"
            f"        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {grantee};\n"
            f"        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM {grantee};\n"
            "    END IF;\n"
            "END\n"
            "$$"
        )


def downgrade() -> None:
    """Intentionally does nothing.

    Turning RLS off or granting the browser roles access again would expose the tables through
    the Supabase Data API, so stepping back past this revision keeps the tables locked down.
    """
