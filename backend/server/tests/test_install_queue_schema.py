"""Tests for scripts/install_queue_schema.py.

Fake engines only, except the last test, which needs SERVER_TEST_DATABASE_URL (a local, disposable
`*_test` database) and is skipped without it.
"""

from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import pytest
from procrastinate.schema import SchemaManager
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from scripts import install_queue_schema as iqs

REMOTE_URL = "postgresql+psycopg://selvia_user:not-a-real-secret@db.example.invalid:5432/postgres"
LOCAL_URL = "postgresql+psycopg://selvia_user:not-a-real-secret@localhost:5432/selvia_migration_test"
# Supabase-shaped fake: never connected to (create_engine is replaced).
SUPABASE_URL = "postgresql+psycopg://postgres.mockref:not-a-real-secret@aws-0-mock.pooler.supabase.com:5432/postgres"
CA_FILE = str(Path(__file__).resolve().parent / "fixtures" / "preflight_placeholder_ca.pem")
SUPABASE_VERIFIED = f"{SUPABASE_URL}?sslmode=verify-full&sslrootcert={quote(CA_FILE, safe='')}"
SECRET_PARTS = ("not-a-real-secret", "selvia_user", "mockref")


# --- fakes ----------------------------------------------------------------------------


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeConnection:
    def __init__(self, installed):
        self.installed = installed
        self.executed = []
        self.driver_sql = []

    def execute(self, statement, params=None):
        self.executed.append(str(statement))
        return FakeResult(self.installed if statement is iqs.Q_INSTALLED else None)

    def exec_driver_sql(self, statement, parameters=None, execution_options=None):
        self.driver_sql.append((statement, parameters, execution_options))
        self.installed = True


class FakeEngine:
    def __init__(self, installed=False):
        self.connection = FakeConnection(installed)
        self.begun = 0
        self.committed = False
        self.disposed = False

    @contextmanager
    def connect(self):
        raise AssertionError("the installer only uses engine.begin()")
        yield

    @contextmanager
    def begin(self):
        self.begun += 1
        yield self.connection
        self.committed = True

    def dispose(self):
        self.disposed = True


# --- installing ---------------------------------------------------------------------------


def test_a_fresh_database_gets_procrastinates_schema_in_one_transaction(capsys):
    engine = FakeEngine(installed=False)

    assert iqs.install_schema(engine) == 0

    assert engine.begun == 1 and engine.committed
    [(statement, parameters, options)] = engine.connection.driver_sql
    assert statement == SchemaManager.get_schema()
    assert parameters is None
    assert options == {"no_parameters": True}
    executed = engine.connection.executed
    assert executed[0].startswith("SET LOCAL lock_timeout")
    assert executed[1] == "SET LOCAL search_path = public"
    out = capsys.readouterr().out
    assert "Queue schema installed" in out
    assert "scripts.secure_queue_schema --check" in out


def test_an_installed_schema_is_left_alone(capsys):
    engine = FakeEngine(installed=True)

    assert iqs.install_schema(engine) == 0

    assert engine.connection.driver_sql == []
    assert "already installed" in capsys.readouterr().out


# --- target guard (main) ----------------------------------------------------------------


class ConnectAttempted(Exception):
    """Raised by the fake create_engine: the guard let the command through."""


@pytest.fixture
def no_real_connections(monkeypatch):
    attempts = []

    def fake_create_engine(url, **kwargs):
        attempts.append(make_url(url))
        raise ConnectAttempted

    monkeypatch.setattr(iqs, "create_engine", fake_create_engine)
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", None)
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", None)
    return attempts


def test_local_target_needs_no_opt_in(no_real_connections, capsys):
    with pytest.raises(ConnectAttempted):
        iqs.main(["--db-url", LOCAL_URL])

    assert [url.database for url in no_real_connections] == ["selvia_migration_test"]
    assert "Target database: postgresql localhost:5432/selvia_migration_test (from --db-url)" in capsys.readouterr().out


