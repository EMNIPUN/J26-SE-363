import pytest
from procrastinate.testing import InMemoryConnector
from shared.contracts import OrchestrationRequest, RequesterContext, UserRole
from shared.jobs import DEFAULT_QUEUE, ORCHESTRATION_TASK_NAME, queue_for
from shared.queue import app as procrastinate_app

from app.services.ai_jobs import start_ai_job

LECTURER = RequesterContext(user_id="lec-01", role=UserRole.LECTURER)


def make_request(**overrides) -> OrchestrationRequest:
    fields = {
        "requester": LECTURER,
        "project_id": "P-01",
        "action": "planning.analyze_guidance",
        "input": {"document_id": "DOC-7"},
    }
    return OrchestrationRequest(**{**fields, **overrides})


@pytest.mark.asyncio
async def test_start_ai_job_enqueues_one_orchestration_job():
    request = make_request()
    connector = InMemoryConnector()

    with procrastinate_app.replace_connector(connector):
        job_id = await start_ai_job(request)

    job = connector.jobs[job_id]
    assert job["task_name"] == ORCHESTRATION_TASK_NAME
    assert job["queue_name"] == "planning"
    assert OrchestrationRequest.model_validate(job["args"]["payload"]) == request


@pytest.mark.parametrize(
    ("overrides", "queue"),
    [
        ({"action": "tutor.chat"}, "tutor"),
        ({"action": "security.scan_repository"}, "security"),
        ({"action": "unknown.thing"}, DEFAULT_QUEUE),
        ({"action": None, "message": "Which groups are behind?"}, DEFAULT_QUEUE),
    ],
)
def test_queue_follows_the_action_area(overrides, queue):
    assert queue_for(make_request(**overrides)) == queue
