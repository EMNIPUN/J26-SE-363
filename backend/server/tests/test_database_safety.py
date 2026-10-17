import os
from pathlib import Path
from urllib.parse import quote

import pytest
from sqlalchemy.engine import make_url

from app.database.safety import (
    UnsafeDatabaseTarget,
    check_migration_target,
    check_schema_change_source,
    check_tls,
    describe,
    disposable_database_url,
    is_local,
    is_supabase,
    is_true,
    parse_url,
    validate_test_database_url,
)

SUPABASE_LIKE = "postgresql+psycopg://postgres.ref:not-a-real-secret@aws-0-xx.pooler.supabase.com:5432/postgres"
LOCAL_TEST = "postgresql+psycopg://selvia_user:not-a-real-secret@localhost:5432/selvia_migration_test"
SECRET_PARTS = ("not-a-real-secret", "selvia_user", "postgres.ref")
# A dummy PEM block, not a real certificate: check_tls only looks for the BEGIN line.
CA_FILE = str(Path(__file__).resolve().parent / "fixtures" / "preflight_placeholder_ca.pem")


def verified(base: str = SUPABASE_LIKE, root_cert: str = CA_FILE) -> str:
    return f"{base}?sslmode=verify-full&sslrootcert={quote(root_cert, safe='')}"


@pytest.mark.parametrize(
    ("url", "local"),
    [
        ("postgresql+psycopg://u:p@localhost:5432/db", True),
        ("postgresql+psycopg://u:p@127.0.0.1/db", True),
        ("postgresql+psycopg://u:p@[::1]:5432/db", True),
        ("sqlite:///tmp/test.db", True),
        (SUPABASE_LIKE, False),
        ("postgresql+psycopg://u:p@db.example.com/db", False),
        # No host: libpq would use PGHOST, which could be anywhere.
        ("postgresql+psycopg://u:p@/db", False),
        # A local URL host does not help when a query parameter redirects the connection.
        ("postgresql+psycopg://u:p@localhost/db?host=db.example.com", False),
        ("postgresql+psycopg://u:p@localhost/db?hostaddr=10.0.0.5", False),
        ("postgresql+psycopg://u:p@localhost/db?service=shared", False),
    ],
)
def test_is_local(url, local):
    assert is_local(make_url(url)) is local


@pytest.mark.parametrize(("value", "expected"), [("true", True), ("TRUE", True), ("1", True), ("yes", True), ("false", False), ("", False), (None, False), ("y", False)])
def test_is_true(value, expected):
    assert is_true(value) is expected


def test_describe_never_contains_credentials():
    description = describe(make_url(SUPABASE_LIKE))

    assert description == "postgresql aws-0-xx.pooler.supabase.com:5432/postgres"
    assert not any(part in description for part in SECRET_PARTS)


def test_parse_url_does_not_echo_an_invalid_url():
    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        parse_url("not a url but with not-a-real-secret inside", "SERVER_DIRECT_URL")

    assert "not-a-real-secret" not in str(excinfo.value)


# --- migration target policy ---------------------------------------------------------


def test_remote_migration_target_is_refused_without_opt_in():
    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        check_migration_target(make_url(SUPABASE_LIKE), allow_remote=False)

    assert "allow_remote=true" in str(excinfo.value)
    assert not any(part in str(excinfo.value) for part in SECRET_PARTS)


def test_remote_migration_target_is_allowed_with_opt_in():
    check_migration_target(make_url(SUPABASE_LIKE), allow_remote=True)


def test_local_migration_target_needs_no_opt_in():
    check_migration_target(make_url(LOCAL_TEST), allow_remote=False)


def test_remote_downgrade_is_refused_with_only_allow_remote():
    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        check_migration_target(make_url(SUPABASE_LIKE), allow_remote=True, downgrade=True)

    assert "allow_remote_downgrade=true" in str(excinfo.value)
    assert not any(part in str(excinfo.value) for part in SECRET_PARTS)


def test_remote_downgrade_opt_in_does_not_replace_allow_remote():
    with pytest.raises(UnsafeDatabaseTarget):
        check_migration_target(
            make_url(SUPABASE_LIKE), allow_remote=False, downgrade=True, allow_remote_downgrade=True
        )


