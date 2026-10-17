"""The test_database_url fixture uses only the SERVER_TEST_DATABASE_URL the shell supplied.

shared.queue's load_dotenv() can add the variable to os.environ after conftest.py has loaded;
that value must never be used. Nothing here connects or reads a .env file.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

import conftest
from app.database.safety import TEST_DATABASE_ENV

SERVER_DIR = Path(__file__).resolve().parents[1]
PASSWORD = "not-a-real-secret"
SHELL_URL = f"postgresql+psycopg://selvia_tester:{PASSWORD}@localhost:5432/selvia_shell_test"
INJECTED_URL = f"postgresql+psycopg://selvia_tester:{PASSWORD}@localhost:5432/selvia_dotenv_test"
APP_URL = f"postgresql+psycopg://selvia_user:{PASSWORD}@localhost:5432/selvia_app_test"


@pytest.fixture
def app_urls(monkeypatch):
    """Known application URLs, so the protected-database check doesn't depend on backend/server/.env."""
    monkeypatch.setattr(conftest.settings, "SERVER_DIRECT_URL", APP_URL)
    monkeypatch.setattr(conftest.settings, "SERVER_DATABASE_URL", None)


def captured(monkeypatch, value: str) -> None:
    monkeypatch.setattr(conftest, "EXPLICIT_TEST_DATABASE_URL", value)


def test_a_url_injected_after_the_capture_is_not_used(app_urls, monkeypatch, request):
    captured(monkeypatch, SHELL_URL)
    monkeypatch.setenv(TEST_DATABASE_ENV, INJECTED_URL)

    url = request.getfixturevalue("test_database_url")

    assert url.database == "selvia_shell_test"


def test_without_a_shell_url_the_fixture_skips_despite_an_injected_one(app_urls, monkeypatch, request):
    captured(monkeypatch, "")
    monkeypatch.setenv(TEST_DATABASE_ENV, INJECTED_URL)

    with pytest.raises(pytest.skip.Exception, match=f"{TEST_DATABASE_ENV} is not set"):
        request.getfixturevalue("test_database_url")


def test_an_explicit_local_test_url_is_accepted(app_urls, monkeypatch, request):
    captured(monkeypatch, SHELL_URL)
    monkeypatch.delenv(TEST_DATABASE_ENV, raising=False)

    url = request.getfixturevalue("test_database_url")

    assert (url.get_backend_name(), url.host, url.port, url.database) == (
        "postgresql",
        "localhost",
        5432,
        "selvia_shell_test",
    )


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (f"postgresql+psycopg://u:{PASSWORD}@db.example.invalid:5432/selvia_test", "only localhost"),
        (f"postgresql+psycopg://u:{PASSWORD}@localhost:5432/selvia_server_db", "must end with '_test'"),
        ("sqlite:///selvia_test", "must be a PostgreSQL URL"),
        (f"postgresql+psycopg://u:{PASSWORD}@localhost:notaport/selvia_test", "is not a valid database URL"),
        (f"postgresql+psycopg://u:{PASSWORD}@/selvia_test?host=db.example.invalid", "only localhost"),
        (APP_URL, "the application's own database"),
    ],
)
def test_unsafe_explicit_urls_still_fail_before_connecting(app_urls, monkeypatch, request, raw, message):
    captured(monkeypatch, raw)
    monkeypatch.setenv(TEST_DATABASE_ENV, SHELL_URL)

    with pytest.raises(pytest.fail.Exception) as excinfo:
        request.getfixturevalue("test_database_url")

    assert message in str(excinfo.value)
    assert PASSWORD not in str(excinfo.value)


def test_conftest_refuses_to_load_after_shared_queue(monkeypatch):
    monkeypatch.setitem(sys.modules, "shared.queue", object())
    spec = importlib.util.spec_from_file_location("conftest_guard_check", SERVER_DIR / "conftest.py")
    module = importlib.util.module_from_spec(spec)

    with pytest.raises(RuntimeError, match="shared.queue was imported before conftest.py"):
        spec.loader.exec_module(module)
