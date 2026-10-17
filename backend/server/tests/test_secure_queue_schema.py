"""Tests for scripts/secure_queue_schema.py. Fake engines only: nothing connects to a database."""

from contextlib import contextmanager

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from scripts import secure_queue_schema as sqs

OWNER = "queue_owner"
REMOTE_URL = "postgresql+psycopg://selvia_user:not-a-real-secret@db.example.invalid:5432/postgres"
LOCAL_URL = "postgresql+psycopg://selvia_user:not-a-real-secret@localhost:5432/selvia_migration_test"
SECRET_PARTS = ("not-a-real-secret", "selvia_user")
FETCH_JOB = "public.procrastinate_fetch_job_v2(target_queue_names character varying[], p_worker_id bigint)"
NOTIFY = "public.procrastinate_notify_queue_job_inserted_v1()"
SEQUENCES = (
    "procrastinate_events_id_seq",
    "procrastinate_jobs_id_seq",
    "procrastinate_periodic_defers_id_seq",
)
ALL_GRANTEES = "PUBLIC, anon, authenticated, service_role"


# --- fakes ----------------------------------------------------------------------------


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return list(self.rows)

    def scalar_one(self):
        (row,) = self.rows
        return next(iter(row.values()))


class FakeConnection:
    """Answers the script's catalog queries; switches to `after` once anything is changed."""

    def __init__(self, before, after):
        self.state = before
        self.after = after
        self.executed = []
        self.rolled_back = False

    def execute(self, statement, params=None):
        sql = str(statement).strip()
        self.executed.append(sql)
        for query, rows in self.state.items():
            if query is statement:
                return FakeResult(rows)
        if sql.startswith(("ALTER", "REVOKE")):
            self.state = self.after
        return FakeResult([])

    def rollback(self):
        self.rolled_back = True

    def changes(self):
        return [sql for sql in self.executed if sql.startswith(("ALTER", "REVOKE", "GRANT"))]


class FakeEngine:
    def __init__(self, before, after=None):
        self.connection = FakeConnection(before, before if after is None else after)
        self.committed = False
        self.rolled_back = False
        self.disposed = False

    @contextmanager
    def connect(self):
        yield self.connection

    @contextmanager
    def begin(self):
        try:
            yield self.connection
        except BaseException:
            self.rolled_back = True
            raise
        self.committed = True

    def dispose(self):
        self.disposed = True


def relation(name, kind="r", *, owner=OWNER, rls=False, forced=False, public_access=False):
    return {
        "name": name,
        "kind": kind,
        "owner": owner,
        "rls": rls,
        "forced": forced,
        "public_access": public_access,
    }


def routine(signature, *, kind="f", owner=OWNER, security_definer=False, public_execute=True):
    return {
        "signature": signature,
        "kind": kind,
        "owner": owner,
        "security_definer": security_definer,
        "public_execute": public_execute,
    }


def catalog(
    *,
    hardened=False,
    user=OWNER,
    roles=sqs.BROWSER_ROLES,
    relations=None,
    routines=None,
    policies=(),
):
    """Catalog rows as the script's queries would return them."""
    if relations is None:
        relations = [relation(name, rls=hardened) for name in sqs.QUEUE_TABLES]
        relations += [relation(name, "S") for name in SEQUENCES]
        relations += [relation("procrastinate_jobs_pkey", "i"), relation("procrastinate_job_to_defer_v1", "c")]
    if routines is None:
        routines = [routine(sig, public_execute=not hardened) for sig in (FETCH_JOB, NOTIFY)]
    objects = [row["name"] for row in relations if row["kind"] in ("r", "S")]
    objects += [row["signature"] for row in routines]
    access = [
        {"object": name, "role": role, "any_access": not hardened, "full_access": not hardened}
        for name in objects
        for role in roles
        if role != user
    ]
    access += [{"object": name, "role": user, "any_access": True, "full_access": True} for name in objects]
    return {
        sqs.Q_CURRENT_USER: [{"role_name": user}],
        sqs.Q_BROWSER_ROLES: [{"rolname": role} for role in roles],
        sqs.Q_RELATIONS: relations,
        sqs.Q_ROUTINES: routines,
        sqs.Q_POLICIES: [{"name": table, "policy": policy} for table, policy in policies],
        sqs.Q_RELATION_ACCESS: [row for row in access if not row["object"].startswith("public.")],
        sqs.Q_ROUTINE_ACCESS: [row for row in access if row["object"].startswith("public.")],
    }


