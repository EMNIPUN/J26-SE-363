"""registration and teams

Account profile fields on users (role becomes optional until onboarding is done), team fields on
groups and group_members, and the team_invitations table.

Existing rows: groups get status 'forming' and group_members get role 'member'. Neither table
has rows on a fresh database, so nothing else is touched.

Revision ID: ec66f4d17052
Revises: 4f6d2a9c8e1b
Create Date: 2026-10-17 10:58:06.827603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ec66f4d17052'
down_revision: Union[str, Sequence[str], None] = '4f6d2a9c8e1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BROWSER_ROLES = ("anon", "authenticated", "service_role")
MEMBER_ROLES = "role IN ('lecturer', 'member')"
TEAM_STATUSES = "status IN ('forming', 'active')"
INVITATION_STATUSES = "status IN ('pending', 'accepted', 'declined', 'revoked')"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('team_invitations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('role', sa.Enum('lecturer', 'member', name='role', native_enum=False, create_constraint=False), nullable=False),
    sa.Column('as_leader', sa.Boolean(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'accepted', 'declined', 'revoked', name='status', native_enum=False, create_constraint=False), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('invited_by_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(MEMBER_ROLES, name=op.f('ck_team_invitations_role')),
    sa.CheckConstraint(INVITATION_STATUSES, name=op.f('ck_team_invitations_status')),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], name=op.f('fk_team_invitations_group_id_groups'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], name=op.f('fk_team_invitations_invited_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_team_invitations')),
    sa.UniqueConstraint('group_id', 'email', name=op.f('uq_team_invitations_group_id_email')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_team_invitations_token_hash'))
    )
    op.create_index(op.f('ix_team_invitations_email'), 'team_invitations', ['email'], unique=False)
    op.create_index(op.f('ix_team_invitations_group_id'), 'team_invitations', ['group_id'], unique=False)

    # Row level security without policies keeps the table out of Supabase's Data API
    # (see docs/SCHEMA_CHANGE_GUIDE.md, "Add a table").
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TABLE team_invitations ENABLE ROW LEVEL SECURITY")
        for role in BROWSER_ROLES:
            op.execute(
                "DO $$\n"
                "BEGIN\n"
                f"    IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{role}')\n"
                f"       AND current_user <> '{role}' THEN\n"
                f"        REVOKE ALL ON TABLE team_invitations FROM {role};\n"
                "    END IF;\n"
                "END\n"
                "$$"
            )

    # Batch mode: plain ALTER statements on PostgreSQL, a table rebuild on SQLite (the tests run
    # every migration on SQLite too).
    #
    # group_members: NOT NULL role, added as nullable, filled, then tightened.
    op.add_column('group_members', sa.Column('role', sa.Enum('lecturer', 'member', name='role', native_enum=False, create_constraint=False), nullable=True))
    op.add_column('group_members', sa.Column('term', sa.String(length=32), nullable=True))
    op.add_column('group_members', sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE group_members SET role = 'member' WHERE role IS NULL")
    with op.batch_alter_table('group_members') as batch_op:
        batch_op.alter_column('role', existing_type=sa.String(length=8), nullable=False)
        batch_op.create_check_constraint(op.f('ck_group_members_role'), MEMBER_ROLES)
        batch_op.create_unique_constraint(op.f('uq_group_members_user_id_term'), ['user_id', 'term'])

    # groups: same recipe for the NOT NULL status.
    op.add_column('groups', sa.Column('term', sa.String(length=32), nullable=True))
    op.add_column('groups', sa.Column('status', sa.Enum('forming', 'active', name='status', native_enum=False, create_constraint=False), nullable=True))
    op.add_column('groups', sa.Column('repo_url', sa.String(length=1024), nullable=True))
    op.add_column('groups', sa.Column('created_by_id', sa.Uuid(), nullable=True))
    op.add_column('groups', sa.Column('leader_id', sa.Uuid(), nullable=True))
    op.add_column('groups', sa.Column('pending_leader_id', sa.Uuid(), nullable=True))
    op.execute("UPDATE groups SET status = 'forming' WHERE status IS NULL")
    with op.batch_alter_table('groups') as batch_op:
        batch_op.alter_column('status', existing_type=sa.String(length=7), nullable=False)
        batch_op.create_check_constraint(op.f('ck_groups_status'), TEAM_STATUSES)
        batch_op.create_foreign_key(op.f('fk_groups_created_by_id_users'), 'users', ['created_by_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key(op.f('fk_groups_leader_id_users'), 'users', ['leader_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key(op.f('fk_groups_pending_leader_id_users'), 'users', ['pending_leader_id'], ['id'], ondelete='SET NULL')

    # users: profile fields, and a role that stays empty until onboarding is finished.
    op.add_column('users', sa.Column('email', sa.String(length=320), nullable=True))
    op.add_column('users', sa.Column('institution', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('department', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('title', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('github_username', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('consent_version', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('consent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('role', existing_type=sa.String(length=8), nullable=True)
        batch_op.create_unique_constraint(op.f('uq_users_github_username'), ['github_username'])
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)


def downgrade() -> None:
    """Downgrade schema (local databases only; never run on Supabase)."""
    op.drop_index(op.f('ix_users_email'), table_name='users')
    # Accounts that never chose a role cannot satisfy the old NOT NULL.
    op.execute("DELETE FROM users WHERE role IS NULL")
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint(op.f('uq_users_github_username'), type_='unique')
        batch_op.alter_column('role', existing_type=sa.String(length=8), nullable=False)
        batch_op.drop_column('onboarding_completed_at')
        batch_op.drop_column('consent_at')
        batch_op.drop_column('consent_version')
        batch_op.drop_column('github_username')
        batch_op.drop_column('title')
        batch_op.drop_column('department')
        batch_op.drop_column('institution')
        batch_op.drop_column('email')

    with op.batch_alter_table('groups') as batch_op:
        batch_op.drop_constraint(op.f('fk_groups_pending_leader_id_users'), type_='foreignkey')
        batch_op.drop_constraint(op.f('fk_groups_leader_id_users'), type_='foreignkey')
        batch_op.drop_constraint(op.f('fk_groups_created_by_id_users'), type_='foreignkey')
        batch_op.drop_constraint(op.f('ck_groups_status'), type_='check')
        batch_op.drop_column('pending_leader_id')
        batch_op.drop_column('leader_id')
        batch_op.drop_column('created_by_id')
        batch_op.drop_column('repo_url')
        batch_op.drop_column('status')
        batch_op.drop_column('term')

    with op.batch_alter_table('group_members') as batch_op:
        batch_op.drop_constraint(op.f('uq_group_members_user_id_term'), type_='unique')
        batch_op.drop_constraint(op.f('ck_group_members_role'), type_='check')
        batch_op.drop_column('joined_at')
        batch_op.drop_column('term')
        batch_op.drop_column('role')

    op.drop_index(op.f('ix_team_invitations_group_id'), table_name='team_invitations')
    op.drop_index(op.f('ix_team_invitations_email'), table_name='team_invitations')
    op.drop_table('team_invitations')
