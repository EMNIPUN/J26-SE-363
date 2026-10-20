import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, Optional
from sqlalchemy import create_engine, event, exc, text, Engine
from sqlalchemy.orm import sessionmaker, Session
try:
    from ..core.config import settings
    from .safety import UnsafeDatabaseTarget, check_tls, parse_url
except (ImportError, ValueError):
    from app.core.config import settings
    from app.database.safety import UnsafeDatabaseTarget, check_tls, parse_url

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


class DatabaseConfigurationError(ValueError):
    """The Core API's database URL is missing, invalid or has unsafe TLS settings."""


def get_engine() -> Engine:
    """Create or return the cached SQLAlchemy Engine.
    
    Dynamically loads the connection URL strictly from environment settings.
    No hardcoded credentials or hosts are permitted.

    TLS settings come only from the URL (`sslmode`, `sslrootcert`), which SQLAlchemy hands to
    psycopg unchanged; a Supabase URL must use sslmode=verify-full with a usable sslrootcert.
    """
    global _engine
    if _engine is not None:
        return _engine

    database_url = (settings.SERVER_DATABASE_URL or "").strip()
    if not database_url:
        raise DatabaseConfigurationError(
            "Database connection failed: Neither SERVER_DATABASE_URL nor individual "
            "SERVER_POSTGRES_USER / SERVER_POSTGRES_PASSWORD / SERVER_POSTGRES_DB "
            "environment variables are configured. Please check backend/server/.env."
        )

    try:
        check_tls(parse_url(database_url, "SERVER_DATABASE_URL"))
    except UnsafeDatabaseTarget as error:
        raise DatabaseConfigurationError(f"Database connection refused: {error}") from None

    pool_size = int(os.getenv("SERVER_DB_POOL_SIZE", "10"))
    max_overflow = int(os.getenv("SERVER_DB_MAX_OVERFLOW", "20"))
    # A new connection to a far-away database takes seconds (TLS and the pooler's login), so connections are kept long and not recycled every few minutes.
    pool_recycle = int(os.getenv("SERVER_DB_POOL_RECYCLE", "1800"))
    ping_after = float(os.getenv("SERVER_DB_PING_AFTER", "20"))

    _engine = create_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,  # Recycles very old connections (Supavisor)
    )
    try:
        _ping_idle_connections(_engine, ping_after)
    except exc.InvalidRequestError:  # an engine that is not a real one (a test double) has no pool events
        logger.debug("Idle-connection check not installed")
    return _engine


def _ping_idle_connections(engine: Engine, ping_after: float) -> None:
    """Check a connection is alive only when it has sat unused for a while.

    `pool_pre_ping` tests every checkout, which costs one full round trip to the database on every request (about half a second to a far-away Supabase).
    A connection that was used a moment ago is alive; one that has been idle may have been closed by the pooler, so only that one is tested.
    """
    @event.listens_for(engine, "checkin")
    def _used(dbapi_connection, record):
        record.info["idle_since"] = time.monotonic()

    @event.listens_for(engine, "checkout")
    def _before_use(dbapi_connection, record, proxy):
        idle_since = record.info.get("idle_since")
        if idle_since is None or time.monotonic() - idle_since < ping_after:
            return
        try:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("SELECT 1")
            finally:
                cursor.close()
        except Exception as error:  # the pool then drops it and opens a fresh one
            raise exc.DisconnectionError() from error


def warm_pool(connections: int = 3) -> int:
    """Open a few connections now, in parallel, so the first requests do not wait for the slow connect. Returns how many opened."""
    engine = get_engine()

    def open_one(_: int) -> bool:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as error:
            logger.warning("Could not warm a database connection: %s", error)
            return False

    with ThreadPoolExecutor(max_workers=connections) as pool:
        return sum(pool.map(open_one, range(connections)))


def get_session_factory() -> sessionmaker:
    """Create or return the sessionmaker bound to the engine."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a managed database session."""
    factory = get_session_factory()
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verify that the database engine can successfully connect and execute queries."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except DatabaseConfigurationError as exc:
        logger.error(f"Database health check failed: {exc}")
        return False
    except Exception as exc:
        # Driver messages can contain the host and the user name (on Supabase, the project reference).
        sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
        logger.error(
            "Database health check failed: %s (SQLSTATE %s; details hidden)",
            type(exc).__name__,
            sqlstate or "unknown",
        )
        return False
