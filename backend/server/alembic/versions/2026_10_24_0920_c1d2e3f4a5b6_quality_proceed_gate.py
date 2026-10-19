"""Persist explicit quality-to-decomposition authorization.

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column(
        "rqa_requirements",
        sa.Column("quality_approved_for_decomposition", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "rqa_requirements",
        sa.Column("decomposition_approved_for_effort", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

def downgrade() -> None:
    op.drop_column("rqa_requirements", "decomposition_approved_for_effort")
    op.drop_column("rqa_requirements", "quality_approved_for_decomposition")
