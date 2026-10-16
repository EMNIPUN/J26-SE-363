"""Store immutable revisions for requirement quality assessments.

Revision ID: f6a7b8c9d0e1
Revises: e1f2a3b4c5d6
Create Date: 2026-10-16 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE = "rqa_quality_assessments"
OLD_UNIQUE = "uq_rqa_quality_assessments_requirement_id_pipeline_session_id"
REVISION_UNIQUE = (
    "uq_rqa_quality_assessments_req_session_revision"
)
REVISION_INDEX = "ix_rqa_quality_assessments_requirement_session_revision"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column("revision_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        TABLE,
        sa.Column("requirement_text_snapshot", sa.Text(), nullable=True),
    )
    # Existing rows become revision 1 and retain the requirement text that was
    # current before history tracking was introduced.
    op.execute(
        """
        UPDATE rqa_quality_assessments AS assessment
        SET revision_number = 1,
            requirement_text_snapshot = requirement.requirement_text
        FROM rqa_requirements AS requirement
        WHERE requirement.id = assessment.requirement_id
        """
    )
    op.alter_column(TABLE, "revision_number", nullable=False)
    op.alter_column(TABLE, "requirement_text_snapshot", nullable=False)
    op.drop_constraint(OLD_UNIQUE, TABLE, type_="unique")
    op.create_unique_constraint(
        REVISION_UNIQUE,
        TABLE,
        ["requirement_id", "pipeline_session_id", "revision_number"],
    )
    op.create_index(
        REVISION_INDEX,
        TABLE,
        ["requirement_id", "pipeline_session_id", "revision_number"],
    )


def downgrade() -> None:
    # Reverting would require discarding every revision after v1. Keep the
    # history intact and make the destructive operation explicit instead.
    raise RuntimeError(
        "Downgrade is blocked because it would discard quality assessment history."
    )