def inspected(**kwargs):
    return sqs.inspect_queue_schema(FakeConnection(catalog(**kwargs), None))


# --- statements -----------------------------------------------------------------------


def test_fresh_queue_gets_rls_and_revokes_for_every_object():
    statements = sqs.hardening_statements(inspected())

    assert statements == [
        "ALTER TABLE public.procrastinate_events ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE public.procrastinate_jobs ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE public.procrastinate_periodic_defers ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE public.procrastinate_workers ENABLE ROW LEVEL SECURITY",
        (
            "REVOKE ALL ON TABLE public.procrastinate_events, public.procrastinate_jobs, "
            "public.procrastinate_periodic_defers, public.procrastinate_workers "
            f"FROM {ALL_GRANTEES}"
        ),
        (
            "REVOKE ALL ON SEQUENCE public.procrastinate_events_id_seq, "
            "public.procrastinate_jobs_id_seq, public.procrastinate_periodic_defers_id_seq "
            f"FROM {ALL_GRANTEES}"
        ),
        f"REVOKE EXECUTE ON ROUTINE {FETCH_JOB} FROM {ALL_GRANTEES}",
        f"REVOKE EXECUTE ON ROUTINE {NOTIFY} FROM {ALL_GRANTEES}",
    ]


def test_statements_never_grant_force_or_add_policies():
    sql = "\n".join(sqs.hardening_statements(inspected())).upper()

    for word in ("GRANT", "FORCE", "POLICY", "DISABLE", "DROP", "CREATE"):
        assert word not in sql
    assert OWNER.upper() not in sql


def test_indexes_and_composite_types_are_left_alone():
    schema = inspected()
    sql = "\n".join(sqs.hardening_statements(schema))

    assert "procrastinate_jobs_pkey" not in sql
    assert "procrastinate_job_to_defer_v1" not in sql
    assert schema.unexpected == []


def test_without_browser_roles_only_public_is_revoked():
    statements = sqs.hardening_statements(inspected(roles=()))

    revokes = [statement for statement in statements if statement.startswith("REVOKE")]
    assert revokes and all(statement.endswith("FROM PUBLIC") for statement in revokes)
    assert sum(statement.endswith("ENABLE ROW LEVEL SECURITY") for statement in statements) == 4


def test_connected_role_is_never_a_grantee_and_browser_role_connection_is_refused():
    schema = inspected(user="service_role")

    assert any("connected as service_role" in problem for problem in sqs.find_problems(schema))
    for statement in sqs.hardening_statements(schema):
        assert "service_role" not in statement


def test_statements_are_the_same_before_and_after_hardening():
    assert sqs.hardening_statements(inspected()) == sqs.hardening_statements(inspected(hardened=True))


# --- checks ---------------------------------------------------------------------------


def test_checks_fail_on_a_fresh_queue_and_pass_once_hardened():
    assert not all(result.ok for result in sqs.check_schema(inspected()))
    assert all(result.ok for result in sqs.check_schema(inspected(hardened=True)))
    assert sqs.find_problems(inspected(hardened=True)) == []


def test_public_table_access_fails_even_without_browser_roles():
    relations = [relation(name, rls=True) for name in sqs.QUEUE_TABLES]
    relations[0] = relation(sqs.QUEUE_TABLES[0], rls=True, public_access=True)
    schema = inspected(hardened=True, roles=(), relations=relations)

    failed = [result for result in sqs.check_schema(schema) if not result.ok]
    assert [result.subject for result in failed] == [sqs.QUEUE_TABLES[0]]


def test_owner_without_full_access_fails():
    state = catalog(hardened=True)
    state[sqs.Q_RELATION_ACCESS] = [
        {**row, "full_access": False} if row["role"] == OWNER else row
        for row in state[sqs.Q_RELATION_ACCESS]
    ]
    schema = sqs.inspect_queue_schema(FakeConnection(state, None))

    assert any(
        not result.ok and result.description == "owner role keeps full access"
        for result in sqs.check_schema(schema)
    )


