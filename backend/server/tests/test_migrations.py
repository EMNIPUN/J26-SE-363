import argparse
import io
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

import pytest
import sqlalchemy
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import CommandLine, Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url

import app.models  # noqa: F401  registers every model on Base.metadata
from app.core.config import settings
from app.database.base import Base
from app.database.migrations import include_object
from app.database.safety import UnsafeDatabaseTarget

SERVER_DIR = Path(__file__).resolve().parents[1]
APP_TABLES = {"users", "groups", "group_members", "projects", "project_documents", "agent_runs"}
INITIAL_REVISION = "c9da91ebdddb"
SECURITY_REVISION = "4f6d2a9c8e1b"
SECURED_TABLES = APP_TABLES | {"alembic_version"}
BROWSER_ROLES = ("anon", "authenticated", "service_role")
# Fake targets: `.invalid` never resolves, and create_engine is replaced in these tests anyway.
REMOTE_URL = "postgresql+psycopg://selvia_user:not-a-real-secret@db.example.invalid:5432/postgres"
LOCAL_URL = "postgresql+psycopg://selvia_user:not-a-real-secret@localhost:5432/selvia_migration_test"
SECRET_PARTS = ("not-a-real-secret", "selvia_user")


def alembic_config(
    connection=None,
    db_url: str | None = None,
    output=None,
    allow_remote: str | None = None,
    allow_remote_downgrade: str | None = None,
) -> Config:
    x_args = [f"db_url={db_url}"] if db_url else []
    if allow_remote is not None:
        x_args.append(f"allow_remote={allow_remote}")
    if allow_remote_downgrade is not None:
        x_args.append(f"allow_remote_downgrade={allow_remote_downgrade}")
    cmd_opts = argparse.Namespace(x=x_args)
    config = Config(str(SERVER_DIR / "alembic.ini"), cmd_opts=cmd_opts, output_buffer=output)
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def schema_diff(connection) -> list:
    context = MigrationContext.configure(connection, opts={"include_object": include_object})
    return compare_metadata(context, Base.metadata)


def offline_sql(*revisions: str) -> str:
    output = io.StringIO()
    config = alembic_config(db_url="postgresql+psycopg://localhost/offline_only", output=output)
    if revisions[0] == "upgrade":
        command.upgrade(config, revisions[1], sql=True)
    else:
        command.downgrade(config, revisions[1], sql=True)
    return output.getvalue()


# --- configuration ------------------------------------------------------------------


def test_alembic_has_a_single_initial_head():
    script = ScriptDirectory.from_config(alembic_config())

    heads = script.get_heads()
    base = script.get_revision(script.get_bases()[0])

    assert len(heads) == 1
    assert base.down_revision is None


@pytest.mark.parametrize(
    ("name", "reflected", "has_model", "included"),
    [
        ("procrastinate_jobs", True, False, False),
        ("procrastinate_events", True, False, False),
        ("some_other_tools_table", True, False, False),
        ("agent_runs", True, True, True),
        ("agent_runs", False, True, True),
    ],
)
def test_include_object_only_manages_model_tables(name, reflected, has_model, included):
    compare_to = object() if has_model else None

    assert include_object(None, name, "table", reflected, compare_to) is included


def test_include_object_keeps_columns_and_indexes():
    assert include_object(None, "status", "column", True, None) is True
    assert include_object(None, "ix_agent_runs_status", "index", True, None) is True


# --- migration on SQLite (no server needed) -----------------------------------------


