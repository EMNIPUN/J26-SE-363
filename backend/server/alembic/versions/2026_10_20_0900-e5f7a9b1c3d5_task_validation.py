"""Task CRUD completion (description field) + AI task-validation persistence —
per-task relevance/scope/actionability/duplication criteria, a run-level
readiness tier (Valid / Needs Improvement / Coverage Warning), and feedback
wiring. Mirrors the decomposition gate redesign (a7c9e1f3b5d7), scoped to one
user story's task set instead of a requirement's story set.

Revision ID: e5f7a9b1c3d5
Revises: d3e5f7a9b1c3
Create Date: 2026-10-20 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f7a9b1c3d5"
down_revision: str | None = "d3e5f7a9b1c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def _ck(table: str, name: str) -> str:
    return f"ck_{table}_{name}"


def upgrade() -> None:
    # ── rqa_user_story_tasks: description, for richer validation context ──
    op.add_column(
        "rqa_user_story_tasks",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("rqa_user_story_tasks", "description", server_default=None)

    # ── rqa_task_validation_assessments ──────────────────────────────
    op.create_table(
        "rqa_task_validation_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_story_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "readiness_status",
            sa.String(32),
            sa.CheckConstraint(
                "readiness_status IN ('Valid','Needs Improvement','Coverage Warning')",
                name=_ck(
                    "rqa_task_validation_assessments", "task_validation_readiness"
                ),
            ),
            nullable=False,
        ),
        sa.Column("readiness_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("quality_score", sa.Numeric(3, 2), nullable=False),
        sa.Column(
            "quality_band",
            sa.String(16),
            sa.CheckConstraint(
                "quality_band IN ('Excellent','Good','Moderate','Poor','Very poor')",
                name=_ck(
                    "rqa_task_validation_assessments", "task_validation_quality_band"
                ),
            ),
            nullable=False,
        ),
        sa.Column(
            "coverage_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"
        ),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False, server_default="0.8"),
        sa.Column(
            "analysis_failed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_task_validation_assessments")),
        sa.ForeignKeyConstraint(
            ["user_story_id"], ["rqa_user_stories.id"],
            name=op.f(
                "fk_rqa_task_validation_assessments_user_story_id_rqa_user_stories"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"], ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_task_validation_assessments_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_rqa_task_validation_assessments_user_story_id"),
        "rqa_task_validation_assessments", ["user_story_id"],
    )
    op.create_index(
        op.f("ix_rqa_task_validation_assessments_pipeline_session_id"),
        "rqa_task_validation_assessments", ["pipeline_session_id"],
    )
    op.create_index(
        op.f("ix_rqa_task_validation_assessments_input_hash"),
        "rqa_task_validation_assessments", ["input_hash"],
    )

    # ── rqa_task_assessments ─────────────────────────────────────────
    op.create_table(
        "rqa_task_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_validation_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("user_story_task_id", sa.Uuid(), nullable=False),
        sa.Column(
            "task_ready", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_task_assessments")),
        sa.ForeignKeyConstraint(
            ["task_validation_assessment_id"],
            ["rqa_task_validation_assessments.id"],
            name=op.f(
                "fk_rqa_task_assessments_task_validation_assessment_id_rqa_task_validation_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_story_task_id"], ["rqa_user_story_tasks.id"],
            name=op.f(
                "fk_rqa_task_assessments_user_story_task_id_rqa_user_story_tasks"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "task_validation_assessment_id", "user_story_task_id",
            name=op.f(
                "uq_rqa_task_assessments_task_validation_assessment_id_user_story_task_id"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_task_assessments_task_validation_assessment_id"),
        "rqa_task_assessments", ["task_validation_assessment_id"],
    )
    op.create_index(
        op.f("ix_rqa_task_assessments_user_story_task_id"),
        "rqa_task_assessments", ["user_story_task_id"],
    )

    # ── rqa_task_criterion_results ───────────────────────────────────
    op.create_table(
        "rqa_task_criterion_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_validation_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("user_story_task_id", sa.Uuid(), nullable=False),
        sa.Column(
            "criterion",
            sa.String(16),
            sa.CheckConstraint(
                "criterion IN ('relevance','scope','actionability','duplication')",
                name=_ck("rqa_task_criterion_results", "task_validation_criterion"),
            ),
            nullable=False,
        ),
        sa.Column(
            "result",
            sa.String(20),
            sa.CheckConstraint(
                "result IN ('Pass','Needs Improvement','Fail','Cannot Assess')",
                name=_ck(
                    "rqa_task_criterion_results", "task_validation_criterion_outcome"
                ),
            ),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_task_criterion_results")),
        sa.ForeignKeyConstraint(
            ["task_validation_assessment_id"],
            ["rqa_task_validation_assessments.id"],
            name=op.f(
                "fk_rqa_task_criterion_results_task_validation_assessment_id_rqa_task_validation_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_story_task_id"], ["rqa_user_story_tasks.id"],
            name=op.f(
                "fk_rqa_task_criterion_results_user_story_task_id_rqa_user_story_tasks"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "task_validation_assessment_id", "user_story_task_id", "criterion",
            name=op.f(
                "uq_rqa_task_criterion_results_task_validation_assessment_id_user_story_task_id_criterion"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_task_criterion_results_task_validation_assessment_id"),
        "rqa_task_criterion_results", ["task_validation_assessment_id"],
    )
    op.create_index(
        op.f("ix_rqa_task_criterion_results_user_story_task_id"),
        "rqa_task_criterion_results", ["user_story_task_id"],
    )

    # ── rqa_feedbacks: link feedback to a task / task-validation run ─
    op.add_column(
        "rqa_feedbacks",
        sa.Column("user_story_task_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_rqa_feedbacks_user_story_task_id_rqa_user_story_tasks"),
        "rqa_feedbacks", "rqa_user_story_tasks",
        ["user_story_task_id"], ["id"], ondelete="SET NULL",
    )
    op.add_column(
        "rqa_feedbacks",
        sa.Column("task_validation_assessment_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f(
            "fk_rqa_feedbacks_task_validation_assessment_id_rqa_task_validation_assessments"
        ),
        "rqa_feedbacks", "rqa_task_validation_assessments",
        ["task_validation_assessment_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_rqa_feedbacks_task_validation_assessment_id"),
        "rqa_feedbacks", ["task_validation_assessment_id"],
    )

    if op.get_context().dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE rqa_task_validation_assessments ENABLE ROW LEVEL SECURITY"
        )
        op.execute("ALTER TABLE rqa_task_assessments ENABLE ROW LEVEL SECURITY")
        op.execute(
            "ALTER TABLE rqa_task_criterion_results ENABLE ROW LEVEL SECURITY"
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_rqa_feedbacks_task_validation_assessment_id"),
        table_name="rqa_feedbacks",
    )
    op.drop_constraint(
        op.f(
            "fk_rqa_feedbacks_task_validation_assessment_id_rqa_task_validation_assessments"
        ),
        "rqa_feedbacks", type_="foreignkey",
    )
    op.drop_column("rqa_feedbacks", "task_validation_assessment_id")
    op.drop_constraint(
        op.f("fk_rqa_feedbacks_user_story_task_id_rqa_user_story_tasks"),
        "rqa_feedbacks", type_="foreignkey",
    )
    op.drop_column("rqa_feedbacks", "user_story_task_id")

    op.drop_index(
        op.f("ix_rqa_task_criterion_results_user_story_task_id"),
        table_name="rqa_task_criterion_results",
    )
    op.drop_index(
        op.f("ix_rqa_task_criterion_results_task_validation_assessment_id"),
        table_name="rqa_task_criterion_results",
    )
    op.drop_table("rqa_task_criterion_results")

    op.drop_index(
        op.f("ix_rqa_task_assessments_user_story_task_id"),
        table_name="rqa_task_assessments",
    )
    op.drop_index(
        op.f("ix_rqa_task_assessments_task_validation_assessment_id"),
        table_name="rqa_task_assessments",
    )
    op.drop_table("rqa_task_assessments")

    op.drop_index(
        op.f("ix_rqa_task_validation_assessments_input_hash"),
        table_name="rqa_task_validation_assessments",
    )
    op.drop_index(
        op.f("ix_rqa_task_validation_assessments_pipeline_session_id"),
        table_name="rqa_task_validation_assessments",
    )
    op.drop_index(
        op.f("ix_rqa_task_validation_assessments_user_story_id"),
        table_name="rqa_task_validation_assessments",
    )
    op.drop_table("rqa_task_validation_assessments")

    op.drop_column("rqa_user_story_tasks", "description")
