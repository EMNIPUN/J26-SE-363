"""decomposition gate redesign — coverage gate (C1-C10), INVEST readiness
gate, 0-4 quality score, gate_status, and structured feedback wiring.

Revision ID: a7c9e1f3b5d7
Revises: f6a7b8c9d0e1
Create Date: 2026-10-18 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7c9e1f3b5d7"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def _ck(table: str, name: str) -> str:
    return f"ck_{table}_{name}"


def upgrade() -> None:
    # Decomposition assessment data produced before this migration was never
    # reliably persisted (save_assessment crashed on any nonzero coverage —
    # see the bug writeup in the plan) and the new gate/score columns below
    # need to be NOT NULL, so clear the slate instead of backfilling broken
    # rows. rqa_coverage_analysis_results / rqa_decomposition_tool_outputs
    # cascade from rqa_decomposition_assessments already; rqa_invest_validations
    # does not (pre-migration FK is only to user_story_id), so it is named
    # explicitly.
    op.execute(
        "TRUNCATE TABLE rqa_decomposition_assessments, "
        "rqa_invest_validations CASCADE"
    )

    # ── rqa_decomposition_assessments: allow re-analysis history ────
    # Previously unique on (requirement_id, pipeline_session_id), which made
    # a second analysis run on the same requirement throw an IntegrityError
    # (this is part of the idempotency bug the plan fixes). Mirrors the
    # Quality assessment's history-tracking precedent
    # (2026_10_16_1130-f6a7b8c9d0e1_add_quality_assessment_history.py):
    # re-running analysis now creates a new row instead of colliding.
    #
    # Name hardcoded (not op.f(...)) because the logical name
    # "uq_rqa_decomposition_assessments_requirement_id_pipeline_session_id"
    # exceeds PostgreSQL's 63-char identifier limit; SQLAlchemy's naming
    # convention deterministically truncates it to this exact name when the
    # original e1f2a3b4c5d6 migration creates the table (verified against a
    # live DB migrated from that revision).
    op.drop_constraint(
        "uq_rqa_decomposition_assessments_requirement_id_pipelin_12f9",
        "rqa_decomposition_assessments",
        type_="unique",
    )

    # ── rqa_decomposition_assessments: new gate/score columns ──────
    op.add_column(
        "rqa_decomposition_assessments",
        sa.Column(
            "gate_status",
            sa.String(16),
            sa.CheckConstraint(
                "gate_status IN ('COMPLETE','INCOMPLETE','NEEDS_REVIEW')",
                name=_ck(
                    "rqa_decomposition_assessments", "decomposition_gate_status"
                ),
            ),
            nullable=False,
        ),
    )
    op.add_column(
        "rqa_decomposition_assessments",
        sa.Column(
            "decomposition_quality_score", sa.Numeric(3, 2), nullable=False
        ),
    )
    op.add_column(
        "rqa_decomposition_assessments",
        sa.Column(
            "quality_band",
            sa.String(16),
            sa.CheckConstraint(
                "quality_band IN "
                "('Excellent','Good','Moderate','Poor','Very poor')",
                name=_ck(
                    "rqa_decomposition_assessments", "decomposition_quality_band"
                ),
            ),
            nullable=False,
        ),
    )
    op.add_column(
        "rqa_decomposition_assessments",
        sa.Column("needs_review_reason", sa.Text(), nullable=True),
    )
    # Deprecated: superseded by decomposition_quality_score. coverage_score
    # stays NOT NULL (repurposed to hold coverage_percentage).
    op.alter_column(
        "rqa_decomposition_assessments", "composite_score", nullable=True
    )
    op.alter_column(
        "rqa_decomposition_assessments", "invest_composite_score", nullable=True
    )

    # ── rqa_invest_validations: 4-state result + run-scoping ────────
    op.add_column(
        "rqa_invest_validations",
        sa.Column("decomposition_assessment_id", sa.Uuid(), nullable=False),
    )
    op.create_foreign_key(
        op.f(
            "fk_rqa_invest_validations_decomposition_assessment_id_rqa_decomposition_assessments"
        ),
        "rqa_invest_validations",
        "rqa_decomposition_assessments",
        ["decomposition_assessment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_rqa_invest_validations_decomposition_assessment_id"),
        "rqa_invest_validations",
        ["decomposition_assessment_id"],
    )
    op.add_column(
        "rqa_invest_validations",
        sa.Column(
            "result",
            sa.String(16),
            sa.CheckConstraint(
                "result IN ('Pass','Pass with note','Fail','Cannot Assess')",
                name=_ck("rqa_invest_validations", "invest_result"),
            ),
            nullable=False,
        ),
    )
    op.alter_column("rqa_invest_validations", "score", nullable=True)
    op.drop_constraint(
        op.f("uq_rqa_invest_validations_user_story_id_criterion"),
        "rqa_invest_validations",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f(
            "uq_rqa_invest_validations_decomposition_assessment_id_user_story_id_criterion"
        ),
        "rqa_invest_validations",
        ["decomposition_assessment_id", "user_story_id", "criterion"],
    )

    # ── rqa_story_assessments ────────────────────────────────────────
    op.create_table(
        "rqa_story_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decomposition_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("user_story_id", sa.Uuid(), nullable=False),
        sa.Column(
            "story_ready", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("coverage_percentage", sa.Numeric(5, 2), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_story_assessments")),
        sa.ForeignKeyConstraint(
            ["decomposition_assessment_id"],
            ["rqa_decomposition_assessments.id"],
            name=op.f(
                "fk_rqa_story_assessments_decomposition_assessment_id_rqa_decomposition_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_story_id"],
            ["rqa_user_stories.id"],
            name=op.f("fk_rqa_story_assessments_user_story_id_rqa_user_stories"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "decomposition_assessment_id",
            "user_story_id",
            name=op.f(
                "uq_rqa_story_assessments_decomposition_assessment_id_user_story_id"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_story_assessments_decomposition_assessment_id"),
        "rqa_story_assessments",
        ["decomposition_assessment_id"],
    )
    op.create_index(
        op.f("ix_rqa_story_assessments_user_story_id"),
        "rqa_story_assessments",
        ["user_story_id"],
    )

    # ── rqa_coverage_elements ────────────────────────────────────────
    op.create_table(
        "rqa_coverage_elements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decomposition_assessment_id", sa.Uuid(), nullable=False),
        sa.Column(
            "element_type",
            sa.String(32),
            sa.CheckConstraint(
                "element_type IN ("
                "'actor','trigger','precondition','main_action','input_data',"
                "'output_result','business_rule','constraint','permission_rule',"
                "'exception_behavior','error_handling','recovery_retry',"
                "'quality_constraint')",
                name=_ck("rqa_coverage_elements", "coverage_element_type"),
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "required", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("covered_by", JSONB, nullable=True),
        sa.Column(
            "coverage_result",
            sa.String(16),
            sa.CheckConstraint(
                "coverage_result IN ('Covered','Missing')",
                name=_ck("rqa_coverage_elements", "coverage_result"),
            ),
            nullable=False,
        ),
        sa.Column(
            "is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_coverage_elements")),
        sa.ForeignKeyConstraint(
            ["decomposition_assessment_id"],
            ["rqa_decomposition_assessments.id"],
            name=op.f(
                "fk_rqa_coverage_elements_decomposition_assessment_id_rqa_decomposition_assessments"
            ),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_rqa_coverage_elements_decomposition_assessment_id"),
        "rqa_coverage_elements",
        ["decomposition_assessment_id"],
    )

    # ── rqa_coverage_gate_checks ──────────────────────────────────────
    op.create_table(
        "rqa_coverage_gate_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decomposition_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("check_id", sa.String(4), nullable=False),
        sa.Column(
            "result",
            sa.String(16),
            sa.CheckConstraint(
                "result IN ('Pass','Fail')",
                name=_ck("rqa_coverage_gate_checks", "coverage_check_result"),
            ),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_coverage_gate_checks")),
        sa.ForeignKeyConstraint(
            ["decomposition_assessment_id"],
            ["rqa_decomposition_assessments.id"],
            name=op.f(
                "fk_rqa_coverage_gate_checks_decomposition_assessment_id_rqa_decomposition_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "decomposition_assessment_id",
            "check_id",
            name=op.f(
                "uq_rqa_coverage_gate_checks_decomposition_assessment_id_check_id"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_coverage_gate_checks_decomposition_assessment_id"),
        "rqa_coverage_gate_checks",
        ["decomposition_assessment_id"],
    )

    # ── rqa_feedbacks: link feedback to the run that generated it ────
    op.add_column(
        "rqa_feedbacks",
        sa.Column("decomposition_assessment_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f(
            "fk_rqa_feedbacks_decomposition_assessment_id_rqa_decomposition_assessments"
        ),
        "rqa_feedbacks",
        "rqa_decomposition_assessments",
        ["decomposition_assessment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_rqa_feedbacks_decomposition_assessment_id"),
        "rqa_feedbacks",
        ["decomposition_assessment_id"],
    )

    # ── rqa_user_stories: staleness tracking for PATCH edits ─────────
    op.add_column(
        "rqa_user_stories",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── drop orphaned pre-normalization JSONB-blob tables ────────────
    # Superseded by rqa_decomposition_assessments / rqa_user_stories; no
    # model references them (see app/models/__init__.py) and nothing reads
    # or joins them. IF EXISTS since some environments already cleaned
    # these up by hand before this migration was written.
    op.execute("DROP TABLE IF EXISTS decomposition_results")
    op.execute("DROP TABLE IF EXISTS user_stories")


def downgrade() -> None:
    # Reverting would discard every decomposition assessment, invest
    # validation, coverage element, and gate-check row persisted after this
    # migration (the truncate + legacy-table drop above are irreversible),
    # and recreating the dead JSONB-blob user_stories/decomposition_results
    # tables serves no purpose. Make the destructive operation explicit
    # instead, matching the precedent in
    # 2026_10_16_1130-f6a7b8c9d0e1_add_quality_assessment_history.py.
    raise RuntimeError(
        "Downgrade is blocked because it would discard decomposition "
        "assessment data and cannot restore the dropped legacy tables."
    )