def test_upgrade_matches_models_and_downgrade_leaves_other_tables(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    with engine.begin() as connection:
        Table("procrastinate_jobs", MetaData(), Column("id", Integer, primary_key=True)).create(connection)

        command.upgrade(alembic_config(connection), "head")
        tables = set(inspect(connection).get_table_names())
        assert APP_TABLES <= tables
        assert "procrastinate_jobs" in tables
        assert schema_diff(connection) == []

        command.downgrade(alembic_config(connection), "base")
        tables = set(inspect(connection).get_table_names())
        assert tables.isdisjoint(APP_TABLES)
        assert "procrastinate_jobs" in tables
    engine.dispose()


# --- PostgreSQL SQL, rendered offline (no connection) ----------------------------------


def test_postgres_upgrade_sql_creates_only_application_tables():
    sql = offline_sql("upgrade", "head")

    for table in APP_TABLES:
        assert f"CREATE TABLE {table} " in sql
    assert "procrastinate" not in sql
    assert "DROP " not in sql
    assert "JSONB" in sql
    assert sql.count("CHECK (status IN ('queued', 'running', 'succeeded', 'failed'))") == 1
    assert "CREATE TYPE" not in sql


def test_postgres_downgrade_sql_drops_only_application_tables():
    sql = offline_sql("downgrade", "head:base")

    for table in APP_TABLES:
        assert f"DROP TABLE {table};" in sql
    assert sql.count("DROP TABLE") == len(APP_TABLES)
    assert "procrastinate" not in sql
    assert "DROP DATABASE" not in sql and "DROP SCHEMA" not in sql


# --- security migration (RLS and browser-role revokes) ---------------------------------


def security_sql() -> str:
    return offline_sql("upgrade", f"{INITIAL_REVISION}:{SECURITY_REVISION}")


def test_security_revision_follows_the_initial_revision():
    script = ScriptDirectory.from_config(alembic_config())

    assert script.get_revision(SECURITY_REVISION).down_revision == INITIAL_REVISION


def test_security_sql_enables_rls_on_core_and_version_tables():
    sql = security_sql()

    for table in SECURED_TABLES:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in sql
    assert sql.count("ENABLE ROW LEVEL SECURITY") == len(SECURED_TABLES)


def test_security_sql_never_grants_forces_or_adds_policies():
    sql = security_sql().upper()

    for word in ("FORCE", "GRANT", "POLICY", "DISABLE", "DROP", "CREATE", "PROCRASTINATE"):
        assert word not in sql


def test_security_sql_revokes_only_from_browser_roles_that_exist():
    sql = security_sql()
    blocks = re.findall(r"DO \$\$(.*?)\$\$", sql, flags=re.DOTALL)
    outside = re.sub(r"DO \$\$.*?\$\$", "", sql, flags=re.DOTALL)

    assert len(blocks) == len(BROWSER_ROLES)
    assert "REVOKE" not in outside and "DEFAULT PRIVILEGES" not in outside
    for role, block in zip(BROWSER_ROLES, blocks, strict=True):
        assert f"IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{role}')" in block
        assert f"current_user <> '{role}'" in block
        revoke = re.search(r"REVOKE ALL ON TABLE (.*?) FROM (\w+);", block)
        assert set(revoke.group(1).split(", ")) == SECURED_TABLES
        assert revoke.group(2) == role
        for kind in ("TABLES", "SEQUENCES", "FUNCTIONS"):
            assert f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON {kind} FROM {role};" in block
    assert set(re.findall(r"IN SCHEMA (\w+)", sql)) == {"public"}
    assert "FOR ROLE" not in sql


def rls_statement_targets(sql: str) -> set[str]:
    return set(re.findall(r"^ALTER TABLE (.+?) ENABLE ROW LEVEL SECURITY;$", sql, flags=re.MULTILINE))


def test_every_model_table_and_the_version_table_get_rls(monkeypatch):
    """Regression guard: a new model table must come with its own ENABLE ROW LEVEL SECURITY."""
    configured = {}
    run_migrations = MigrationContext.run_migrations

    def recording_run_migrations(self, **kwargs):
        configured["table"] = self.version_table
        configured["schema"] = self.version_table_schema
        return run_migrations(self, **kwargs)

    monkeypatch.setattr(MigrationContext, "run_migrations", recording_run_migrations)
    sql = offline_sql("upgrade", "head")

    preparer = postgresql.dialect().identifier_preparer
    expected = {preparer.format_table(table) for table in Base.metadata.tables.values()}
    version_table = preparer.quote(configured["table"])
    if configured["schema"]:
        version_table = f"{preparer.quote_schema(configured['schema'])}.{version_table}"
    expected.add(version_table)

    assert len(expected) > 1
    missing = expected - rls_statement_targets(sql)
    assert not missing, f"tables without ENABLE ROW LEVEL SECURITY: {sorted(missing)}"


def test_security_migration_quotes_a_configured_version_table(monkeypatch):
    module = ScriptDirectory.from_config(alembic_config()).get_revision(SECURITY_REVISION).module
    executed = []
    context = SimpleNamespace(
        dialect=postgresql.dialect(), version_table="Version Table", version_table_schema="Ops"
    )
    monkeypatch.setattr(
        module, "op", SimpleNamespace(get_context=lambda: context, execute=executed.append)
    )

    module.upgrade()

    assert 'ALTER TABLE "Ops"."Version Table" ENABLE ROW LEVEL SECURITY' in executed
    assert all('"Ops"."Version Table"' in sql for sql in executed if "REVOKE ALL ON TABLE " in sql)


def test_security_downgrade_restores_no_access():
    sql = offline_sql("downgrade", f"{SECURITY_REVISION}:{INITIAL_REVISION}")

    for word in ("GRANT", "REVOKE", "ROW LEVEL SECURITY", "POLICY", "DROP"):
        assert word not in sql
    assert INITIAL_REVISION in sql


def test_security_revision_is_a_no_op_on_sqlite(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'security.db'}")
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), SECURITY_REVISION)
        assert MigrationContext.configure(connection).get_current_revision() == SECURITY_REVISION

        command.downgrade(alembic_config(connection), INITIAL_REVISION)
        assert MigrationContext.configure(connection).get_current_revision() == INITIAL_REVISION
        assert APP_TABLES <= set(inspect(connection).get_table_names())

        command.upgrade(alembic_config(connection), "head")
        assert schema_diff(connection) == []
    engine.dispose()


