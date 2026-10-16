"""rqa normalized tables — replace JSONB blobs with relational schema

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-10-16 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def _ck(table: str, name: str) -> str:
    return f"ck_{table}_{name}"


def upgrade() -> None:
    # ── rqa_sprints ──────────────────────────────────────────────
    op.create_table(
        "rqa_sprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("sprint_number", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="planning"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_sprints")),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_rqa_sprints_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "project_id",
            "sprint_number",
            name=op.f("uq_rqa_sprints_project_id_sprint_number"),
        ),
    )
    op.create_index(op.f("ix_rqa_sprints_project_id"), "rqa_sprints", ["project_id"])

    # ── rqa_pipeline_sessions ────────────────────────────────────
    op.create_table(
        "rqa_pipeline_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("initiated_by", sa.Uuid(), nullable=False),
        sa.Column(
            "current_stage",
            sa.String(32),
            sa.CheckConstraint(
                "current_stage IN ("
                "'parsing','quality','decomposition','effort_estimation')",
                name=_ck("rqa_pipeline_sessions", "pipeline_stage"),
            ),
            nullable=False,
            server_default="parsing",
        ),
        sa.Column(
            "status",
            sa.String(32),
            sa.CheckConstraint(
                "status IN ('active','completed','failed')",
                name=_ck("rqa_pipeline_sessions", "session_status"),
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "dart_activation_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("overall_composite_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_pipeline_sessions")),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name=op.f("fk_rqa_pipeline_sessions_group_id_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_rqa_pipeline_sessions_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by"],
            ["users.id"],
            name=op.f("fk_rqa_pipeline_sessions_initiated_by_users"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "group_id",
            "version",
            name=op.f("uq_rqa_pipeline_sessions_group_id_version"),
        ),
    )
    op.create_index(
        op.f("ix_rqa_pipeline_sessions_group_id"),
        "rqa_pipeline_sessions",
        ["group_id"],
    )
    op.create_index(
        op.f("ix_rqa_pipeline_sessions_project_id"),
        "rqa_pipeline_sessions",
        ["project_id"],
    )
    op.create_index(
        op.f("ix_rqa_pipeline_sessions_initiated_by"),
        "rqa_pipeline_sessions",
        ["initiated_by"],
    )

    # ── rqa_srs_documents ────────────────────────────────────────
    op.create_table(
        "rqa_srs_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_file_path", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column(
            "parse_status",
            sa.String(32),
            sa.CheckConstraint(
                "parse_status IN ('pending','parsed','failed')",
                name=_ck("rqa_srs_documents", "parse_status"),
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "total_requirements_extracted",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("parse_error_message", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_srs_documents")),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f("fk_rqa_srs_documents_pipeline_session_id_rqa_pipeline_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name=op.f("fk_rqa_srs_documents_group_id_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            name=op.f("fk_rqa_srs_documents_uploaded_by_users"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "pipeline_session_id",
            name=op.f("uq_rqa_srs_documents_pipeline_session_id"),
        ),
    )
    op.create_index(
        op.f("ix_rqa_srs_documents_group_id"),
        "rqa_srs_documents",
        ["group_id"],
    )

    # ── rqa_requirements ─────────────────────────────────────────
    op.create_table(
        "rqa_requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("srs_document_id", sa.Uuid(), nullable=True),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_ref", sa.String(20), nullable=False),
        sa.Column(
            "requirement_category",
            sa.String(32),
            sa.CheckConstraint(
                "requirement_category IN ('functional','non_functional','constraint',"
                "'interface','performance','security','usability')",
                name=_ck("rqa_requirements", "requirement_category"),
            ),
            nullable=False,
            server_default="functional",
        ),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("section_reference", sa.String(100), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_requirements")),
        sa.ForeignKeyConstraint(
            ["srs_document_id"],
            ["rqa_srs_documents.id"],
            name=op.f("fk_rqa_requirements_srs_document_id_rqa_srs_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f("fk_rqa_requirements_pipeline_session_id_rqa_pipeline_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_rqa_requirements_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name=op.f("fk_rqa_requirements_group_id_groups"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_rqa_requirements_srs_document_id"),
        "rqa_requirements",
        ["srs_document_id"],
    )
    op.create_index(
        op.f("ix_rqa_requirements_pipeline_session_id"),
        "rqa_requirements",
        ["pipeline_session_id"],
    )
    op.create_index(
        op.f("ix_rqa_requirements_project_id"),
        "rqa_requirements",
        ["project_id"],
    )
    op.create_index(
        op.f("ix_rqa_requirements_group_id"),
        "rqa_requirements",
        ["group_id"],
    )

    # ── rqa_quality_assessments ──────────────────────────────────
    op.create_table(
        "rqa_quality_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("composite_score", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "confidence_level",
            sa.String(32),
            sa.CheckConstraint(
                "confidence_level IN ('high','moderate','low')",
                name=_ck("rqa_quality_assessments", "qa_confidence_level"),
            ),
            nullable=False,
        ),
        sa.Column("confidence_basis", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("relevant_quality_criterion", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("tools_invoked", JSONB, nullable=True),
        sa.Column(
            "assessment_status",
            sa.String(32),
            sa.CheckConstraint(
                "assessment_status IN ('pending','in_progress','completed','failed')",
                name=_ck("rqa_quality_assessments", "qa_assessment_status"),
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_quality_assessments")),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["rqa_requirements.id"],
            name=op.f("fk_rqa_quality_assessments_requirement_id_rqa_requirements"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_quality_assessments_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "requirement_id",
            "pipeline_session_id",
            name=op.f("uq_rqa_quality_assessments_requirement_id_pipeline_session_id"),
        ),
    )
    op.create_index(
        op.f("ix_rqa_quality_assessments_requirement_id"),
        "rqa_quality_assessments",
        ["requirement_id"],
    )
    op.create_index(
        op.f("ix_rqa_quality_assessments_pipeline_session_id"),
        "rqa_quality_assessments",
        ["pipeline_session_id"],
    )

    # ── rqa_quality_dimension_scores ─────────────────────────────
    op.create_table(
        "rqa_quality_dimension_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quality_assessment_id", sa.Uuid(), nullable=False),
        sa.Column(
            "dimension",
            sa.String(32),
            sa.CheckConstraint(
                "dimension IN ('clarity','completeness','correctness',"
                "'testability','consistency','traceability')",
                name=_ck("rqa_quality_dimension_scores", "quality_dimension"),
            ),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False, server_default="1.0"),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("relevant_standard_reference", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_quality_dimension_scores")),
        sa.ForeignKeyConstraint(
            ["quality_assessment_id"],
            ["rqa_quality_assessments.id"],
            name=op.f(
                "fk_rqa_quality_dimension_scores_quality_assessment_id_rqa_quality_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "quality_assessment_id",
            "dimension",
            name=op.f(
                "uq_rqa_quality_dimension_scores_quality_assessment_id_dimension"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_quality_dimension_scores_quality_assessment_id"),
        "rqa_quality_dimension_scores",
        ["quality_assessment_id"],
    )

    # ── rqa_quality_tool_outputs ─────────────────────────────────
    op.create_table(
        "rqa_quality_tool_outputs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quality_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("execution_order", sa.Integer(), nullable=False),
        sa.Column("input_summary", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            sa.CheckConstraint(
                "status IN ('success','failed','timeout','skipped')",
                name=_ck("rqa_quality_tool_outputs", "qa_tool_status"),
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_quality_tool_outputs")),
        sa.ForeignKeyConstraint(
            ["quality_assessment_id"],
            ["rqa_quality_assessments.id"],
            name=op.f(
                "fk_rqa_quality_tool_outputs_quality_assessment_id_rqa_quality_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "quality_assessment_id",
            "tool_name",
            name=op.f("uq_rqa_quality_tool_outputs_quality_assessment_id_tool_name"),
        ),
    )
    op.create_index(
        op.f("ix_rqa_quality_tool_outputs_quality_assessment_id"),
        "rqa_quality_tool_outputs",
        ["quality_assessment_id"],
    )

    # ── rqa_quality_gate_decisions ───────────────────────────────
    op.create_table(
        "rqa_quality_gate_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("composite_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("threshold", sa.Numeric(5, 2), nullable=False, server_default="75.0"),
        sa.Column(
            "decision",
            sa.String(32),
            sa.CheckConstraint(
                "decision IN ('pass','block')",
                name=_ck("rqa_quality_gate_decisions", "gate_decision"),
            ),
            nullable=False,
        ),
        sa.Column("total_requirements", sa.Integer(), nullable=False),
        sa.Column("requirements_above_threshold", sa.Integer(), nullable=False),
        sa.Column("requirements_below_threshold", sa.Integer(), nullable=False),
        sa.Column("blocking_dimensions", JSONB, nullable=True),
        sa.Column("gate_summary", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_quality_gate_decisions")),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_quality_gate_decisions_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "pipeline_session_id",
            name=op.f("uq_rqa_quality_gate_decisions_pipeline_session_id"),
        ),
    )

    # ── rqa_student_quality_self_assessments ─────────────────────
    op.create_table(
        "rqa_student_quality_self_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("assessed_by", sa.Uuid(), nullable=False),
        sa.Column(
            "dimension",
            sa.String(32),
            sa.CheckConstraint(
                "dimension IN ('clarity','completeness','correctness',"
                "'testability','consistency','traceability')",
                name=_ck(
                    "rqa_student_quality_self_assessments",
                    "self_assess_quality_dimension",
                ),
            ),
            nullable=False,
        ),
        sa.Column("student_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("student_justification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_rqa_student_quality_self_assessments"),
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["rqa_requirements.id"],
            name=op.f(
                "fk_rqa_student_quality_self_assessments_requirement_id_rqa_requirements"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_student_quality_self_assessments_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assessed_by"],
            ["users.id"],
            name=op.f("fk_rqa_student_quality_self_assessments_assessed_by_users"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "requirement_id",
            "pipeline_session_id",
            "dimension",
            name=op.f(
                "uq_rqa_student_quality_self_assessments_requirement_id_pipeline_session_id_dimension"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_student_quality_self_assessments_requirement_id"),
        "rqa_student_quality_self_assessments",
        ["requirement_id"],
    )
    op.create_index(
        op.f("ix_rqa_student_quality_self_assessments_pipeline_session_id"),
        "rqa_student_quality_self_assessments",
        ["pipeline_session_id"],
    )

    # ── rqa_user_stories ─────────────────────────────────────────
    op.create_table(
        "rqa_user_stories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("authored_by", sa.Uuid(), nullable=True),
        sa.Column("story_ref", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("as_a", sa.String(255), nullable=True),
        sa.Column("i_want", sa.String(500), nullable=True),
        sa.Column("so_that", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("acceptance_criteria", JSONB, nullable=True),
        sa.Column("student_story_points", sa.Integer(), nullable=True),
        sa.Column(
            "priority",
            sa.String(32),
            sa.CheckConstraint(
                "priority IN ('critical','high','medium','low')",
                name=_ck("rqa_user_stories", "story_priority"),
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_user_stories")),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["rqa_requirements.id"],
            name=op.f("fk_rqa_user_stories_requirement_id_rqa_requirements"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f("fk_rqa_user_stories_pipeline_session_id_rqa_pipeline_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["authored_by"],
            ["users.id"],
            name=op.f("fk_rqa_user_stories_authored_by_users"),
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        op.f("ix_rqa_user_stories_requirement_id"),
        "rqa_user_stories",
        ["requirement_id"],
    )
    op.create_index(
        op.f("ix_rqa_user_stories_pipeline_session_id"),
        "rqa_user_stories",
        ["pipeline_session_id"],
    )

    # ── rqa_invest_validations ───────────────────────────────────
    op.create_table(
        "rqa_invest_validations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_story_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "criterion",
            sa.String(32),
            sa.CheckConstraint(
                "criterion IN ('independent','negotiable','valuable',"
                "'estimable','small','testable')",
                name=_ck("rqa_invest_validations", "invest_criterion"),
            ),
            nullable=False,
        ),
        sa.Column("is_satisfied", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column(
            "validation_method", sa.String(32), nullable=False, server_default="hybrid"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_invest_validations")),
        sa.ForeignKeyConstraint(
            ["user_story_id"],
            ["rqa_user_stories.id"],
            name=op.f("fk_rqa_invest_validations_user_story_id_rqa_user_stories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_invest_validations_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_story_id",
            "criterion",
            name=op.f("uq_rqa_invest_validations_user_story_id_criterion"),
        ),
    )
    op.create_index(
        op.f("ix_rqa_invest_validations_user_story_id"),
        "rqa_invest_validations",
        ["user_story_id"],
    )
    op.create_index(
        op.f("ix_rqa_invest_validations_pipeline_session_id"),
        "rqa_invest_validations",
        ["pipeline_session_id"],
    )

    # ── rqa_decomposition_assessments ────────────────────────────
    op.create_table(
        "rqa_decomposition_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("composite_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("coverage_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("invest_composite_score", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "confidence_level",
            sa.String(32),
            sa.CheckConstraint(
                "confidence_level IN ('high','moderate','low')",
                name=_ck("rqa_decomposition_assessments", "dec_confidence_level"),
            ),
            nullable=False,
        ),
        sa.Column("confidence_basis", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("tools_invoked", JSONB, nullable=True),
        sa.Column(
            "stories_evaluated", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "stories_needing_revision", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "assessment_status",
            sa.String(32),
            sa.CheckConstraint(
                "assessment_status IN ('pending','in_progress','completed','failed')",
                name=_ck("rqa_decomposition_assessments", "dec_assessment_status"),
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_decomposition_assessments")),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["rqa_requirements.id"],
            name=op.f(
                "fk_rqa_decomposition_assessments_requirement_id_rqa_requirements"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_decomposition_assessments_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "requirement_id",
            "pipeline_session_id",
            name=op.f(
                "uq_rqa_decomposition_assessments_requirement_id_pipeline_session_id"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_decomposition_assessments_requirement_id"),
        "rqa_decomposition_assessments",
        ["requirement_id"],
    )
    op.create_index(
        op.f("ix_rqa_decomposition_assessments_pipeline_session_id"),
        "rqa_decomposition_assessments",
        ["pipeline_session_id"],
    )

    # ── rqa_coverage_analysis_results ────────────────────────────
    op.create_table(
        "rqa_coverage_analysis_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decomposition_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("overall_coverage_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("covered_aspects", JSONB, nullable=True),
        sa.Column("uncovered_gaps", JSONB, nullable=True),
        sa.Column("story_coverage_map", JSONB, nullable=True),
        sa.Column("semantic_similarity_scores", JSONB, nullable=True),
        sa.Column("highest_similarity", sa.Numeric(5, 4), nullable=True),
        sa.Column("lowest_similarity", sa.Numeric(5, 4), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_coverage_analysis_results")),
        sa.ForeignKeyConstraint(
            ["decomposition_assessment_id"],
            ["rqa_decomposition_assessments.id"],
            name=op.f(
                "fk_rqa_coverage_analysis_results_decomposition_assessment_id_rqa_decomposition_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["rqa_requirements.id"],
            name=op.f(
                "fk_rqa_coverage_analysis_results_requirement_id_rqa_requirements"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "decomposition_assessment_id",
            name=op.f("uq_rqa_coverage_analysis_results_decomposition_assessment_id"),
        ),
    )
    op.create_index(
        op.f("ix_rqa_coverage_analysis_results_requirement_id"),
        "rqa_coverage_analysis_results",
        ["requirement_id"],
    )

    # ── rqa_decomposition_tool_outputs ───────────────────────────
    op.create_table(
        "rqa_decomposition_tool_outputs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decomposition_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("execution_order", sa.Integer(), nullable=False),
        sa.Column("input_summary", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            sa.CheckConstraint(
                "status IN ('success','failed','timeout','skipped')",
                name=_ck("rqa_decomposition_tool_outputs", "dec_tool_status"),
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_decomposition_tool_outputs")),
        sa.ForeignKeyConstraint(
            ["decomposition_assessment_id"],
            ["rqa_decomposition_assessments.id"],
            name=op.f(
                "fk_rqa_decomposition_tool_outputs_decomposition_assessment_id_rqa_decomposition_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "decomposition_assessment_id",
            "tool_name",
            name=op.f(
                "uq_rqa_decomposition_tool_outputs_decomposition_assessment_id_tool_name"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_decomposition_tool_outputs_decomposition_assessment_id"),
        "rqa_decomposition_tool_outputs",
        ["decomposition_assessment_id"],
    )

    # ── rqa_student_effort_estimates ─────────────────────────────
    op.create_table(
        "rqa_student_effort_estimates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_story_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("estimated_by", sa.Uuid(), nullable=True),
        sa.Column("estimated_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("estimated_story_points", sa.Integer(), nullable=False),
        sa.Column("estimation_basis", sa.Text(), nullable=True),
        sa.Column(
            "estimation_technique",
            sa.String(32),
            sa.CheckConstraint(
                "estimation_technique IN ("
                "'planning_poker','t_shirt',"
                "'fibonacci','expert_judgment')",
                name=_ck("rqa_student_effort_estimates", "estimation_technique"),
            ),
            nullable=False,
            server_default="fibonacci",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_student_effort_estimates")),
        sa.ForeignKeyConstraint(
            ["user_story_id"],
            ["rqa_user_stories.id"],
            name=op.f("fk_rqa_student_effort_estimates_user_story_id_rqa_user_stories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_student_effort_estimates_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["estimated_by"],
            ["users.id"],
            name=op.f("fk_rqa_student_effort_estimates_estimated_by_users"),
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "user_story_id",
            "pipeline_session_id",
            name=op.f(
                "uq_rqa_student_effort_estimates_user_story_id_pipeline_session_id"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_student_effort_estimates_user_story_id"),
        "rqa_student_effort_estimates",
        ["user_story_id"],
    )
    op.create_index(
        op.f("ix_rqa_student_effort_estimates_pipeline_session_id"),
        "rqa_student_effort_estimates",
        ["pipeline_session_id"],
    )

    # ── rqa_estimate_comparisons ─────────────────────────────────
    op.create_table(
        "rqa_estimate_comparisons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_story_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("student_estimate_id", sa.Uuid(), nullable=True),
        sa.Column("ai_assessment_id", sa.Uuid(), nullable=True),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("student_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("ai_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("deviation_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("deviation_category", sa.String(32), nullable=True),
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
        sa.Column("final_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("final_story_points", sa.Integer(), nullable=False),
        sa.Column("final_decision_basis", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_estimate_comparisons")),
        sa.ForeignKeyConstraint(
            ["user_story_id"],
            ["rqa_user_stories.id"],
            name=op.f("fk_rqa_estimate_comparisons_user_story_id_rqa_user_stories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_estimate_comparisons_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_estimate_id"],
            ["rqa_student_effort_estimates.id"],
            name=op.f(
                "fk_rqa_estimate_comparisons_student_estimate_id_rqa_student_effort_estimates"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"],
            ["users.id"],
            name=op.f("fk_rqa_estimate_comparisons_decided_by_users"),
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "user_story_id",
            "pipeline_session_id",
            name=op.f("uq_rqa_estimate_comparisons_user_story_id_pipeline_session_id"),
        ),
    )
    op.create_index(
        op.f("ix_rqa_estimate_comparisons_user_story_id"),
        "rqa_estimate_comparisons",
        ["user_story_id"],
    )
    op.create_index(
        op.f("ix_rqa_estimate_comparisons_pipeline_session_id"),
        "rqa_estimate_comparisons",
        ["pipeline_session_id"],
    )

    # ── rqa_effort_estimation_assessments (placeholder) ──────────
    op.create_table(
        "rqa_effort_estimation_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_story_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("composite_score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "confidence_level",
            sa.String(32),
            sa.CheckConstraint(
                "confidence_level IN ('high','moderate','low')",
                name=_ck("rqa_effort_estimation_assessments", "eff_confidence_level"),
            ),
            nullable=True,
        ),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("tools_invoked", JSONB, nullable=True),
        sa.Column(
            "assessment_status",
            sa.String(32),
            sa.CheckConstraint(
                "assessment_status IN ('pending','in_progress','completed','failed')",
                name=_ck("rqa_effort_estimation_assessments", "eff_assessment_status"),
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_rqa_effort_estimation_assessments")
        ),
        sa.ForeignKeyConstraint(
            ["user_story_id"],
            ["rqa_user_stories.id"],
            name=op.f(
                "fk_rqa_effort_estimation_assessments_user_story_id_rqa_user_stories"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_effort_estimation_assessments_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_story_id",
            "pipeline_session_id",
            name=op.f(
                "uq_rqa_effort_estimation_assessments_user_story_id_pipeline_session_id"
            ),
        ),
    )
    op.create_index(
        op.f("ix_rqa_effort_estimation_assessments_user_story_id"),
        "rqa_effort_estimation_assessments",
        ["user_story_id"],
    )
    op.create_index(
        op.f("ix_rqa_effort_estimation_assessments_pipeline_session_id"),
        "rqa_effort_estimation_assessments",
        ["pipeline_session_id"],
    )

    # ── rqa_effort_tool_outputs (placeholder) ────────────────────
    op.create_table(
        "rqa_effort_tool_outputs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("execution_order", sa.Integer(), nullable=False),
        sa.Column("input_summary", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            sa.CheckConstraint(
                "status IN ('success','failed','timeout','skipped')",
                name=_ck("rqa_effort_tool_outputs", "eff_tool_status"),
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_effort_tool_outputs")),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["rqa_effort_estimation_assessments.id"],
            name=op.f(
                "fk_rqa_effort_tool_outputs_assessment_id_rqa_effort_estimation_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "tool_name",
            name=op.f("uq_rqa_effort_tool_outputs_assessment_id_tool_name"),
        ),
    )
    op.create_index(
        op.f("ix_rqa_effort_tool_outputs_assessment_id"),
        "rqa_effort_tool_outputs",
        ["assessment_id"],
    )

    # ── rqa_shap_explanations (placeholder) ──────────────────────
    op.create_table(
        "rqa_shap_explanations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("feature_name", sa.String(128), nullable=False),
        sa.Column("feature_value", sa.Numeric(10, 4), nullable=True),
        sa.Column("shap_value", sa.Numeric(10, 4), nullable=True),
        sa.Column("feature_importance_rank", sa.Integer(), nullable=True),
        sa.Column("direction", sa.String(16), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_shap_explanations")),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["rqa_effort_estimation_assessments.id"],
            name=op.f(
                "fk_rqa_shap_explanations_assessment_id_rqa_effort_estimation_assessments"
            ),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            name=op.f("uq_rqa_shap_explanations_assessment_id"),
        ),
    )

    # ── rqa_dart_sessions ────────────────────────────────────────
    op.create_table(
        "rqa_dart_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "triggering_stage",
            sa.String(32),
            sa.CheckConstraint(
                "triggering_stage IN ("
                "'parsing','quality','decomposition',"
                "'effort_estimation')",
                name=_ck("rqa_dart_sessions", "dart_triggering_stage"),
            ),
            nullable=False,
        ),
        sa.Column("triggering_assessment_id", sa.Uuid(), nullable=True),
        sa.Column("triggering_assessment_type", sa.String(16), nullable=True),
        sa.Column(
            "trigger_reason",
            sa.String(32),
            sa.CheckConstraint(
                "trigger_reason IN ('tool_conflict','low_confidence',"
                "'insufficient_evidence','cross_stage_conflict','score_divergence')",
                name=_ck("rqa_dart_sessions", "dart_trigger_reason"),
            ),
            nullable=False,
        ),
        sa.Column("trigger_description", sa.Text(), nullable=True),
        sa.Column("conflicting_tool_names", JSONB, nullable=True),
        sa.Column("conflicting_outputs_summary", JSONB, nullable=True),
        sa.Column(
            "diagnostic_hypothesis",
            sa.String(32),
            sa.CheckConstraint(
                "diagnostic_hypothesis IN ("
                "'compound','ambiguous','structural','novel')",
                name=_ck("rqa_dart_sessions", "dart_hypothesis"),
            ),
            nullable=True,
        ),
        sa.Column("hypothesis_justification", sa.Text(), nullable=True),
        sa.Column(
            "hypothesis_classified_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("resolution_strategy", sa.Text(), nullable=True),
        sa.Column("selected_resolution_tool", sa.String(100), nullable=True),
        sa.Column(
            "final_decision",
            sa.String(32),
            sa.CheckConstraint(
                "final_decision IN ('resolve','retrieve','re_route','escalate')",
                name=_ck("rqa_dart_sessions", "dart_decision"),
            ),
            nullable=True,
        ),
        sa.Column("final_decision_justification", sa.Text(), nullable=True),
        sa.Column("resolved_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("iteration_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sequence_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="30000"),
        sa.Column(
            "status",
            sa.String(32),
            sa.CheckConstraint(
                "status IN ('active','resolved','escalated',"
                "'timed_out','circuit_broken')",
                name=_ck("rqa_dart_sessions", "dart_status"),
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_dart_sessions")),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f("fk_rqa_dart_sessions_pipeline_session_id_rqa_pipeline_sessions"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_rqa_dart_sessions_pipeline_session_id"),
        "rqa_dart_sessions",
        ["pipeline_session_id"],
    )

    # ── rqa_dart_iterations ──────────────────────────────────────
    op.create_table(
        "rqa_dart_iterations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dart_session_id", sa.Uuid(), nullable=False),
        sa.Column("iteration_number", sa.Integer(), nullable=False),
        sa.Column("resolution_tool_used", sa.String(100), nullable=True),
        sa.Column("resolution_question", sa.Text(), nullable=True),
        sa.Column("resolution_input", JSONB, nullable=True),
        sa.Column("resolution_output", JSONB, nullable=True),
        sa.Column("confidence_before", sa.Numeric(5, 2), nullable=True),
        sa.Column("confidence_after", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_before", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_after", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "convergence_achieved", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("iteration_outcome", sa.String(32), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_dart_iterations")),
        sa.ForeignKeyConstraint(
            ["dart_session_id"],
            ["rqa_dart_sessions.id"],
            name=op.f("fk_rqa_dart_iterations_dart_session_id_rqa_dart_sessions"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "dart_session_id",
            "iteration_number",
            name=op.f("uq_rqa_dart_iterations_dart_session_id_iteration_number"),
        ),
    )
    op.create_index(
        op.f("ix_rqa_dart_iterations_dart_session_id"),
        "rqa_dart_iterations",
        ["dart_session_id"],
    )

    # ── rqa_dart_evidence ────────────────────────────────────────
    op.create_table(
        "rqa_dart_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dart_iteration_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", sa.String(64), nullable=False),
        sa.Column("source_tool", sa.String(100), nullable=True),
        sa.Column("source_collection", sa.String(100), nullable=True),
        sa.Column("evidence_data", JSONB, nullable=True),
        sa.Column("relevance_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("supports_hypothesis", sa.Boolean(), nullable=True),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_dart_evidence")),
        sa.ForeignKeyConstraint(
            ["dart_iteration_id"],
            ["rqa_dart_iterations.id"],
            name=op.f("fk_rqa_dart_evidence_dart_iteration_id_rqa_dart_iterations"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_rqa_dart_evidence_dart_iteration_id"),
        "rqa_dart_evidence",
        ["dart_iteration_id"],
    )

    # ── rqa_dart_escalations ─────────────────────────────────────
    op.create_table(
        "rqa_dart_escalations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dart_session_id", sa.Uuid(), nullable=False),
        sa.Column("escalated_to", sa.Uuid(), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("diagnostic_context", JSONB, nullable=True),
        sa.Column("original_conflicting_outputs", JSONB, nullable=True),
        sa.Column("iteration_history", JSONB, nullable=True),
        sa.Column("instructor_decision", sa.Text(), nullable=True),
        sa.Column("instructor_override_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("instructor_notes", sa.Text(), nullable=True),
        sa.Column("resolution_action", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_dart_escalations")),
        sa.ForeignKeyConstraint(
            ["dart_session_id"],
            ["rqa_dart_sessions.id"],
            name=op.f("fk_rqa_dart_escalations_dart_session_id_rqa_dart_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["escalated_to"],
            ["users.id"],
            name=op.f("fk_rqa_dart_escalations_escalated_to_users"),
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "dart_session_id",
            name=op.f("uq_rqa_dart_escalations_dart_session_id"),
        ),
    )

    # ── rqa_retrieval_logs ───────────────────────────────────────
    op.create_table(
        "rqa_retrieval_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "stage",
            sa.String(32),
            sa.CheckConstraint(
                "stage IN ('parsing','quality','decomposition','effort_estimation')",
                name=_ck("rqa_retrieval_logs", "retrieval_stage"),
            ),
            nullable=False,
        ),
        sa.Column("triggering_assessment_id", sa.Uuid(), nullable=True),
        sa.Column("triggering_assessment_type", sa.String(16), nullable=True),
        sa.Column("collection_name", sa.String(64), nullable=False),
        sa.Column("retrieval_decision", sa.String(16), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("results_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("top_similarity_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("retrieved_document_ids", JSONB, nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_retrieval_logs")),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_retrieval_logs_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_rqa_retrieval_logs_pipeline_session_id"),
        "rqa_retrieval_logs",
        ["pipeline_session_id"],
    )

    # ── rqa_sprint_backlog_items ─────────────────────────────────
    op.create_table(
        "rqa_sprint_backlog_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("user_story_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("sprint_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
        sa.Column(
            "task_type",
            sa.String(32),
            sa.CheckConstraint(
                "task_type IN ('story','task','subtask')",
                name=_ck("rqa_sprint_backlog_items", "backlog_task_type"),
            ),
            nullable=False,
            server_default="story",
        ),
        sa.Column("task_description", sa.Text(), nullable=True),
        sa.Column("final_story_points", sa.Integer(), nullable=False),
        sa.Column("final_estimated_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column(
            "priority",
            sa.String(32),
            sa.CheckConstraint(
                "priority IN ('critical','high','medium','low')",
                name=_ck("rqa_sprint_backlog_items", "backlog_priority"),
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "status",
            sa.String(32),
            sa.CheckConstraint(
                "status IN ('todo','in_progress','blocked','done')",
                name=_ck("rqa_sprint_backlog_items", "backlog_task_status"),
            ),
            nullable=False,
            server_default="todo",
        ),
        sa.Column(
            "estimation_source",
            sa.String(32),
            sa.CheckConstraint(
                "estimation_source IN ('student_only','ai_only','consensus')",
                name=_ck("rqa_sprint_backlog_items", "backlog_estimation_source"),
            ),
            nullable=False,
            server_default="student_only",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_sprint_backlog_items")),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_sprint_backlog_items_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_story_id"],
            ["rqa_user_stories.id"],
            name=op.f("fk_rqa_sprint_backlog_items_user_story_id_rqa_user_stories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["rqa_requirements.id"],
            name=op.f("fk_rqa_sprint_backlog_items_requirement_id_rqa_requirements"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sprint_id"],
            ["rqa_sprints.id"],
            name=op.f("fk_rqa_sprint_backlog_items_sprint_id_rqa_sprints"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to"],
            ["users.id"],
            name=op.f("fk_rqa_sprint_backlog_items_assigned_to_users"),
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        op.f("ix_rqa_sprint_backlog_items_pipeline_session_id"),
        "rqa_sprint_backlog_items",
        ["pipeline_session_id"],
    )
    op.create_index(
        op.f("ix_rqa_sprint_backlog_items_user_story_id"),
        "rqa_sprint_backlog_items",
        ["user_story_id"],
    )
    op.create_index(
        op.f("ix_rqa_sprint_backlog_items_requirement_id"),
        "rqa_sprint_backlog_items",
        ["requirement_id"],
    )
    op.create_index(
        op.f("ix_rqa_sprint_backlog_items_sprint_id"),
        "rqa_sprint_backlog_items",
        ["sprint_id"],
    )
    op.create_index(
        op.f("ix_rqa_sprint_backlog_items_assigned_to"),
        "rqa_sprint_backlog_items",
        ["assigned_to"],
    )

    # ── rqa_feedbacks ────────────────────────────────────────────
    op.create_table(
        "rqa_feedbacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=True),
        sa.Column("user_story_id", sa.Uuid(), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("dart_session_id", sa.Uuid(), nullable=True),
        sa.Column(
            "feedback_stage",
            sa.String(32),
            sa.CheckConstraint(
                "feedback_stage IN ('quality','decomposition','estimation','dart')",
                name=_ck("rqa_feedbacks", "feedback_stage"),
            ),
            nullable=False,
        ),
        sa.Column(
            "feedback_type",
            sa.String(64),
            sa.CheckConstraint(
                "feedback_type IN ('actionable_improvement','strength_acknowledgment',"
                "'standard_reference','learning_opportunity','revision_required')",
                name=_ck("rqa_feedbacks", "feedback_type"),
            ),
            nullable=False,
        ),
        sa.Column("feedback_text", sa.Text(), nullable=False),
        sa.Column("standard_reference", sa.String(255), nullable=True),
        sa.Column(
            "severity",
            sa.String(32),
            sa.CheckConstraint(
                "severity IN ('critical','high','medium','low','info')",
                name=_ck("rqa_feedbacks", "feedback_severity"),
            ),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "is_dart_generated", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("is_viewed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "is_acted_upon", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acted_upon_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_feedbacks")),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f("fk_rqa_feedbacks_pipeline_session_id_rqa_pipeline_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["rqa_requirements.id"],
            name=op.f("fk_rqa_feedbacks_requirement_id_rqa_requirements"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_story_id"],
            ["rqa_user_stories.id"],
            name=op.f("fk_rqa_feedbacks_user_story_id_rqa_user_stories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name=op.f("fk_rqa_feedbacks_target_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dart_session_id"],
            ["rqa_dart_sessions.id"],
            name=op.f("fk_rqa_feedbacks_dart_session_id_rqa_dart_sessions"),
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        op.f("ix_rqa_feedbacks_pipeline_session_id"),
        "rqa_feedbacks",
        ["pipeline_session_id"],
    )
    op.create_index(
        op.f("ix_rqa_feedbacks_requirement_id"),
        "rqa_feedbacks",
        ["requirement_id"],
    )
    op.create_index(
        op.f("ix_rqa_feedbacks_target_user_id"),
        "rqa_feedbacks",
        ["target_user_id"],
    )

    # ── rqa_instructor_alerts ────────────────────────────────────
    op.create_table(
        "rqa_instructor_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_session_id", sa.Uuid(), nullable=True),
        sa.Column("dart_escalation_id", sa.Uuid(), nullable=True),
        sa.Column("target_instructor_id", sa.Uuid(), nullable=False),
        sa.Column("related_student_id", sa.Uuid(), nullable=True),
        sa.Column("related_group_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column(
            "severity",
            sa.String(32),
            sa.CheckConstraint(
                "severity IN ('critical','high','medium','low','info')",
                name=_ck("rqa_instructor_alerts", "alert_severity"),
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rqa_instructor_alerts")),
        sa.ForeignKeyConstraint(
            ["pipeline_session_id"],
            ["rqa_pipeline_sessions.id"],
            name=op.f(
                "fk_rqa_instructor_alerts_pipeline_session_id_rqa_pipeline_sessions"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dart_escalation_id"],
            ["rqa_dart_escalations.id"],
            name=op.f(
                "fk_rqa_instructor_alerts_dart_escalation_id_rqa_dart_escalations"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_instructor_id"],
            ["users.id"],
            name=op.f("fk_rqa_instructor_alerts_target_instructor_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["related_student_id"],
            ["users.id"],
            name=op.f("fk_rqa_instructor_alerts_related_student_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_group_id"],
            ["groups.id"],
            name=op.f("fk_rqa_instructor_alerts_related_group_id_groups"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name=op.f("fk_rqa_instructor_alerts_resolved_by_users"),
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        op.f("ix_rqa_instructor_alerts_pipeline_session_id"),
        "rqa_instructor_alerts",
        ["pipeline_session_id"],
    )
    op.create_index(
        op.f("ix_rqa_instructor_alerts_target_instructor_id"),
        "rqa_instructor_alerts",
        ["target_instructor_id"],
    )

    # ── Drop old JSONB-blob tables ───────────────────────────────
    op.drop_table("sprint_tasks")
    op.drop_table("dart_cases")
    op.drop_table("decomposition_results")
    op.drop_table("user_stories")
    op.drop_table("requirement_quality_results")


def downgrade() -> None:
    # ── Recreate old JSONB-blob tables ───────────────────────────
    op.create_table(
        "requirement_quality_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("requirement_ref", sa.String(64), nullable=False),
        sa.Column("result", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_requirement_quality_results")),
    )
    op.create_table(
        "user_stories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("story_ref", sa.String(64), nullable=False),
        sa.Column("requirement_ref", sa.String(64), nullable=False),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_stories")),
    )
    op.create_table(
        "decomposition_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("requirement_ref", sa.String(64), nullable=False),
        sa.Column("result", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decomposition_results")),
    )
    op.create_table(
        "dart_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("requirement_ref", sa.String(64), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("result", JSONB, nullable=False),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dart_cases")),
    )
    op.create_table(
        "sprint_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("task_ref", sa.String(64), nullable=False),
        sa.Column("story_ref", sa.String(64), nullable=False),
        sa.Column("requirement_ref", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sprint_tasks")),
    )

    # ── Drop all new rqa_ tables in reverse dependency order ─────
    op.drop_table("rqa_instructor_alerts")
    op.drop_table("rqa_feedbacks")
    op.drop_table("rqa_sprint_backlog_items")
    op.drop_table("rqa_retrieval_logs")
    op.drop_table("rqa_dart_escalations")
    op.drop_table("rqa_dart_evidence")
    op.drop_table("rqa_dart_iterations")
    op.drop_table("rqa_dart_sessions")
    op.drop_table("rqa_shap_explanations")
    op.drop_table("rqa_effort_tool_outputs")
    op.drop_table("rqa_effort_estimation_assessments")
    op.drop_table("rqa_estimate_comparisons")
    op.drop_table("rqa_student_effort_estimates")
    op.drop_table("rqa_decomposition_tool_outputs")
    op.drop_table("rqa_coverage_analysis_results")
    op.drop_table("rqa_decomposition_assessments")
    op.drop_table("rqa_invest_validations")
    op.drop_table("rqa_user_stories")
    op.drop_table("rqa_student_quality_self_assessments")
    op.drop_table("rqa_quality_gate_decisions")
    op.drop_table("rqa_quality_tool_outputs")
    op.drop_table("rqa_quality_dimension_scores")
    op.drop_table("rqa_quality_assessments")
    op.drop_table("rqa_requirements")
    op.drop_table("rqa_srs_documents")
    op.drop_table("rqa_pipeline_sessions")
    op.drop_table("rqa_sprints")
