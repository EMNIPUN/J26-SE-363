"""Fixtures for API tests: an in-memory database, a switchable signed-in identity, captured email.

    def test_something(api):
        api.sign_in("sub-1", email="ada@example.com")        # a verified Keycloak login
        response = api.get("/me")

Keycloak is replaced by `sign_in`; everything after the token (accounts, teams, rules) is the
real code running on SQLite with foreign keys enforced.

To run the same tests on a real PostgreSQL, point SELVIA_API_TEST_DATABASE_URL at a *local*,
already migrated database (for example the Docker development database). Every table is
emptied before each test, so never use a database that holds data you want to keep: the URL
must name localhost or 127.0.0.1.
"""

import os
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from shared.contracts import UserRole
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.security import CurrentUser, get_current_user
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.services.email import EmailService, InMemoryEmailSender, get_email_service

API = "/api/v1"
POSTGRES_URL = os.environ.get("SELVIA_API_TEST_DATABASE_URL")
APP_URL = "https://selvia.test"


@dataclass
class Api:
    client: TestClient
    sessions: sessionmaker
    email: InMemoryEmailSender
    identity: CurrentUser | None = field(default=None)
    _opened: list[Session] = field(default_factory=list)

    def sign_in(
        self,
        sub: str,
        *,
        email: str | None = None,
        name: str | None = None,
        verified: bool = True,
        admin: bool = False,
    ) -> None:
        self.identity = CurrentUser(
            user_id=sub,
            username=sub,
            name=name,
            email=email,
            email_verified=verified,
            role=UserRole.ADMIN if admin else UserRole.STUDENT,
        )

    def sign_out(self) -> None:
        self.identity = None

    def db(self) -> Session:
        """A session for looking at (or arranging) data directly. Closed after the test: an open
        transaction would block the next test's TRUNCATE on PostgreSQL."""
        session = self.sessions()
        self._opened.append(session)
        return session

    def close_sessions(self) -> None:
        for session in self._opened:
            session.close()

    def request(self, method: str, path: str, **kwargs):
        return self.client.request(method, f"{API}{path}", **kwargs)

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, json=None, **kwargs):
        return self.request("POST", path, json=json, **kwargs)

    def patch(self, path: str, json=None, **kwargs):
        return self.request("PATCH", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)


def _database_engine():
    if POSTGRES_URL:
        if make_url(POSTGRES_URL).host not in ("localhost", "127.0.0.1"):
            pytest.fail(
                "SELVIA_API_TEST_DATABASE_URL must point at localhost", pytrace=False
            )
        engine = create_engine(POSTGRES_URL)
        tables = ", ".join(f'"{name}"' for name in Base.metadata.tables)
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        return engine

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def api():
    engine = _database_engine()
    sessions = sessionmaker(bind=engine, autoflush=False)
    outbox = InMemoryEmailSender()
    harness = Api(TestClient(app), sessions, outbox)

    def override_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    def override_identity():
        from fastapi import HTTPException

        if harness.identity is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return harness.identity

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_identity
    app.dependency_overrides[get_email_service] = lambda: EmailService(outbox, APP_URL)
    yield harness
    harness.close_sessions()
    app.dependency_overrides.clear()
    engine.dispose()