@pytest.mark.parametrize("role", ["anon", OWNER])
def test_missing_permission_record_fails_closed(role):
    state = catalog(hardened=True)
    state[sqs.Q_RELATION_ACCESS] = [
        row
        for row in state[sqs.Q_RELATION_ACCESS]
        if not (row["object"] == "procrastinate_jobs" and row["role"] == role)
    ]
    schema = sqs.inspect_queue_schema(FakeConnection(state, None))

    failed = [result for result in sqs.check_schema(schema) if not result.ok]
    assert failed
    assert {result.subject for result in failed} == {"procrastinate_jobs"}
    assert any(result.description == f"no permission record for {role}" for result in failed)


def test_missing_routine_permission_record_fails_closed():
    state = catalog(hardened=True)
    state[sqs.Q_ROUTINE_ACCESS] = [
        row
        for row in state[sqs.Q_ROUTINE_ACCESS]
        if not (row["object"] == NOTIFY and row["role"] == "service_role")
    ]
    schema = sqs.inspect_queue_schema(FakeConnection(state, None))

    failed = [result for result in sqs.check_schema(schema) if not result.ok]
    assert {result.subject for result in failed} == {NOTIFY}


def test_roles_that_do_not_exist_are_not_required():
    schema = inspected(hardened=True, roles=("anon",))

    assert all(result.ok for result in sqs.check_schema(schema))


# --- check mode -----------------------------------------------------------------------


def test_check_mode_only_reads(capsys):
    engine = FakeEngine(catalog())

    assert sqs.run_check(engine) == 1

    executed = engine.connection.executed
    assert executed[0] == "SET TRANSACTION READ ONLY"
    assert all(sql.startswith("SELECT") for sql in executed[1:])
    assert engine.connection.changes() == []
    assert engine.connection.rolled_back
    assert not engine.committed
    out = capsys.readouterr().out
    assert "FAIL | procrastinate_jobs |" in out
    assert "Queue schema is NOT secured." in out


def test_check_mode_passes_on_a_hardened_queue(capsys):
    assert sqs.run_check(FakeEngine(catalog(hardened=True))) == 0

    out = capsys.readouterr().out
    assert "FAIL" not in out
    assert "PASS | procrastinate_workers | row level security on, not forced" in out
    assert "Queue schema is secured." in out


def test_check_mode_reports_a_missing_schema(capsys):
    assert sqs.run_check(FakeEngine(catalog(relations=[], routines=[]))) == 1

    assert "python -m scripts.install_queue_schema" in capsys.readouterr().out


# --- apply mode -----------------------------------------------------------------------


def test_apply_runs_in_one_transaction_and_commits(capsys):
    engine = FakeEngine(catalog(), catalog(hardened=True))

    assert sqs.run_apply(engine) == 0

    executed = engine.connection.executed
    assert executed[0] == f"SET LOCAL lock_timeout = '{sqs.LOCK_TIMEOUT}'"
    assert engine.connection.changes() == sqs.hardening_statements(inspected())
    assert engine.committed and not engine.rolled_back
    assert "Queue schema is secured." in capsys.readouterr().out


def test_apply_twice_is_harmless():
    engine = FakeEngine(catalog(), catalog(hardened=True))

    assert sqs.run_apply(engine) == 0
    assert sqs.run_apply(engine) == 0
    assert engine.committed


def test_apply_rolls_back_when_verification_fails(capsys):
    engine = FakeEngine(catalog(), catalog())

    assert sqs.run_apply(engine) == 1

    assert engine.connection.changes()
    assert engine.rolled_back and not engine.committed
    assert "verification failed" in capsys.readouterr().out


def _with_table(**changes):
    rows = [relation(name) for name in sqs.QUEUE_TABLES]
    rows[0] = relation(sqs.QUEUE_TABLES[0], **changes)
    return rows


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (catalog(relations=[], routines=[]), "missing queue tables"),
        (catalog(routines=[]), "no procrastinate_* functions"),
        (catalog(relations=_with_table() + [relation("procrastinate_job_view", "v")]), "unexpected object"),
        (catalog(relations=_with_table() + [relation("procrastinate_new_table")]), "unexpected object"),
        (catalog(policies=[("procrastinate_jobs", "allow_all")]), "already has policy"),
        (catalog(relations=_with_table(forced=True)), "FORCE ROW LEVEL SECURITY"),
        (catalog(routines=[routine(FETCH_JOB, security_definer=True)]), "SECURITY DEFINER"),
        (catalog(routines=[routine(FETCH_JOB, kind="a")]), "unexpected routine"),
        (catalog(relations=_with_table(owner="someone_else")), "owned by another role"),
        (catalog(user="anon"), "connected as anon"),
    ],
)
def test_apply_refuses_unexpected_schemas_without_changing_anything(capsys, state, message):
    engine = FakeEngine(state)

    assert sqs.run_apply(engine) == 1

    assert engine.connection.changes() == []
    assert engine.rolled_back and not engine.committed
    out = capsys.readouterr().out
    assert message in out
    assert "nothing was changed" in out