# --- env.py safety guard -----------------------------------------------------------------


class ConnectAttempted(Exception):
    """Raised by the fake create_engine: the guard let the command through."""


@pytest.fixture
def no_real_connections(monkeypatch):
    """Replace create_engine (used by env.py) and the app's database settings with fakes."""
    attempts = []

    def fake_create_engine(url, **kwargs):
        attempts.append(make_url(url))
        raise ConnectAttempted

    monkeypatch.setattr(sqlalchemy, "create_engine", fake_create_engine)
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", None)
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", None)
    return attempts


@pytest.mark.parametrize("operation", ["upgrade", "downgrade", "stamp", "current"])
def test_remote_target_is_refused_without_opt_in(no_real_connections, operation):
    config = alembic_config(db_url=REMOTE_URL)

    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        if operation == "upgrade":
            command.upgrade(config, "head")
        elif operation == "downgrade":
            command.downgrade(config, "base")
        elif operation == "stamp":
            command.stamp(config, "head")
        else:
            command.current(config)

    assert no_real_connections == []
    assert "db.example.invalid" in str(excinfo.value)
    assert not any(part in str(excinfo.value) for part in SECRET_PARTS)


@pytest.mark.parametrize("setting", ["SERVER_DIRECT_URL", "SERVER_DATABASE_URL"])
def test_remote_url_from_settings_is_refused(no_real_connections, monkeypatch, setting):
    monkeypatch.setattr(settings, setting, REMOTE_URL)

    with pytest.raises(UnsafeDatabaseTarget):
        command.upgrade(alembic_config(), "head")

    assert no_real_connections == []


@pytest.mark.parametrize("value", ["false", "0", "no", ""])
def test_anything_but_an_explicit_true_is_not_an_opt_in(no_real_connections, value):
    with pytest.raises(UnsafeDatabaseTarget):
        command.upgrade(alembic_config(db_url=REMOTE_URL, allow_remote=value), "head")

    assert no_real_connections == []


def test_injected_remote_connection_is_refused(no_real_connections):
    config = alembic_config()
    config.attributes["connection"] = SimpleNamespace(engine=SimpleNamespace(url=make_url(REMOTE_URL)))

    with pytest.raises(UnsafeDatabaseTarget):
        command.upgrade(config, "head")


def test_remote_target_with_opt_in_connects_and_logs_no_credentials(no_real_connections, capsys):
    with pytest.raises(ConnectAttempted):
        command.upgrade(alembic_config(db_url=REMOTE_URL, allow_remote="true"), "head")

    assert [url.host for url in no_real_connections] == ["db.example.invalid"]
    log = capsys.readouterr().err
    assert "Target database: postgresql db.example.invalid:5432/postgres" in log
    assert "Remote database allowed" in log
    assert not any(part in log for part in SECRET_PARTS)


def test_remote_downgrade_is_not_covered_by_allow_remote(no_real_connections):
    config = alembic_config(db_url=REMOTE_URL, allow_remote="true")

    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        command.downgrade(config, "base")

    assert no_real_connections == []
    assert "allow_remote_downgrade=true" in str(excinfo.value)
    assert not any(part in str(excinfo.value) for part in SECRET_PARTS)


