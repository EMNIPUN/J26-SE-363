"""profile pictures

Two optional columns on users (the provider's picture address and when an upload was made) and
the user_avatars table that holds uploaded pictures. No existing row changes.

Revision ID: e5b7a1c3d924
Revises: d8a41c7e5b90
Create Date: 2026-10-17 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5b7a1c3d924'
down_revision: Union[str, Sequence[str], None] = 'd8a41c7e5b90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BROWSER_ROLES = ("anon", "authenticated", "service_role")


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('picture_url', sa.String(length=1024), nullable=True))
    op.add_column('users', sa.Column('avatar_updated_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table('user_avatars',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('content_type', sa.String(length=32), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_avatars_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_user_avatars'))
    )

    # Row level security without policies keeps the table out of Supabase's Data API
    # (see docs/SCHEMA_CHANGE_GUIDE.md, "Add a table").
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TABLE user_avatars ENABLE ROW LEVEL SECURITY")
        for role in BROWSER_ROLES:
            op.execute(
                "DO $$\n"
                "BEGIN\n"
                f"    IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{role}')\n"
                f"       AND current_user <> '{role}' THEN\n"
                f"        REVOKE ALL ON TABLE user_avatars FROM {role};\n"
                "    END IF;\n"
                "END\n"
                "$$"
            )


def downgrade() -> None:
    """Downgrade schema (local databases only; never run on Supabase)."""
    op.drop_table('user_avatars')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('avatar_updated_at')
        batch_op.drop_column('picture_url')
