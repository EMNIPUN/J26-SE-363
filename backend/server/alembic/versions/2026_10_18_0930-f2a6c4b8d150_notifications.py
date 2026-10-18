"""notifications

The notifications table (what the bell shows) and notification_preferences (who wants which
emails). No existing row changes.

Revision ID: f2a6c4b8d150
Revises: e5b7a1c3d924
Create Date: 2026-10-18 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f2a6c4b8d150'
down_revision: Union[str, Sequence[str], None] = 'e5b7a1c3d924'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BROWSER_ROLES = ("anon", "authenticated", "service_role")
NEW_TABLES = ("notifications", "notification_preferences")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=48), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('body', sa.String(length=1000), nullable=True),
    sa.Column('link', sa.String(length=255), nullable=True),
    sa.Column('data', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('ref', sa.String(length=64), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index('ix_notifications_user_id_created_at', 'notifications', ['user_id', 'created_at'], unique=False)

    op.create_table('notification_preferences',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('category', sa.String(length=32), nullable=False),
    sa.Column('email_enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notification_preferences_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_preferences')),
    sa.UniqueConstraint('user_id', 'category', name=op.f('uq_notification_preferences_user_id_category'))
    )
    op.create_index(op.f('ix_notification_preferences_user_id'), 'notification_preferences', ['user_id'], unique=False)

    # Row level security without policies keeps the tables out of Supabase's Data API
    # (see docs/SCHEMA_CHANGE_GUIDE.md, "Add a table").
    if op.get_context().dialect.name == "postgresql":
        for table in NEW_TABLES:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            for role in BROWSER_ROLES:
                op.execute(
                    "DO $$\n"
                    "BEGIN\n"
                    f"    IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{role}')\n"
                    f"       AND current_user <> '{role}' THEN\n"
                    f"        REVOKE ALL ON TABLE {table} FROM {role};\n"
                    "    END IF;\n"
                    "END\n"
                    "$$"
                )


def downgrade() -> None:
    """Downgrade schema (local databases only; never run on Supabase)."""
    op.drop_index(op.f('ix_notification_preferences_user_id'), table_name='notification_preferences')
    op.drop_table('notification_preferences')
    op.drop_index('ix_notifications_user_id_created_at', table_name='notifications')
    op.drop_table('notifications')
