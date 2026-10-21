"""support multiple performance questions per student

Revision ID: b3f1c9d8e7a6
Revises: a7c3d5e91f02
"""
from alembic import op

revision = "b3f1c9d8e7a6"
down_revision = "a7c3d5e91f02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE perf_quizzes ADD COLUMN IF NOT EXISTS n integer NOT NULL DEFAULT 1 CHECK (n > 0)")
    op.execute("ALTER TABLE perf_quizzes ADD COLUMN IF NOT EXISTS of integer NOT NULL DEFAULT 1 CHECK (of > 0)")
    op.execute("ALTER TABLE perf_quizzes ADD COLUMN IF NOT EXISTS type text NOT NULL DEFAULT 'explain_behaviour'")
    op.execute("ALTER TABLE perf_quizzes ADD COLUMN IF NOT EXISTS batch_id text")
    op.execute("ALTER TABLE perf_quizzes DROP CONSTRAINT IF EXISTS perf_quizzes_team_ref_sprint_id_student_id_key")
    op.execute("ALTER TABLE perf_quizzes ADD CONSTRAINT perf_quizzes_team_sprint_student_n_key UNIQUE (team_ref, sprint_id, student_id, n)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_perf_quizzes_batch ON perf_quizzes (team_ref, sprint_id, student_id, batch_id)")


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE perf_quizzes DROP CONSTRAINT IF EXISTS perf_quizzes_team_sprint_student_n_key")
    op.execute("ALTER TABLE perf_quizzes ADD CONSTRAINT perf_quizzes_team_ref_sprint_id_student_id_key UNIQUE (team_ref, sprint_id, student_id)")
    op.execute("ALTER TABLE perf_quizzes DROP COLUMN IF EXISTS batch_id")
    op.execute("ALTER TABLE perf_quizzes DROP COLUMN IF EXISTS type")
    op.execute("ALTER TABLE perf_quizzes DROP COLUMN IF EXISTS of")
    op.execute("ALTER TABLE perf_quizzes DROP COLUMN IF EXISTS n")
