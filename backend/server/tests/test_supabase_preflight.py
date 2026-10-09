"""Tests for scripts/supabase_preflight.py.

Everything except the last two tests uses fakes and never connects. The last two need the local
disposable database in SERVER_TEST_DATABASE_URL and skip without it.
"""

import argparse
import dataclasses
import ipaddress
import re
import socket
import ssl
import subprocess
import sys
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
    event,
    inspect,
    text,
)
from sqlalchemy import create_engine as real_create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  registers every model on Base.metadata
from app.database.base import Base
from scripts import supabase_preflight as pf

SERVER_DIR = Path(__file__).resolve().parents[1]
INITIAL_REVISION = "c9da91ebdddb"
SECURITY_REVISION = "4f6d2a9c8e1b"
REF = "abcdefghijklmnopqrst"
PASSWORD = "not-a-real-secret"
# Nothing connects with it, but it must look like a PEM certificate. Its path must never be printed.
CA_FILE = str(Path(__file__).resolve().parent / "fixtures" / "preflight_placeholder_ca.pem")
SUPABASE_BASE_URL = (
    f"postgresql+psycopg://postgres.{REF}:{PASSWORD}@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
)
VERIFIED_TLS = f"sslmode=verify-full&sslrootcert={quote(CA_FILE, safe='')}"
SUPABASE_URL = f"{SUPABASE_BASE_URL}?{VERIFIED_TLS}"
SECRET_PARTS = (PASSWORD, REF, f"postgres.{REF}", CA_FILE)
ROLE = "postgres"
EXPECT = pf.Expectations(
    pf.Roles(ROLE, ROLE, ROLE),
    pf.Revisions((INITIAL_REVISION, SECURITY_REVISION), (SECURITY_REVISION,)),
    pf.QueueSpec(
        "3.10.0",
        frozenset(pf.QUEUE_TABLES),
        frozenset({"procrastinate_fetch_job_v2"}),
        frozenset({"procrastinate_job_status"}),
        frozenset({"procrastinate_trigger_status_events_insert_v1"}),
        frozenset({"procrastinate_jobs_queue_name_idx_v1"}),
    ),
    pf.BROWSER_ROLES,
)
FETCH_JOB = "public.procrastinate_fetch_job_v2(target_queue_names character varying[], p_worker_id bigint)"
WRITE_WORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|GRANT|REVOKE|TRUNCATE|COPY|COMMENT|VACUUM|"
    r"ANALYZE|REINDEX|CLUSTER|LOCK|CALL|DO|REFRESH|NOTIFY|LISTEN|IMPORT|EXECUTE|PREPARE|SECURITY)\b",
    re.IGNORECASE,
)
ALLOWED_SET_STATEMENTS = {
    "SET TRANSACTION READ ONLY",
    "SET LOCAL statement_timeout = '30s'",
    "SET LOCAL lock_timeout = '5s'",
}


def levels(findings) -> set[str]:
    return {finding.level for finding in findings}


def messages(findings, level=None) -> str:
    return "\n".join(
        f"{finding.subject} | {finding.message}"
        for finding in findings
        if level is None or finding.level == level
    )


def all_findings(snapshot, expect=EXPECT):
    return [finding for _, findings in pf.evaluate(snapshot, expect) for finding in findings]


# --- read-only by construction ---------------------------------------------------------


def without_literals(sql: str) -> str:
    return re.sub(r"'[^']*'", "''", sql)


@pytest.mark.parametrize("query", [*pf.QUERIES, pf.version_rows_query()], ids=lambda q: str(q)[:40])
def test_every_query_only_reads(query):
    sql = " ".join(str(query).split())
    assert sql.startswith(("SELECT", "SHOW", "SET"))
    if sql.startswith("SET"):
        assert sql in ALLOWED_SET_STATEMENTS
    else:
        assert not WRITE_WORDS.search(without_literals(sql)), sql


def test_the_script_never_executes_sql_outside_its_query_list():
    source = (SERVER_DIR / "scripts" / "supabase_preflight.py").read_text(encoding="utf-8")
    executed = re.findall(r"connection\.execute\(([^,)]+)", source)
    assert executed
    for name in executed:
        assert name.startswith(("Q_", "version_rows_query(")), name
    assert "exec_driver_sql" not in source
    assert ".commit(" not in source


def test_the_script_never_reads_env_files():
    """Importing it and loading the repository expectations opens no .env file."""
    code = (
        "import sys\n"
        "opened = []\n"
        "sys.addaudithook(lambda event, args: event == 'open' and str(args[0]).endswith('.env')"
        " and opened.append(str(args[0])))\n"
        "from scripts import supabase_preflight as pf\n"
        "pf.load_revisions(); pf.load_queue_spec()\n"
        "print(opened, 'app.core.config' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=SERVER_DIR, capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[] False"


# --- repository expectations -----------------------------------------------------------

CONSTRAINT_KINDS = {
    PrimaryKeyConstraint: "p",
    UniqueConstraint: "u",
    ForeignKeyConstraint: "f",
    CheckConstraint: "c",
}


FK_ACTION_CODES = {None: "a", "NO ACTION": "a", "RESTRICT": "r", "CASCADE": "c", "SET NULL": "n", "SET DEFAULT": "d"}


def model_type(column) -> str:
    compiled = column.type.compile(dialect=postgresql.dialect()).lower()
    return re.sub(r"^varchar\((\d+)\)$", r"character varying(\1)", compiled)


def model_check(constraint) -> tuple[str, frozenset[str]]:
    sql = str(constraint.sqltext.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    match = re.fullmatch(r"(?:\w+\.)?(\w+) IN \((.*)\)", sql)
    assert match, sql
    return match.group(1), frozenset(re.findall(r"'([^']*)'", match.group(2)))


def model_foreign_key(constraint) -> pf.ForeignKey:
    assert constraint.match is None, constraint.name
    return pf.ForeignKey(
        tuple(column.name for column in constraint.columns),
        constraint.referred_table.name,
        tuple(element.column.name for element in constraint.elements),
        FK_ACTION_CODES[constraint.ondelete and constraint.ondelete.upper()],
        FK_ACTION_CODES[constraint.onupdate and constraint.onupdate.upper()],
    )


def test_expected_tables_match_the_models():
    models = Base.metadata.tables
    assert set(pf.APP_TABLES) == set(models)
    for name, table in models.items():
        spec = pf.APP_TABLES[name]
        assert dict(spec.columns) == {
            column.name: (model_type(column), not column.nullable) for column in table.columns
        }, name
        for column in table.columns:
            assert column.server_default is None, (name, column.name)
            assert column.identity is None and column.computed is None, (name, column.name)
        assert spec.constraint_kinds(name) == {
            constraint.name: CONSTRAINT_KINDS[type(constraint)] for constraint in table.constraints
        }, name

        unique, foreign_keys, checks = {}, {}, {}
        for constraint in table.constraints:
            assert not constraint.deferrable and constraint.initially is None, constraint.name
            if isinstance(constraint, PrimaryKeyConstraint):
                assert spec.primary_key == tuple(column.name for column in constraint.columns), name
            elif isinstance(constraint, UniqueConstraint):
                unique[constraint.name] = tuple(column.name for column in constraint.columns)
            elif isinstance(constraint, ForeignKeyConstraint):
                foreign_keys[constraint.name] = model_foreign_key(constraint)
            else:
                checks[constraint.name] = model_check(constraint)
        assert dict(spec.unique) == unique, name
        assert dict(spec.foreign_keys) == foreign_keys, name
        assert dict(spec.checks) == checks, name

        indexes = {}
        for index in table.indexes:
            options = index.dialect_options["postgresql"]
            assert options["where"] is None and not options["using"], index.name
            assert len(index.expressions) == len(index.columns), index.name
            indexes[index.name] = pf.Index(tuple(column.name for column in index.columns), index.unique)
        assert dict(spec.indexes) == indexes, name


def test_revisions_come_from_the_repository():
    revisions = pf.load_revisions()
    assert revisions.ordered == (INITIAL_REVISION, SECURITY_REVISION)
    assert revisions.heads == (SECURITY_REVISION,)


def test_queue_expectations_come_from_the_installed_procrastinate():
    spec = pf.load_queue_spec()
    assert spec.tables == set(pf.QUEUE_TABLES)
    assert {"procrastinate_job_status", "procrastinate_job_event_type"} <= spec.types
    assert "procrastinate_fetch_job_v2" in spec.functions
    assert spec.triggers and spec.indexes


# --- target --------------------------------------------------------------------------------


@pytest.fixture
def no_connections(monkeypatch):
    """Fails the test if the script tries to create an engine; returns the attempts."""
    attempts = []

    def fake_create_engine(url, **kwargs):
        attempts.append(url)
        raise AssertionError("the script tried to connect")

    monkeypatch.setattr(pf, "create_engine", fake_create_engine)
    monkeypatch.setattr(pf, "_interactive", lambda: False)
    monkeypatch.delenv(pf.URL_ENV, raising=False)
    monkeypatch.delenv(pf.PROJECT_REF_ENV, raising=False)
    clear_libpq_overrides(monkeypatch)
    return attempts


def clear_libpq_overrides(monkeypatch) -> None:
    """Only for this test process; monkeypatch restores os.environ afterwards."""
    for name in pf.UNSAFE_LIBPQ_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def assert_no_secrets(text_: str) -> None:
    for secret in SECRET_PARTS:
        assert secret not in text_


def test_url_comes_only_from_the_dedicated_variable(no_connections, monkeypatch, capsys):
    monkeypatch.setenv("SERVER_DIRECT_URL", SUPABASE_URL)
    monkeypatch.setenv("SERVER_DATABASE_URL", SUPABASE_URL)
    monkeypatch.setenv("SERVER_TEST_DATABASE_URL", SUPABASE_URL)

    assert pf.main(["--yes"]) == 2
    captured = capsys.readouterr()
    assert pf.URL_ENV in captured.err
    assert "no fallback" in captured.err
    assert no_connections == []
    assert_no_secrets(captured.out + captured.err)


def test_the_project_reference_is_required(no_connections, monkeypatch, capsys):
    monkeypatch.setenv(pf.URL_ENV, SUPABASE_URL)
    assert pf.main(["--yes"]) == 2
    captured = capsys.readouterr()
    assert pf.PROJECT_REF_ENV in captured.err
    assert no_connections == []


@pytest.mark.parametrize(
    ("url", "args", "message"),
    [
        (
            f"postgresql+psycopg://postgres.{REF}:{PASSWORD}@db.example.invalid:5432/postgres?sslmode=require",
            [],
            "not an accepted Supabase host",
        ),
        (SUPABASE_BASE_URL, [], "sslmode=verify-full"),
        (f"{SUPABASE_BASE_URL}?sslmode=prefer", [], "sslmode=verify-full"),
        (f"{SUPABASE_BASE_URL}?sslmode=disable", [], "sslmode=verify-full"),
        (f"{SUPABASE_BASE_URL}?sslmode=require", [], "--allow-unverified-tls"),
        (f"{SUPABASE_BASE_URL}?sslmode=verify-full", [], "needs sslrootcert"),
        (f"{SUPABASE_BASE_URL}?sslmode=verify-full&sslrootcert=", [], "needs sslrootcert"),
        (f"{SUPABASE_BASE_URL}?{VERIFIED_TLS.replace('verify-full', 'verify-ca')}", [], "not that it was issued"),
        (f"{SUPABASE_BASE_URL}?sslmode=verify-ca&sslrootcert=", ["--allow-unverified-tls"], "needs sslrootcert"),
        (
            f"{SUPABASE_BASE_URL}?sslmode=verify-full&sslrootcert={quote(CA_FILE + '.missing', safe='')}",
            [],
            "sslrootcert file does not exist",
        ),
        (f"{SUPABASE_URL}&sslmode=verify-full", [], "sslmode=verify-full"),
        (f"{SUPABASE_URL}&options=-csearch_path%3Devil", [], "libpq 'options' parameter"),
        (
            SUPABASE_URL.replace(f"postgres.{REF}", "postgres"),
            [],
            "no Supabase project reference",
        ),
        (
            SUPABASE_URL.replace(f"postgres.{REF}", "postgres.zzzzzzzzzzzzzzzzzzzz"),
            [],
            "does not match",
        ),
        (
            f"postgresql+psycopg://postgres.{REF}:{PASSWORD}@/postgres?service=prod&{VERIFIED_TLS}",
            [],
            "libpq 'service' parameter",
        ),
        (
            f"postgresql+psycopg://selvia:{PASSWORD}@localhost:5432/selvia_test?options=-crole%3Dpostgres",
            ["--local-test"],
            "libpq 'options' parameter",
        ),
        (f"postgresql+psycopg://selvia:{PASSWORD}@localhost:5432/selvia_test", [], "not an accepted Supabase host"),
        (SUPABASE_URL, ["--local-test"], "only localhost"),
        (f"postgresql+psycopg://selvia:{PASSWORD}@localhost:5432/selvia_server_db", ["--local-test"], "_test"),
        ("sqlite:///preflight.db", [], "PostgreSQL"),
        (f"postgresql+psycopg://postgres.{REF}:{PASSWORD}@host:notaport/postgres", [], "not a valid"),
    ],
)
def test_unsafe_targets_are_refused_before_connecting(
    no_connections, monkeypatch, capsys, url, args, message
):
    monkeypatch.setenv(pf.URL_ENV, url)
    monkeypatch.setenv(pf.PROJECT_REF_ENV, REF)

    assert pf.main([*args, "--yes"]) == 2
    captured = capsys.readouterr()
    assert message in captured.err
    assert no_connections == []
    assert_no_secrets(captured.out + captured.err)


PRIVATE_IP = "10.20.30.40"


@pytest.mark.parametrize(
    ("url", "args", "hidden"),
    [
        # A trailing dot defeats the project-reference pattern, so the reference couldn't be masked.
        (f"postgresql+psycopg://postgres:{PASSWORD}@db.{REF}.supabase.co.:5432/postgres?{VERIFIED_TLS}", [], ()),
        (f"{SUPABASE_URL}&hostaddr={PRIVATE_IP}", [], (PRIVATE_IP,)),
        (f"{SUPABASE_URL}&host=db.internal.example", [], ("db.internal.example",)),
        (
            f"postgresql+psycopg://selvia:{PASSWORD}@localhost:5432/selvia_test?hostaddr={PRIVATE_IP}",
            ["--local-test"],
            (PRIVATE_IP,),
        ),
        (f"postgresql+psycopg://selvia:{PASSWORD}@{PRIVATE_IP}:5432/selvia_test", ["--local-test"], (PRIVATE_IP,)),
    ],
)
def test_refused_hosts_are_never_printed(no_connections, monkeypatch, capsys, url, args, hidden):
    monkeypatch.setenv(pf.URL_ENV, url)
    monkeypatch.setenv(pf.PROJECT_REF_ENV, REF)

    assert pf.main([*args, "--yes"]) == 2
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "host details are omitted" in captured.err
    assert no_connections == []
    for value in (*hidden, "supabase.co.", "pooler.supabase.com"):
        assert value not in output
    assert_no_secrets(output)


def test_a_refused_supabase_host_gets_the_fixed_message(no_connections, monkeypatch, capsys):
    monkeypatch.setenv(pf.URL_ENV, f"{SUPABASE_URL}&hostaddr={PRIVATE_IP}")
    monkeypatch.setenv(pf.PROJECT_REF_ENV, REF)

    assert pf.main(["--yes"]) == 2
    assert capsys.readouterr().err.startswith(f"ERROR: {pf.HOST_NOT_ACCEPTED} (")


def test_redacted_target_hides_the_project_reference_and_user():
    direct = pf.target_url(f"postgresql://postgres:{PASSWORD}@db.{REF}.supabase.co:5432/postgres?sslmode=require")
    assert pf.redacted_target(direct) == "postgresql db.<project-ref>.supabase.co:5432/postgres"
    assert pf.redacted_target(pf.target_url(SUPABASE_URL)) == (
        "postgresql aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
    )


def test_direct_supabase_urls_are_accepted_and_use_psycopg():
    url = pf.target_url(f"postgresql://postgres:{PASSWORD}@db.{REF}.supabase.co:5432/postgres?{VERIFIED_TLS}")
    assert url.drivername == "postgresql+psycopg"
    findings = pf.check_supabase_target(url, REF.upper())
    assert levels(findings) == {pf.PASS}
    assert "certificate chain and host name verified" in messages(findings, pf.PASS)


@pytest.mark.parametrize(
    ("query", "allow", "level", "message"),
    [
        (VERIFIED_TLS, False, pf.PASS, "sslmode=verify-full: certificate chain and host name verified"),
        ("sslmode=verify-full&sslrootcert=system", False, pf.PASS, "sslmode=verify-full"),
        (VERIFIED_TLS, True, pf.PASS, "sslmode=verify-full"),
        (VERIFIED_TLS.replace("verify-full", "verify-ca"), True, pf.WARN, "not that it was issued for this host name"),
    ],
)
def test_verified_tls_modes(query, allow, level, message):
    finding = pf.check_tls(pf.target_url(f"{SUPABASE_BASE_URL}?{query}"), allow_unverified_tls=allow)
    assert finding.level == level
    assert message in finding.message
    assert CA_FILE not in finding.message


def test_verify_ca_is_refused_unless_explicitly_allowed():
    url = pf.target_url(f"{SUPABASE_BASE_URL}?{VERIFIED_TLS.replace('verify-full', 'verify-ca')}")
    with pytest.raises(pf.PreflightRefused, match="not that it was issued for this host name"):
        pf.check_tls(url, allow_unverified_tls=False)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "holds no PEM certificate"),
        (b"SERVER_DATABASE_URL=not-a-certificate\n", "holds no PEM certificate"),
        (b"0\x82\x03\x10binary DER is not read by libpq", "holds no PEM certificate"),
    ],
)
def test_the_root_certificate_must_be_a_pem_file(tmp_path, content, message):
    path = tmp_path / "not-a-ca.crt"
    path.write_bytes(content)
    url = pf.target_url(f"{SUPABASE_BASE_URL}?sslmode=verify-full&sslrootcert={quote(str(path), safe='')}")
    with pytest.raises(pf.PreflightRefused, match=message) as refused:
        pf.check_tls(url, allow_unverified_tls=False)
    assert str(path) not in str(refused.value)
    assert "not-a-certificate" not in str(refused.value)


