"""Missing or blank database/queue URLs must fail clearly, never fall back to a default database.

Nothing here connects: create_engine and the Procrastinate parent connector are replaced, or the
real create_engine is used only to build an engine (which doesn't connect).
"""

import logging
from pathlib import Path
from urllib.parse import quote

import procrastinate
import pytest
import sqlalchemy
from procrastinate import cli as procrastinate_cli
from procrastinate.schema import SchemaManager
from procrastinate.testing import InMemoryConnector
from shared import queue
from shared.queue import (
    GuardedSchemaManager,
    QueueApp,
    QueueConfigurationError,
    QueueConnector,
    QueueSchemaInstallRefused,
    get_dsn,
)
from shared.queue import app as procrastinate_app
from sqlalchemy.exc import OperationalError

from app.core.config import Settings, settings
from app.database import session
from app.database.session import DatabaseConfigurationError
from app.main import app, lifespan

DATABASE_VARIABLES = (
    "SERVER_DATABASE_URL",
    "SERVER_DIRECT_URL",
    "SERVER_POSTGRES_USER",
    "SERVER_POSTGRES_PASSWORD",
    "SERVER_POSTGRES_HOST",
    "SERVER_POSTGRES_PORT",
    "SERVER_POSTGRES_DB",
)
POOLER_URL = "postgresql+psycopg://selvia_user:not-a-real-secret@localhost:6543/selvia"
DIRECT_URL = "postgresql+psycopg://selvia_user:not-a-real-secret@localhost:5432/selvia"
BLANK_VALUES = ["", "   "]
# Supabase-shaped fakes (nothing connects): not a real project, user or password.
SUPABASE_BASE = "postgresql+psycopg://postgres.mockref:not-a-real-secret@aws-0-mock.pooler.supabase.com:6543/postgres"
SECRET_PARTS = ("not-a-real-secret", "selvia_user", "mockref", "aws-0-mock")
CA_FILE = str(Path(__file__).resolve().parent / "fixtures" / "preflight_placeholder_ca.pem")
VERIFIED_QUERY = f"sslmode=verify-full&sslrootcert={quote(CA_FILE, safe='')}"
SUPABASE_VERIFIED = f"{SUPABASE_BASE}?{VERIFIED_QUERY}"


@pytest.fixture
def clean_environment(monkeypatch):
    """Hide any database variables already loaded from backend/server/.env."""
    for name in DATABASE_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def make_settings(**values) -> Settings:
    return Settings(_env_file=None, **values)


# --- Core API settings ---------------------------------------------------------------


@pytest.mark.parametrize("blank", BLANK_VALUES)
def test_blank_database_urls_count_as_unset(clean_environment, blank):
    loaded = make_settings(SERVER_DATABASE_URL=blank, SERVER_DIRECT_URL=blank)

    assert loaded.SERVER_DATABASE_URL is None
    assert loaded.SERVER_DIRECT_URL is None


@pytest.mark.parametrize("blank", BLANK_VALUES)
def test_blank_database_url_in_the_environment_counts_as_unset(clean_environment, monkeypatch, blank):
    monkeypatch.setenv("SERVER_DATABASE_URL", blank)

    assert make_settings().SERVER_DATABASE_URL is None


def test_blank_database_url_still_falls_back_to_the_individual_parts(clean_environment):
    loaded = make_settings(
        SERVER_DATABASE_URL=" ",
        SERVER_POSTGRES_USER="selvia_user",
        SERVER_POSTGRES_PASSWORD="not-a-real-secret",
        SERVER_POSTGRES_DB="selvia",
    )

    assert loaded.SERVER_DATABASE_URL == (
        "postgresql+psycopg://selvia_user:not-a-real-secret@localhost:5433/selvia"
    )


def test_configured_database_urls_are_kept(clean_environment):
    loaded = make_settings(SERVER_DATABASE_URL=POOLER_URL, SERVER_DIRECT_URL=DIRECT_URL)

    assert loaded.SERVER_DATABASE_URL == POOLER_URL
    assert loaded.SERVER_DIRECT_URL == DIRECT_URL


