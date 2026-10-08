# Schemas

- Contracts shared with the Core API and between the orchestrator and agents (`AgentRequest`,
  `AgentResponse`, `OrchestrationRequest`, `OrchestrationResponse`, project context models) live in
  the shared package: `from shared.contracts import ...` (`backend/shared/src/shared/contracts/`).
- Agent-specific models live in that agent's own `schemas.py`.
- This folder is for AI Backend models that are neither of the above.