def test_local_settings_url_is_used(no_real_connections, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", LOCAL_URL)

    with pytest.raises(ConnectAttempted):
        iqs.main([])

    assert [url.database for url in no_real_connections] == ["selvia_migration_test"]


def test_remote_target_is_refused_without_opt_in(no_real_connections, capsys):
    assert iqs.main(["--db-url", REMOTE_URL]) == 2

    assert no_real_connections == []
    err = capsys.readouterr().err
    assert "--allow-remote" in err
    assert not any(part in err for part in SECRET_PARTS)


@pytest.mark.parametrize("setting", ["SERVER_DIRECT_URL", "SERVER_DATABASE_URL"])
def test_remote_url_from_settings_is_refused_without_opt_in(no_real_connections, monkeypatch, setting):
    monkeypatch.setattr(settings, setting, REMOTE_URL)

    assert iqs.main([]) == 2
    assert no_real_connections == []


def test_remote_fallback_to_the_app_url_is_refused_even_with_opt_in(no_real_connections, monkeypatch, capsys):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", REMOTE_URL)

    assert iqs.main(["--allow-remote"]) == 2
    assert no_real_connections == []
    assert "SERVER_DIRECT_URL is not set" in capsys.readouterr().err


@pytest.mark.parametrize("via_settings", [True, False], ids=["SERVER_DIRECT_URL", "--db-url"])
def test_remote_transaction_pooler_is_refused_even_with_opt_in(no_real_connections, monkeypatch, capsys, via_settings):
    pooler = SUPABASE_VERIFIED.replace(":5432/", ":6543/")
    if via_settings:
        monkeypatch.setattr(settings, "SERVER_DIRECT_URL", pooler)
        argv = ["--allow-remote"]
    else:
        argv = ["--db-url", pooler, "--allow-remote"]

    assert iqs.main(argv) == 2
    assert no_real_connections == []
    err = capsys.readouterr().err
    assert "port 6543" in err
    assert not any(part in err for part in SECRET_PARTS)


@pytest.mark.parametrize("query", ["", "?sslmode=require", "?sslmode=verify-full"])
def test_supabase_without_verified_tls_is_refused_even_with_opt_in(no_real_connections, capsys, query):
    assert iqs.main(["--db-url", f"{SUPABASE_URL}{query}", "--allow-remote"]) == 2

    assert no_real_connections == []
    err = capsys.readouterr().err
    assert "sslmode=verify-full" in err or "sslrootcert" in err
    assert not any(part in err for part in SECRET_PARTS)


def test_verified_supabase_session_url_with_opt_in_connects_and_warns(no_real_connections, monkeypatch, capsys):
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", SUPABASE_VERIFIED)
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", SUPABASE_VERIFIED.replace(":5432/", ":6543/"))

    with pytest.raises(ConnectAttempted):
        iqs.main(["--allow-remote"])

    [url] = no_real_connections
    assert url.port == 5432
    assert url.query["sslmode"] == "verify-full"
    captured = capsys.readouterr()
    assert "(from SERVER_DIRECT_URL)" in captured.out
    assert "remote database allowed" in captured.err
    assert not any(part in captured.out + captured.err for part in SECRET_PARTS)
    assert "preflight_placeholder_ca" not in captured.out + captured.err


@pytest.mark.parametrize("url", [None, "sqlite:///queue.db"], ids=["missing", "sqlite"])
def test_missing_or_non_postgresql_url_is_refused(no_real_connections, capsys, url):
    assert iqs.main(["--db-url", url] if url else []) == 2

    assert no_real_connections == []
    assert "ERROR:" in capsys.readouterr().err


def test_an_invalid_url_is_refused_without_echoing_it(no_real_connections, capsys):
    assert iqs.main(["--db-url", "not a url with not-a-real-secret inside"]) == 2

    assert no_real_connections == []
    assert "not-a-real-secret" not in capsys.readouterr().err


class FakeAuthError(Exception):
    sqlstate = "28P01"


def test_database_errors_hide_connection_details(monkeypatch, capsys):
    engine = FakeEngine()

    @contextmanager
    def failing_begin():
        raise OperationalError(
            "SELECT 1", {}, FakeAuthError('password authentication failed for user "postgres.mockref"')
        )
        yield

    engine.begin = failing_begin
    monkeypatch.setattr(iqs, "create_engine", lambda url, **kwargs: engine)

    assert iqs.main(["--db-url", LOCAL_URL]) == 1

    err = capsys.readouterr().err
    assert "SQLSTATE 28P01: authentication failed" in err
    assert "nothing was changed" in err
    assert not any(part in err for part in SECRET_PARTS)
    assert engine.disposed


# --- local PostgreSQL (skipped unless SERVER_TEST_DATABASE_URL is set) ---------------------


def test_installs_on_the_disposable_test_database(test_database_url, capsys):
    raw = test_database_url.render_as_string(hide_password=False)

    assert iqs.main(["--db-url", raw]) == 0
    assert iqs.main(["--db-url", raw]) == 0

    engine = create_engine(test_database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(iqs.Q_INSTALLED).scalar_one()
            functions = connection.execute(
                text(
                    "SELECT count(*) FROM pg_catalog.pg_proc p"
                    " JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace"
                    " WHERE n.nspname = 'public' AND p.proname LIKE 'procrastinate%'"
                )
            ).scalar_one()
            status_type = connection.execute(
                text("SELECT pg_catalog.to_regtype('public.procrastinate_job_status') IS NOT NULL")
            ).scalar_one()
    finally:
        engine.dispose()
    assert functions > 0
    assert status_type
    assert "already installed" in capsys.readouterr().out
