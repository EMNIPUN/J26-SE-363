import httpx
import pytest
from procrastinate import PsycopgConnector
from procrastinate.schema import SchemaManager
from shared.contracts import UserRole
from shared.queue import app as procrastinate_app

from app.core.security import CurrentUser, get_current_user
from app.main import app, lifespan

# Jobs go to their own queue on the disposable test database: no worker serving the real
# queues picks them up, and the test deletes them afterwards.
TEST_QUEUE = "selvia_test_jobs_api"


@pytest.fixture
def as_admin():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id="admin-1", role=UserRole.ADMIN
    )
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def test_queue_connector(test_database_url):
    """Point the app's job queue at SERVER_TEST_DATABASE_URL for the duration of the test."""
    conninfo = test_database_url.set(drivername="postgresql").render_as_string(hide_password=False)
    connector = PsycopgConnector(conninfo=conninfo)
    with procrastinate_app.replace_connector(connector):
        yield connector


async def ensure_queue_schema(connector: PsycopgConnector) -> None:
    row = await connector.execute_query_one_async(
        "SELECT to_regclass('procrastinate_jobs') IS NOT NULL AS ready"
    )
    if not row["ready"]:
        await SchemaManager(connector).apply_schema_async()


@pytest.mark.asyncio
async def test_publish_and_get_job(as_admin, test_queue_connector):
    async with lifespan(app):
        await ensure_queue_schema(test_queue_connector)
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                res = await client.post(
                    "/api/v1/jobs",
                    json={
                        "task_name": "selvia_test.noop",
                        "queue": TEST_QUEUE,
                        "payload": {"student_id": "IT210001", "batch_id": "Y4S1"},
                    },
                )
                assert res.status_code == 202
                data = res.json()
                assert data["task_name"] == "selvia_test.noop"
                assert data["queue"] == TEST_QUEUE
                job_id = data["job_id"]

                res_status = await client.get(f"/api/v1/jobs/{job_id}")
                assert res_status.status_code == 200
                status_data = res_status.json()
                assert status_data["job_id"] == job_id
                assert status_data["queue"] == TEST_QUEUE
                assert status_data["status"] == "todo"
                assert status_data["input_payload"]["student_id"] == "IT210001"
        finally:
            await test_queue_connector.execute_query_async(
                "DELETE FROM procrastinate_jobs WHERE queue_name = %(queue)s", queue=TEST_QUEUE
            )
