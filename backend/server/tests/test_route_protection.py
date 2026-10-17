"""Guards against shipping an unauthenticated route.

Takes every /api/v1 operation from the OpenAPI schema (which includes routes from nested
routers) and calls it without a token. Each one must answer 401, before any request
validation or database access happens.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

# (METHOD, path) pairs that are intentionally public. Keep this empty unless there is a reason.
PUBLIC_OPERATIONS: set[tuple[str, str]] = set()

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def api_operations() -> list[tuple[str, str]]:
    return sorted(
        (method.upper(), path)
        for path, item in app.openapi()["paths"].items()
        if path.startswith("/api/v1")
        for method in item
        if method in HTTP_METHODS
    )


def test_the_schema_lists_api_operations():
    # A guard that checks nothing would pass forever: fail if discovery breaks.
    operations = api_operations()
    assert ("GET", "/api/v1/auth/me") in operations
    assert ("POST", "/api/v1/jobs") in operations


@pytest.mark.parametrize(("method", "path"), api_operations())
def test_operation_rejects_requests_without_a_token(method, path):
    if (method, path) in PUBLIC_OPERATIONS:
        pytest.skip("intentionally public")

    response = TestClient(app).request(method, path.replace("{job_id}", "1"))

    assert response.status_code == 401, f"{method} {path} answered {response.status_code}"
    assert response.headers.get("www-authenticate") == "Bearer"
