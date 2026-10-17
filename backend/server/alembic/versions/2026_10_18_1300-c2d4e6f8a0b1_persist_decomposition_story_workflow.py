"""Persist user-story lifecycle and decomposition tasks.

Revision ID: c2d4e6f8a0b1
Revises: b1d3f5a7c9e2
Create Date: 2026-10-18 13:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2d4e6f8a0b1"
down_revision: str | None = "b1d3f5a7c9e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rqa_user_stories",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
    )
    op.create_check_constraint(
        op.f("ck_rqa_user_stories_story_lifecycle_status"),
        "rqa_user_stories",
        "status IN ('draft', 'invest_passed', 'accepted', 'estimated', 'in_backlog')",
    )
    op.create_unique_constraint(
        op.f("uq_rqa_user_stories_pipeline_session_id_story_ref"),
        "rqa_user_stories",
        ["pipeline_session_id", "story_ref"],
    )
    op.create_table(
        "rqa_user_story_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_story_id", sa.Uuid(), nullable=False),
        sa.Column("parent_task_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False, server_default="task"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="todo"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_user_story_tasks")),
        sa.ForeignKeyConstraint(
            ["user_story_id"], ["rqa_user_stories.id"],
            name=op.f("fk_rqa_user_story_tasks_user_story_id_rqa_user_stories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_task_id"], ["rqa_user_story_tasks.id"],
            name=op.f("fk_rqa_user_story_tasks_parent_task_id_rqa_user_story_tasks"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("task_type IN ('task', 'subtask')", name=op.f("ck_rqa_user_story_tasks_decomposition_task_type")),
        sa.CheckConstraint("status IN ('todo', 'in_progress', 'blocked', 'done')", name=op.f("ck_rqa_user_story_tasks_decomposition_task_status")),
    )
    op.create_index(op.f("ix_rqa_user_story_tasks_user_story_id"), "rqa_user_story_tasks", ["user_story_id"])
    op.create_index(op.f("ix_rqa_user_story_tasks_parent_task_id"), "rqa_user_story_tasks", ["parent_task_id"])
    op.create_unique_constraint(
        op.f("uq_rqa_sprint_backlog_items_pipeline_session_id_user_story_id"),
        "rqa_sprint_backlog_items",
        ["pipeline_session_id", "user_story_id"],
    )

    # The original security migration predates this table. Keep it inaccessible
    # through Supabase's browser roles; Core API connections own the table.
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TABLE rqa_user_story_tasks ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_constraint(op.f("uq_rqa_sprint_backlog_items_pipeline_session_id_user_story_id"), "rqa_sprint_backlog_items", type_="unique")
    op.drop_index(op.f("ix_rqa_user_story_tasks_parent_task_id"), table_name="rqa_user_story_tasks")
    op.drop_index(op.f("ix_rqa_user_story_tasks_user_story_id"), table_name="rqa_user_story_tasks")
    op.drop_table("rqa_user_story_tasks")
    op.drop_constraint(op.f("uq_rqa_user_stories_pipeline_session_id_story_ref"), "rqa_user_stories", type_="unique")
    op.drop_constraint("ck_rqa_user_stories_story_lifecycle_status", "rqa_user_stories", type_="check")
    op.drop_column("rqa_user_stories", "status")
