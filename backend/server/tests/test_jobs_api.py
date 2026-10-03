import pytest
import httpx
from server.app.main import app, lifespan


@pytest.mark.asyncio
async def test_publish_and_get_job():
    async with lifespan(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Publish job
            res = await client.post(
                "/api/v1/jobs",
                json={
                    "task_name": "performance.assess_student",
                    "queue": "performance",
                    "payload": {"student_id": "IT210001", "batch_id": "Y4S1"},
                },
            )
            assert res.status_code == 202
            data = res.json()
            assert "job_id" in data
            assert data["task_name"] == "performance.assess_student"
            assert data["queue"] == "performance"
            job_id = data["job_id"]

            # 2. Query status
            res_status = await client.get(f"/api/v1/jobs/{job_id}")
            assert res_status.status_code == 200
            status_data = res_status.json()
            assert status_data["job_id"] == job_id
            assert status_data["status"] in ["todo", "doing", "succeeded"]
            assert status_data["input_payload"]["student_id"] == "IT210001"
