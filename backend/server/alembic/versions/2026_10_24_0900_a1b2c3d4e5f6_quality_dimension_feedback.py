"""Persist specific per-dimension quality feedback.

Revision ID: a1b2c3d4e5f6
Revises: d1e2f3a4b5c6
Create Date: 2026-10-24 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rqa_quality_dimension_scores",
        sa.Column("issues", sa.JSON(), nullable=True),
    )
    op.add_column(
        "rqa_quality_dimension_scores",
        sa.Column("recommended_action", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rqa_quality_dimension_scores", "recommended_action")
    op.drop_column("rqa_quality_dimension_scores", "issues")
