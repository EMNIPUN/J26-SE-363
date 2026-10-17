"""decomposition analysis_failed flag — distinguish a real INCOMPLETE
verdict from a coverage-LLM system failure, so the frontend never shows a
mechanically-derived placeholder score/checklist as if it were a real result.

Revision ID: b1d3f5a7c9e2
Revises: a7c9e1f3b5d7
Create Date: 2026-10-18 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1d3f5a7c9e2"
down_revision: str | None = "a7c9e1f3b5d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rqa_decomposition_assessments",
        sa.Column(
            "analysis_failed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "rqa_decomposition_assessments",
        sa.Column("failure_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rqa_decomposition_assessments", "failure_reason")
    op.drop_column("rqa_decomposition_assessments", "analysis_failed")
