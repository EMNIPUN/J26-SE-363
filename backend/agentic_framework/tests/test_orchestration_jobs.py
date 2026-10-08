import pytest
from procrastinate.testing import InMemoryConnector
from pydantic import ValidationError
from shared.contracts import (
    AgentName,
    AgentRequest,
    AgentResponse,
    OrchestrationRequest,
    OrchestrationResponse,
    RequesterContext,
    ResultStatus,
    UserRole,
)
from shared.jobs import ORCHESTRATION_TASK_NAME, queue_for
from shared.queue import app as procrastinate_app

from app.orchestrator import AgentExecutor, Orchestrator
from app.tasks import orchestration_tasks

REQUEST = OrchestrationRequest(
    request_id="job-req-001",
    requester=RequesterContext(user_id="lec-01", role=UserRole.LECTURER),
    project_id="P-01",
    action="planning.analyze_guidance",
    input={"document_id": "DOC-7"},
)


class RecordingPlanner:
    name = AgentName.PROJECT_PLANNING

    def __init__(self):
        self.requests: list[AgentRequest] = []

    async def handle(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=ResultStatus.COMPLETED,
            result={"requirements": ["R1", "R2"]},
        )


@pytest.fixture
def planner(monkeypatch):
    planner = RecordingPlanner()
    orchestrator = Orchestrator(AgentExecutor({AgentName.PROJECT_PLANNING: planner}))
    monkeypatch.setattr(orchestration_tasks, "get_orchestrator", lambda: orchestrator)
    return planner


@pytest.mark.asyncio
async def test_job_is_handled_by_the_orchestrator(planner):
    result = await orchestration_tasks.run_orchestration(payload=REQUEST.model_dump(mode="json"))

    response = OrchestrationResponse.model_validate(result)
    assert response.status is ResultStatus.COMPLETED
    assert response.result == {"requirements": ["R1", "R2"]}
    assert planner.requests[0].project_id == "P-01"
    assert planner.requests[0].action == "planning.analyze_guidance"


@pytest.mark.asyncio
async def test_job_without_registered_agent_is_unavailable():
    result = await orchestration_tasks.run_orchestration(payload=REQUEST.model_dump(mode="json"))

    assert OrchestrationResponse.model_validate(result).status is ResultStatus.UNAVAILABLE


@pytest.mark.asyncio
async def test_job_payload_must_follow_the_contract():
    with pytest.raises(ValidationError):
        await orchestration_tasks.run_orchestration(payload={"action": "planning.analyze_guidance"})


@pytest.mark.asyncio
async def test_worker_runs_queued_job_through_the_orchestrator(planner):
    connector = InMemoryConnector()

    with procrastinate_app.replace_connector(connector):
        async with procrastinate_app.open_async():
            job_id = await procrastinate_app.configure_task(
                name=ORCHESTRATION_TASK_NAME, queue=queue_for(REQUEST)
            ).defer_async(payload=REQUEST.model_dump(mode="json"))
            await procrastinate_app.run_worker_async(
                wait=False, install_signal_handlers=False, listen_notify=False
            )

    assert connector.jobs[job_id]["status"] == "succeeded"
    assert planner.requests[0].request_id == "job-req-001"
