"""Repair user profile columns for databases stamped ahead of their schema.

Some local databases were stamped at the latest revision while retaining the
original ``users`` table.  Keep this migration idempotent so it is safe for
both those databases and databases where part of the profile schema exists.
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a5b6c7d8e9"
down_revision = ("e3f4a5b6c7d8", "c4f8a9b2d761")
branch_labels = None
depends_on = None


USER_COLUMNS = {
    "email": sa.String(length=320),
    "institution": sa.String(length=255),
    "department": sa.String(length=255),
    "title": sa.String(length=128),
    "github_username": sa.String(length=64),
    "consent_version": sa.String(length=32),
    "consent_at": sa.DateTime(timezone=True),
    "onboarding_completed_at": sa.DateTime(timezone=True),
    "picture_url": sa.String(length=1024),
    "avatar_updated_at": sa.DateTime(timezone=True),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("users")}

    for name, column_type in USER_COLUMNS.items():
        if name not in existing:
            op.add_column("users", sa.Column(name, column_type, nullable=True))

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_email" not in indexes:
        op.create_index("ix_users_email", "users", ["email"], unique=False)

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("users")
    }
    if "uq_users_github_username" not in unique_constraints:
        with op.batch_alter_table("users") as batch_op:
            batch_op.create_unique_constraint(
                "uq_users_github_username", ["github_username"]
            )


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_github_username", type_="unique")
        for name in reversed(tuple(USER_COLUMNS)):
            batch_op.drop_column(name)
