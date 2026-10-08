"""End-to-end flow across both backend services.

Needs the web server running separately (it has its own environment):
    cd backend/server && uv run uvicorn app.main:app --port 8002
Then, from backend/agentic_framework:
    uv run pytest tests/test_e2e_server_flow.py

Set SELVIA_SERVER_URL if the server is not on http://localhost:8002.
"""

import os

import httpx
import pytest

from shared.queue import app as procrastinate_app

# Ensure all task modules are registered
import app.tasks  # noqa: F401

SERVER_URL = os.getenv("SELVIA_SERVER_URL", "http://localhost:8002")


def _server_is_running() -> bool:
    try:
        return httpx.get(f"{SERVER_URL}/health", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(
    not _server_is_running(), reason=f"SELVIA server is not running at {SERVER_URL}"
)


@pytest.mark.asyncio
async def test_full_e2e_all_four_agents():
    """Complete End-to-End Test:
    1. Verify server health & Supabase DB connectivity
    2. Enqueue tasks for all 4 agent modules via REST API (POST /api/v1/jobs)
    3. Run Procrastinate worker to consume and process all queues
    4. Verify all 4 jobs successfully transition to 'succeeded' in Supabase
    5. Query results via REST API (GET /api/v1/jobs/{id})
    """
    async with procrastinate_app.open_async():
        async with httpx.AsyncClient(base_url=SERVER_URL) as client:
            # Step 1: Health check
            res_health = await client.get("/health")
            assert res_health.status_code == 200
            assert res_health.json()["status"] == "UP"
            assert res_health.json()["database_connected"] is True

            # Step 2: Enqueue jobs for all 4 research agents via REST API
            tasks_to_test = [
                {
                    "module": "performance",
                    "task_name": "performance.assess_student",
                    "queue": "performance",
                    "payload": {"student_id": "IT210001", "batch_id": "Y4S1", "sprint_id": "sprint-2"},
                },
                {
                    "module": "planning",
                    "task_name": "planning.estimate_story_points",
                    "queue": "planning",
                    "payload": {"user_stories": [{"id": "US101", "title": "Auth"}, {"id": "US102", "title": "Profile"}]},
                },
                {
                    "module": "security",
                    "task_name": "security.scan_repository_secrets",
                    "queue": "security",
                    "payload": {"repo_url": "https://github.com/test/repo", "commit_hash": "a1b2c3d4"},
                },
                {
                    "module": "tutor",
                    "task_name": "tutor.generate_guidance",
                    "queue": "tutor",
                    "payload": {"student_id": "IT210001", "question": "How do I fix git merge conflicts?"},
                },
            ]

            enqueued_job_ids = []
            for item in tasks_to_test:
                res = await client.post(
                    "/api/v1/jobs",
                    json={
                        "task_name": item["task_name"],
                        "queue": item["queue"],
                        "payload": item["payload"],
                    },
                )
                assert res.status_code == 202
                body = res.json()
                assert "job_id" in body
                assert body["status"] == "todo"
                enqueued_job_ids.append((item["module"], body["job_id"]))

            # Step 3: Run worker across all queues to process every pending job
            all_queues = ["performance", "planning", "security", "tutor"]
            await procrastinate_app.run_worker_async(
                queues=all_queues,
                wait=False,
                listen_notify=False,
                fetch_job_polling_interval=0.1,
                install_signal_handlers=False,
            )

            # Step 4: Verify all jobs reached 'succeeded' state via REST API
            for module, job_id in enqueued_job_ids:
                res_status = await client.get(f"/api/v1/jobs/{job_id}")
                assert res_status.status_code == 200
                data = res_status.json()
                assert data["job_id"] == job_id
                assert data["status"] == "succeeded", f"Job {job_id} for module {module} did not succeed: {data}"
                assert data["input_payload"] is not None
