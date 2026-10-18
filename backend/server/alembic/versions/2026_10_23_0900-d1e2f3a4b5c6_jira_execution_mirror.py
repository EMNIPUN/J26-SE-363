"""Persist Jira execution data separately from local planning data.

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-10-23 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = "c0d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("rqa_user_stories", "rqa_user_story_tasks"):
        op.add_column(table, sa.Column("jira_status", sa.String(length=128), nullable=True))
        op.add_column(table, sa.Column("jira_assignee_display_name", sa.String(length=255), nullable=True))
        op.add_column(table, sa.Column("jira_assignee_account_id", sa.String(length=128), nullable=True))
        op.add_column(table, sa.Column("jira_sprint_id", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("jira_updated_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("jira_last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rqa_sprints", sa.Column("jira_state", sa.String(length=32), nullable=True))
    op.add_column("rqa_sprints", sa.Column("jira_goal", sa.String(length=2000), nullable=True))
    op.add_column("rqa_sprints", sa.Column("jira_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rqa_sprints", sa.Column("jira_last_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for table in ("rqa_user_story_tasks", "rqa_user_stories"):
        for column in (
            "jira_last_synced_at", "jira_updated_at", "jira_sprint_id",
            "jira_assignee_account_id", "jira_assignee_display_name", "jira_status",
        ):
            op.drop_column(table, column)
    for column in ("jira_last_synced_at", "jira_updated_at", "jira_goal", "jira_state"):
        op.drop_column("rqa_sprints", column)
