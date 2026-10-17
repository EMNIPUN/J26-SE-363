"""Alembic environment for the Core API database.

Target database, in order of precedence:
1. a connection passed in by code as `config.attributes["connection"]` (tests);
2. `uv run alembic -x db_url=postgresql+psycopg://... <command>` for one command;
3. SERVER_DIRECT_URL, else SERVER_DATABASE_URL, from the Core API settings
   (backend/server/.env). DDL needs a session connection, so prefer the direct URL.

Safety: online commands (upgrade, downgrade, stamp, current, ...) run only against a
local database (localhost, 127.0.0.1, ::1). Any other target, such as Supabase, is
refused before a connection is opened unless `-x allow_remote=true` is passed. A remote
`downgrade` additionally needs `-x allow_remote_downgrade=true`. A remote target is also
refused when it came from SERVER_DATABASE_URL (the Core API's URL, used only because
SERVER_DIRECT_URL is unset) or uses port 6543 (Supabase's transaction pooler). A Supabase
target must also set sslmode=verify-full and a usable sslrootcert in the URL. Offline SQL
generation (`--sql`) never connects and is not restricted.
"""

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL, Connection

import app.models  # noqa: F401  registers every model on Base.metadata
from app.core.config import settings
from app.database.base import Base
from app.database.migrations import include_object
from app.database.safety import (
    check_migration_target,
    check_schema_change_source,
    check_tls,
    describe,
    is_local,
    is_true,
    parse_url,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

logger = logging.getLogger("alembic.env")

target_metadata = Base.metadata


def x_arguments() -> dict[str, str]:
    return context.get_x_argument(as_dictionary=True)


def database_source() -> tuple[str, URL]:
    """(where the URL came from, the URL)."""
    sources = (
        ("-x db_url", x_arguments().get("db_url")),
        ("SERVER_DIRECT_URL", settings.SERVER_DIRECT_URL),
        ("SERVER_DATABASE_URL", settings.SERVER_DATABASE_URL),
    )
    for name, raw in sources:
        if raw:
            return name, parse_url(raw, name)
    raise RuntimeError(
        "No database URL: set SERVER_DIRECT_URL in backend/server/.env or pass -x db_url=..."
    )


def database_url() -> URL:
    return database_source()[1]


def configure_context(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Print the SQL (`--sql`) without connecting to the database."""
    configure_context(
        url=database_url(), literal_binds=True, dialect_opts={"paramstyle": "named"}
    )
    with context.begin_transaction():
        context.run_migrations()


def run_with_connection(connection: Connection) -> None:
    configure_context(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


def is_downgrade(url: URL) -> bool:
    """True for `downgrade`, from the CLI or alembic.command.downgrade().

    Alembic tells env.py which command runs only through the migration function, readable
    after configure(); configuring with a URL does not connect. A missing function counts
    as a downgrade so an unknown caller is held to the stricter rule.
    """
    context.configure(url=url)
    name = getattr(context.get_context().opts.get("fn"), "__name__", None)
    return name in (None, "downgrade")


def check_target(url: URL) -> bool:
    """Raise UnsafeDatabaseTarget unless the command may run on `url`; return is_downgrade."""
    x_args = x_arguments()
    downgrade = is_downgrade(url)
    check_migration_target(
        url,
        is_true(x_args.get("allow_remote")),
        downgrade=downgrade,
        allow_remote_downgrade=is_true(x_args.get("allow_remote_downgrade")),
    )
    return downgrade


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        check_target(connection.engine.url)
        run_with_connection(connection)
        return

    source, url = database_source()
    downgrade = check_target(url)
    check_schema_change_source(url, source, "-x db_url=...")
    check_tls(url)
    logger.info("Target database: %s", describe(url))
    if not is_local(url):
        logger.warning("Remote database allowed by -x allow_remote=true")
        if downgrade:
            logger.warning("Remote downgrade allowed by -x allow_remote_downgrade=true")
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        run_with_connection(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
