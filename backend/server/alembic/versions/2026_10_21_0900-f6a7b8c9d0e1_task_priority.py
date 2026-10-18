"""Persist a priority for each decomposed user-story task.

Revision ID: a8b9c0d1e2f3
Revises: e5f7a9b1c3d5
Create Date: 2026-10-21 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "e5f7a9b1c3d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rqa_user_story_tasks",
        sa.Column(
            "priority",
            sa.String(length=32),
            sa.CheckConstraint(
                "priority IN ('critical','high','medium','low')",
                name=op.f("ck_rqa_user_story_tasks_task_priority"),
            ),
            nullable=False,
            server_default="medium",
        ),
    )
    op.alter_column("rqa_user_story_tasks", "priority", server_default=None)


def downgrade() -> None:
    op.drop_column("rqa_user_story_tasks", "priority")
