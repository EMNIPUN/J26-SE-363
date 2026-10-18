"""Replace random user-story references with immutable issue keys.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-10-22 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b9c0d1e2f3a4"
down_revision: str | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rqa_user_stories",
        sa.Column("legacy_story_ref", sa.String(length=20), nullable=True),
    )
    op.create_unique_constraint(
        op.f("uq_rqa_user_stories_pipeline_session_id_legacy_story_ref"),
        "rqa_user_stories",
        ["pipeline_session_id", "legacy_story_ref"],
    )
    op.execute("CREATE SEQUENCE IF NOT EXISTS rqa_user_story_ref_seq START WITH 1")
    op.execute(
        """
        WITH numbered AS (
            SELECT id, row_number() OVER (ORDER BY created_at, id) AS issue_number
            FROM rqa_user_stories
        )
        UPDATE rqa_user_stories AS story
        SET legacy_story_ref = story.story_ref,
            story_ref = 'SCRUM-' || numbered.issue_number::text
        FROM numbered
        WHERE story.id = numbered.id
        """
    )
    op.execute(
        """
        SELECT setval(
            'rqa_user_story_ref_seq',
            GREATEST((SELECT count(*) FROM rqa_user_stories), 1),
            (SELECT count(*) > 0 FROM rqa_user_stories)
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE rqa_user_stories
        SET story_ref = legacy_story_ref
        WHERE legacy_story_ref IS NOT NULL
        """
    )
    op.drop_constraint(
        op.f("uq_rqa_user_stories_pipeline_session_id_legacy_story_ref"),
        "rqa_user_stories",
        type_="unique",
    )
    op.drop_column("rqa_user_stories", "legacy_story_ref")
    op.execute("DROP SEQUENCE IF EXISTS rqa_user_story_ref_seq")
