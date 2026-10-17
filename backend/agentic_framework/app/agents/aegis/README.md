# AEGIS Security Agent

Owner: AEGIS team member. All security analysis logic lives in this directory.

- Implement an agent class with `name = AgentName.AEGIS` and
  `async def handle(request: AgentRequest) -> AgentResponse` (see `app/agents/base.py`).
- Actions use the `security.` prefix (e.g. `security.scan_repository`); the orchestrator routes
  them here.
- Findings must be evidence-grounded: return scanner output as `Evidence` items; the LLM explains
  and prioritizes verified findings, it does not invent them.
- If a finding needs student learning, return a `NextAction` with
  `target_agent=AgentName.ADAPTIVE_TUTOR`. Never call the tutor directly; the orchestrator
  coordinates AEGIS -> Tutor -> AEGIS.
- External scanners/tools are wrapped in `app/integrations/`.
- When ready, register the agent in `app/agents/registry.py`.

See `docs/TEAM_DEVELOPMENT_GUIDE.md`.
