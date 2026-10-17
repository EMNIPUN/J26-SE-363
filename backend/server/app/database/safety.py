"""Checks that keep migrations and database tests away from shared databases.

Only the hosts in LOCAL_HOSTS count as local; every other host (Supabase included) is
remote. Error messages and descriptions never contain a user name or password.
"""

from collections.abc import Iterable, Mapping
from pathlib import Path

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
TRUE_VALUES = frozenset({"1", "true", "yes"})
# Tests may create and drop tables in SERVER_TEST_DATABASE_URL, so its name must say it's disposable.
DISPOSABLE_DATABASE_SUFFIX = "_test"
TEST_DATABASE_ENV = "SERVER_TEST_DATABASE_URL"
DEFAULT_POSTGRES_PORT = 5432
# The Core API's own URL; on Supabase it is the transaction pooler.
APP_URL_SETTING = "SERVER_DATABASE_URL"
TRANSACTION_POOLER_PORT = 6543
SUPABASE_HOST_SUFFIXES = (".supabase.com", ".supabase.co")
VERIFIED_SSLMODE = "verify-full"
# libpq's keyword for the operating system's trust store (libpq 16+).
SYSTEM_ROOT_CERTS = "system"
PEM_CERTIFICATE = b"-----BEGIN CERTIFICATE-----"
MAX_ROOT_CERT_BYTES = 1024 * 1024


class UnsafeDatabaseTarget(RuntimeError):
    """A database target failed a safety check. Raised before any connection is opened."""


def is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


def parse_url(raw: str, name: str) -> URL:
    """Parse a database URL without echoing it (SQLAlchemy's parse error contains the password)."""
    try:
        return make_url(raw)
    except (ArgumentError, ValueError):
        raise UnsafeDatabaseTarget(f"{name} is not a valid database URL") from None


def target_hosts(url: URL) -> list[str]:
    """Every host the driver may connect to: the URL host plus libpq `host`/`hostaddr` parameters."""
    hosts = [url.host] if url.host else []
    for key in ("host", "hostaddr"):
        value = url.query.get(key)
        values = value if isinstance(value, tuple) else (value,) if value else ()
        for item in values:
            hosts.extend(host.strip() for host in item.split(",") if host.strip())
    return hosts


def is_local(url: URL) -> bool:
    """True only when every possible host is verifiably this machine.

    A PostgreSQL URL without a host, or with a libpq `service`, is not verifiably local:
    the driver would take the real host from PGHOST or pg_service.conf.
    """
    if url.get_backend_name() == "sqlite":
        return True
    if "service" in url.query:
        return False
    hosts = target_hosts(url)
    return bool(hosts) and all(host.strip("[]").lower() in LOCAL_HOSTS for host in hosts)


def describe(url: URL) -> str:
    """Backend, host, port and database name; never the user name or password."""
    if url.get_backend_name() == "sqlite":
        return f"sqlite database {url.database or ':memory:'}"
    hosts = ",".join(target_hosts(url)) or "<no host>"
    port = f":{url.port}" if url.port else ""
    return f"{url.get_backend_name()} {hosts}{port}/{url.database or ''}"


def check_migration_target(
    url: URL,
    allow_remote: bool,
    *,
    downgrade: bool = False,
    allow_remote_downgrade: bool = False,
) -> None:
    """Allow online migrations on local databases; remote ones only with explicit opt-in.

    A remote downgrade can drop tables and data, so `allow_remote` alone is not enough:
    it also needs its own `allow_remote_downgrade` opt-in.
    """
    if is_local(url):
        return
    if not allow_remote:
        raise UnsafeDatabaseTarget(
            f"Refusing to run against {describe(url)}: it is not a local database. "
            "Pass -x allow_remote=true only if you really mean to change that database."
        )
    if downgrade and not allow_remote_downgrade:
        raise UnsafeDatabaseTarget(
            f"Refusing to downgrade {describe(url)}: it is not a local database and a "
            "downgrade can drop tables and data. -x allow_remote=true does not cover "
            "downgrades; also pass -x allow_remote_downgrade=true only if you really mean it."
        )


def check_schema_change_source(url: URL, source: str, explicit_option: str) -> None:
    """Refuse a remote target for schema changes that came from SERVER_DATABASE_URL or uses port 6543.

    Supabase's transaction pooler (port 6543, the usual SERVER_DATABASE_URL) can hand each
    transaction to a different server session, so migrations and queue hardening need the session
    URL: SERVER_DIRECT_URL or one passed with `explicit_option`. Local databases are not affected.
    """
    if is_local(url):
        return
    if source == APP_URL_SETTING:
        raise UnsafeDatabaseTarget(
            f"Refusing to use {APP_URL_SETTING} for a remote database: it is the Core API's own URL "
            "(on Supabase, the transaction pooler) and SERVER_DIRECT_URL is not set. Set "
            f"SERVER_DIRECT_URL to the session pooler URL (port 5432) or pass {explicit_option}."
        )
    if url.port == TRANSACTION_POOLER_PORT:
        raise UnsafeDatabaseTarget(
            f"Refusing a remote database on port {TRANSACTION_POOLER_PORT}, Supabase's transaction "
            "pooler: schema changes need a session connection. Use the session pooler URL (port 5432)."
        )


