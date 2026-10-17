"""Shared Neo4j driver helpers. Construction is lazy; no connection at import time."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from neo4j import Driver, GraphDatabase, Session

from app.core.config import Settings, settings
from app.knowledge_graph.errors import KnowledgeGraphConfigError, KnowledgeGraphQueryError

_driver: Driver | None = None


def neo4j_configured(cfg: Settings | None = None) -> bool:
    active = cfg or settings
    return bool(
        active.NEO4J_URI
        and active.NEO4J_USERNAME
        and active.NEO4J_PASSWORD
        and active.NEO4J_DATABASE
    )


def get_neo4j_driver(cfg: Settings | None = None) -> Driver:
    """Return a process-wide driver. Does not open a session until used."""
    global _driver
    active = cfg or settings
    if not neo4j_configured(active):
        raise KnowledgeGraphConfigError(
            "Neo4j is not configured. Set NEO4J_URI, NEO4J_USERNAME, "
            "NEO4J_PASSWORD, and NEO4J_DATABASE."
        )
    if _driver is None:
        _driver = GraphDatabase.driver(
            active.NEO4J_URI,  # type: ignore[arg-type]
            auth=(active.NEO4J_USERNAME, active.NEO4J_PASSWORD),
        )
    return _driver


def reset_neo4j_driver() -> None:
    """Close and clear the cached driver (tests / shutdown)."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


@contextmanager
def neo4j_session(cfg: Settings | None = None) -> Iterator[Session]:
    active = cfg or settings
    driver = get_neo4j_driver(active)
    session = driver.session(database=active.NEO4J_DATABASE)
    try:
        yield session
    finally:
        session.close()


def run_read_query(
    cypher: str,
    parameters: dict[str, Any] | None = None,
    *,
    cfg: Settings | None = None,
) -> list[dict[str, Any]]:
    """Execute a parameterized read query and return list[dict] rows."""
    try:
        with neo4j_session(cfg) as session:
            result = session.run(cypher, parameters or {})
            return [dict(record) for record in result]
    except KnowledgeGraphConfigError:
        raise
    except Exception as exc:  # neo4j raises driver-specific types
        raise KnowledgeGraphQueryError(
            "Neo4j query failed while reading course knowledge."
        ) from exc
