"""add sprint_tasks

Revision ID: d4e5f6a7b8c9
Revises: b5c8d3e7f9a1
Create Date: 2026-10-15 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "b5c8d3e7f9a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sprint_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("task_ref", sa.String(length=64), nullable=False),
        sa.Column("story_ref", sa.String(length=64), nullable=False),
        sa.Column("requirement_ref", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sprint_tasks")),
    )
    op.create_index(op.f("ix_sprint_tasks_project_id"), "sprint_tasks", ["project_id"])
    op.create_index(op.f("ix_sprint_tasks_task_ref"), "sprint_tasks", ["task_ref"])
    op.create_index(op.f("ix_sprint_tasks_story_ref"), "sprint_tasks", ["story_ref"])
    op.create_index(op.f("ix_sprint_tasks_requirement_ref"), "sprint_tasks", ["requirement_ref"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sprint_tasks_requirement_ref"), table_name="sprint_tasks")
    op.drop_index(op.f("ix_sprint_tasks_story_ref"), table_name="sprint_tasks")
    op.drop_index(op.f("ix_sprint_tasks_task_ref"), table_name="sprint_tasks")
    op.drop_index(op.f("ix_sprint_tasks_project_id"), table_name="sprint_tasks")
    op.drop_table("sprint_tasks")
