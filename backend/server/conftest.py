import asyncio
import os
import sys

import pytest
from sqlalchemy.engine import URL

from app.core.config import settings
from app.database.safety import (
    TEST_DATABASE_ENV,
    UnsafeDatabaseTarget,
    disposable_database_url,
)

# Importing shared.queue runs load_dotenv(), which copies backend/server/.env into os.environ.
# The test database must come from the shell, so its URL is captured before any test module
# can import shared.queue.
if "shared.queue" in sys.modules:
    raise RuntimeError(
        f"shared.queue was imported before conftest.py captured {TEST_DATABASE_ENV}; "
        "os.environ may already contain values from .env, so the test database can't be trusted"
    )
EXPLICIT_TEST_DATABASE_URL = os.environ.get(TEST_DATABASE_ENV, "")

# On Windows, psycopg async requires WindowsSelectorEventLoopPolicy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def test_database_url() -> URL:
    """Disposable PostgreSQL database for tests that write to a real database.

    Skips when SERVER_TEST_DATABASE_URL was unset in the shell (never falls back to the
    application's SERVER_DIRECT_URL / SERVER_DATABASE_URL, or to a value loaded from .env
    later) and fails, before connecting, when it is not a local `*_test` database.
    """
    try:
        url = disposable_database_url(
            {TEST_DATABASE_ENV: EXPLICIT_TEST_DATABASE_URL},
            protected_urls=(settings.SERVER_DIRECT_URL, settings.SERVER_DATABASE_URL),
        )
    except UnsafeDatabaseTarget as exc:
        # No traceback: pytest would print the frames' arguments, including the raw URL and password.
        pytest.fail(str(exc), pytrace=False)
    if url is None:
        pytest.skip(f"{TEST_DATABASE_ENV} is not set")
    return url
