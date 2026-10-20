"""Add Backlog Readiness Passport table.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rqa_backlog_passports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("user_story_id", sa.Uuid(), nullable=False),
        sa.Column("overall_status", sa.String(length=32), nullable=False, server_default="not_ready"),
        sa.Column("quality_gate_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("decomposition_gate_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("invest_gate_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("points_assigned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quality_status", sa.String(length=64), nullable=False, server_default="Not evaluated"),
        sa.Column("coverage_status", sa.String(length=64), nullable=False, server_default="Not evaluated"),
        sa.Column("invest_status", sa.String(length=64), nullable=False, server_default="Not evaluated"),
        sa.Column("estimation_status", sa.String(length=64), nullable=False, server_default="Not assigned"),
        sa.Column("dart_status", sa.String(length=64), nullable=False, server_default="Clear"),
        sa.Column("readiness_gap", sa.Text(), nullable=True),
        sa.Column("student_action_required", sa.Text(), nullable=True),
        sa.Column("evidence_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("passport_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name="fk_rqa_backlog_passports_pipeline_session_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["rqa_requirements.id"],
            name="fk_rqa_backlog_passports_requirement_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_story_id"],
            ["rqa_user_stories.id"],
            name="fk_rqa_backlog_passports_user_story_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rqa_backlog_passports"),
        sa.UniqueConstraint(
            "pipeline_session_id",
            "user_story_id",
            name="uq_rqa_backlog_passports_session_story",
        ),
    )
    op.create_index(
        "ix_rqa_backlog_passports_pipeline_session_id",
        "rqa_backlog_passports",
        ["pipeline_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_rqa_backlog_passports_requirement_id",
        "rqa_backlog_passports",
        ["requirement_id"],
        unique=False,
    )
    op.create_index(
        "ix_rqa_backlog_passports_user_story_id",
        "rqa_backlog_passports",
        ["user_story_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rqa_backlog_passports_user_story_id", table_name="rqa_backlog_passports")
    op.drop_index("ix_rqa_backlog_passports_requirement_id", table_name="rqa_backlog_passports")
    op.drop_index("ix_rqa_backlog_passports_pipeline_session_id", table_name="rqa_backlog_passports")
    op.drop_table("rqa_backlog_passports")
