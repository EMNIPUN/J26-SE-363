# Project Planning Agent

Owner: Project Planning team member. All planning logic lives in this directory.

- Implement an agent class with `name = AgentName.PROJECT_PLANNING` and
  `async def handle(request: AgentRequest) -> AgentResponse` (see `app/agents/base.py`).
- Actions use the `planning.` prefix (e.g. `planning.analyze_requirements`); the orchestrator
  routes them here.
- Put planning-specific input/output models in `schemas.py`; they travel inside
  `AgentRequest.input` and `AgentResponse.result`.
- Never import or call another agent. To involve another agent, return a `NextAction` with
  `target_agent` set.
- When ready, register the agent in `app/agents/registry.py`.

See `docs/TEAM_DEVELOPMENT_GUIDE.md`.
