"""add dart_cases table

Revision ID: b5c8d3e7f9a1
Revises: a3b7c1d2e4f6
Create Date: 2026-10-15 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b5c8d3e7f9a1'
down_revision: Union[str, Sequence[str], None] = 'a3b7c1d2e4f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BROWSER_ROLES = ("anon", "authenticated", "service_role")


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
    op.create_table('dart_cases',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=False),
        sa.Column('case_ref', sa.String(length=64), nullable=False),
        sa.Column('requirement_ref', sa.String(length=64), nullable=False),
        sa.Column('source_stage', sa.String(length=32), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('result', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('resolved_by', sa.String(length=255), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_dart_cases'))
    )
    op.create_index(op.f('ix_dart_cases_project_id'), 'dart_cases', ['project_id'], unique=False)
    op.create_index(op.f('ix_dart_cases_case_ref'), 'dart_cases', ['case_ref'], unique=False)
    op.create_index(op.f('ix_dart_cases_requirement_ref'), 'dart_cases', ['requirement_ref'], unique=False)
    op.create_index(op.f('ix_dart_cases_category'), 'dart_cases', ['category'], unique=False)
    op.create_index(op.f('ix_dart_cases_status'), 'dart_cases', ['status'], unique=False)

    _rls_guard('dart_cases')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_dart_cases_status'), table_name='dart_cases')
    op.drop_index(op.f('ix_dart_cases_category'), table_name='dart_cases')
    op.drop_index(op.f('ix_dart_cases_requirement_ref'), table_name='dart_cases')
    op.drop_index(op.f('ix_dart_cases_case_ref'), table_name='dart_cases')
    op.drop_index(op.f('ix_dart_cases_project_id'), table_name='dart_cases')
    op.drop_table('dart_cases')