def test_a_directory_or_unreadable_root_certificate_is_refused(tmp_path, monkeypatch):
    url = pf.target_url(f"{SUPABASE_BASE_URL}?sslmode=verify-full&sslrootcert={quote(str(tmp_path), safe='')}")
    with pytest.raises(pf.PreflightRefused, match="does not exist"):
        pf.check_tls(url, allow_unverified_tls=False)

    def unreadable(self, *args, **kwargs):
        raise PermissionError(f"permission denied: {self}")

    monkeypatch.setattr(Path, "open", unreadable)
    with pytest.raises(pf.PreflightRefused, match="can't be read") as refused:
        pf.check_tls(pf.target_url(SUPABASE_URL), allow_unverified_tls=False)
    assert CA_FILE not in str(refused.value)


def test_tls_settings_reach_libpq_unchanged():
    """SQLAlchemy hands the URL's sslmode and sslrootcert to psycopg, and libpq accepts them."""
    engine = real_create_engine(pf.target_url(SUPABASE_URL), poolclass=NullPool)
    _, kwargs = engine.dialect.create_connect_args(engine.url)
    kwargs.pop("context", None)  # psycopg's adapters, not a libpq option
    parsed = psycopg.conninfo.conninfo_to_dict(psycopg.conninfo.make_conninfo(**kwargs))
    assert parsed["sslmode"] == "verify-full"
    assert parsed["sslrootcert"] == CA_FILE
    assert parsed["host"] == "aws-0-eu-west-1.pooler.supabase.com"
    assert "hostaddr" not in parsed


# libpq's own certificate checks, against a fake server on 127.0.0.1 that answers PostgreSQL's
# SSLRequest and completes a TLS handshake with a generated certificate. It is not a database,
# never asks for a password, and no URL here has one.


def generate_certificate(name, signer=None, ip=None, dns=None):
    """(key, certificate): a CA when `signer` is None, otherwise a server certificate it signed."""
    pytest.importorskip("cryptography")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    issuer_key, issuer = signer if signer else (key, None)
    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer.subject if issuer else subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=signer is None, path_length=None), critical=True)
    )
    if signer is None:
        usage = dict.fromkeys(
            ("digital_signature", "content_commitment", "key_encipherment", "data_encipherment",
             "key_agreement", "encipher_only", "decipher_only"),
            False,
        )
        builder = builder.add_extension(x509.KeyUsage(key_cert_sign=True, crl_sign=True, **usage), critical=True)
    else:
        names = [x509.IPAddress(ipaddress.ip_address(ip))] if ip else [x509.DNSName(dns)]
        builder = builder.add_extension(x509.SubjectAlternativeName(names), critical=False)
    return key, builder.sign(issuer_key, hashes.SHA256())


def write_pem(path, certificate, key=None):
    from cryptography.hazmat.primitives import serialization

    path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    if key is not None:
        key_path = path.with_suffix(".key")
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        return path, key_path
    return path


GSSENC_REQUEST = 80877104


