"""Add agent-designed review forms and answers (unapplied by this change).

Revision ID: c4f8a9b2d761
Revises: b8e1d7c3a9f4
"""
from alembic import op

revision = "c4f8a9b2d761"
down_revision = ("b3f1c9d8e7a6", "b8e1d7c3a9f4")
branch_labels = None
depends_on = None


def upgrade():
    if op.get_context().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE perf_reviews ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE perf_reviews ADD COLUMN IF NOT EXISTS summary text NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE perf_reviews ADD COLUMN IF NOT EXISTS severity text NOT NULL DEFAULT 'warn'")
    op.execute("ALTER TABLE perf_reviews ADD COLUMN IF NOT EXISTS form jsonb NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE perf_reviews ADD COLUMN IF NOT EXISTS answers jsonb")
    op.execute("ALTER TABLE perf_reviews ADD CONSTRAINT perf_reviews_severity_check CHECK (severity IN ('info', 'warn', 'critical'))")


def downgrade():
    if op.get_context().dialect.name != "postgresql":
        return
    for column in ("answers", "form", "severity", "summary", "title"):
        op.execute(f"ALTER TABLE perf_reviews DROP COLUMN IF EXISTS {column}")