# --- target guard (main) ----------------------------------------------------------------


class ConnectAttempted(Exception):
    """Raised by the fake create_engine: the guard let the command through."""


@pytest.fixture
def no_real_connections(monkeypatch):
    attempts = []

    def fake_create_engine(url, **kwargs):
        attempts.append(make_url(url))
        raise ConnectAttempted

    monkeypatch.setattr(sqs, "create_engine", fake_create_engine)
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", None)
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", None)
    return attempts


@pytest.mark.parametrize("mode", ["--check", "--apply"])
def test_remote_target_is_refused_without_opt_in(no_real_connections, capsys, mode):
    assert sqs.main([mode, "--db-url", REMOTE_URL]) == 2

    assert no_real_connections == []
    err = capsys.readouterr().err
    assert "db.example.invalid" in err and "--allow-remote" in err
    assert not any(part in err for part in SECRET_PARTS)


@pytest.mark.parametrize("setting", ["SERVER_DIRECT_URL", "SERVER_DATABASE_URL"])
def test_remote_url_from_settings_is_refused(no_real_connections, monkeypatch, setting):
    monkeypatch.setattr(settings, setting, REMOTE_URL)

    assert sqs.main(["--check"]) == 2
    assert no_real_connections == []


def test_remote_target_with_opt_in_connects_and_warns(no_real_connections, capsys):
    with pytest.raises(ConnectAttempted):
        sqs.main(["--check", "--db-url", REMOTE_URL, "--allow-remote"])

    assert [url.host for url in no_real_connections] == ["db.example.invalid"]
    captured = capsys.readouterr()
    assert "Target database: postgresql db.example.invalid:5432/postgres" in captured.out
    assert "remote database allowed" in captured.err
    assert not any(part in captured.out + captured.err for part in SECRET_PARTS)


REMOTE_TRANSACTION_POOLER_URL = REMOTE_URL.replace(":5432/", ":6543/")


@pytest.mark.parametrize("mode", ["--check", "--apply"])
def test_remote_fallback_to_the_app_url_is_refused_even_with_opt_in(no_real_connections, monkeypatch, capsys, mode):
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", REMOTE_URL)

    assert sqs.main([mode, "--allow-remote"]) == 2
    assert no_real_connections == []
    err = capsys.readouterr().err
    assert "SERVER_DIRECT_URL is not set" in err and "--db-url" in err
    assert not any(part in err for part in SECRET_PARTS)


@pytest.mark.parametrize("via_settings", [True, False], ids=["SERVER_DIRECT_URL", "--db-url"])
def test_remote_transaction_pooler_is_refused_even_with_opt_in(no_real_connections, monkeypatch, capsys, via_settings):
    if via_settings:
        monkeypatch.setattr(settings, "SERVER_DIRECT_URL", REMOTE_TRANSACTION_POOLER_URL)
        argv = ["--apply", "--allow-remote"]
    else:
        argv = ["--apply", "--db-url", REMOTE_TRANSACTION_POOLER_URL, "--allow-remote"]

    assert sqs.main(argv) == 2
    assert no_real_connections == []
    assert "port 6543" in capsys.readouterr().err


