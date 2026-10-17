"""Adaptive AI Tutor — single orchestrator agent entry point.

Supports:
- ``tutor.chat``: MCP evidence/activity retrieval (no adaptive decision yet)
- ``tutor.identify_required_knowledge``: map assigned tasks to Neo4j course concepts
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from shared.contracts import (
    AgentName,
    AgentRequest,
    AgentResponse,
    ErrorInfo,
    ResultStatus,
)

from app.agents.adaptive_tutor.context import (
    ContextBuildError,
    SprintDataProvider,
    SprintDataProviderError,
)
from app.agents.adaptive_tutor.evidence.normalizer import (
    EvidenceNormalizationError,
    normalize_performance_evidence,
)
from app.agents.adaptive_tutor.knowledge import (
    ConceptSelector,
    KnowledgeIdentificationError,
    KnowledgeLlmError,
    OpenAIConceptSelector,
    identify_required_knowledge,
)
from app.agents.adaptive_tutor.schemas import TutorChatInput
from app.core.config import settings
from app.core.tutor_token_context import RequestScopedTutorTokenProvider
from app.integrations.selvia_tutor_mcp import (
    SelviaMcpAuthError,
    SelviaMcpError,
    SelviaMcpToolError,
    SelviaMcpTransportError,
    SelviaMcpValidationError,
    SelviaTutorMcpClient,
    TokenProvider,
)
from app.knowledge_graph import (
    CourseKnowledgeRepository,
    KnowledgeGraphConfigError,
    KnowledgeGraphError,
    KnowledgeGraphQueryError,
    Neo4jCourseKnowledgeRepository,
    UnknownCourseError,
)

SUPPORTED_CHAT_ACTION = "tutor.chat"
SUPPORTED_KNOWLEDGE_ACTION = "tutor.identify_required_knowledge"


class AdaptiveTutorAgent:
    """ONE Adaptive Tutor agent. Internal packages are modules, not sub-agents."""

    name = AgentName.ADAPTIVE_TUTOR

    def __init__(
        self,
        *,
        mcp_url: str | None = None,
        token_provider: TokenProvider | None = None,
        mcp_client: SelviaTutorMcpClient | None = None,
        sprint_provider: SprintDataProvider | None = None,
        course_repository: CourseKnowledgeRepository | None = None,
        concept_selector: ConceptSelector | None = None,
    ) -> None:
        # Token provider reads the request-scoped ContextVar per call; never store a token here.
        self._token_provider: TokenProvider = (
            token_provider if token_provider is not None else RequestScopedTutorTokenProvider()
        )
        if mcp_client is not None:
            self._mcp_client: SelviaTutorMcpClient | None = mcp_client
        elif mcp_url and mcp_url.strip():
            self._mcp_client = SelviaTutorMcpClient(
                mcp_url.strip(),
                self._token_provider,
            )
        else:
            self._mcp_client = None

        # Sprint provider is injected by the registry (fixture-backed until Planning is wired).
        self._sprint_provider = sprint_provider
        self._course_repository = course_repository
        self._concept_selector = concept_selector

    async def handle(self, request: AgentRequest) -> AgentResponse:
        if request.action == SUPPORTED_KNOWLEDGE_ACTION:
            return await self._handle_identify_required_knowledge(request)
        if request.action != SUPPORTED_CHAT_ACTION:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": f"Action {request.action!r} is not supported yet."},
            )
        return await self._handle_chat(request)

    async def _handle_identify_required_knowledge(
        self,
        request: AgentRequest,
    ) -> AgentResponse:
        if self._sprint_provider is None:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={
                    "detail": "Sprint data provider is not configured for required-knowledge identification."
                },
                error=ErrorInfo(
                    code="sprint_provider_not_configured",
                    message="Sprint data provider is not configured.",
                ),
            )

        try:
            course_repository = self._resolve_course_repository()
            concept_selector = self._resolve_concept_selector()
            result = await identify_required_knowledge(
                request,
                sprint_provider=self._sprint_provider,
                course_repository=course_repository,
                concept_selector=concept_selector,
            )
        except ContextBuildError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc)),
            )
        except SprintDataProviderError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc)),
            )
        except UnknownCourseError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc)),
            )
        except KnowledgeGraphConfigError as exc:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": str(exc)},
                error=ErrorInfo(code=exc.code, message=str(exc), retryable=False),
            )
        except KnowledgeGraphQueryError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc), retryable=True),
            )
        except KnowledgeGraphError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc)),
            )
        except KnowledgeLlmError as exc:
            status = (
                ResultStatus.UNAVAILABLE
                if exc.code == "openai_not_configured"
                else ResultStatus.FAILED
            )
            return self._response(
                request,
                status=status,
                result={"detail": str(exc)},
                error=ErrorInfo(
                    code=exc.code,
                    message=str(exc),
                    retryable=exc.code == "openai_selection_failed",
                ),
            )
        except KnowledgeIdentificationError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc)),
            )

        return self._response(
            request,
            status=ResultStatus.COMPLETED,
            result=result.model_dump(mode="json"),
        )

    def _resolve_course_repository(self) -> CourseKnowledgeRepository:
        if self._course_repository is not None:
            return self._course_repository
        if not settings.neo4j_configured:
            raise KnowledgeGraphConfigError(
                "Neo4j is not configured for required-knowledge identification."
            )
        return Neo4jCourseKnowledgeRepository()

    def _resolve_concept_selector(self) -> ConceptSelector:
        if self._concept_selector is not None:
            return self._concept_selector
        return OpenAIConceptSelector()

    async def _handle_chat(self, request: AgentRequest) -> AgentResponse:
        try:
            chat_input = TutorChatInput.model_validate(request.input)
        except ValidationError:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code="invalid_input",
                    message="tutor.chat requires a non-empty message in input",
                ),
            )

        if self._mcp_client is None:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={
                    "detail": "Tutor MCP is not configured",
                    "student_message": chat_input.message,
                },
            )

        try:
            await self._require_request_token()
        except SelviaMcpAuthError:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={
                    "detail": "Tutor access token is not available for this request",
                    "student_message": chat_input.message,
                },
            )

        try:
            evidence_records = await self._mcp_client.get_current_evidence()
            activity_records = await self._mcp_client.get_learning_activities()
        except SelviaMcpAuthError:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={
                    "detail": "Tutor MCP authentication failed",
                    "student_message": chat_input.message,
                },
            )
        except SelviaMcpTransportError:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={
                    "detail": "Tutor MCP is temporarily unavailable",
                    "student_message": chat_input.message,
                },
                error=ErrorInfo(
                    code="mcp_transport_error",
                    message="Tutor MCP transport failed",
                    retryable=True,
                ),
            )
        except SelviaMcpToolError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code=exc.code,
                    message="Tutor MCP tool call failed",
                    retryable=False,
                ),
                result={"student_message": chat_input.message},
            )
        except SelviaMcpValidationError:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code="mcp_validation_error",
                    message="Tutor MCP request validation failed",
                ),
                result={"student_message": chat_input.message},
            )
        except SelviaMcpError:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code="mcp_error",
                    message="Tutor MCP request failed",
                ),
                result={"student_message": chat_input.message},
            )

        normalized_evidence: list[dict[str, Any]] = []
        raw_evidence: list[dict[str, Any]] = []
        for record in evidence_records:
            raw_evidence.append(record.model_dump(mode="json", by_alias=True))
            if request.student_id:
                try:
                    item = normalize_performance_evidence(record, request.student_id)
                    normalized_evidence.append(item.model_dump(mode="json"))
                except EvidenceNormalizationError:
                    # Preserve the raw record; do not invent a score or competency.
                    pass

        return self._response(
            request,
            status=ResultStatus.COMPLETED,
            result={
                "student_message": chat_input.message,
                "performance_evidence": raw_evidence,
                "normalized_evidence": normalized_evidence,
                "learning_activities": [
                    record.model_dump(mode="json", by_alias=True)
                    for record in activity_records
                ],
                # Explicit: adaptive decision / chat answer is not produced in this step.
                "adaptive_decision": None,
            },
        )

    async def _require_request_token(self) -> None:
        token = await self._token_provider.get_access_token()
        if not isinstance(token, str) or not token.strip():
            raise SelviaMcpAuthError(
                "No request-scoped tutor access token is available for this request"
            )

    def _response(
        self,
        request: AgentRequest,
        *,
        status: ResultStatus,
        result: dict[str, Any] | None = None,
        error: ErrorInfo | None = None,
    ) -> AgentResponse:
        return AgentResponse(
            request_id=request.request_id,
            agent_name=self.name,
            status=status,
            result=result or {},
            error=error,
        )
