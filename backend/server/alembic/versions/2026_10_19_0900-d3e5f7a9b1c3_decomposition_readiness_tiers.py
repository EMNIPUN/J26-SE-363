"""Student-friendly decomposition readiness — replace the strict pass/fail
gate with three non-blocking tiers (Ready / Ready with Improvements / Needs
Attention), and add input_hash so re-running analysis on unchanged stories
can reuse the prior assessment instead of spending another LLM call.

Revision ID: d3e5f7a9b1c3
Revises: c2d4e6f8a0b1
Create Date: 2026-10-19 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e5f7a9b1c3"
down_revision: str | None = "c2d4e6f8a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "rqa_decomposition_assessments"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "readiness_status",
            sa.String(32),
            sa.CheckConstraint(
                "readiness_status IN ('Ready', 'Ready with Improvements', 'Needs Attention')",
                name=f"ck_{TABLE}_decomposition_readiness",
            ),
            nullable=False,
            server_default="Needs Attention",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column("readiness_reason", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        TABLE,
        sa.Column("input_hash", sa.String(64), nullable=True),
    )
    op.create_index(op.f(f"ix_{TABLE}_input_hash"), TABLE, ["input_hash"])

    # gate_status is deprecated (superseded by readiness_status) — relax it
    # to nullable rather than drop it outright, consistent with this
    # project's convention of deferring destructive column drops.
    op.alter_column(TABLE, "gate_status", nullable=True)

    op.alter_column(TABLE, "readiness_status", server_default=None)
    op.alter_column(TABLE, "readiness_reason", server_default=None)


def downgrade() -> None:
    op.alter_column(TABLE, "gate_status", nullable=False)
    op.drop_index(op.f(f"ix_{TABLE}_input_hash"), table_name=TABLE)
    op.drop_column(TABLE, "input_hash")
    op.drop_column(TABLE, "readiness_reason")
    op.drop_column(TABLE, "readiness_status")
