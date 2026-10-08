"""The background orchestration job, shared by the Core API (producer) and the worker (consumer).

Every background AI request is one `orchestration.run` job whose payload is an
OrchestrationRequest. The worker hands it to the Main Orchestrator, exactly like
the HTTP route, so agents have a single entry point. The queue only decides
which worker picks the job up (`python -m worker --queues tutor`).
"""

from shared.contracts import OrchestrationRequest, agent_for_action

ORCHESTRATION_TASK_NAME = "orchestration.run"
DEFAULT_QUEUE = "default"


def queue_for(request: OrchestrationRequest) -> str:
    """'planning.analyze_guidance' -> 'planning'; requests without a known action -> 'default'."""
    if request.action is None or agent_for_action(request.action) is None:
        return DEFAULT_QUEUE
    return request.action.split(".", 1)[0]