def test_remote_downgrade_from_the_cli_is_not_covered_by_allow_remote(no_real_connections):
    argv = [
        "-c", str(SERVER_DIR / "alembic.ini"),
        "-x", f"db_url={REMOTE_URL}",
        "-x", "allow_remote=true",
        "downgrade", "base",
    ]  # fmt: skip

    with pytest.raises(UnsafeDatabaseTarget):
        CommandLine(prog="alembic").main(argv=argv)

    assert no_real_connections == []


def test_injected_remote_connection_downgrade_is_not_covered_by_allow_remote(no_real_connections):
    config = alembic_config(allow_remote="true")
    config.attributes["connection"] = SimpleNamespace(engine=SimpleNamespace(url=make_url(REMOTE_URL)))

    with pytest.raises(UnsafeDatabaseTarget):
        command.downgrade(config, "base")


@pytest.mark.parametrize(
    ("allow_remote", "allow_remote_downgrade"),
    [(None, "true"), ("true", "false"), ("true", "0"), ("true", "")],
)
def test_remote_downgrade_needs_both_explicit_opt_ins(
    no_real_connections, allow_remote, allow_remote_downgrade
):
    config = alembic_config(
        db_url=REMOTE_URL, allow_remote=allow_remote, allow_remote_downgrade=allow_remote_downgrade
    )

    with pytest.raises(UnsafeDatabaseTarget):
        command.downgrade(config, "base")

    assert no_real_connections == []


def test_remote_downgrade_with_both_opt_ins_connects_and_logs_it(no_real_connections, capsys):
    config = alembic_config(db_url=REMOTE_URL, allow_remote="true", allow_remote_downgrade="true")

    with pytest.raises(ConnectAttempted):
        command.downgrade(config, "base")

    assert [url.host for url in no_real_connections] == ["db.example.invalid"]
    log = capsys.readouterr().err
    assert "Remote downgrade allowed by -x allow_remote_downgrade=true" in log
    assert not any(part in log for part in SECRET_PARTS)


@pytest.mark.parametrize("operation", ["upgrade", "stamp", "current"])
def test_allow_remote_still_covers_non_downgrade_commands(no_real_connections, capsys, operation):
    config = alembic_config(db_url=REMOTE_URL, allow_remote="true")

    with pytest.raises(ConnectAttempted):
        if operation == "upgrade":
            command.upgrade(config, "head")
        elif operation == "stamp":
            command.stamp(config, "head")
        else:
            command.current(config)

    assert [url.host for url in no_real_connections] == ["db.example.invalid"]
    assert "Remote downgrade allowed" not in capsys.readouterr().err


REMOTE_TRANSACTION_POOLER_URL = REMOTE_URL.replace(":5432/", ":6543/")


