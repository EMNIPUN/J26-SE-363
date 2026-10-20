"""Widen Backlog Readiness Passport diagnostic status fields.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_STATUS_COLUMNS = (
    "quality_status",
    "coverage_status",
    "invest_status",
    "estimation_status",
    "dart_status",
)


def upgrade() -> None:
    for column in _STATUS_COLUMNS:
        op.alter_column(
            "rqa_backlog_passports",
            column,
            existing_type=sa.String(length=64),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade() -> None:
    for column in _STATUS_COLUMNS:
        op.alter_column(
            "rqa_backlog_passports",
            column,
            existing_type=sa.Text(),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