def is_supabase(url: URL) -> bool:
    """True when any host the driver may connect to is a Supabase host."""
    return any(
        host.strip("[]").rstrip(".").lower().endswith(SUPABASE_HOST_SUFFIXES)
        for host in target_hosts(url)
    )


def _single_query_value(url: URL, key: str) -> str | None:
    value = url.query.get(key)
    if isinstance(value, tuple):
        raise UnsafeDatabaseTarget(
            f"the Supabase database URL sets {key} more than once; set sslmode={VERIFIED_SSLMODE} "
            "and sslrootcert once each"
        )
    return value


def check_root_cert(root_cert: str | None) -> None:
    """`system`, or a readable file holding a PEM certificate. The path is never printed."""
    if not root_cert:
        raise UnsafeDatabaseTarget(
            "the Supabase database URL needs sslrootcert: the path to the Supabase CA certificate "
            "(Project Settings > Database > SSL Configuration)"
        )
    if root_cert == SYSTEM_ROOT_CERTS:
        return
    path = Path(root_cert)
    if not path.is_file():
        raise UnsafeDatabaseTarget(
            "the sslrootcert file in the Supabase database URL does not exist or is not a file "
            "(the path is not printed)"
        )
    try:
        with path.open("rb") as file:
            content = file.read(MAX_ROOT_CERT_BYTES)
    except OSError:
        raise UnsafeDatabaseTarget(
            "the sslrootcert file in the Supabase database URL can't be read (the path is not printed)"
        ) from None
    if PEM_CERTIFICATE not in content:
        raise UnsafeDatabaseTarget(
            "the sslrootcert file in the Supabase database URL holds no PEM certificate "
            "(a -----BEGIN CERTIFICATE----- line); the path is not printed"
        )


def check_tls(url: URL) -> None:
    """Supabase targets must verify the server: sslmode=verify-full and a usable sslrootcert.

    Both must be in the URL itself, so SQLAlchemy hands them to psycopg and libpq unchanged and
    PGSSLMODE/PGSSLROOTCERT never apply. Other targets keep whatever the URL says. Messages
    never contain the URL, the host or the certificate path.
    """
    if not is_supabase(url):
        return
    sslmode = _single_query_value(url, "sslmode")
    if sslmode != VERIFIED_SSLMODE:
        raise UnsafeDatabaseTarget(
            f"the Supabase database URL must set sslmode={VERIFIED_SSLMODE} (it has "
            f"{f'sslmode={sslmode}' if sslmode else 'no sslmode'}); weaker modes don't verify that "
            "the server is the real Supabase host"
        )
    check_root_cert(_single_query_value(url, "sslrootcert"))


def _database_key(url: URL) -> tuple[tuple[str, ...], int, str]:
    hosts = tuple(sorted(host.strip("[]").lower() for host in target_hosts(url)))
    return hosts, url.port or DEFAULT_POSTGRES_PORT, url.database or ""


def validate_test_database_url(raw: str, protected_urls: Iterable[str | None] = ()) -> URL:
    """Accept only a local, PostgreSQL, disposable (`*_test`) database that is not the app's database."""
    url = parse_url(raw, TEST_DATABASE_ENV)
    if url.get_backend_name() != "postgresql":
        raise UnsafeDatabaseTarget(f"{TEST_DATABASE_ENV} must be a PostgreSQL URL")
    if not is_local(url):
        raise UnsafeDatabaseTarget(
            f"{TEST_DATABASE_ENV} points at {describe(url)}; only localhost databases are allowed"
        )
    if not (url.database or "").endswith(DISPOSABLE_DATABASE_SUFFIX):
        raise UnsafeDatabaseTarget(
            f"{TEST_DATABASE_ENV} database name must end with '{DISPOSABLE_DATABASE_SUFFIX}' "
            f"(got {url.database!r}); tests create and drop tables in it"
        )
    for protected in protected_urls:
        if not protected:
            continue
        try:
            same = _database_key(make_url(protected)) == _database_key(url)
        except (ArgumentError, ValueError):
            continue
        if same:
            raise UnsafeDatabaseTarget(
                f"{TEST_DATABASE_ENV} points at the application's own database"
            )
    return url


def disposable_database_url(
    environ: Mapping[str, str], protected_urls: Iterable[str | None] = ()
) -> URL | None:
    """The validated SERVER_TEST_DATABASE_URL, or None when it isn't set.

    There is deliberately no fallback to SERVER_DIRECT_URL or SERVER_DATABASE_URL.
    """
    raw = environ.get(TEST_DATABASE_ENV)
    if not raw:
        return None
    return validate_test_database_url(raw, protected_urls)
