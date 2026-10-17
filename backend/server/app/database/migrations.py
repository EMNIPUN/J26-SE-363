"""Alembic filters: Core API migrations manage only the tables declared in app.models."""

from typing import Any

# Procrastinate (the job queue) creates and upgrades its own tables in the same database.
PROCRASTINATE_TABLE_PREFIX = "procrastinate_"


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    """`include_object` hook for Alembic's autogenerate."""
    if type_ != "table":
        return True
    if name and name.startswith(PROCRASTINATE_TABLE_PREFIX):
        return False
    # A table that exists in the database but has no model (another tool's table):
    # never generate a DROP for it.
    return not (reflected and compare_to is None)
