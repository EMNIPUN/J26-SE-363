"""Enforce global uniqueness for public user-story issue keys.

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-10-22 09:10:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "c0d1e2f3a4b5"
down_revision: str | Sequence[str] | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_rqa_user_stories_story_ref"),
        "rqa_user_stories",
        ["story_ref"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_rqa_user_stories_story_ref"),
        "rqa_user_stories",
        type_="unique",
    )