def test_remote_downgrade_is_allowed_with_both_opt_ins():
    check_migration_target(
        make_url(SUPABASE_LIKE), allow_remote=True, downgrade=True, allow_remote_downgrade=True
    )


def test_local_downgrade_needs_no_opt_in():
    check_migration_target(make_url(LOCAL_TEST), allow_remote=False, downgrade=True)


# --- schema-change source -----------------------------------------------------------------

TRANSACTION_POOLER = SUPABASE_LIKE.replace(":5432/", ":6543/")


@pytest.mark.parametrize(
    ("url", "source", "message"),
    [
        (SUPABASE_LIKE, "SERVER_DATABASE_URL", "SERVER_DIRECT_URL is not set"),
        (TRANSACTION_POOLER, "SERVER_DATABASE_URL", "SERVER_DIRECT_URL is not set"),
        (TRANSACTION_POOLER, "SERVER_DIRECT_URL", "port 6543"),
        (TRANSACTION_POOLER, "--db-url", "port 6543"),
    ],
)
def test_remote_schema_changes_refuse_the_app_url_and_the_transaction_pooler(url, source, message):
    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        check_schema_change_source(make_url(url), source, "--db-url")

    assert message in str(excinfo.value)
    assert not any(part in str(excinfo.value) for part in SECRET_PARTS)
    assert "pooler.supabase.com" not in str(excinfo.value)


@pytest.mark.parametrize(
    ("url", "source"),
    [
        (SUPABASE_LIKE, "SERVER_DIRECT_URL"),
        (SUPABASE_LIKE, "--db-url"),
        (LOCAL_TEST, "SERVER_DATABASE_URL"),
        (LOCAL_TEST.replace(":5432/", ":6543/"), "SERVER_DIRECT_URL"),
    ],
)
def test_session_urls_and_local_databases_are_accepted(url, source):
    check_schema_change_source(make_url(url), source, "--db-url")


# --- TLS for Supabase targets --------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "supabase"),
    [
        (SUPABASE_LIKE, True),
        ("postgresql+psycopg://u:p@db.abcdefgh.supabase.co:5432/postgres", True),
        ("postgresql+psycopg://u:p@aws-0-xx.pooler.SUPABASE.com.:5432/postgres", True),
        ("postgresql+psycopg://u:p@localhost/db?host=aws-0-xx.pooler.supabase.com", True),
        (LOCAL_TEST, False),
        ("postgresql+psycopg://u:p@db.example.com/db", False),
        ("postgresql+psycopg://u:p@supabase.com.example.com/db", False),
    ],
)
def test_is_supabase(url, supabase):
    assert is_supabase(make_url(url)) is supabase


@pytest.mark.parametrize(
    "url",
    [
        verified(),
        verified(root_cert="system"),
        verified("postgresql+psycopg://u:p@db.abcdefgh.supabase.co:5432/postgres"),
        # Local and other remote targets keep whatever the URL says; nothing is added or weakened.
        LOCAL_TEST,
        f"{LOCAL_TEST}?sslmode=disable",
        "postgresql+psycopg://u:p@db.example.com/db?sslmode=require",
        "sqlite:///selvia.db",
    ],
)
def test_tls_settings_that_are_accepted(url):
    check_tls(make_url(url))


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ("", "no sslmode"),
        ("?sslmode=require", "sslmode=require"),
        ("?sslmode=verify-ca", "sslmode=verify-ca"),
        ("?sslmode=prefer", "sslmode=prefer"),
        ("?sslmode=disable", "sslmode=disable"),
        ("?sslmode=allow", "sslmode=allow"),
        ("?sslmode=verify-full", "needs sslrootcert"),
        ("?sslmode=verify-full&sslrootcert=", "needs sslrootcert"),
        ("?sslmode=verify-full&sslmode=require", "more than once"),
    ],
)
def test_supabase_urls_need_verify_full_and_a_root_certificate(query, message):
    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        check_tls(make_url(f"{SUPABASE_LIKE}{query}"))

    text = str(excinfo.value)
    assert message in text
    assert "sslmode=verify-full" in text or "sslrootcert" in text
    assert not any(part in text for part in SECRET_PARTS)
    assert "pooler.supabase.com" not in text


