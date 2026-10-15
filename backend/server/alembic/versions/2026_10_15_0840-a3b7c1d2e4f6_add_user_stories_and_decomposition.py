"""add user_stories and decomposition_results

Revision ID: a3b7c1d2e4f6
Revises: fd1709d0b6b4
Create Date: 2026-10-15 08:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3b7c1d2e4f6'
down_revision: Union[str, Sequence[str], None] = 'fd1709d0b6b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BROWSER_ROLES = ("anon", "authenticated", "service_role")
TABLES = ("user_stories", "decomposition_results")


def _rls_guard(table: str) -> None:
    if op.get_context().dialect.name == "postgresql":
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


def upgrade() -> None:
    """Upgrade schema."""
    # user_stories — student-authored stories, CRUD source of truth
    op.create_table('user_stories',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=False),
        sa.Column('requirement_ref', sa.String(length=64), nullable=False),
        sa.Column('story_ref', sa.String(length=64), nullable=False),
        sa.Column('data', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_stories'))
    )
    op.create_index(op.f('ix_user_stories_project_id'), 'user_stories', ['project_id'], unique=False)
    op.create_index(op.f('ix_user_stories_requirement_ref'), 'user_stories', ['requirement_ref'], unique=False)
    op.create_index(op.f('ix_user_stories_story_ref'), 'user_stories', ['story_ref'], unique=False)

    # decomposition_results — versioned agent analysis results
    op.create_table('decomposition_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=False),
        sa.Column('requirement_ref', sa.String(length=64), nullable=False),
        sa.Column('requirement_text', sa.Text(), nullable=False),
        sa.Column('result', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_decomposition_results'))
    )
    op.create_index(op.f('ix_decomposition_results_project_id'), 'decomposition_results', ['project_id'], unique=False)
    op.create_index(op.f('ix_decomposition_results_requirement_ref'), 'decomposition_results', ['requirement_ref'], unique=False)

    for table in TABLES:
        _rls_guard(table)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_decomposition_results_requirement_ref'), table_name='decomposition_results')
    op.drop_index(op.f('ix_decomposition_results_project_id'), table_name='decomposition_results')
    op.drop_table('decomposition_results')
    op.drop_index(op.f('ix_user_stories_story_ref'), table_name='user_stories')
    op.drop_index(op.f('ix_user_stories_requirement_ref'), table_name='user_stories')
    op.drop_index(op.f('ix_user_stories_project_id'), table_name='user_stories')
    op.drop_table('user_stories')