def test_remote_fallback_to_the_app_url_is_refused_even_with_opt_in(no_real_connections, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", REMOTE_URL)

    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        command.upgrade(alembic_config(allow_remote="true"), "head")

    assert no_real_connections == []
    assert "SERVER_DIRECT_URL is not set" in str(excinfo.value)
    assert not any(part in str(excinfo.value) for part in SECRET_PARTS)


@pytest.mark.parametrize("via_settings", [True, False], ids=["SERVER_DIRECT_URL", "-x db_url"])
def test_remote_transaction_pooler_is_refused_even_with_opt_in(no_real_connections, monkeypatch, via_settings):
    if via_settings:
        monkeypatch.setattr(settings, "SERVER_DIRECT_URL", REMOTE_TRANSACTION_POOLER_URL)
        config = alembic_config(allow_remote="true")
    else:
        config = alembic_config(db_url=REMOTE_TRANSACTION_POOLER_URL, allow_remote="true")

    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        command.upgrade(config, "head")

    assert no_real_connections == []
    assert "port 6543" in str(excinfo.value)


def test_remote_direct_url_is_used_over_the_app_url(no_real_connections, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", REMOTE_URL)
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", REMOTE_TRANSACTION_POOLER_URL)

    with pytest.raises(ConnectAttempted):
        command.upgrade(alembic_config(allow_remote="true"), "head")

    assert [url.port for url in no_real_connections] == [5432]


SUPABASE_URL = "postgresql+psycopg://postgres.mockref:not-a-real-secret@aws-0-mock.pooler.supabase.com:5432/postgres"
CA_FILE = str(Path(__file__).resolve().parent / "fixtures" / "preflight_placeholder_ca.pem")


@pytest.mark.parametrize("query", ["", "?sslmode=require", "?sslmode=verify-ca", "?sslmode=verify-full"])
def test_remote_supabase_without_verified_tls_is_refused_even_with_opt_in(no_real_connections, monkeypatch, query):
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", f"{SUPABASE_URL}{query}")

    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        command.upgrade(alembic_config(allow_remote="true"), "head")

    assert no_real_connections == []
    text = str(excinfo.value)
    assert "sslmode=verify-full" in text or "sslrootcert" in text
    assert not any(part in text for part in (*SECRET_PARTS, "mockref"))


def test_remote_supabase_with_verified_tls_and_opt_in_connects(no_real_connections, monkeypatch):
    verified = f"{SUPABASE_URL}?sslmode=verify-full&sslrootcert={quote(CA_FILE, safe='')}"
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", verified)

    with pytest.raises(ConnectAttempted):
        command.upgrade(alembic_config(allow_remote="true"), "head")

    [url] = no_real_connections
    assert url.query["sslmode"] == "verify-full"
    assert url.query["sslrootcert"] == CA_FILE


def test_local_fallback_to_the_app_url_still_works(no_real_connections, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", LOCAL_URL)

    with pytest.raises(ConnectAttempted):
        command.upgrade(alembic_config(), "head")

    assert [url.database for url in no_real_connections] == ["selvia_migration_test"]


def test_local_downgrade_needs_no_opt_in(no_real_connections):
    with pytest.raises(ConnectAttempted):
        command.downgrade(alembic_config(db_url=LOCAL_URL), "base")

    assert [url.database for url in no_real_connections] == ["selvia_migration_test"]


def test_local_postgres_target_is_accepted_without_opt_in(no_real_connections, capsys):
    with pytest.raises(ConnectAttempted):
        command.upgrade(alembic_config(db_url=LOCAL_URL), "head")

    assert [url.database for url in no_real_connections] == ["selvia_migration_test"]
    log = capsys.readouterr().err
    assert "Target database: postgresql localhost:5432/selvia_migration_test" in log
    assert "Remote database allowed" not in log
    assert not any(part in log for part in SECRET_PARTS)


def test_local_sqlite_target_runs_through_db_url(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'local.db'}"

    command.upgrade(alembic_config(db_url=db_url), "head")
    engine = create_engine(db_url)
    assert APP_TABLES <= set(inspect(engine).get_table_names())
    command.downgrade(alembic_config(db_url=db_url), "base")
    assert set(inspect(engine).get_table_names()).isdisjoint(APP_TABLES)
    engine.dispose()


def test_offline_sql_is_not_blocked_for_remote_urls(no_real_connections):
    output = io.StringIO()

    command.upgrade(alembic_config(db_url=REMOTE_URL, output=output), "head", sql=True)

    assert "CREATE TABLE agent_runs" in output.getvalue()
    assert no_real_connections == []


# --- optional round trip on a disposable PostgreSQL database ---------------------------


def test_upgrade_and_downgrade_on_postgres(test_database_url):
    engine = create_engine(test_database_url)
    with engine.begin() as connection:
        existing = set(inspect(connection).get_table_names())
        current = MigrationContext.configure(connection).get_current_revision()
        if existing & APP_TABLES or current is not None:
            pytest.fail("SERVER_TEST_DATABASE_URL must point to an empty, unmigrated database")

        command.upgrade(alembic_config(connection), "head")
        assert APP_TABLES <= set(inspect(connection).get_table_names())
        assert schema_diff(connection) == []
        rls = connection.execute(
            text(
                "SELECT CAST(relname AS text) AS name, relrowsecurity, relforcerowsecurity"
                " FROM pg_catalog.pg_class"
                " WHERE relnamespace = CAST('public' AS regnamespace)"
                " AND CAST(relname AS text) = ANY(CAST(:names AS text[]))"
            ),
            {"names": sorted(SECURED_TABLES)},
        ).all()
        assert {row.name: (row.relrowsecurity, row.relforcerowsecurity) for row in rls} == {
            table: (True, False) for table in SECURED_TABLES
        }
        policies = connection.execute(
            text(
                "SELECT count(*) FROM pg_catalog.pg_policies"
                " WHERE schemaname = 'public' AND CAST(tablename AS text) = ANY(CAST(:names AS text[]))"
            ),
            {"names": sorted(SECURED_TABLES)},
        ).scalar_one()
        assert policies == 0

        command.downgrade(alembic_config(connection), "base")
        tables = set(inspect(connection).get_table_names())
        assert tables.isdisjoint(APP_TABLES)
        assert existing <= tables
    engine.dispose()
