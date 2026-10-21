"""github app links

A person's verified GitHub account (user_github_accounts), the GitHub App installation and
repository of a team (team_github), and what GitHub said each member may do on that repository
(team_github_access). No existing table or row changes.

Revision ID: b8e1d7c3a9f4
Revises: a7c3d5e91f02
Create Date: 2026-10-20 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8e1d7c3a9f4'
down_revision: Union[str, Sequence[str], None] = 'a7c3d5e91f02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BROWSER_ROLES = ("anon", "authenticated", "service_role")
NEW_TABLES = ("user_github_accounts", "team_github", "team_github_access")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user_github_accounts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('github_id', sa.BigInteger(), nullable=False),
    sa.Column('login', sa.String(length=64), nullable=False),
    sa.Column('avatar_url', sa.String(length=1024), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_github_accounts_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user_github_accounts')),
    sa.UniqueConstraint('github_id', name=op.f('uq_user_github_accounts_github_id')),
    sa.UniqueConstraint('user_id', name=op.f('uq_user_github_accounts_user_id'))
    )
    op.create_index(op.f('ix_user_github_accounts_login'), 'user_github_accounts', ['login'], unique=False)

    op.create_table('team_github',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('installation_id', sa.BigInteger(), nullable=False),
    sa.Column('account_login', sa.String(length=64), nullable=True),
    sa.Column('repo_full_name', sa.String(length=255), nullable=True),
    sa.Column('repo_id', sa.BigInteger(), nullable=True),
    sa.Column('repo_private', sa.Boolean(), nullable=False),
    sa.Column('linked_by_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], name=op.f('fk_team_github_group_id_groups'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['linked_by_id'], ['users.id'], name=op.f('fk_team_github_linked_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_team_github')),
    sa.UniqueConstraint('group_id', name=op.f('uq_team_github_group_id'))
    )

    op.create_table('team_github_access',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('permission', sa.String(length=8), nullable=False),
    sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], name=op.f('fk_team_github_access_group_id_groups'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_team_github_access_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_team_github_access')),
    sa.UniqueConstraint('group_id', 'user_id', name=op.f('uq_team_github_access_group_id_user_id'))
    )
    op.create_index(op.f('ix_team_github_access_group_id'), 'team_github_access', ['group_id'], unique=False)

    # Row level security without policies keeps the tables out of the Supabase Data API
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
    op.drop_index(op.f('ix_team_github_access_group_id'), table_name='team_github_access')
    op.drop_table('team_github_access')
    op.drop_table('team_github')
    op.drop_index(op.f('ix_user_github_accounts_login'), table_name='user_github_accounts')
    op.drop_table('user_github_accounts')
