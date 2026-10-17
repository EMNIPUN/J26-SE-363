import pytest
from pydantic import ValidationError
from shared.contracts import (
    AgentName,
    AgentRequest,
    AgentResponse,
    ErrorInfo,
    Evidence,
    NextAction,
    OrchestrationRequest,
    OrchestrationResponse,
    ProjectContext,
    RequesterContext,
    ResultStatus,
    SelviaContext,
    StudentContext,
    TaskContext,
    UserRole,
)

STUDENT = RequesterContext(user_id="kc-123", role=UserRole.STUDENT)


def test_ids_are_filled_from_context():
    request = AgentRequest(
        action="tutor.chat",
        context=SelviaContext(
            student=StudentContext(student_id="ST001"),
            project=ProjectContext(project_id="P-01", title="Online Food Ordering System", group_id="G01"),
        ),
    )

    assert request.student_id == "ST001"
    assert request.project_id == "P-01"
    assert request.group_id is None
    assert request.request_id


def test_id_that_contradicts_context_is_rejected():
    with pytest.raises(ValidationError, match="task_id"):
        AgentRequest(action="tutor.chat", task_id="T-1", context=SelviaContext(task=TaskContext(task_id="T-2")))


@pytest.mark.parametrize("action", ["chat", "Tutor.chat", "tutor.", "tutor.chat.extra"])
def test_agent_request_rejects_malformed_action(action):
    with pytest.raises(ValidationError):
        AgentRequest(action=action)


def test_failed_response_requires_error():
    with pytest.raises(ValidationError, match="error is required"):
        AgentResponse(request_id="r1", agent_name=AgentName.AEGIS, status=ResultStatus.FAILED)

    response = AgentResponse(
        request_id="r1",
        agent_name=AgentName.AEGIS,
        status=ResultStatus.FAILED,
        error=ErrorInfo(code="scanner_unavailable", message="Gitleaks is not installed"),
    )
    assert response.error.retryable is False


def test_orchestration_request_needs_requester_and_action_or_message():
    with pytest.raises(ValidationError):
        OrchestrationRequest(action="tutor.chat")
    with pytest.raises(ValidationError, match="either action or message"):
        OrchestrationRequest(requester=STUDENT)

    assert OrchestrationRequest(requester=STUDENT, message="What groups are falling behind?").action is None


def test_orchestration_response_round_trips_as_json():
    response = OrchestrationResponse(
        request_id="r1",
        status=ResultStatus.COMPLETED,
        result={"answer": "JWT is a signed token."},
        evidence=[Evidence(source="quiz_result", description="Scored 4/5 on JWT basics")],
        next_action=NextAction(type="request_agent", target_agent=AgentName.ADAPTIVE_TUTOR),
        agent_responses=[
            AgentResponse(request_id="r1", agent_name=AgentName.ADAPTIVE_TUTOR, status=ResultStatus.COMPLETED)
        ],
    )

    restored = OrchestrationResponse.model_validate_json(response.model_dump_json())

    assert restored == response
    assert restored.agent_responses[0].agent_name is AgentName.ADAPTIVE_TUTOR
