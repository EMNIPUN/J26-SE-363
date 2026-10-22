"""Adaptive AI Tutor — single orchestrator agent entry point.

Supports:
- ``tutor.chat``: MCP evidence/activity retrieval (no adaptive decision yet)
- ``tutor.identify_required_knowledge``: map assigned tasks to Neo4j course concepts
- ``tutor.estimate_competency``: BKT mastery from required concepts + performance evidence
- ``tutor.compare_bkt``: baseline predefined BKT vs data-fitted BKT (option C)
- ``tutor.evaluate_bkt``: hold-out evaluation of baseline vs fitted BKT (Step 4)
- ``tutor.decide_next_action``: Adaptive Decision Engine baseline policy (no I/O)
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

from app.agents.adaptive_tutor.competency.compare import compare_baseline_and_fitted_bkt
from app.agents.adaptive_tutor.competency.evaluate import (
    evaluate_baseline_and_fitted_bkt_holdout,
)
from app.agents.adaptive_tutor.competency.observations import resolve_bkt_observation
from app.agents.adaptive_tutor.competency.pipeline import (
    CompetencyPipelineError,
    estimate_competency_for_request,
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
from app.agents.adaptive_tutor.decision import (
    DecisionPolicyError,
    decide_next_action,
)
from app.agents.adaptive_tutor.schemas import (
    AdaptiveDecisionInput,
    EstimateCompetencyInput,
    TutorChatInput,
)
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
SUPPORTED_COMPETENCY_ACTION = "tutor.estimate_competency"
SUPPORTED_COMPARE_BKT_ACTION = "tutor.compare_bkt"
SUPPORTED_EVALUATE_BKT_ACTION = "tutor.evaluate_bkt"
SUPPORTED_DECISION_ACTION = "tutor.decide_next_action"


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
        if request.action == SUPPORTED_COMPETENCY_ACTION:
            return await self._handle_estimate_competency(request)
        if request.action == SUPPORTED_COMPARE_BKT_ACTION:
            return await self._handle_compare_bkt(request)
        if request.action == SUPPORTED_EVALUATE_BKT_ACTION:
            return await self._handle_evaluate_bkt(request)
        if request.action == SUPPORTED_DECISION_ACTION:
            return await self._handle_decide_next_action(request)
        if request.action != SUPPORTED_CHAT_ACTION:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": f"Action {request.action!r} is not supported yet."},
            )
        return await self._handle_chat(request)

    async def _handle_decide_next_action(self, request: AgentRequest) -> AgentResponse:
        """Pure decision over caller-supplied learner state (no MCP / Neo4j / OpenAI)."""
        try:
            payload = AdaptiveDecisionInput.model_validate(request.input)
        except ValidationError:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code="invalid_input",
                    message="tutor.decide_next_action input is invalid.",
                ),
            )
        try:
            decision = decide_next_action(payload)
        except DecisionPolicyError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc)),
            )
        return self._response(
            request,
            status=ResultStatus.COMPLETED,
            result={"adaptive_decision": decision.model_dump(mode="json")},
        )

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

    async def _handle_estimate_competency(self, request: AgentRequest) -> AgentResponse:
        if self._sprint_provider is None:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={
                    "detail": "Sprint data provider is not configured for competency estimation."
                },
                error=ErrorInfo(
                    code="sprint_provider_not_configured",
                    message="Sprint data provider is not configured.",
                ),
            )

        try:
            payload = EstimateCompetencyInput.model_validate(request.input)
        except ValidationError:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code="invalid_input",
                    message="tutor.estimate_competency input is invalid.",
                ),
            )

        print(
            "[tutor.estimate_competency] start "
            f"request_id={request.request_id} student_id={request.student_id} "
            f"project_id={request.project_id} sprint_id={request.sprint_id}",
            flush=True,
        )

        try:
            if payload.performance_evidence:
                performance_records: list[Any] = list(payload.performance_evidence)
                print(
                    f"[tutor.estimate_competency] evidence_source=inline "
                    f"count={len(performance_records)}",
                    flush=True,
                )
            else:
                print(
                    f"[tutor.estimate_competency] evidence_source=mcp "
                    f"course_id={payload.course_id}",
                    flush=True,
                )
                performance_records = await self._load_mcp_performance_evidence(
                    course_id=payload.course_id
                )
                print(
                    f"[tutor.estimate_competency] mcp_evidence_loaded "
                    f"count={len(performance_records)}",
                    flush=True,
                )
        except SelviaMcpAuthError:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": "Tutor MCP authentication failed"},
                error=ErrorInfo(
                    code="mcp_auth_error",
                    message="Tutor MCP authentication failed",
                ),
            )
        except SelviaMcpTransportError:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": "Tutor MCP is temporarily unavailable"},
                error=ErrorInfo(
                    code="mcp_transport_error",
                    message="Tutor MCP transport failed",
                    retryable=True,
                ),
            )
        except SelviaMcpError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code=getattr(exc, "code", "mcp_error"),
                    message="Tutor MCP request failed",
                ),
            )
        except RuntimeError as exc:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": str(exc)},
                error=ErrorInfo(code="mcp_not_configured", message=str(exc)),
            )

        try:
            course_repository = self._resolve_course_repository()
            concept_selector = self._resolve_concept_selector()
            estimates, knowledge_result = await estimate_competency_for_request(
                request,
                sprint_provider=self._sprint_provider,
                course_repository=course_repository,
                concept_selector=concept_selector,
                performance_records=performance_records,
            )
        except CompetencyPipelineError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc)),
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

        estimate_course_id = (
            knowledge_result.course_id
            if knowledge_result is not None
            else (estimates[0].course_id if estimates else None)
        )
        public_evidence, normalized_evidence = self._public_evidence_payload(
            performance_records,
            student_id=str(request.student_id) if request.student_id else None,
            course_id=estimate_course_id,
            concept_ids=[item.concept_id for item in estimates] if estimates else None,
        )
        result: dict[str, Any] = {
            "student_id": request.student_id,
            "project_id": request.project_id,
            "sprint_id": request.sprint_id,
            "estimates": [item.model_dump(mode="json") for item in estimates],
            "performance_evidence_count": len(public_evidence),
            "performance_evidence": public_evidence,
            "normalized_evidence": normalized_evidence,
        }
        if knowledge_result is not None:
            result["required_knowledge"] = knowledge_result.model_dump(mode="json")

        self._log_competency_analysis_details(
            performance_records=performance_records,
            public_evidence=public_evidence,
            normalized_evidence=normalized_evidence,
            estimates=result["estimates"],
            knowledge_result=knowledge_result,
        )
        return self._response(request, status=ResultStatus.COMPLETED, result=result)

    async def _handle_compare_bkt(self, request: AgentRequest) -> AgentResponse:
        """Option C: predefined baseline BKT vs grid-fitted BKT on the same evidence."""
        if self._sprint_provider is None:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={
                    "detail": "Sprint data provider is not configured for BKT comparison."
                },
                error=ErrorInfo(
                    code="sprint_provider_not_configured",
                    message="Sprint data provider is not configured.",
                ),
            )

        try:
            payload = EstimateCompetencyInput.model_validate(request.input)
        except ValidationError:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code="invalid_input",
                    message="tutor.compare_bkt input is invalid.",
                ),
            )

        try:
            if payload.performance_evidence:
                performance_records: list[Any] = list(payload.performance_evidence)
            else:
                performance_records = await self._load_mcp_performance_evidence(
                    course_id=payload.course_id
                )
        except SelviaMcpAuthError:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": "Tutor MCP authentication failed"},
                error=ErrorInfo(
                    code="mcp_auth_error",
                    message="Tutor MCP authentication failed",
                ),
            )
        except SelviaMcpTransportError:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": "Tutor MCP is temporarily unavailable"},
                error=ErrorInfo(
                    code="mcp_transport_error",
                    message="Tutor MCP transport failed",
                    retryable=True,
                ),
            )
        except SelviaMcpError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code=getattr(exc, "code", "mcp_error"),
                    message="Tutor MCP request failed",
                ),
            )
        except RuntimeError as exc:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": str(exc)},
                error=ErrorInfo(code="mcp_not_configured", message=str(exc)),
            )

        try:
            course_repository = self._resolve_course_repository()
            concept_selector = self._resolve_concept_selector()
            estimates, knowledge_result = await estimate_competency_for_request(
                request,
                sprint_provider=self._sprint_provider,
                course_repository=course_repository,
                concept_selector=concept_selector,
                performance_records=performance_records,
            )
        except CompetencyPipelineError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc)),
            )
        except (
            ContextBuildError,
            SprintDataProviderError,
            UnknownCourseError,
            KnowledgeGraphError,
            KnowledgeIdentificationError,
        ) as exc:
            code = getattr(exc, "code", "compare_bkt_failed")
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=code, message=str(exc)),
            )
        except KnowledgeGraphConfigError as exc:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": str(exc)},
                error=ErrorInfo(code=exc.code, message=str(exc), retryable=False),
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

        if not estimates:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code="no_concepts",
                    message="No concepts available for BKT comparison.",
                ),
            )

        report = compare_baseline_and_fitted_bkt(
            student_id=str(request.student_id),
            course_id=estimates[0].course_id,
            concept_ids=[item.concept_id for item in estimates],
            records=performance_records,
        )
        result: dict[str, Any] = {
            "student_id": request.student_id,
            "project_id": request.project_id,
            "sprint_id": request.sprint_id,
            "bkt_comparison": report.model_dump(mode="json"),
            "performance_evidence_count": len(performance_records),
        }
        if knowledge_result is not None:
            result["required_knowledge"] = knowledge_result.model_dump(mode="json")
        return self._response(request, status=ResultStatus.COMPLETED, result=result)

    async def _handle_evaluate_bkt(self, request: AgentRequest) -> AgentResponse:
        """Step 4: fit on earlier answers; score baseline vs fitted on held-out answers."""
        if self._sprint_provider is None:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={
                    "detail": "Sprint data provider is not configured for BKT evaluation."
                },
                error=ErrorInfo(
                    code="sprint_provider_not_configured",
                    message="Sprint data provider is not configured.",
                ),
            )

        try:
            payload = EstimateCompetencyInput.model_validate(request.input)
        except ValidationError:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code="invalid_input",
                    message="tutor.evaluate_bkt input is invalid.",
                ),
            )

        try:
            if payload.performance_evidence:
                performance_records: list[Any] = list(payload.performance_evidence)
            else:
                performance_records = await self._load_mcp_performance_evidence(
                    course_id=payload.course_id
                )
        except SelviaMcpAuthError:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": "Tutor MCP authentication failed"},
                error=ErrorInfo(
                    code="mcp_auth_error",
                    message="Tutor MCP authentication failed",
                ),
            )
        except SelviaMcpTransportError:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": "Tutor MCP is temporarily unavailable"},
                error=ErrorInfo(
                    code="mcp_transport_error",
                    message="Tutor MCP transport failed",
                    retryable=True,
                ),
            )
        except SelviaMcpError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code=getattr(exc, "code", "mcp_error"),
                    message="Tutor MCP request failed",
                ),
            )
        except RuntimeError as exc:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": str(exc)},
                error=ErrorInfo(code="mcp_not_configured", message=str(exc)),
            )

        try:
            course_repository = self._resolve_course_repository()
            concept_selector = self._resolve_concept_selector()
            estimates, knowledge_result = await estimate_competency_for_request(
                request,
                sprint_provider=self._sprint_provider,
                course_repository=course_repository,
                concept_selector=concept_selector,
                performance_records=performance_records,
            )
        except CompetencyPipelineError as exc:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=exc.code, message=str(exc)),
            )
        except (
            ContextBuildError,
            SprintDataProviderError,
            UnknownCourseError,
            KnowledgeGraphError,
            KnowledgeIdentificationError,
        ) as exc:
            code = getattr(exc, "code", "evaluate_bkt_failed")
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(code=code, message=str(exc)),
            )
        except KnowledgeGraphConfigError as exc:
            return self._response(
                request,
                status=ResultStatus.UNAVAILABLE,
                result={"detail": str(exc)},
                error=ErrorInfo(code=exc.code, message=str(exc), retryable=False),
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

        if not estimates:
            return self._response(
                request,
                status=ResultStatus.FAILED,
                error=ErrorInfo(
                    code="no_concepts",
                    message="No concepts available for BKT hold-out evaluation.",
                ),
            )

        report = evaluate_baseline_and_fitted_bkt_holdout(
            student_id=str(request.student_id),
            course_id=estimates[0].course_id,
            concept_ids=[item.concept_id for item in estimates],
            records=performance_records,
        )
        result: dict[str, Any] = {
            "student_id": request.student_id,
            "project_id": request.project_id,
            "sprint_id": request.sprint_id,
            "bkt_holdout_evaluation": report.model_dump(mode="json"),
            "performance_evidence_count": len(performance_records),
        }
        if knowledge_result is not None:
            result["required_knowledge"] = knowledge_result.model_dump(mode="json")
        return self._response(request, status=ResultStatus.COMPLETED, result=result)

    async def _load_mcp_performance_evidence(
        self,
        *,
        course_id: str | None,
    ) -> list[Any]:
        if self._mcp_client is None:
            raise RuntimeError(
                "Tutor MCP is not configured and no performance_evidence was provided."
            )
        await self._require_request_token()
        if course_id:
            return await self._mcp_client.get_current_evidence(course_id=course_id)
        return await self._mcp_client.get_current_evidence()

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

    @staticmethod
    def _log_competency_analysis_details(
        *,
        performance_records: list[Any],
        public_evidence: list[dict[str, Any]],
        normalized_evidence: list[dict[str, Any]],
        estimates: list[dict[str, Any]],
        knowledge_result: Any,
    ) -> None:
        """Print analysis + evidence details to the AI Backend terminal (no tokens)."""
        print(
            "[tutor.estimate_competency] summary "
            f"public_rows={len(public_evidence)} bkt_usable={len(normalized_evidence)} "
            f"estimates={len(estimates)} has_required_knowledge={knowledge_result is not None}",
            flush=True,
        )

        for index, raw in enumerate(performance_records):
            detail = AdaptiveTutorAgent._evidence_log_row(raw, index=index)
            print(f"[tutor.estimate_competency] evidence[{index}] {detail}", flush=True)

        for index, row in enumerate(normalized_evidence):
            print(
                f"[tutor.estimate_competency] bkt_obs[{index}] "
                f"evidence_id={row.get('evidence_id')} concept_id={row.get('concept_id')} "
                f"correct={row.get('correct')} used_for_bkt={row.get('used_for_bkt')} "
                f"score={row.get('score')}",
                flush=True,
            )

        for index, est in enumerate(estimates):
            print(
                f"[tutor.estimate_competency] estimate[{index}] "
                f"concept_id={est.get('concept_id')} mastery={est.get('mastery_probability')} "
                f"observations={est.get('observation_count')} "
                f"explanation={est.get('explanation')}",
                flush=True,
            )

        print("[tutor.estimate_competency] completed", flush=True)

    @staticmethod
    def _evidence_log_row(raw: Any, *, index: int) -> dict[str, Any]:
        if hasattr(raw, "model_dump"):
            dumped = raw.model_dump(mode="json", by_alias=True)
        elif isinstance(raw, dict):
            dumped = raw
        else:
            return {"index": index, "unreadable": type(raw).__name__}

        meta = dumped.get("metadata") if isinstance(dumped.get("metadata"), dict) else {}
        return {
            "id": dumped.get("id"),
            "sourceType": dumped.get("sourceType") or dumped.get("source_type"),
            "conceptId": dumped.get("conceptId") or dumped.get("concept_id"),
            "courseId": dumped.get("courseId") or dumped.get("course_id"),
            "score": dumped.get("score"),
            "maxScore": dumped.get("maxScore") or dumped.get("max_score"),
            "percentage": dumped.get("percentage"),
            "status": dumped.get("status"),
            "observedAt": dumped.get("observedAt") or dumped.get("observed_at"),
            "exercise_id": meta.get("exercise_id"),
            "question_id": meta.get("question_id") or meta.get("assessment_question_id"),
            "is_correct": meta.get("is_correct"),
        }

    @staticmethod
    def _public_evidence_payload(
        records: list[Any],
        *,
        student_id: str | None,
        course_id: str | None = None,
        concept_ids: list[str] | None = None,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Sanitized evidence list for UI (no secrets); plus BKT-usable normalized rows.

        The public list keeps only the analysis course and the required concept
        ids. Other courses and unrelated concepts are omitted. ``used_for_bkt`` /
        ``correct`` still follow ``resolve_bkt_observation``, not a score threshold.
        A required-concept row can appear in the public list without being used
        for BKT when its metadata is not a valid observation.
        """
        course_filter = (
            course_id.strip() if isinstance(course_id, str) and course_id.strip() else None
        )
        allowed_concepts = (
            {
                str(concept_id).strip()
                for concept_id in concept_ids
                if concept_id and str(concept_id).strip()
            }
            if concept_ids is not None
            else None
        )
        public: list[dict[str, Any]] = []
        normalized: list[dict[str, Any]] = []
        for raw in records:
            if hasattr(raw, "model_dump"):
                dumped = raw.model_dump(mode="json", by_alias=True)
                record = raw
            elif isinstance(raw, dict):
                dumped = raw
                try:
                    from app.agents.adaptive_tutor.schemas import PerformanceEvidenceRecord

                    record = PerformanceEvidenceRecord.model_validate(raw)
                except Exception:
                    record = None
            else:
                continue

            row_course = dumped.get("courseId") or dumped.get("course_id")
            row_concept = dumped.get("conceptId") or dumped.get("concept_id")
            if course_filter is not None and row_course != course_filter:
                continue
            if allowed_concepts is not None and row_concept not in allowed_concepts:
                continue
            if len(public) >= limit:
                break

            public.append(
                {
                    "id": dumped.get("id"),
                    "conceptId": dumped.get("conceptId") or dumped.get("concept_id"),
                    "courseId": dumped.get("courseId") or dumped.get("course_id"),
                    "sourceType": dumped.get("sourceType") or dumped.get("source_type"),
                    "sourceId": dumped.get("sourceId") or dumped.get("source_id"),
                    "score": dumped.get("score"),
                    "maxScore": dumped.get("maxScore") or dumped.get("max_score"),
                    "percentage": dumped.get("percentage"),
                    "attemptNumber": dumped.get("attemptNumber")
                    or dumped.get("attempt_number"),
                    "status": dumped.get("status"),
                    "observedAt": dumped.get("observedAt") or dumped.get("observed_at"),
                }
            )
            if record is None or not student_id:
                continue
            resolved = resolve_bkt_observation(
                record,
                student_id=student_id,
                course_id=course_id,
                concept_ids=concept_ids,
            )
            if resolved is None:
                continue
            item, correct = resolved
            row = item.model_dump(mode="json")
            row["used_for_bkt"] = True
            row["correct"] = correct
            normalized.append(row)
        return public, normalized

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
