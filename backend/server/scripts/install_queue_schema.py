"""Install Procrastinate's job-queue schema, after the same target checks as Alembic.

This is the only supported way to install the queue schema: `procrastinate
--app=shared.queue.app schema --apply` is disabled (see shared/queue.py). Run from backend/server/
after `alembic upgrade head`, then secure the new objects with scripts.secure_queue_schema:

    uv run python -m scripts.install_queue_schema
    uv run python -m scripts.install_queue_schema --allow-remote    # Supabase, after the preflight

The target is --db-url, else SERVER_DIRECT_URL, else SERVER_DATABASE_URL from the Core API settings
(backend/server/.env, found by its absolute path, so the current folder doesn't pick the
credentials). Before any connection is opened it refuses: a URL that isn't PostgreSQL; a non-local
database without --allow-remote; a remote target that came from SERVER_DATABASE_URL or uses port
6543 (Supabase's transaction pooler); and a Supabase URL without sslmode=verify-full and a usable
sslrootcert.

It then runs the installed Procrastinate version's schema.sql in one transaction, with
search_path set to public. If public.procrastinate_jobs already exists it changes nothing. Output
never contains a user name, a password or the URL; database errors show only the error class and
SQLSTATE.
"""

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version as package_version

from procrastinate.schema import SchemaManager
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from app.database.safety import (
    UnsafeDatabaseTarget,
    check_schema_change_source,
    check_tls,
    describe,
    is_local,
)
from scripts.secure_queue_schema import (
    LOCK_TIMEOUT,
    check_target,
    safe_error_summary,
    target_source,
)

Q_INSTALLED = text("SELECT pg_catalog.to_regclass('public.procrastinate_jobs') IS NOT NULL")
NEXT_STEPS = (
    "Next: uv run python -m scripts.secure_queue_schema --check, then --apply, then --check again."
)


def install_schema(engine: Engine) -> int:
    with engine.begin() as connection:
        connection.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
        # schema.sql creates unqualified objects in the first listed schema, so that must be public.
        # pg_catalog is still searched first implicitly, so built-ins can't be shadowed.
        connection.execute(text("SET LOCAL search_path = public"))
        if connection.execute(Q_INSTALLED).scalar_one():
            print("Queue schema is already installed (public.procrastinate_jobs exists); nothing was changed.")
            print(NEXT_STEPS)
            return 0
        # Without parameters psycopg sends schema.sql as is; its % signs must not be read as placeholders.
        connection.exec_driver_sql(
            SchemaManager.get_schema(), execution_options={"no_parameters": True}
        )
    print(f"Queue schema installed (Procrastinate {package_version('procrastinate')}).")
    print(NEXT_STEPS)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.install_queue_schema",
        description="Install Procrastinate's job-queue schema after checking the target database.",
    )
    parser.add_argument("--db-url", help="target database (default: SERVER_DIRECT_URL, then SERVER_DATABASE_URL)")
    parser.add_argument("--allow-remote", action="store_true", help="allow a non-local database")
    args = parser.parse_args(argv)

    try:
        source, url = target_source(args.db_url)
        check_target(url, args.allow_remote)
        check_schema_change_source(url, source, "--db-url")
        check_tls(url)
    except UnsafeDatabaseTarget as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    print(f"Target database: {describe(url)} (from {source})")
    if not is_local(url):
        print("WARNING: remote database allowed by --allow-remote", file=sys.stderr)

    engine = create_engine(url, poolclass=NullPool)
    try:
        return install_schema(engine)
    except DBAPIError as error:
        print(f"ERROR: {safe_error_summary(error)}; nothing was changed", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