def test_remote_direct_url_is_used_over_the_app_url(no_real_connections, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", REMOTE_URL)
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", REMOTE_TRANSACTION_POOLER_URL)

    with pytest.raises(ConnectAttempted):
        sqs.main(["--check", "--allow-remote"])

    assert [url.port for url in no_real_connections] == [5432]


@pytest.mark.parametrize("query", ["", "?sslmode=require", "?sslmode=verify-full"])
def test_remote_supabase_without_verified_tls_is_refused_even_with_opt_in(no_real_connections, capsys, query):
    url = f"postgresql+psycopg://postgres.mockref:not-a-real-secret@aws-0-mock.pooler.supabase.com:5432/postgres{query}"

    assert sqs.main(["--check", "--db-url", url, "--allow-remote"]) == 2

    assert no_real_connections == []
    err = capsys.readouterr().err
    assert "sslmode=verify-full" in err or "sslrootcert" in err
    assert not any(part in err for part in (*SECRET_PARTS, "mockref"))


def test_local_target_needs_no_opt_in(no_real_connections):
    with pytest.raises(ConnectAttempted):
        sqs.main(["--check", "--db-url", LOCAL_URL])

    assert [url.database for url in no_real_connections] == ["selvia_migration_test"]


def test_sqlite_is_refused(no_real_connections, tmp_path):
    assert sqs.main(["--check", "--db-url", f"sqlite:///{tmp_path / 'queue.db'}"]) == 2
    assert no_real_connections == []


def test_missing_url_is_refused(no_real_connections, capsys):
    assert sqs.main(["--check"]) == 2

    assert no_real_connections == []
    assert "SERVER_DIRECT_URL" in capsys.readouterr().err


def test_url_precedence_matches_alembic(no_real_connections, monkeypatch):
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", "postgresql+psycopg://u:p@localhost/direct_db")
    monkeypatch.setattr(settings, "SERVER_DATABASE_URL", "postgresql+psycopg://u:p@localhost/pooled_db")

    for argv in (["--check", "--db-url", "postgresql+psycopg://u:p@localhost/cli_db"], ["--check"]):
        with pytest.raises(ConnectAttempted):
            sqs.main(argv)
    monkeypatch.setattr(settings, "SERVER_DIRECT_URL", None)
    with pytest.raises(ConnectAttempted):
        sqs.main(["--check"])

    assert [url.database for url in no_real_connections] == ["cli_db", "direct_db", "pooled_db"]


def test_plain_postgresql_url_uses_psycopg(no_real_connections):
    with pytest.raises(ConnectAttempted):
        sqs.main(["--check", "--db-url", "postgresql://u:p@localhost/selvia_migration_test"])

    assert no_real_connections[0].drivername == "postgresql+psycopg"


@pytest.mark.parametrize("argv", [[], ["--check", "--apply"]])
def test_exactly_one_mode_is_required(no_real_connections, argv):
    with pytest.raises(SystemExit):
        sqs.main(argv)
    assert no_real_connections == []


def test_database_errors_hide_connection_details(monkeypatch, capsys):
    engine = FakeEngine(catalog())

    @contextmanager
    def failing_connect():
        raise OperationalError(
            "SELECT 1", {}, RuntimeError("password authentication failed for user selvia_user")
        )
        yield

    engine.connect = failing_connect
    monkeypatch.setattr(sqs, "create_engine", lambda url, **kwargs: engine)

    assert sqs.main(["--check", "--db-url", LOCAL_URL]) == 1

    err = capsys.readouterr().err
    assert "details hidden" in err
    assert not any(part in err for part in SECRET_PARTS)
    assert engine.disposed


class FakeAuthError(Exception):
    """Shaped like a psycopg error that carries a server SQLSTATE and diagnostics."""

    sqlstate = "28P01"

    def __init__(self, message):
        super().__init__(message)
        self.diag = type("Diag", (), {"message_primary": message, "sqlstate": self.sqlstate})()


def test_authentication_errors_never_print_server_messages(monkeypatch, capsys):
    leaked = (
        "postgres.mockprojectref123",
        "mockprojectref123",
        "mock-password-value",
        "aws-0-mock-region.pooler.example.invalid",
        "selvia_user",
    )
    message = (
        'connection to server at "aws-0-mock-region.pooler.example.invalid" failed: '
        'FATAL: password authentication failed for user "postgres.mockprojectref123" '
        "(password mock-password-value, also tried selvia_user)"
    )
    engine = FakeEngine(catalog())

    @contextmanager
    def failing_connect():
        raise OperationalError("SELECT 1", {}, FakeAuthError(message))
        yield

    engine.connect = failing_connect
    monkeypatch.setattr(sqs, "create_engine", lambda url, **kwargs: engine)

    assert sqs.main(["--check", "--db-url", LOCAL_URL]) == 1

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "SQLSTATE 28P01: authentication failed" in captured.err
    assert "FakeAuthError" in captured.err
    assert not any(part in output for part in leaked)
