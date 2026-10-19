"""Persist reproducible decomposition component scores and evidence.

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("rqa_decomposition_assessments", sa.Column("coverage_component_score", sa.Numeric(3, 2), nullable=True))
    op.add_column("rqa_decomposition_assessments", sa.Column("story_acceptance_component_score", sa.Numeric(3, 2), nullable=True))
    op.add_column("rqa_decomposition_assessments", sa.Column("task_quality_component_score", sa.Numeric(3, 2), nullable=True))
    op.add_column("rqa_decomposition_assessments", sa.Column("assessment_evidence", sa.JSON(), nullable=True))
    op.add_column("rqa_coverage_gate_checks", sa.Column("suggestion", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("rqa_decomposition_assessments", "assessment_evidence")
    op.drop_column("rqa_coverage_gate_checks", "suggestion")
    op.drop_column("rqa_decomposition_assessments", "task_quality_component_score")
    op.drop_column("rqa_decomposition_assessments", "story_acceptance_component_score")
    op.drop_column("rqa_decomposition_assessments", "coverage_component_score")