# --- Core API engine -----------------------------------------------------------------


@pytest.fixture
def engine_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(session, "_engine", None)
    monkeypatch.setattr(session, "create_engine", lambda url, **kwargs: calls.append(url) or object())
    return calls


@pytest.mark.parametrize("missing", [None, *BLANK_VALUES])
def test_engine_without_database_url_fails_clearly(engine_calls, monkeypatch, missing):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", missing)

    with pytest.raises(DatabaseConfigurationError, match="SERVER_DATABASE_URL"):
        session.get_engine()

    assert engine_calls == []


def test_engine_uses_the_configured_database_url(engine_calls, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", POOLER_URL)

    session.get_engine()

    assert engine_calls == [POOLER_URL]


def test_health_check_reports_missing_database_url_as_down(engine_calls, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", None)

    assert session.check_db_connection() is False
    assert engine_calls == []


# --- Core API engine TLS ----------------------------------------------------------------


@pytest.fixture
def engine_kwargs(monkeypatch):
    """Record create_engine's arguments without building an engine."""
    calls = []
    monkeypatch.setattr(session, "_engine", None)
    monkeypatch.setattr(
        session, "create_engine", lambda url, **kwargs: calls.append((url, kwargs)) or object()
    )
    return calls


def test_a_verified_supabase_url_is_passed_on_unchanged(engine_kwargs, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", SUPABASE_VERIFIED)

    session.get_engine()

    [(url, kwargs)] = engine_kwargs
    assert url == SUPABASE_VERIFIED
    assert "connect_args" not in kwargs


@pytest.fixture
def real_engine(monkeypatch):
    """The real create_engine: building an engine parses the URL but never connects."""
    monkeypatch.setattr(session, "_engine", None)
    built = []

    def build(url, **kwargs):
        engine = sqlalchemy.create_engine(url, **kwargs)
        built.append(engine)
        return engine

    monkeypatch.setattr(session, "create_engine", build)
    yield built
    for engine in built:
        engine.dispose()


def test_verify_full_and_the_root_certificate_reach_psycopg(real_engine, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", SUPABASE_VERIFIED)

    engine = session.get_engine()

    _, params = engine.dialect.create_connect_args(engine.url)
    assert params["sslmode"] == "verify-full"
    assert params["sslrootcert"] == CA_FILE
    assert engine.dialect.driver == "psycopg"


def test_a_local_url_gets_no_tls_settings_added(real_engine, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", DIRECT_URL)

    engine = session.get_engine()

    _, params = engine.dialect.create_connect_args(engine.url)
    assert "sslmode" not in params and "sslrootcert" not in params


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ("", "no sslmode"),
        ("?sslmode=require", "sslmode=require"),
        ("?sslmode=verify-ca", "sslmode=verify-ca"),
        ("?sslmode=verify-full", "needs sslrootcert"),
        (f"?sslmode=verify-full&sslrootcert={quote(CA_FILE + '.missing', safe='')}", "does not exist"),
    ],
)
def test_unsafe_supabase_tls_is_refused_before_an_engine_exists(engine_kwargs, monkeypatch, query, message):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", f"{SUPABASE_BASE}{query}")

    with pytest.raises(DatabaseConfigurationError) as excinfo:
        session.get_engine()

    assert engine_kwargs == []
    text = str(excinfo.value)
    assert message in text
    assert not any(part in text for part in SECRET_PARTS)
    assert "preflight_placeholder_ca" not in text


def test_an_invalid_database_url_is_refused_without_echoing_it(engine_kwargs, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", "not a url with not-a-real-secret inside")

    with pytest.raises(DatabaseConfigurationError) as excinfo:
        session.get_engine()

    assert engine_kwargs == []
    assert "not-a-real-secret" not in str(excinfo.value)


def test_health_check_reports_unsafe_tls_as_down(engine_kwargs, monkeypatch, caplog):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", f"{SUPABASE_BASE}?sslmode=require")

    with caplog.at_level(logging.ERROR, logger=session.logger.name):
        assert session.check_db_connection() is False

    assert engine_kwargs == []
    assert "sslmode=verify-full" in caplog.text
    assert not any(part in caplog.text for part in SECRET_PARTS)


class FakeDriverError(Exception):
    sqlstate = "08006"


def test_health_check_never_logs_driver_messages(monkeypatch, caplog):
    message = (
        'connection to server at "aws-0-mock.pooler.supabase.com" failed: FATAL: password '
        'authentication failed for user "postgres.mockref" (not-a-real-secret)'
    )

    class FailingEngine:
        def connect(self):
            raise OperationalError("SELECT 1", {}, FakeDriverError(message))

    monkeypatch.setattr(session, "get_engine", lambda: FailingEngine())

    with caplog.at_level(logging.ERROR, logger=session.logger.name):
        assert session.check_db_connection() is False

    assert "OperationalError" in caplog.text and "SQLSTATE 08006" in caplog.text
    assert not any(part in caplog.text for part in SECRET_PARTS)


# --- job queue DSN -------------------------------------------------------------------


def test_queue_dsn_prefers_the_direct_url(clean_environment, monkeypatch):
    monkeypatch.setenv("SERVER_DIRECT_URL", DIRECT_URL)
    monkeypatch.setenv("SERVER_DATABASE_URL", POOLER_URL)

    assert get_dsn() == "postgresql://selvia_user:not-a-real-secret@localhost:5432/selvia"


@pytest.mark.parametrize("blank", BLANK_VALUES)
def test_blank_direct_url_falls_through_to_the_database_url(clean_environment, monkeypatch, blank):
    monkeypatch.setenv("SERVER_DIRECT_URL", blank)
    monkeypatch.setenv("SERVER_DATABASE_URL", POOLER_URL)

    assert get_dsn() == "postgresql://selvia_user:not-a-real-secret@localhost:6543/selvia"


@pytest.mark.parametrize("blank", [None, *BLANK_VALUES])
def test_queue_dsn_is_empty_when_nothing_is_configured(clean_environment, monkeypatch, blank):
    if blank is not None:
        monkeypatch.setenv("SERVER_DIRECT_URL", blank)
        monkeypatch.setenv("SERVER_DATABASE_URL", blank)

    assert get_dsn() == ""


# --- job queue connector -------------------------------------------------------------


@pytest.fixture
def parent_open_calls(monkeypatch):
    """Replace PsycopgConnector.open_async so no pool is created and nothing connects."""
    calls = []

    async def fake_open_async(self, pool=None):
        calls.append(pool)

    monkeypatch.setattr(procrastinate.PsycopgConnector, "open_async", fake_open_async)
    return calls


def test_core_api_queue_uses_the_guarded_connector():
    assert isinstance(procrastinate_app.connector, QueueConnector)
    assert queue.app is procrastinate_app


@pytest.mark.asyncio
@pytest.mark.parametrize("blank", BLANK_VALUES)
async def test_queue_without_url_refuses_to_open(parent_open_calls, blank):
    with pytest.raises(QueueConfigurationError) as excinfo:
        await QueueConnector(conninfo=blank).open_async()

    assert parent_open_calls == []
    assert "SERVER_DIRECT_URL" in str(excinfo.value)
    assert "SERVER_DATABASE_URL" in str(excinfo.value)


@pytest.mark.asyncio
async def test_queue_with_url_opens(parent_open_calls):
    await QueueConnector(conninfo="postgresql://localhost/selvia").open_async()

    assert parent_open_calls == [None]


@pytest.mark.asyncio
async def test_queue_with_an_external_pool_does_not_need_a_url(parent_open_calls):
    pool = object()

    await QueueConnector(conninfo="").open_async(pool)

    assert parent_open_calls == [pool]


def test_sync_queue_use_without_url_fails_clearly():
    with pytest.raises(QueueConfigurationError):
        QueueConnector(conninfo=" ").get_sync_connector()


QUEUE_SUPABASE = SUPABASE_BASE.replace("postgresql+psycopg://", "postgresql://").replace(":6543/", ":5432/")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "conninfo",
    [
        QUEUE_SUPABASE,
        f"{QUEUE_SUPABASE}?sslmode=require",
        f"{QUEUE_SUPABASE}?sslmode=verify-ca&sslrootcert=ca.crt",
        f"{QUEUE_SUPABASE}?sslmode=verify-full",
        "host=aws-0-mock.pooler.supabase.com dbname=postgres sslmode=require",
    ],
)
async def test_queue_refuses_supabase_without_verified_tls(parent_open_calls, conninfo):
    with pytest.raises(QueueConfigurationError) as excinfo:
        await QueueConnector(conninfo=conninfo).open_async()

    assert parent_open_calls == []
    assert "sslmode=verify-full" in str(excinfo.value)
    assert not any(part in str(excinfo.value) for part in SECRET_PARTS)


def test_sync_queue_use_also_checks_tls():
    with pytest.raises(QueueConfigurationError):
        QueueConnector(conninfo=f"{QUEUE_SUPABASE}?sslmode=require").get_sync_connector()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "conninfo",
    [
        f"{QUEUE_SUPABASE}?{VERIFIED_QUERY}",
        "postgresql://selvia_user:not-a-real-secret@localhost:5433/selvia_server_db",
        "postgresql://u:p@db.example.com/selvia?sslmode=require",
    ],
)
async def test_queue_opens_with_verified_supabase_tls_or_a_non_supabase_url(parent_open_calls, conninfo):
    await QueueConnector(conninfo=conninfo).open_async()

    assert parent_open_calls == [None]


@pytest.mark.asyncio
async def test_queue_refuses_an_invalid_connection_string_without_echoing_it(parent_open_calls):
    with pytest.raises(QueueConfigurationError) as excinfo:
        await QueueConnector(conninfo="host=localhost password='not-a-real-secret").open_async()

    assert parent_open_calls == []
    assert "not-a-real-secret" not in str(excinfo.value)


# --- queue schema installation guard ---------------------------------------------------


def test_the_shared_app_uses_the_guarded_schema_manager():
    assert isinstance(procrastinate_app, QueueApp)
    assert isinstance(procrastinate_app.schema_manager, GuardedSchemaManager)
    assert procrastinate_app.schema_manager.get_schema() == SchemaManager.get_schema()


@pytest.mark.asyncio
async def test_applying_the_schema_through_the_shared_app_is_refused():
    connector = InMemoryConnector()

    with procrastinate_app.replace_connector(connector):
        with pytest.raises(QueueSchemaInstallRefused) as excinfo:
            await procrastinate_app.schema_manager.apply_schema_async()
        with pytest.raises(QueueSchemaInstallRefused):
            procrastinate_app.schema_manager.apply_schema()

    assert connector.queries == []
    assert "scripts.install_queue_schema" in str(excinfo.value)


@pytest.mark.asyncio
async def test_the_procrastinate_cli_schema_apply_is_refused(capsys):
    connector = InMemoryConnector()
    parsed = procrastinate_cli.parse_args(["--app", "shared.queue.app", "schema", "--apply"])
    for name in ("verbose", "log_level", "log_format", "log_format_style"):
        parsed.pop(name, None)

    with procrastinate_app.replace_connector(connector), pytest.raises(SystemExit) as excinfo:
        await procrastinate_cli.execute_command(parsed)

    assert excinfo.value.code == 1
    assert not any(name == "apply_schema" for name, _ in connector.queries)
    assert "scripts.install_queue_schema" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_the_procrastinate_cli_can_still_print_the_schema(capsys):
    parsed = procrastinate_cli.parse_args(["--app", "shared.queue.app", "schema", "--read"])
    for name in ("verbose", "log_level", "log_format", "log_format_style"):
        parsed.pop(name, None)

    with procrastinate_app.replace_connector(InMemoryConnector()):
        await procrastinate_cli.execute_command(parsed)

    assert "procrastinate_jobs" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_core_api_startup_fails_clearly_without_queue_url(parent_open_calls):
    with (
        procrastinate_app.replace_connector(QueueConnector(conninfo="")),
        pytest.raises(QueueConfigurationError),
    ):
        async with lifespan(app):
            pass

    assert parent_open_calls == []
