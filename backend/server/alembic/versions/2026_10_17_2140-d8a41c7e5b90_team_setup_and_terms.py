"""team setup and terms

A team can be "pending" while its lecturer sets it up, and terms become a list that lecturers add
to. Adds the terms table, fills it with the terms teams already use, and lets groups.status hold
'pending'. No existing row changes.

Revision ID: d8a41c7e5b90
Revises: ec66f4d17052
Create Date: 2026-10-17 21:40:00.000000

"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd8a41c7e5b90'
down_revision: Union[str, Sequence[str], None] = 'ec66f4d17052'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BROWSER_ROLES = ("anon", "authenticated", "service_role")
TEAM_STATUSES = "status IN ('pending', 'forming', 'active')"
OLD_TEAM_STATUSES = "status IN ('forming', 'active')"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('terms',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=32), nullable=False),
    sa.Column('created_by_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_terms_created_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_terms')),
    sa.UniqueConstraint('name', name=op.f('uq_terms_name'))
    )

    # Row level security without policies keeps the table out of Supabase's Data API
    # (see docs/SCHEMA_CHANGE_GUIDE.md, "Add a table").
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TABLE terms ENABLE ROW LEVEL SECURITY")
        for role in BROWSER_ROLES:
            op.execute(
                "DO $$\n"
                "BEGIN\n"
                f"    IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{role}')\n"
                f"       AND current_user <> '{role}' THEN\n"
                f"        REVOKE ALL ON TABLE terms FROM {role};\n"
                "    END IF;\n"
                "END\n"
                "$$"
            )

    # The terms teams already use become the starting list (one per spelling, ignoring case).
    if op.get_context().dialect.name == "postgresql":
        op.execute(
            "INSERT INTO terms (id, name, created_at, updated_at) "
            "SELECT gen_random_uuid(), name, now(), now() FROM ("
            "    SELECT DISTINCT ON (lower(btrim(term))) btrim(term) AS name"
            "    FROM groups WHERE btrim(term) <> ''"
            "    ORDER BY lower(btrim(term)), btrim(term)"
            ") AS used"
        )
    elif not op.get_context().as_sql:  # SQLite: only ever a development or test database
        now = datetime.now(timezone.utc)
        used = op.get_bind().execute(
            sa.text("SELECT DISTINCT term FROM groups WHERE term IS NOT NULL")
        ).scalars().all()
        seen: set[str] = set()
        rows = []
        for name in used:
            key = name.strip().lower()
            if key and key not in seen:
                seen.add(key)
                rows.append({'id': uuid.uuid4(), 'name': name.strip(), 'created_at': now, 'updated_at': now})
        if rows:
            op.bulk_insert(
                sa.table(
                    'terms',
                    sa.column('id', sa.Uuid()),
                    sa.column('name', sa.String()),
                    sa.column('created_at', sa.DateTime(timezone=True)),
                    sa.column('updated_at', sa.DateTime(timezone=True)),
                ),
                rows,
            )

    with op.batch_alter_table('groups') as batch_op:
        batch_op.drop_constraint(op.f('ck_groups_status'), type_='check')
        batch_op.create_check_constraint(op.f('ck_groups_status'), TEAM_STATUSES)


def downgrade() -> None:
    """Downgrade schema (local databases only; never run on Supabase)."""
    # A pending team cannot exist under the old rule; treat it as one that has been opened.
    op.execute("UPDATE groups SET status = 'forming' WHERE status = 'pending'")
    with op.batch_alter_table('groups') as batch_op:
        batch_op.drop_constraint(op.f('ck_groups_status'), type_='check')
        batch_op.create_check_constraint(op.f('ck_groups_status'), OLD_TEAM_STATUSES)
    op.drop_table('terms')