@pytest.mark.parametrize("host_param", ["host", "hostaddr"])
def test_a_supabase_host_parameter_cannot_hide_behind_a_local_url_host(host_param):
    url = f"{LOCAL_TEST}?host=aws-0-xx.pooler.supabase.com&sslmode=require"
    if host_param == "hostaddr":
        url = f"{url}&hostaddr=127.0.0.1"

    with pytest.raises(UnsafeDatabaseTarget, match="sslmode=verify-full"):
        check_tls(make_url(url))


def _refusal(url: str) -> str:
    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        check_tls(make_url(url))
    return str(excinfo.value)


def test_a_missing_root_certificate_file_is_refused_without_printing_its_path(tmp_path):
    missing = tmp_path / "private-folder" / "supabase-ca.crt"

    text = _refusal(verified(root_cert=str(missing)))

    assert "does not exist" in text
    assert "private-folder" not in text and "supabase-ca" not in text


def test_a_directory_is_not_a_root_certificate(tmp_path):
    text = _refusal(verified(root_cert=str(tmp_path)))

    assert "not a file" in text
    assert str(tmp_path) not in text


def test_a_root_certificate_without_a_pem_block_is_refused(tmp_path):
    not_pem = tmp_path / "supabase-ca.der"
    not_pem.write_bytes(b"\x30\x82\x01\x0a not a PEM file")

    text = _refusal(verified(root_cert=str(not_pem)))

    assert "no PEM certificate" in text
    assert "supabase-ca" not in text


@pytest.mark.skipif(os.name == "nt", reason="file permissions can't make a file unreadable here")
def test_an_unreadable_root_certificate_is_refused(tmp_path):
    unreadable = tmp_path / "supabase-ca.crt"
    unreadable.write_bytes(Path(CA_FILE).read_bytes())
    unreadable.chmod(0)
    if os.access(unreadable, os.R_OK):
        pytest.skip("running with permissions that ignore file modes")

    assert "can't be read" in _refusal(verified(root_cert=str(unreadable)))


# --- SERVER_TEST_DATABASE_URL --------------------------------------------------------


def test_local_disposable_test_database_is_accepted():
    url = validate_test_database_url(LOCAL_TEST)

    assert url.host == "localhost"
    assert url.database == "selvia_migration_test"


@pytest.mark.parametrize(
    "raw",
    [
        SUPABASE_LIKE,
        "postgresql+psycopg://u:p@aws-0-xx.pooler.supabase.com:5432/selvia_test",
        "postgresql+psycopg://u:p@localhost:5432/selvia_test?host=db.example.com",
        "postgresql+psycopg://u:p@/selvia_test",
    ],
)
def test_remote_test_database_is_rejected(raw):
    with pytest.raises(UnsafeDatabaseTarget) as excinfo:
        validate_test_database_url(raw)

    assert not any(part in str(excinfo.value) for part in SECRET_PARTS)


@pytest.mark.parametrize("database", ["postgres", "selvia_server_db", "selvia_test_data", ""])
def test_test_database_name_must_end_with_test(database):
    with pytest.raises(UnsafeDatabaseTarget):
        validate_test_database_url(f"postgresql+psycopg://u:p@localhost:5432/{database}")


def test_test_database_must_be_postgres():
    with pytest.raises(UnsafeDatabaseTarget):
        validate_test_database_url("sqlite:///selvia_test")


def test_test_database_must_not_be_the_application_database():
    app_url = "postgresql+psycopg://other_user:other@127.0.0.1:5432/selvia_migration_test"

    with pytest.raises(UnsafeDatabaseTarget):
        validate_test_database_url(LOCAL_TEST.replace("localhost", "127.0.0.1"), protected_urls=[app_url])


def test_missing_test_database_never_falls_back_to_application_settings():
    environ = {"SERVER_DIRECT_URL": SUPABASE_LIKE, "SERVER_DATABASE_URL": SUPABASE_LIKE}

    assert disposable_database_url(environ, protected_urls=[SUPABASE_LIKE]) is None
    assert disposable_database_url({"SERVER_TEST_DATABASE_URL": ""}) is None


def test_configured_test_database_is_validated():
    environ = {"SERVER_TEST_DATABASE_URL": SUPABASE_LIKE}

    with pytest.raises(UnsafeDatabaseTarget):
        disposable_database_url(environ)
