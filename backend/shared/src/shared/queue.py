import asyncio
import os
import sys

import procrastinate
import psycopg
from dotenv import load_dotenv
from procrastinate.schema import SchemaManager
from psycopg.conninfo import conninfo_to_dict

# psycopg async on Windows requires WindowsSelectorEventLoopPolicy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# The service's own .env: run commands from backend/server or backend/agentic_framework.
load_dotenv(dotenv_path=".env", override=False)

# In order of precedence; a blank value counts as unset.
QUEUE_URL_VARIABLES = ("SERVER_DIRECT_URL", "SERVER_DATABASE_URL")
SUPABASE_HOST_SUFFIXES = (".supabase.com", ".supabase.co")
VERIFIED_SSLMODE = "verify-full"
SCHEMA_INSTALL_COMMAND = "uv run python -m scripts.install_queue_schema"


class QueueConfigurationError(RuntimeError):
    """The job queue has no database URL configured, or its TLS settings are unsafe."""


class QueueSchemaInstallRefused(RuntimeError):
    """The queue schema is installed only through the guarded Core API script."""


def get_dsn() -> str:
    """Return a psycopg-compatible DSN (strips SQLAlchemy dialect prefix), or "" if unset.
    
    Prefers SERVER_DIRECT_URL (port 5432) which supports direct session connections.
    """
    for name in QUEUE_URL_VARIABLES:
        url = (os.getenv(name) or "").strip()
        if url:
            return url.replace("postgresql+psycopg://", "postgresql://")
    return ""


def check_tls(conninfo: str) -> None:
    """A Supabase queue URL must set sslmode=verify-full and sslrootcert; other hosts are left as set.

    Messages never contain the connection string, the host or the certificate path.
    """
    try:
        params = conninfo_to_dict(conninfo)
    except psycopg.Error:
        raise QueueConfigurationError(
            f"The job queue database URL ({' or '.join(QUEUE_URL_VARIABLES)}) is not a valid "
            "connection string"
        ) from None
    hosts = [host.strip() for host in str(params.get("host") or "").split(",") if host.strip()]
    if not any(host.rstrip(".").lower().endswith(SUPABASE_HOST_SUFFIXES) for host in hosts):
        return
    if params.get("sslmode") != VERIFIED_SSLMODE or not params.get("sslrootcert"):
        raise QueueConfigurationError(
            f"The Supabase job queue URL must set sslmode={VERIFIED_SSLMODE} and sslrootcert "
            "(the path to the Supabase CA certificate) so the server's certificate and host name "
            "are verified; see docs/SERVER_DATABASE_GUIDE.md, section 2"
        )


class QueueConnector(procrastinate.PsycopgConnector):
    """PsycopgConnector that refuses to open without a queue URL, or with unsafe Supabase TLS.

    An empty conninfo is valid for libpq: it would silently connect to whatever
    PGHOST/PGDATABASE or the local default server points at.
    """

    def __init__(self, *, conninfo: str, **kwargs):
        super().__init__(conninfo=conninfo, **kwargs)
        self.conninfo = conninfo

    def require_conninfo(self) -> None:
        if not self.conninfo.strip():
            raise QueueConfigurationError(
                "Job queue database URL is not configured: set "
                f"{' or '.join(QUEUE_URL_VARIABLES)} in the service's .env "
                "(backend/server/.env or backend/agentic_framework/.env) "
                "and run the command from that service's folder."
            )
        check_tls(self.conninfo)

    async def open_async(self, pool=None) -> None:
        if pool is None:
            self.require_conninfo()
        await super().open_async(pool)

    def get_sync_connector(self) -> procrastinate.BaseConnector:
        self.require_conninfo()
        return super().get_sync_connector()


class GuardedSchemaManager(SchemaManager):
    """Reads the schema as usual but refuses to apply it.

    `procrastinate --app=shared.queue.app schema --apply` reaches apply_schema_async() with
    whatever .env the current folder holds and no local/remote check, so it is disabled.
    """

    def _refuse(self) -> None:
        raise QueueSchemaInstallRefused(
            "Installing the job queue schema through shared.queue.app (procrastinate schema "
            "--apply) is disabled because it has no target checks. From backend/server, run "
            f"`{SCHEMA_INSTALL_COMMAND}`, which checks the target before connecting. "
            "No schema was changed."
        )

    def apply_schema(self) -> None:
        self._refuse()

    async def apply_schema_async(self) -> None:
        self._refuse()


class QueueApp(procrastinate.App):
    @property
    def schema_manager(self) -> SchemaManager:
        return GuardedSchemaManager(connector=self.connector)


# Global Procrastinate App instance initialized with the Supabase connection info
app = QueueApp(
    connector=QueueConnector(conninfo=get_dsn())
)