@contextmanager
def fake_tls_server(cert_file, key_file):
    """Yields (port, events): "handshake" once TLS completes, then "startup" if the client sends
    anything over it. libpq's startup packet comes before any password, so no "startup" means the
    client gave up before sending credentials."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)
    listener = socket.create_server(("127.0.0.1", 0))
    listener.settimeout(10)
    events = []

    def serve():
        try:
            client, _ = listener.accept()
        except OSError:
            return
        with client:
            client.settimeout(10)
            try:
                while int.from_bytes(client.recv(8)[4:8], "big") == GSSENC_REQUEST:
                    client.sendall(b"N")  # no GSSAPI encryption; libpq follows with SSLRequest
                client.sendall(b"S")
                with context.wrap_socket(client, server_side=True) as tls:
                    events.append("handshake")
                    if tls.recv(1024):
                        events.append("startup")
            except (ssl.SSLError, OSError):
                pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1], events
    finally:
        listener.close()
        thread.join(10)


def connect_through_the_driver(port, sslmode, root_cert):
    """Connects the way the preflight does (SQLAlchemy and psycopg); returns the failure."""
    url = make_url(
        f"postgresql+psycopg://preflight@127.0.0.1:{port}/postgres"
        f"?sslmode={sslmode}&sslrootcert={quote(str(root_cert), safe='')}"
    )
    engine = real_create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": 5})
    try:
        with pytest.raises(OperationalError) as failure, engine.connect():
            pass
    finally:
        engine.dispose()
    return failure.value


@pytest.fixture
def trusted_ca(tmp_path):
    ca = generate_certificate("preflight test CA")
    return ca, write_pem(tmp_path / "trusted-ca.crt", ca[1])


@pytest.mark.parametrize(
    ("signed_by_trusted_ca", "server_name", "reason"),
    [
        (False, {"ip": "127.0.0.1"}, "certificate from an untrusted CA"),
        (True, {"dns": "db.other-project.invalid"}, "certificate for another host name"),
    ],
)
def test_libpq_rejects_a_bad_server_certificate_with_verify_full(
    tmp_path, trusted_ca, signed_by_trusted_ca, server_name, reason
):
    ca, ca_file = trusted_ca
    signer = ca if signed_by_trusted_ca else generate_certificate("impostor CA")
    server = generate_certificate("server", signer=signer, **server_name)
    cert_file, key_file = write_pem(tmp_path / "server.crt", server[1], server[0])

    with fake_tls_server(cert_file, key_file) as (port, events):
        error = connect_through_the_driver(port, "verify-full", ca_file)

    assert "startup" not in events, reason
    summary = pf.safe_error_summary(error)
    assert "the server certificate could not be verified" in summary, (reason, summary)
    for detail in (str(ca_file), "127.0.0.1", "other-project"):
        assert detail not in summary


def test_libpq_accepts_the_right_certificate_and_verify_ca_skips_the_host_name(tmp_path, trusted_ca):
    """Control: with the right certificate libpq goes on to send its startup packet (the fake
    server then hangs up), and verify-ca does so even for a certificate for another host name,
    which is why the preflight refuses verify-ca without --allow-unverified-tls."""
    ca, ca_file = trusted_ca
    for mode, server_name in (("verify-full", {"ip": "127.0.0.1"}), ("verify-ca", {"dns": "db.other-project.invalid"})):
        server = generate_certificate("server", signer=ca, **server_name)
        cert_file, key_file = write_pem(tmp_path / f"server-{mode}.crt", server[1], server[0])
        with fake_tls_server(cert_file, key_file) as (port, events):
            error = connect_through_the_driver(port, mode, ca_file)
        assert events == ["handshake", "startup"], mode
        assert "certificate could not be verified" not in pf.safe_error_summary(error), mode


def test_sslmode_require_is_refused_unless_explicitly_allowed():
    url = pf.target_url(f"{SUPABASE_BASE_URL}?sslmode=require")
    with pytest.raises(pf.PreflightRefused, match="never checks the server certificate"):
        pf.check_tls(url, allow_unverified_tls=False)
    finding = pf.check_tls(url, allow_unverified_tls=True)
    assert finding.level == pf.WARN
    assert "not verified" in finding.message


def test_allow_unverified_tls_reports_a_warning_and_still_inspects(fake_supabase, monkeypatch, capsys):
    engine = fake_supabase()
    monkeypatch.setenv(pf.URL_ENV, f"{SUPABASE_BASE_URL}?sslmode=require")
    assert pf.main(["--yes", "--allow-unverified-tls"]) == 0
    out = capsys.readouterr().out
    assert "WARN    | TLS | sslmode=require: encrypted, but the server certificate is not verified" in out
    assert inspected(engine.connection)
    assert_no_secrets(out)


@pytest.mark.parametrize("name", sorted(pf.UNSAFE_LIBPQ_VARIABLES))
@pytest.mark.parametrize(
    ("url", "args"),
    [
        (SUPABASE_URL, []),
        (f"postgresql+psycopg://selvia:{PASSWORD}@localhost:5432/selvia_test", ["--local-test"]),
    ],
    ids=["supabase", "local-test"],
)
def test_libpq_environment_overrides_are_refused(no_connections, monkeypatch, capsys, name, url, args):
    value = "sentinel-override-value"
    monkeypatch.setenv(name, value)
    monkeypatch.setenv(pf.URL_ENV, url)
    monkeypatch.setenv(pf.PROJECT_REF_ENV, REF)

    assert pf.main([*args, "--yes"]) == 2
    captured = capsys.readouterr()
    assert f"unset {name}" in captured.err
    assert value not in captured.out + captured.err
    assert no_connections == []
    assert_no_secrets(captured.out + captured.err)


def test_every_libpq_override_is_named():
    environ = dict.fromkeys(pf.UNSAFE_LIBPQ_VARIABLES, "x")
    with pytest.raises(pf.PreflightRefused) as refused:
        pf.check_connection_overrides(pf.target_url(SUPABASE_URL), environ)
    assert f"unset {', '.join(sorted(pf.UNSAFE_LIBPQ_VARIABLES))}" in str(refused.value)


def test_unrelated_libpq_variables_are_allowed():
    environ = {"PGHOST": "elsewhere", "PGSSLMODE": "disable", "PGPORT": "1"}
    pf.check_connection_overrides(pf.target_url(SUPABASE_URL), environ)


def test_the_transaction_pooler_port_is_flagged():
    url = pf.target_url(SUPABASE_URL.replace(":5432/", ":6543/"))
    findings = pf.check_supabase_target(url, REF)
    assert pf.WARN in levels(findings)
    assert "6543" in messages(findings, pf.WARN)


# --- connection identity, with a fake engine ------------------------------------------------


class FakeResult:
    def __init__(self, rows):
        self.rows = list(rows)

    def mappings(self):
        return self

    def one(self):
        (row,) = self.rows
        return row

    def all(self):
        return list(self.rows)

    def __iter__(self):
        return iter(self.rows)

    def scalars(self):
        return iter(self.rows)

    def scalar_one(self):
        (row,) = self.rows
        return row


class FakeConnection:
    """Answers queries by identity; any query not listed returns no rows.

    An answer may be a callable returning the rows, for answers that change between calls, and
    `failures` maps queries to the exception they raise."""

    def __init__(self, answers, read_only="on", failures=()):
        self.answers = answers
        self.read_only = read_only
        self.failures = failures
        self.executed = []
        self.params = []
        self.rollbacks = 0

    def execute(self, statement, params=None):
        self.executed.append(statement)
        self.params.append((statement, params))
        for query, error in self.failures:
            if query is statement:
                raise error
        if statement is pf.Q_READ_ONLY_STATUS:
            return FakeResult([self.read_only])
        for query, rows in self.answers:
            if query is statement:
                return FakeResult(rows() if callable(rows) else rows)
        assert any(statement is query for query in pf.QUERIES), str(statement)
        return FakeResult([])

    @contextmanager
    def begin_nested(self):
        yield

    def rollback(self):
        self.rollbacks += 1


class FakeEngine:
    def __init__(self, connection):
        self.connection = connection
        self.disposed = False

    @contextmanager
    def connect(self):
        yield self.connection

    def dispose(self):
        self.disposed = True


def identity_row(database="postgres", schema="public", search_path='"$user", public, extensions', role=ROLE):
    return {
        "database_name": database,
        "role_name": role,
        "session_role": role,
        "server_version": "17.4",
        "schema_name": schema,
        "search_path": search_path,
    }


def fresh_supabase_answers(database="postgres", schemas=("auth", "storage")):
    roles = [ROLE, *pf.BROWSER_ROLES]
    return [
        (pf.Q_IDENTITY, [identity_row(database)]),
        (pf.Q_SCHEMAS_PRESENT, list(schemas)),
        (pf.Q_ROLES_PRESENT, list(pf.BROWSER_ROLES)),
        (
            pf.Q_ROLES,
            [
                {"name": ROLE, "rolsuper": False, "rolbypassrls": True, "rolcanlogin": True},
                {"name": "anon", "rolsuper": False, "rolbypassrls": False, "rolcanlogin": False},
                {"name": "authenticated", "rolsuper": False, "rolbypassrls": False, "rolcanlogin": False},
                {"name": "service_role", "rolsuper": False, "rolbypassrls": True, "rolcanlogin": False},
            ],
        ),
        (
            pf.Q_SCHEMA_ACCESS,
            [{"role_name": role, "can_use": True, "can_create": role == ROLE} for role in roles],
        ),
        (pf.Q_ACTS_AS_OWNER, [{"role_name": ROLE, "owner": ROLE, "acts_as_owner": True}]),
        (pf.Q_AUTHENTICATOR, [{"rolsuper": False, "rolbypassrls": False, "rolcanlogin": True}]),
        (pf.Q_ROLE_MEMBERSHIPS, membership_rows(STOCK_MEMBERSHIPS)),
    ]


# As on a new Supabase project: authenticator is granted the three browser roles.
STOCK_MEMBERSHIPS = tuple((pf.AUTHENTICATOR, role, True) for role in pf.BROWSER_ROLES)


def membership_rows(memberships):
    return [{"member": member, "granted": granted, "can_set": can_set} for member, granted, can_set in memberships]


@pytest.fixture
def fake_supabase(monkeypatch):
    clear_libpq_overrides(monkeypatch)

    def install(answers=None, read_only="on", interactive=False, answer="yes", failures=()):
        connection = FakeConnection(answers or fresh_supabase_answers(), read_only, failures)
        engine = FakeEngine(connection)

        def fake_create_engine(url, **kwargs):
            engine.create_kwargs = kwargs
            return engine

        monkeypatch.setattr(pf, "create_engine", fake_create_engine)
        monkeypatch.setattr(pf, "_interactive", lambda: interactive)
        monkeypatch.setattr(pf, "_ask", lambda prompt: answer)
        monkeypatch.setenv(pf.URL_ENV, SUPABASE_URL)
        monkeypatch.setenv(pf.PROJECT_REF_ENV, REF)
        return engine

    return install


def inspected(connection) -> bool:
    return any(statement is pf.Q_RELATIONS for statement in connection.executed)


def test_a_fresh_supabase_database_passes_and_only_reads(fake_supabase, capsys):
    engine = fake_supabase()

    assert pf.main(["--yes"]) == 0
    out = capsys.readouterr().out
    assert "fresh database" in out
    assert "queue schema not installed" in out
    assert engine.connection.executed[0] is pf.Q_SET_READ_ONLY
    assert all(any(s is q for q in pf.QUERIES) for s in engine.connection.executed)
    assert engine.connection.rollbacks == 2
    assert engine.disposed
    assert_no_secrets(out)


def test_the_connection_attempt_has_a_bounded_timeout(fake_supabase, monkeypatch):
    engine = fake_supabase()
    monkeypatch.setenv(pf.URL_ENV, SUPABASE_URL + "&connect_timeout=0")
    assert pf.main(["--yes"]) == 0
    assert engine.create_kwargs["connect_args"] == {"connect_timeout": pf.CONNECT_TIMEOUT_SECONDS}
    assert 0 < pf.CONNECT_TIMEOUT_SECONDS <= 30


def test_a_role_missing_from_the_role_query_blocks_the_report(fake_supabase, capsys):
    answers = [
        (query, [row for row in rows if row.get("name") != "anon"] if query is pf.Q_ROLES else rows)
        for query, rows in fresh_supabase_answers()
    ]
    fake_supabase(answers)
    assert pf.main(["--yes"]) == 1
    out = capsys.readouterr().out
    assert "role query returned nothing for anon" in out
    assert "NOT READY" in out


def test_inspection_waits_for_a_read_only_transaction(fake_supabase, capsys):
    engine = fake_supabase(read_only="off")
    assert pf.main(["--yes"]) == 2
    assert "not read-only" in capsys.readouterr().err
    assert engine.connection.executed[-1] is pf.Q_READ_ONLY_STATUS


@pytest.mark.parametrize(
    ("answers", "message"),
    [
        (fresh_supabase_answers(database="other_db"), "expected 'postgres'"),
        (fresh_supabase_answers(schemas=()), "does not look like a Supabase database"),
    ],
)
def test_a_wrong_identity_stops_before_inspection(fake_supabase, capsys, answers, message):
    engine = fake_supabase(answers)
    assert pf.main(["--yes"]) == 2
    assert message in capsys.readouterr().err
    assert not inspected(engine.connection)


def test_declining_the_confirmation_stops_before_inspection(fake_supabase, capsys):
    engine = fake_supabase(interactive=True, answer="no")
    assert pf.main([]) == 2
    assert "not confirmed" in capsys.readouterr().err
    assert not inspected(engine.connection)


def test_without_a_terminal_the_identity_needs_yes(fake_supabase, capsys):
    engine = fake_supabase(interactive=False)
    assert pf.main([]) == 2
    assert "--yes" in capsys.readouterr().err
    assert not inspected(engine.connection)


def test_hidden_prompts_are_used_when_the_variables_are_unset(fake_supabase, monkeypatch, capsys):
    fake_supabase(interactive=True, answer="yes")
    monkeypatch.delenv(pf.URL_ENV)
    monkeypatch.delenv(pf.PROJECT_REF_ENV)
    prompts = []

    def secret_input(prompt):
        prompts.append(prompt)
        return SUPABASE_URL if "URL" in prompt else REF

    monkeypatch.setattr(pf, "_secret_input", secret_input)
    assert pf.main([]) == 0
    out = capsys.readouterr().out
    assert len(prompts) == 2
    assert "URL from hidden prompt" in out
    assert_no_secrets(out)


def test_connection_errors_never_print_server_messages(monkeypatch, capsys):
    class FakeAuthError(Exception):
        sqlstate = "28P01"

    class FailingEngine(FakeEngine):
        @contextmanager
        def connect(self):
            raise OperationalError(
                "connect",
                {},
                FakeAuthError(f'password authentication failed for user "postgres.{REF}" {PASSWORD}'),
            )
            yield

    monkeypatch.setattr(pf, "create_engine", lambda url, **kwargs: FailingEngine(None))
    clear_libpq_overrides(monkeypatch)
    monkeypatch.setenv(pf.URL_ENV, SUPABASE_URL)
    monkeypatch.setenv(pf.PROJECT_REF_ENV, REF)

    assert pf.main(["--yes"]) == 1
    captured = capsys.readouterr()
    assert "SQLSTATE 28P01: authentication failed" in captured.err
    assert_no_secrets(captured.out + captured.err)


class FakeServerError(Exception):
    def __init__(self, sqlstate):
        super().__init__(f'server says: user "postgres.{REF}" password {PASSWORD} host {SUPABASE_URL}')
        self.sqlstate = sqlstate


def database_error(sqlstate, invalidated=False):
    return OperationalError(
        "SELECT ...", {}, FakeServerError(sqlstate), connection_invalidated=invalidated
    )


@pytest.mark.parametrize(
    ("message", "hint"),
    [
        (f'FATAL:  password authentication failed for user "postgres.{REF}"', "wrong user name or password"),
        (f'FATAL:  database "{REF}" does not exist', "the database or role does not exist"),
        (
            f'root certificate file "{CA_FILE}" does not exist\nEither provide the file or change sslmode',
            "a certificate file could not be read",
        ),
        (f'could not read root certificate file "{CA_FILE}": permission denied', "a certificate file could not be read"),
        ("SSL error: certificate verify failed", "the server certificate could not be verified"),
        (f'FATAL:  no pg_hba.conf entry for host "10.0.0.1", user "postgres.{REF}"', "pg_hba.conf has no entry"),
        (f"connection to server at {SUPABASE_URL} failed: Connection refused", "connection refused"),
        ("connection to server failed: timeout expired", "timed out"),
        (f"server sent {PASSWORD} something unusual", "no SQLSTATE: the connection failed or was lost"),
    ],
)
def test_connection_failures_without_sqlstate_get_a_fixed_hint(monkeypatch, capsys, message, hint):
    class FailingEngine(FakeEngine):
        @contextmanager
        def connect(self):
            raise OperationalError("connect", {}, Exception(message))
            yield

    monkeypatch.setattr(pf, "create_engine", lambda url, **kwargs: FailingEngine(None))
    clear_libpq_overrides(monkeypatch)
    monkeypatch.setenv(pf.URL_ENV, SUPABASE_URL)
    monkeypatch.setenv(pf.PROJECT_REF_ENV, REF)

    assert pf.main(["--yes"]) == 1
    captured = capsys.readouterr()
    assert "SQLSTATE unknown: " in captured.err
    assert hint in captured.err
    assert captured.err.rstrip().endswith("while connecting")
    assert message not in captured.err
    assert_no_secrets(captured.out + captured.err)


def test_an_identity_change_between_transactions_stops_before_inspection(fake_supabase, capsys):
    identities = iter([[identity_row()], [identity_row(role="someone_else")]])
    answers = [
        (query, (lambda: next(identities)) if query is pf.Q_IDENTITY else rows)
        for query, rows in fresh_supabase_answers()
    ]
    engine = fake_supabase(answers)
    assert pf.main(["--yes"]) == 2
    captured = capsys.readouterr()
    assert "identity changed between transactions" in captured.err
    assert not inspected(engine.connection)
    assert engine.disposed


def test_losing_the_connection_during_inspection_stops_without_a_report(fake_supabase, capsys):
    engine = fake_supabase(failures=[(pf.Q_GRANTS, database_error("08006", invalidated=True))])
    assert pf.main(["--yes"]) == 1
    captured = capsys.readouterr()
    assert "SQLSTATE 08006: connection failure) after connecting" in captured.err
    assert "Summary:" not in captured.out
    # Nothing after the failed read ran: a reconnect would be outside the read-only transaction.
    assert engine.connection.executed[-1] is pf.Q_GRANTS
    assert engine.disposed
    assert_no_secrets(captured.out + captured.err)


def test_one_failed_section_is_limited_and_the_rest_still_run(fake_supabase, capsys):
    engine = fake_supabase(failures=[(pf.Q_TYPES, database_error("42501"))])
    assert pf.main(["--yes"]) == 1
    captured = capsys.readouterr()
    assert "LIMITED | routines and types | database error FakeServerError (SQLSTATE 42501" in captured.out
    assert "NOT READY" in captured.out
    assert any(statement is pf.Q_DEFAULT_ACL for statement in engine.connection.executed)
    assert_no_secrets(captured.out + captured.err)


def test_an_unexpected_error_before_connecting_is_sanitised(no_connections, monkeypatch, capsys):
    def explode():
        raise RuntimeError(f"cannot read {SUPABASE_URL}")

    monkeypatch.setattr(pf, "load_queue_spec", explode)
    monkeypatch.setenv(pf.URL_ENV, SUPABASE_URL)
    monkeypatch.setenv(pf.PROJECT_REF_ENV, REF)
    assert pf.main(["--yes"]) == 1
    captured = capsys.readouterr()
    assert "ERROR: unexpected RuntimeError at test_supabase_preflight.py" in captured.err
    assert "in explode (details hidden). Nothing was changed." in captured.err
    assert "cannot read" not in captured.err
    assert no_connections == []
    assert_no_secrets(captured.out + captured.err)


def test_an_unexpected_error_during_inspection_is_sanitised(fake_supabase, monkeypatch, capsys):
    engine = fake_supabase()

    def explode(connection, roles):
        raise KeyError(f"{PASSWORD} {SUPABASE_URL}")

    monkeypatch.setattr(pf, "inspect_database", explode)
    assert pf.main(["--yes"]) == 1
    captured = capsys.readouterr()
    assert "ERROR: unexpected KeyError" in captured.err
    assert "Summary:" not in captured.out
    assert engine.disposed
    assert_no_secrets(captured.out + captured.err)


@pytest.mark.parametrize(
    ("search_path", "refused"),
    [
        ('"$user", public, extensions', False),
        ("pg_catalog, public", False),
        ("", False),
        ("public, pg_catalog", True),
        ('"$user", "pg_catalog"', True),
        ("pg_temp, pg_catalog, public", True),
    ],
)
def test_search_path_must_not_put_pg_catalog_after_another_schema(search_path, refused):
    identity = pf.Identity("postgres", ROLE, ROLE, "17.4", "public", pf.SUPABASE_SCHEMAS, pf.BROWSER_ROLES, search_path)
    problems = pf.identity_problems(identity, "postgres", supabase=True)
    assert any("pg_catalog after another schema" in problem for problem in problems) == refused


def test_an_unsafe_search_path_stops_before_inspection(fake_supabase, capsys):
    answers = [
        (query, [identity_row(search_path="public, pg_catalog")] if query is pf.Q_IDENTITY else rows)
        for query, rows in fresh_supabase_answers()
    ]
    engine = fake_supabase(answers)
    assert pf.main(["--yes"]) == 2
    assert "pg_catalog after another schema" in capsys.readouterr().err
    assert not inspected(engine.connection)


def test_catalog_functions_are_schema_qualified():
    functions = (
        "current_database|current_setting|current_schema|has_\\w+_privilege|pg_has_role|unnest|"
        "starts_with|quote_ident|aclexplode|acldefault|format_type|pg_get_\\w+"
    )
    for query in pf.QUERIES:
        sql = str(query)
        assert not re.search(rf"(?<![\w.])({functions})\(", sql), sql
        assert not re.search(r"AS regclass\)", sql), sql


def test_a_non_public_current_schema_fails():
    identity = pf.Identity("postgres", ROLE, ROLE, "17.4", "extensions", (), ())
    assert pf.FAIL in levels(pf.identity_findings(identity, []))


# --- evaluation ---------------------------------------------------------------------------------


def fresh_snapshot() -> pf.Snapshot:
    return pf.Snapshot(
        roles={
            ROLE: pf.RoleInfo(False, True, True),
            "anon": pf.RoleInfo(False, False, False),
            "authenticated": pf.RoleInfo(False, False, False),
            "service_role": pf.RoleInfo(False, True, False),
        },
        schema_access={
            ROLE: (True, True),
            "anon": (True, False),
            "authenticated": (True, False),
            "service_role": (True, False),
        },
        authenticator=pf.RoleInfo(False, False, True),
        api_roles=pf.BROWSER_ROLES,
    )


def check_definition(column: str, values) -> str:
    """A CHECK (column IN (...)) on a varchar column as pg_get_constraintdef() prints it."""
    array = ", ".join(f"'{value}'::character varying" for value in sorted(values))
    return f"CHECK ((({column})::text = ANY ((ARRAY[{array}])::text[])))"


def spec_constraints(table: str, spec: pf.TableSpec) -> dict[str, pf.ConstraintInfo]:
    constraints = {f"pk_{table}": pf.ConstraintInfo("p", spec.primary_key)}
    constraints |= {name: pf.ConstraintInfo("u", columns) for name, columns in spec.unique.items()}
    constraints |= {
        name: pf.ConstraintInfo(
            "f", fk.columns, "public", fk.table, fk.referred, fk.on_delete, fk.on_update, pf.FK_MATCH_SIMPLE
        )
        for name, fk in spec.foreign_keys.items()
    }
    constraints |= {
        name: pf.ConstraintInfo("c", (column,), definition=check_definition(column, values))
        for name, (column, values) in spec.checks.items()
    }
    return constraints


def grant_access(s: pf.Snapshot, table: str, browser_privileges) -> None:
    for role in pf.BROWSER_ROLES:
        s.access[(table, role)] = frozenset(browser_privileges)
        s.column_access[(table, role)] = frozenset(browser_privileges) & set(pf.COLUMN_PRIVILEGES)
    s.access[(table, ROLE)] = frozenset(pf.TABLE_PRIVILEGES)
    s.column_access[(table, ROLE)] = frozenset(pf.COLUMN_PRIVILEGES)


def add_core_tables(s: pf.Snapshot, revision: str | None = SECURITY_REVISION, owner=ROLE) -> pf.Snapshot:
    secured = revision == SECURITY_REVISION
    for name, spec in pf.APP_TABLES.items():
        s.relations[name] = pf.Relation("r", owner, secured, False)
        s.columns[name] = {column: pf.ColumnInfo(*definition) for column, definition in spec.columns.items()}
        s.constraints[name] = spec_constraints(name, spec)
        s.indexes[name] = {index: pf.IndexInfo(i.columns, i.unique) for index, i in spec.indexes.items()}
    s.relations[pf.VERSION_TABLE] = pf.Relation("r", owner, secured, False)
    s.version_schemas = ["public"]
    s.version_rows = [revision] if revision else []
    for table in [*pf.APP_TABLES, pf.VERSION_TABLE]:
        grant_access(s, table, () if secured else ("SELECT", "INSERT"))
    return s


def add_queue(s: pf.Snapshot, secured=True, tables=pf.QUEUE_TABLES) -> pf.Snapshot:
    for table in tables:
        s.relations[table] = pf.Relation("r", ROLE, secured, False)
        grant_access(s, table, () if secured else ("SELECT",))
    s.indexes["procrastinate_jobs"] = {"procrastinate_jobs_queue_name_idx_v1": pf.IndexInfo(("queue_name",))}
    s.triggers["procrastinate_jobs"] = {"procrastinate_trigger_status_events_insert_v1"}
    s.types["procrastinate_job_status"] = False
    s.routines.append(pf.Routine("procrastinate_fetch_job_v2", FETCH_JOB, ROLE, False, not secured))
    for role in (*pf.BROWSER_ROLES, ROLE):
        s.routine_access[(FETCH_JOB, role)] = role == ROLE or not secured
    return s


def test_fresh_database_has_no_blocking_findings():
    findings = all_findings(fresh_snapshot())
    assert not levels(findings) & pf.BLOCKING, messages(findings)
    assert "fresh database" in messages(findings, pf.PASS)


def test_service_role_bypassrls_is_reported_and_browser_bypass_fails():
    s = fresh_snapshot()
    report = messages(pf.evaluate_roles(s, EXPECT), pf.INFO)
    assert "service_role | exists: BYPASSRLS yes" in report
    assert "only the revokes keep it out" in report

    s.roles["anon"] = pf.RoleInfo(False, True, False)
    assert "anon | can bypass RLS" in messages(pf.evaluate_roles(s, EXPECT), pf.FAIL)


def test_a_migrated_and_secured_database_passes():
    findings = all_findings(add_queue(add_core_tables(fresh_snapshot())))
    assert not levels(findings) & pf.BLOCKING, messages(findings)
    assert f"at head {SECURITY_REVISION}" in messages(findings, pf.PASS)
    assert messages(findings, pf.PASS).count("match the models") == 6
    assert messages(findings, pf.PASS).count("RLS on, not forced") == 7 + 4


def test_tables_without_alembic_history_fail():
    s = add_core_tables(fresh_snapshot())
    s.version_schemas, s.version_rows = [], None
    del s.relations[pf.VERSION_TABLE]
    assert "created outside Alembic" in messages(pf.evaluate_alembic(s, EXPECT), pf.FAIL)


def test_an_empty_version_table_warns_without_tables_and_fails_with_them():
    s = fresh_snapshot()
    s.version_schemas, s.version_rows = ["public"], []
    s.relations[pf.VERSION_TABLE] = pf.Relation("r", ROLE, True, False)
    assert "exists but is empty" in messages(pf.evaluate_alembic(s, EXPECT), pf.WARN)

    s = add_core_tables(fresh_snapshot(), revision=None)
    assert "is empty, but Core API tables exist" in messages(pf.evaluate_alembic(s, EXPECT), pf.FAIL)


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (["0123456789ab"], "not in this repository"),
        ([INITIAL_REVISION, SECURITY_REVISION], "single head"),
    ],
)
def test_unknown_or_multiple_revisions_fail(rows, message):
    s = add_core_tables(fresh_snapshot())
    s.version_rows = rows
    assert message in messages(pf.evaluate_alembic(s, EXPECT), pf.FAIL)


def test_recorded_revision_with_missing_tables_fails():
    s = add_core_tables(fresh_snapshot())
    del s.relations["agent_runs"]
    assert "agent_runs" in messages(pf.evaluate_alembic(s, EXPECT), pf.FAIL)
    assert "only some exist" in messages(pf.evaluate_app_tables(s, EXPECT), pf.FAIL)


def test_pending_revisions_are_listed_and_browser_access_only_warns_before_securing():
    s = add_core_tables(fresh_snapshot(), revision=INITIAL_REVISION)
    assert f"pending: {SECURITY_REVISION}" in messages(pf.evaluate_alembic(s, EXPECT), pf.INFO)
    rls = pf.evaluate_rls(s, EXPECT)
    assert pf.FAIL not in levels(rls)
    assert "the security migration revokes this" in messages(rls, pf.WARN)


def test_browser_access_after_securing_fails():
    s = add_core_tables(fresh_snapshot())
    s.access[("users", "anon")] = frozenset({"SELECT"})
    assert "users | accessible to anon: SELECT" in messages(pf.evaluate_rls(s, EXPECT), pf.FAIL)


def test_public_grants_and_forced_rls_fail():
    s = add_core_tables(fresh_snapshot())
    s.grants["projects"] = {"PUBLIC": {"SELECT"}}
    s.relations["groups"] = pf.Relation("r", ROLE, True, True)
    failures = messages(pf.evaluate_rls(s, EXPECT), pf.FAIL)
    assert "projects | PUBLIC (every role) has SELECT" in failures
    assert "groups | FORCE ROW LEVEL SECURITY" in failures


def test_a_missing_permission_record_fails_closed():
    s = add_core_tables(fresh_snapshot())
    del s.access[("users", "authenticated")]
    assert "no permission record for authenticated" in messages(pf.evaluate_rls(s, EXPECT), pf.FAIL)


def test_schema_drift_is_reported():
    s = add_core_tables(fresh_snapshot())
    s.columns["users"]["name"] = pf.ColumnInfo("text", True)
    s.indexes["users"] = {"ix_users_extra": pf.IndexInfo(("name",))}
    del s.constraints["groups"]["uq_groups_code"]
    findings = pf.evaluate_app_tables(s, EXPECT)
    assert "column name is text, expected character varying(255)" in messages(findings, pf.FAIL)
    assert "missing constraint uq_groups_code" in messages(findings, pf.FAIL)
    assert "index ix_users_extra is not in the models" in messages(findings, pf.WARN)


def change_column(table, name, **changes):
    def mutate(s):
        s.columns[table][name] = dataclasses.replace(s.columns[table][name], **changes)

    return mutate


def change_constraint(table, name, **changes):
    def mutate(s):
        s.constraints[table][name] = dataclasses.replace(s.constraints[table][name], **changes)

    return mutate


def change_index(table, name, **changes):
    def mutate(s):
        s.indexes[table][name] = dataclasses.replace(s.indexes[table][name], **changes)

    return mutate


def add_to(attribute, table, name, value):
    def mutate(s):
        getattr(s, attribute)[table][name] = value

    return mutate


@pytest.mark.parametrize(
    ("table", "mutate", "message"),
    [
        (
            "group_members",
            change_constraint("group_members", "fk_group_members_group_id_groups", on_delete="a"),
            "foreign key fk_group_members_group_id_groups has ON DELETE NO ACTION, expected CASCADE",
        ),
        (
            "projects",
            change_constraint("projects", "fk_projects_group_id_groups", on_delete="c"),
            "foreign key fk_projects_group_id_groups has ON DELETE CASCADE, expected RESTRICT",
        ),
        (
            "projects",
            change_constraint("projects", "fk_projects_created_by_id_users", on_update="c"),
            "has ON UPDATE CASCADE, expected NO ACTION",
        ),
        (
            "group_members",
            change_constraint("group_members", "fk_group_members_group_id_groups", referred_table="projects"),
            "is (group_id) -> public.projects(id), expected (group_id) -> public.groups(id)",
        ),
        (
            "group_members",
            change_constraint("group_members", "fk_group_members_user_id_users", referred_schema="auth"),
            "is (user_id) -> auth.users(id), expected (user_id) -> public.users(id)",
        ),
        (
            "project_documents",
            change_constraint(
                "project_documents", "fk_project_documents_project_id_projects", referred_columns=("title",)
            ),
            "-> public.projects(title), expected",
        ),
        (
            "projects",
            change_constraint("projects", "fk_projects_group_id_groups", match_type="f"),
            "foreign key fk_projects_group_id_groups is not MATCH SIMPLE",
        ),
        (
            "group_members",
            change_constraint("group_members", "uq_group_members_group_id_user_id", columns=("group_id",)),
            "constraint uq_group_members_group_id_user_id is on (group_id), expected (group_id, user_id)",
        ),
        (
            "groups",
            change_constraint("groups", "pk_groups", columns=("code",)),
            "constraint pk_groups is on (code), expected (id)",
        ),
        ("groups", change_constraint("groups", "uq_groups_code", deferrable=True), "is DEFERRABLE"),
        ("groups", change_constraint("groups", "uq_groups_code", kind="x"), "has type x, expected u"),
        (
            "projects",
            change_constraint("projects", "fk_projects_group_id_groups", validated=False),
            "constraint fk_projects_group_id_groups is NOT VALID",
        ),
        (
            "users",
            change_constraint(
                "users", "ck_users_role", definition=check_definition("role", {"student", "lecturer"})
            ),
            "constraint ck_users_role allows lecturer, student; expected admin, lecturer, student",
        ),
        (
            "agent_runs",
            change_constraint(
                "agent_runs", "ck_agent_runs_status", definition=check_definition("requester_role", pf.STATUS_VALUES)
            ),
            "ck_agent_runs_status could not be compared",
        ),
        (
            "projects",
            change_index("projects", "ix_projects_group_id", columns=("created_by_id",)),
            "index ix_projects_group_id is on (created_by_id), expected (group_id)",
        ),
        (
            "projects",
            change_index("projects", "ix_projects_group_id", columns=("group_id", "title")),
            "index ix_projects_group_id is on (group_id, title), expected (group_id)",
        ),
        ("agent_runs", change_index("agent_runs", "ix_agent_runs_status", unique=True), "is UNIQUE"),
        (
            "agent_runs",
            change_index("agent_runs", "ix_agent_runs_status", predicate="((status)::text = 'queued'::text)"),
            "index ix_agent_runs_status is partial (WHERE ((status)::text = 'queued'::text))",
        ),
        (
            "agent_runs",
            change_index("agent_runs", "ix_agent_runs_group_id", columns=(None,), has_expressions=True),
            "index ix_agent_runs_group_id indexes an expression",
        ),
        ("agent_runs", change_index("agent_runs", "ix_agent_runs_group_id", method="hash"), "uses hash"),
        ("agent_runs", change_index("agent_runs", "ix_agent_runs_group_id", valid=False), "is INVALID"),
        (
            "users",
            change_column("users", "id", default="gen_random_uuid()"),
            "column id has DEFAULT gen_random_uuid(); the models define none",
        ),
        ("users", change_column("users", "id", identity="a"), "column id is an identity column"),
        ("users", change_column("users", "name", generated="s"), "column name is a generated column"),
        (
            "users",
            add_to("columns", "users", "tenant_id", pf.ColumnInfo(pf.UUID, True)),
            "column tenant_id is not in the models and is NOT NULL without a default",
        ),
        (
            "users",
            add_to("indexes", "users", "ix_users_name", pf.IndexInfo(("name",), unique=True)),
            "unique index ix_users_name is not in the models and may reject rows",
        ),
        (
            "users",
            add_to("constraints", "users", "ck_users_name", pf.ConstraintInfo("c", ("name",))),
            "constraint ck_users_name (c) is not in the models and may reject rows",
        ),
    ],
)
def test_definition_mismatches_never_pass(table, mutate, message):
    s = add_core_tables(fresh_snapshot())
    mutate(s)
    findings = pf.evaluate_app_tables(s, EXPECT)
    assert message in messages(findings), messages(findings)
    assert levels(finding for finding in findings if message in finding.message) <= pf.BLOCKING
    assert f"{table} | columns, constraints and indexes match the models" not in messages(findings, pf.PASS)
    assert f"{table} | everything the models define matches" not in messages(findings, pf.PASS)


def test_an_unrecognised_check_is_limited_not_passed(capsys):
    s = add_core_tables(fresh_snapshot())
    s.constraints["users"]["ck_users_role"] = pf.ConstraintInfo(
        "c", ("role",), definition="CHECK ((length((role)::text) > 0))"
    )
    findings = pf.evaluate_app_tables(s, EXPECT)
    assert "users | constraint ck_users_role could not be compared" in messages(findings, pf.LIMITED)
    assert not [f for f in findings if f.subject == "users" and f.level == pf.PASS and "models" in f.message]
    assert pf.print_report([("Core API tables", findings)]) == 1


def test_extras_that_cannot_reject_rows_only_warn():
    s = add_core_tables(fresh_snapshot())
    s.columns["users"]["nickname"] = pf.ColumnInfo(pf.TEXT, False)
    s.indexes["users"] = {"ix_users_name": pf.IndexInfo(("name",))}
    findings = pf.evaluate_app_tables(s, EXPECT)
    assert levels(finding for finding in findings if finding.subject == "users") == {pf.WARN, pf.PASS}
    assert "users | everything the models define matches" in messages(findings, pf.PASS)


@pytest.mark.parametrize(
    ("definition", "expected"),
    [
        (check_definition("role", pf.ROLE_VALUES), pf.ROLE_VALUES),
        (check_definition("status", {"it''s"}), frozenset({"it's"})),
        ("CHECK ((role = ANY (ARRAY['student'::text, 'admin'::text])))", None),
        ("CHECK (((role)::text = 'student'::text))", None),
        (check_definition("other", pf.ROLE_VALUES), None),
        ("CHECK ((((role)::text = ANY ((ARRAY['admin'::character varying])::text[])) OR true))", None),
        ("CHECK (((role)::text = ANY ((ARRAY[E'a\\\\b'::character varying])::text[])))", None),
        ("CHECK ((length((role)::text) > 0))", None),
        ("", None),
    ],
)
def test_check_values_accepts_only_the_expected_form(definition, expected):
    column = "status" if "status" in definition else "role"
    assert pf.check_values(definition, column) == expected


# --- column privileges ---------------------------------------------------------------------


def test_no_column_grants_pass():
    findings = pf.evaluate_rls(add_core_tables(fresh_snapshot()), EXPECT)
    assert messages(findings, pf.PASS).count("no privileges for PUBLIC or the Supabase browser roles") == 7
    assert not levels(findings) & pf.BLOCKING, messages(findings)


def test_column_grants_to_browser_roles_fail_after_securing():
    s = add_core_tables(fresh_snapshot())
    s.column_access[("users", "anon")] = frozenset({"SELECT"})
    s.column_grants["users"] = {"anon": {("name", "SELECT"), ("role", "SELECT")}}
    s.column_access[("agent_runs", "authenticated")] = frozenset({"UPDATE"})
    findings = pf.evaluate_rls(s, EXPECT)
    failures = messages(findings, pf.FAIL)
    assert "users | accessible to anon: SELECT on columns name, role" in failures
    assert "agent_runs | accessible to authenticated: UPDATE on some columns" in failures
    assert "users | direct column grants: anon: SELECT on columns name, role" in messages(findings, pf.INFO)
    passed = messages(findings, pf.PASS)
    assert "users | no privileges" not in passed
    assert "agent_runs | no privileges" not in passed


def test_column_grants_before_securing_warn():
    s = add_core_tables(fresh_snapshot(), revision=INITIAL_REVISION)
    s.column_access[("users", "anon")] |= {"REFERENCES"}
    s.column_grants["users"] = {"anon": {("id", "REFERENCES")}}
    warnings = messages(pf.evaluate_rls(s, EXPECT), pf.WARN)
    assert "users | accessible to anon: INSERT, SELECT, REFERENCES on columns id" in warnings


def test_public_column_grants_fail():
    s = add_core_tables(fresh_snapshot())
    s.column_grants["projects"] = {"PUBLIC": {("title", "SELECT")}}
    failures = messages(pf.evaluate_rls(s, EXPECT), pf.FAIL)
    assert "projects | PUBLIC (every role) has SELECT on columns title" in failures


def test_a_missing_column_permission_record_fails_closed():
    s = add_core_tables(fresh_snapshot())
    del s.column_access[("users", "anon")]
    findings = pf.evaluate_rls(s, EXPECT)
    assert "users | no permission record for anon" in messages(findings, pf.FAIL)
    assert "users | no privileges" not in messages(findings, pf.PASS)


def test_column_grants_on_a_secured_queue_fail():
    s = add_queue(fresh_snapshot())
    s.column_grants["procrastinate_jobs"] = {"PUBLIC": {("queue_name", "SELECT")}}
    s.column_access[("procrastinate_jobs", "anon")] = frozenset({"SELECT"})
    findings = pf.evaluate_queue(s, EXPECT)
    failures = messages(findings, pf.FAIL)
    assert "procrastinate_jobs | accessible to PUBLIC: SELECT on columns queue_name; anon: SELECT on some" in failures
    assert "rerun scripts.secure_queue_schema --apply" in failures
    assert "procrastinate_jobs | no privileges" not in messages(findings, pf.PASS)


def test_column_grants_on_an_unsecured_queue_warn():
    s = add_queue(fresh_snapshot(), secured=False)
    s.column_grants["procrastinate_jobs"] = {"PUBLIC": {("queue_name", "SELECT")}}
    findings = pf.evaluate_queue(s, EXPECT)
    assert "procrastinate_jobs | accessible to PUBLIC: SELECT on columns queue_name" in messages(findings, pf.WARN)
    assert pf.FAIL not in levels(findings)


# --- sequences, views, other relations and routines ------------------------------------------


def add_relation(s: pf.Snapshot, name: str, relation: pf.Relation, privileges=(), column_privileges=()):
    """A relation outside the Core API and queue tables, with the same access for every browser role."""
    s.relations[name] = relation
    for role in pf.BROWSER_ROLES:
        s.object_access[(name, role)] = frozenset(privileges)
        s.object_column_access[(name, role)] = frozenset(column_privileges)
    return s


def add_routine(s: pf.Snapshot, routine: pf.Routine, callers=()):
    s.routines.append(routine)
    for role in pf.BROWSER_ROLES:
        s.routine_access[(routine.signature, role)] = role in callers
    return s


def routine(name, security_definer=False, public_execute=False, kind="f", extension_member=False):
    return pf.Routine(name, f"public.{name}()", ROLE, security_definer, public_execute, extension_member, kind)


def object_findings(s):
    return pf.evaluate_object_access(s, EXPECT)


def test_nothing_else_in_public_passes():
    findings = object_findings(add_queue(add_core_tables(fresh_snapshot())))
    assert levels(findings) == {pf.PASS}
    assert "none is SECURITY DEFINER" in messages(findings, pf.PASS)


@pytest.mark.parametrize(
    ("relation", "privileges", "column_privileges", "message"),
    [
        (pf.Relation("v", ROLE, False, False), {"SELECT"}, (), "view runs with postgres's privileges"),
        (
            pf.Relation("v", ROLE, False, False, options=("security_invoker=false",)),
            {"SELECT"},
            (),
            "view runs with",
        ),
        (pf.Relation("v", ROLE, False, False), (), {"SELECT"}, "anon: SELECT on some columns"),
        (pf.Relation("m", ROLE, False, False), {"SELECT"}, (), "materialized view: RLS doesn't apply"),
        (pf.Relation("f", ROLE, False, False), {"SELECT"}, (), "foreign table: RLS doesn't apply"),
        (pf.Relation("S", ROLE, False, False, owned_by="users"), {"USAGE"}, (), "sequence of users"),
        (pf.Relation("r", ROLE, False, False), {"SELECT"}, (), "RLS off: every row is visible"),
        (pf.Relation("p", ROLE, False, False), {"INSERT"}, (), "RLS off"),
    ],
)
def test_browser_access_that_can_expose_data_fails(relation, privileges, column_privileges, message):
    s = add_relation(fresh_snapshot(), "exposed", relation, privileges, column_privileges)
    findings = object_findings(s)
    assert message in messages(findings, pf.FAIL), messages(findings)
    assert pf.PASS not in levels(findings)


@pytest.mark.parametrize(
    ("relation", "privileges", "message"),
    [
        (
            pf.Relation("v", ROLE, False, False, options=("security_invoker=true",)),
            {"SELECT"},
            "security_invoker view",
        ),
        (pf.Relation("v", ROLE, False, False, options=("security_invoker=on",)), {"SELECT"}, "security_invoker"),
        (pf.Relation("v", ROLE, False, False, extension_member=True), {"SELECT"}, "belongs to an extension"),
        (pf.Relation("S", ROLE, False, False), {"USAGE", "SELECT"}, "sequence: callers can read and advance it"),
        (pf.Relation("r", ROLE, True, False), {"SELECT"}, "RLS on: its policies decide"),
    ],
)
def test_browser_access_that_relies_on_rls_or_extensions_warns(relation, privileges, message):
    s = add_relation(fresh_snapshot(), "shared", relation, privileges)
    findings = object_findings(s)
    assert levels(findings) == {pf.WARN}, messages(findings)
    assert message in messages(findings, pf.WARN)


@pytest.mark.parametrize("kind", ["v", "m", "f", "S", "r"])
def test_relations_without_browser_access_pass(kind):
    s = add_relation(fresh_snapshot(), "private", pf.Relation(kind, ROLE, False, False))
    assert levels(object_findings(s)) == {pf.PASS}


def test_public_grants_on_other_relations_fail():
    s = add_relation(fresh_snapshot(), "report", pf.Relation("v", ROLE, False, False))
    s.grants["report"] = {"PUBLIC": {"SELECT"}}
    assert "report | view accessible to PUBLIC: SELECT" in messages(object_findings(s), pf.FAIL)

    s = add_relation(fresh_snapshot(), "report", pf.Relation("m", ROLE, False, False))
    s.column_grants["report"] = {"PUBLIC": {("total", "SELECT")}}
    assert "PUBLIC: SELECT on columns total" in messages(object_findings(s), pf.FAIL)


def test_a_missing_object_permission_record_fails_closed():
    s = add_relation(fresh_snapshot(), "report", pf.Relation("v", ROLE, False, False))
    del s.object_access[("report", "authenticated")]
    findings = object_findings(s)
    assert "report | view: no permission record for authenticated" in messages(findings, pf.FAIL)
    assert pf.PASS not in levels(findings)


@pytest.mark.parametrize(
    ("item", "callers", "level", "message"),
    [
        (routine("grant_admin", security_definer=True, public_execute=True), (), pf.FAIL, "executable by PUBLIC"),
        (
            routine("archive", security_definer=True, kind="p"),
            ("authenticated",),
            pf.FAIL,
            "SECURITY DEFINER procedure executable by authenticated",
        ),
        (routine("internal", security_definer=True), (), pf.WARN, "not executable by PUBLIC or the browser roles"),
        (routine("slugify", public_execute=True), ("anon",), pf.WARN, "with the caller's privileges"),
        (
            routine("ext_definer", security_definer=True, public_execute=True, extension_member=True),
            (),
            pf.WARN,
            "it belongs to an extension",
        ),
    ],
)
def test_routines_executable_by_browser_roles(item, callers, level, message):
    findings = object_findings(add_routine(fresh_snapshot(), item, callers))
    assert levels(findings) == {level}, messages(findings)
    assert message in messages(findings, level)


def test_routines_nobody_else_can_execute_pass():
    s = add_routine(fresh_snapshot(), routine("helper"))
    add_routine(s, routine("uuid_generate_v4", public_execute=True, extension_member=True), pf.BROWSER_ROLES)
    assert levels(object_findings(s)) == {pf.PASS}


def test_a_missing_routine_execute_record_fails_closed():
    s = add_routine(fresh_snapshot(), routine("helper"))
    del s.routine_access[("public.helper()", "service_role")]
    assert "function: no EXECUTE record for service_role" in messages(object_findings(s), pf.FAIL)


def test_other_object_checks_need_the_role_and_privilege_reads():
    s = add_relation(fresh_snapshot(), "report", pf.Relation("v", ROLE, False, False), {"SELECT"})
    s.limited["privileges"] = "database error InsufficientPrivilege (SQLSTATE 42501: permission denied)"
    assert levels(object_findings(s)) == {pf.LIMITED}


QUEUE_SEQUENCE = "procrastinate_jobs_id_seq"


def add_queue_sequence(s, privileges=()):
    return add_relation(
        s, QUEUE_SEQUENCE, pf.Relation("S", ROLE, False, False, owned_by="procrastinate_jobs"), privileges
    )


@pytest.mark.parametrize(("secured", "level"), [(True, pf.FAIL), (False, pf.WARN)])
def test_queue_sequence_access(secured, level):
    s = add_queue_sequence(add_queue(fresh_snapshot(), secured=secured), {"USAGE"})
    findings = pf.evaluate_queue(s, EXPECT)
    assert f"{QUEUE_SEQUENCE} | sequence accessible to anon: USAGE" in messages(findings, level)
    assert "queue sequences" not in messages(findings, pf.PASS)
    assert QUEUE_SEQUENCE not in messages(object_findings(s))


@pytest.mark.parametrize("name", ["users", pf.VERSION_TABLE, "procrastinate_jobs"])
def test_a_view_reusing_a_protected_table_name_is_still_graded(name):
    s = add_relation(fresh_snapshot(), name, pf.Relation("v", ROLE, False, False), {"SELECT"})
    failures = messages(object_findings(s), pf.FAIL)
    assert f"{name} | view accessible to anon: SELECT" in failures
    assert "view runs with postgres's privileges" in failures


@pytest.mark.parametrize("name", ["users", pf.VERSION_TABLE, "procrastinate_jobs", QUEUE_SEQUENCE])
@pytest.mark.parametrize("kind", ["v", "m", "f"])
def test_other_kinds_reusing_a_protected_name_are_unexpected(name, kind):
    s = fresh_snapshot()
    s.relations[name] = pf.Relation(kind, ROLE, False, False)
    assert f"{name} ({pf.KIND_NAMES[kind]})" in messages(pf.evaluate_unexpected(s), pf.WARN)


def test_the_project_tables_and_queue_sequences_are_expected():
    s = add_queue_sequence(add_queue(add_core_tables(fresh_snapshot())))
    assert levels(pf.evaluate_unexpected(s)) == {pf.PASS}
    assert levels(object_findings(s)) == {pf.PASS}


def test_a_secured_queue_sequence_passes():
    s = add_queue_sequence(add_queue(fresh_snapshot()))
    findings = pf.evaluate_queue(s, EXPECT)
    assert "1 queue sequences: no privileges for PUBLIC or the browser roles" in messages(findings, pf.PASS)
    assert not levels(findings) & pf.BLOCKING, messages(findings)


def test_a_queue_sequence_without_a_permission_record_fails_closed():
    s = add_queue_sequence(add_queue(fresh_snapshot()))
    del s.object_access[(QUEUE_SEQUENCE, "anon")]
    assert f"{QUEUE_SEQUENCE} | no permission record for anon" in messages(pf.evaluate_queue(s, EXPECT), pf.FAIL)


def test_queue_routines_executable_by_browser_roles_fail_once_secured():
    s = add_queue(fresh_snapshot())
    s.routine_access[(FETCH_JOB, "authenticated")] = True
    assert "queue functions executable by authenticated" in messages(pf.evaluate_queue(s, EXPECT), pf.FAIL)


@pytest.mark.parametrize(("callable_by_anon", "level"), [(True, pf.FAIL), (False, pf.WARN)])
def test_a_security_definer_queue_function(callable_by_anon, level):
    s = add_queue(fresh_snapshot())
    s.routines[0] = dataclasses.replace(s.routines[0], security_definer=True)
    s.routine_access[(FETCH_JOB, "anon")] = callable_by_anon
    findings = pf.evaluate_queue(s, EXPECT)
    assert f"{FETCH_JOB} | SECURITY DEFINER" in messages(findings, level)


# --- role inspection failures ----------------------------------------------------------------


def role_dependent_findings(s, expect=EXPECT):
    return [*pf.evaluate_roles(s, expect), *pf.evaluate_rls(s, expect), *pf.evaluate_queue(s, expect)]


def test_a_failed_role_query_blocks_rls_and_queue_checks(capsys):
    s = add_queue(add_core_tables(fresh_snapshot()))
    s.limited["roles"] = "database error InsufficientPrivilege (SQLSTATE 42501: permission denied)"
    findings = role_dependent_findings(s)
    assert levels(findings) == {pf.LIMITED}, messages(findings)
    assert pf.print_report(pf.evaluate(s, EXPECT)) == 1


@pytest.mark.parametrize("missing", ["anon", "authenticated", "service_role", ROLE])
def test_roles_missing_from_the_role_query_block_rls_and_queue_checks(missing, capsys):
    s = add_queue(add_core_tables(fresh_snapshot()))
    del s.roles[missing]
    findings = role_dependent_findings(s)
    assert levels(findings) == {pf.LIMITED}, messages(findings)
    assert f"role query returned nothing for {missing}" in messages(findings, pf.LIMITED)
    assert pf.print_report(pf.evaluate(s, EXPECT)) == 1


def test_a_browser_role_that_does_not_exist_is_not_a_gap():
    expect = dataclasses.replace(EXPECT, present_roles=("authenticated", "service_role"))
    s = add_queue(add_core_tables(fresh_snapshot()))
    del s.roles["anon"]
    s.api_roles = ("authenticated", "service_role")
    findings = role_dependent_findings(s, expect)
    assert not levels(findings) & pf.BLOCKING, messages(findings)
    assert "anon | does not exist" in messages(findings, pf.INFO)


def test_a_missing_queue_execute_record_fails_closed():
    s = add_queue(fresh_snapshot())
    del s.routine_access[(FETCH_JOB, "anon")]
    findings = pf.evaluate_queue(s, EXPECT)
    assert "no EXECUTE record on queue functions for anon" in messages(findings, pf.FAIL)
    assert "not executable by PUBLIC" not in messages(findings, pf.PASS)


# --- roles the Data API can switch to -------------------------------------------------------

AUTH = pf.AUTHENTICATOR


@pytest.mark.parametrize(
    ("memberships", "expected"),
    [
        (STOCK_MEMBERSHIPS, pf.BROWSER_ROLES),
        ([(AUTH, "web_api", True), ("web_api", "reporting", True)], ("reporting", "web_api")),
        ([(AUTH, "web_api", True), ("web_api", "reporting", False)], ("web_api",)),
        ([(AUTH, "web_api", False), ("web_api", "reporting", True)], ()),
        ([(AUTH, "anon", True), ("etl", "reporting", True), ("reporting", "warehouse", True)], ("anon",)),
        ([(ROLE, AUTH, True)], ()),
        ([(AUTH, "a", True), ("a", AUTH, True), ("a", "b", True)], ("a", "b")),
        ([], ()),
    ],
    ids=["direct", "nested", "nested-without-set", "direct-without-set", "unrelated", "reverse", "cycle", "none"],
)
def test_assumable_roles_follow_set_memberships(memberships, expected):
    assert pf.assumable_roles(memberships, AUTH) == expected


def test_inspection_covers_roles_reachable_only_through_nesting():
    memberships = [*STOCK_MEMBERSHIPS, (AUTH, "web_api", True), ("web_api", "reporting", True), ("etl", "warehouse", True)]
    answers = [
        (query, membership_rows(memberships) if query is pf.Q_ROLE_MEMBERSHIPS else rows)
        for query, rows in fresh_supabase_answers()
    ]
    connection = FakeConnection(answers)
    s = pf.inspect_database(connection, pf.Roles(ROLE, ROLE, ROLE))

    assert s.api_roles == ("anon", "authenticated", "reporting", "service_role", "web_api")
    assert connection.executed.index(pf.Q_ROLE_MEMBERSHIPS) < connection.executed.index(pf.Q_ROLES)
    for query in (pf.Q_TABLE_ACCESS, pf.Q_COLUMN_ACCESS, pf.Q_OBJECT_ACCESS, pf.Q_ROUTINE_ACCESS):
        (params,) = [params for statement, params in connection.params if statement is query]
        assert {"reporting", "web_api"} <= set(params["roles"])
        assert not {"etl", "warehouse"} & set(params["roles"])


PLAIN_ROLE = pf.RoleInfo(False, False, False)


def add_api_role(s: pf.Snapshot, role: str, info=PLAIN_ROLE) -> pf.Snapshot:
    """A role authenticator can switch to, with no privileges on anything yet."""
    s.roles[role] = info
    s.api_roles = (*s.api_roles, role)
    for name in s.relations:
        for access in (s.access, s.column_access, s.object_access, s.object_column_access):
            access.setdefault((name, role), frozenset())
    for item in s.routines:
        s.routine_access.setdefault((item.signature, role), False)
    return s


def test_stock_supabase_roles_pass():
    findings = pf.evaluate_data_api_roles(fresh_snapshot(), EXPECT)
    assert "can switch to no role besides anon, authenticated, service_role" in messages(findings, pf.PASS)
    assert not levels(findings) & pf.BLOCKING


def test_a_reachable_custom_role_is_checked_like_the_browser_roles():
    s = add_api_role(add_queue(add_core_tables(fresh_snapshot())), "reporting")
    assert not levels(all_findings(s)) & pf.BLOCKING, messages(all_findings(s))
    assert "reporting: checked like the browser roles" in messages(pf.evaluate_data_api_roles(s, EXPECT), pf.INFO)

    s.access[("users", "reporting")] = frozenset({"SELECT"})
    s.column_access[("procrastinate_jobs", "reporting")] = frozenset({"SELECT"})
    s.routine_access[(FETCH_JOB, "reporting")] = True
    assert "users | accessible to reporting: SELECT" in messages(pf.evaluate_rls(s, EXPECT), pf.FAIL)
    queue = messages(pf.evaluate_queue(s, EXPECT), pf.FAIL)
    assert "procrastinate_jobs | accessible to reporting: SELECT on some columns" in queue
    assert "queue functions executable by reporting" in queue


def test_other_objects_reachable_through_a_nested_role_fail():
    s = add_relation(fresh_snapshot(), "sales_report", pf.Relation("v", ROLE, False, False))
    add_api_role(s, "reporting")
    s.object_access[("sales_report", "reporting")] = frozenset({"SELECT"})
    add_routine(s, routine("grant_admin", security_definer=True))
    s.routine_access[("public.grant_admin()", "reporting")] = True
    failures = messages(pf.evaluate_object_access(s, EXPECT), pf.FAIL)
    assert "sales_report | view accessible to reporting: SELECT" in failures
    assert "SECURITY DEFINER function executable by reporting" in failures


def test_a_reachable_role_without_a_permission_record_fails_closed():
    s = add_api_role(add_core_tables(fresh_snapshot()), "reporting")
    del s.access[("users", "reporting")]
    assert "users | no permission record for reporting" in messages(pf.evaluate_rls(s, EXPECT), pf.FAIL)


def test_unrelated_custom_roles_are_not_treated_as_browser_roles():
    s = add_relation(add_core_tables(fresh_snapshot()), "sales_report", pf.Relation("v", ROLE, False, False))
    s.roles["etl"] = pf.RoleInfo(False, True, True)
    s.access[("users", "etl")] = frozenset(pf.TABLE_PRIVILEGES)
    s.object_access[("sales_report", "etl")] = frozenset({"SELECT"})
    s.default_grants = [pf.DefaultGrant(ROLE, "public", "r", "etl", "SELECT")]
    findings = all_findings(s)
    assert "etl" not in messages(findings)
    assert not levels(findings) & pf.BLOCKING, messages(findings)


def test_default_privileges_for_a_reachable_role_are_reported():
    s = add_api_role(fresh_snapshot(), "reporting")
    s.default_grants = [pf.DefaultGrant(ROLE, "", "r", "reporting", "SELECT")]
    assert "granted to reporting: SELECT" in messages(pf.evaluate_default_privileges(s, EXPECT), pf.WARN)


@pytest.mark.parametrize(
    ("role", "info", "level", "message"),
    [
        (ROLE, pf.RoleInfo(False, True, True), pf.FAIL, "the role used for migrations and the Core API and the worker"),
        ("ops_admin", pf.RoleInfo(True, True, True), pf.FAIL, "superuser reachable through the Data API"),
        ("reporting", pf.RoleInfo(False, True, False), pf.WARN, "BYPASSRLS"),
    ],
)
def test_dangerous_reachable_roles(role, info, level, message):
    s = fresh_snapshot()
    if role == ROLE:
        s.api_roles = (*s.api_roles, ROLE)
    else:
        add_api_role(s, role, info)
    findings = pf.evaluate_data_api_roles(s, EXPECT)
    assert f"{role} | " in messages(findings, level)
    assert message in messages(findings, level)
    assert pf.PASS not in levels(findings)


def test_a_superuser_authenticator_fails():
    s = fresh_snapshot()
    s.authenticator = pf.RoleInfo(True, True, True)
    findings = pf.evaluate_data_api_roles(s, EXPECT)
    assert "authenticator | is a superuser" in messages(findings, pf.FAIL)


def test_a_missing_authenticator_is_limited_on_supabase(fake_supabase, capsys):
    s = fresh_snapshot()
    s.authenticator, s.api_roles = None, ()
    findings = pf.evaluate_data_api_roles(s, EXPECT)
    assert levels(findings) == {pf.LIMITED}
    assert "only anon, authenticated, service_role were checked" in messages(findings)

    answers = [
        (query, [] if query is pf.Q_AUTHENTICATOR else rows) for query, rows in fresh_supabase_answers()
    ]
    engine = fake_supabase(answers)
    assert pf.main(["--yes"]) == 1
    out = capsys.readouterr().out
    assert "LIMITED | authenticator | does not exist" in out
    assert not any(statement is pf.Q_ROLE_MEMBERSHIPS for statement in engine.connection.executed)


def test_a_missing_authenticator_outside_supabase_is_only_noted():
    expect = dataclasses.replace(EXPECT, present_roles=())
    s = pf.Snapshot(roles={ROLE: pf.RoleInfo(False, False, True)}, schema_access={ROLE: (True, True)})
    findings = pf.evaluate_data_api_roles(s, expect)
    assert levels(findings) == {pf.INFO}
    assert "not a Supabase database" in messages(findings)


def test_a_failed_membership_query_blocks_every_access_check(fake_supabase, capsys):
    s = add_queue(add_core_tables(fresh_snapshot()))
    s.limited["data api roles"] = "database error InsufficientPrivilege (SQLSTATE 42501: permission denied)"
    for evaluate in (
        pf.evaluate_data_api_roles,
        pf.evaluate_rls,
        pf.evaluate_queue,
        pf.evaluate_object_access,
        pf.evaluate_default_privileges,
    ):
        assert levels(evaluate(s, EXPECT)) == {pf.LIMITED}, evaluate.__name__

    engine = fake_supabase(failures=[(pf.Q_ROLE_MEMBERSHIPS, database_error("42501"))])
    assert pf.main(["--yes"]) == 1
    captured = capsys.readouterr()
    assert "LIMITED | authenticator | its role memberships could not be read" in captured.out
    assert "LIMITED | data api roles | database error FakeServerError (SQLSTATE 42501" in captured.out
    assert any(statement is pf.Q_OBJECT_ACCESS for statement in engine.connection.executed)
    assert_no_secrets(captured.out + captured.err)


def test_tables_owned_by_another_role_fail():
    s = add_core_tables(fresh_snapshot(), owner="supabase_admin")
    assert "can't ALTER it" in messages(pf.evaluate_app_tables(s, EXPECT), pf.FAIL)


def test_an_app_role_that_is_not_the_owner_needs_grants_and_bypassrls():
    expect = pf.Expectations(pf.Roles(ROLE, "selvia_app", ROLE), EXPECT.revisions, EXPECT.queue)
    s = fresh_snapshot()
    s.roles["selvia_app"] = pf.RoleInfo(False, False, True)
    s.schema_access["selvia_app"] = (True, False)
    assert "would see no rows" in messages(pf.evaluate_roles(s, expect), pf.WARN)

    s = add_core_tables(s)
    s.access[("users", "selvia_app")] = frozenset({"SELECT"})
    failures = messages(pf.evaluate_roles(s, expect), pf.FAIL)
    assert "users: missing INSERT, UPDATE, DELETE" in failures
    assert "RLS without policies hides every row" in failures


def test_a_partial_queue_install_fails():
    s = add_queue(fresh_snapshot(), tables=pf.QUEUE_TABLES[:2])
    assert "missing tables" in messages(pf.evaluate_queue(s, EXPECT), pf.FAIL)


def test_an_unsecured_queue_warns():
    findings = pf.evaluate_queue(add_queue(fresh_snapshot(), secured=False), EXPECT)
    assert pf.FAIL not in levels(findings)
    warnings = messages(findings, pf.WARN)
    assert "RLS off" in warnings
    assert "executable by PUBLIC, anon, authenticated, service_role" in warnings


def test_a_worker_that_cannot_run_the_queue_fails():
    s = add_queue(fresh_snapshot())
    s.routine_access[(FETCH_JOB, ROLE)] = False
    assert "can't execute" in messages(pf.evaluate_roles(s, EXPECT), pf.FAIL)


def test_default_privileges_are_explained():
    s = fresh_snapshot()
    s.default_grants = [
        pf.DefaultGrant(ROLE, "public", "r", "anon", "SELECT"),
        pf.DefaultGrant(ROLE, "", "r", "anon", "SELECT"),
        pf.DefaultGrant("supabase_admin", "public", "r", "anon", "SELECT"),
    ]
    findings = pf.evaluate_default_privileges(s, EXPECT)
    assert "in schema public are granted to anon: SELECT; the security migration removes this" in messages(
        findings, pf.INFO
    )
    assert "in every schema" in messages(findings, pf.WARN)
    assert "only affects objects supabase_admin creates" in messages(findings, pf.INFO)


def test_unexpected_objects_warn_and_extension_objects_are_ignored():
    s = fresh_snapshot()
    s.relations["legacy_users"] = pf.Relation("r", ROLE, False, False)
    s.relations["pg_stat_statements"] = pf.Relation("v", ROLE, False, False, extension_member=True)
    findings = pf.evaluate_unexpected(s)
    assert "legacy_users (table)" in messages(findings, pf.WARN)
    assert "pg_stat_statements" not in messages(findings, pf.WARN)


def test_failed_sections_are_limited_and_block(capsys):
    s = fresh_snapshot()
    s.limited["privileges"] = "database error InsufficientPrivilege (SQLSTATE 42501: permission denied)"
    sections = pf.evaluate(s, EXPECT)
    assert pf.LIMITED in levels(finding for _, findings in sections for finding in findings)
    assert pf.print_report(sections) == 1
    assert "NOT READY" in capsys.readouterr().out


def test_an_unreadable_version_table_is_limited():
    s = fresh_snapshot()
    s.version_schemas, s.version_rows = ["public"], None
    assert pf.LIMITED in levels(pf.evaluate_alembic(s, EXPECT))


CREDENTIALS_IN_URL = re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@", re.IGNORECASE)


def credential_leaks(output: str, url) -> list[str]:
    """How `output` discloses the URL's credentials; the descriptions never contain the secret.

    The password counts as disclosed in a connection string, as `user:password@`, after
    `password=` / `password:`, or as a standalone token. A password that only occurs inside a
    longer identifier, such as a database or role name, is not a disclosure.
    """
    leaks = []
    for drivername in {url.drivername, "postgresql"}:
        if url.set(drivername=drivername).render_as_string(hide_password=False) in output:
            leaks.append(f"{drivername} connection URL")
    if CREDENTIALS_IN_URL.search(output):
        leaks.append("a URL with embedded credentials")
    password = url.password or ""
    if not password:
        return leaks
    identifiers = {url.username, url.database, url.host}
    for form, secret in (("password", password), ("URL-encoded password", quote(password, safe=""))):
        lowered = output.lower()
        if f":{secret}@" in output:
            leaks.append(f"user:{form}@")
        if f"password={secret}".lower() in lowered or f"password: {secret}".lower() in lowered:
            leaks.append(f"password field with the {form}")
        standalone = re.compile(rf"(?<![\w-]){re.escape(secret)}(?![\w-])")
        if secret not in identifiers and standalone.search(output):
            leaks.append(f"standalone {form}")
    return list(dict.fromkeys(leaks))


def test_credential_leaks_ignores_the_password_inside_identifiers():
    url = make_url("postgresql+psycopg://selvia_migrator:selvia@localhost:5432/selvia_migration_test")
    metadata = (
        "Target: postgresql localhost:5432/selvia_migration_test\n"
        "  role:             selvia_migrator (session role selvia_migrator)\n"
        "INFO    | selvia_migrator | connection (runs the migrations) role\n"
    )
    assert credential_leaks(metadata, url) == []


@pytest.mark.parametrize(
    ("output", "leak"),
    [
        ("postgresql+psycopg://selvia_migrator:selvia@localhost:5432/selvia_migration_test", "connection URL"),
        ("postgresql://selvia_migrator:selvia@localhost:5432/selvia_migration_test", "connection URL"),
        ("dsn postgresql://someone:other@db.example.invalid/x", "embedded credentials"),
        ("auth selvia_migrator:selvia@localhost", "user:password@"),
        ("connect password=selvia host=localhost", "password field"),
        ("Password: selvia", "password field"),
        ("the password is selvia.", "standalone password"),
        ("p@ss in a URL: p%40ss", "standalone URL-encoded password"),
    ],
)
def test_credential_leaks_detects_disclosures(output, leak):
    password = "p@ss" if "p%40ss" in output else "selvia"
    url = make_url(
        f"postgresql+psycopg://selvia_migrator:{quote(password, safe='')}@localhost:5432/selvia_migration_test"
    )
    found = credential_leaks(output, url)
    assert any(leak in item for item in found), found
    assert all(password not in item for item in found)


# --- optional: the local disposable PostgreSQL database -------------------------------------


def statement_recorder(monkeypatch):
    statements = []

    def recording_create_engine(url, **kwargs):
        engine = real_create_engine(url, **kwargs)

        @event.listens_for(engine, "before_cursor_execute")
        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(" ".join(statement.split()))

        return engine

    monkeypatch.setattr(pf, "create_engine", recording_create_engine)
    return statements


def test_preflight_on_the_local_test_database_only_reads(test_database_url, monkeypatch, capsys):
    statements = statement_recorder(monkeypatch)
    raw_url = test_database_url.render_as_string(hide_password=False)
    monkeypatch.setenv(pf.URL_ENV, raw_url)
    clear_libpq_overrides(monkeypatch)

    code = pf.main(["--local-test", "--yes"])
    captured = capsys.readouterr()
    assert code in (0, 1), captured.err
    assert "ERROR" not in captured.err
    assert "READ ONLY confirmed" in captured.out
    assert "== Alembic history ==" in captured.out
    assert raw_url not in captured.out + captured.err
    assert credential_leaks(captured.out + captured.err, test_database_url) == []

    assert statements
    for statement in statements:
        head = statement.split()[0].upper()
        assert head in {"SELECT", "SHOW", "SET", "SAVEPOINT", "RELEASE", "ROLLBACK"}, statement
        if head == "SET":
            assert statement in ALLOWED_SET_STATEMENTS, statement


def test_preflight_reports_a_migrated_local_database(test_database_url):
    engine = real_create_engine(test_database_url, poolclass=NullPool)
    with engine.connect() as connection:
        existing = set(inspect(connection).get_table_names())
        current = MigrationContext.configure(connection).get_current_revision()
        if existing & set(pf.APP_TABLES) or current is not None:
            pytest.fail("SERVER_TEST_DATABASE_URL must point to an empty, unmigrated database")
        connection.rollback()

        transaction = connection.begin()
        try:
            config = Config(str(SERVER_DIR / "alembic.ini"), cmd_opts=argparse.Namespace(x=[]))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            role = connection.execute(text("SELECT CAST(current_user AS text)")).scalar_one()
            roles = pf.Roles(role, role, role)
            snapshot = pf.inspect_database(connection, roles)
            # Rolled back with the tables below.
            connection.execute(text("GRANT SELECT (name) ON TABLE public.users TO PUBLIC"))
            granted = pf.inspect_database(connection, roles)
        finally:
            transaction.rollback()
        assert set(inspect(connection).get_table_names()).isdisjoint(pf.APP_TABLES)
    engine.dispose()

    expect = pf.Expectations(roles, pf.load_revisions(), pf.load_queue_spec())
    findings = all_findings(snapshot, expect)
    assert snapshot.limited == {}
    assert not levels(findings) & pf.BLOCKING, messages(findings)
    passed = messages(findings, pf.PASS)
    assert f"at head {SECURITY_REVISION}" in passed
    assert passed.count("columns, constraints and indexes match the models") == 6
    for table in [*pf.APP_TABLES, pf.VERSION_TABLE]:
        assert f"{table} | RLS on, not forced" in passed
        assert f"{table} | no privileges for PUBLIC or the Supabase browser roles" in passed

    assert granted.column_grants["users"] == {"PUBLIC": {("name", "SELECT")}}
    rls = pf.evaluate_rls(granted, expect)
    assert "users | PUBLIC (every role) has SELECT on columns name" in messages(rls, pf.FAIL)
    assert "users | no privileges" not in messages(rls, pf.PASS)
