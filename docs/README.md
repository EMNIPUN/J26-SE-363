# Documentation - J26-SE-363

A multi-agent generative AI framework for supporting project-based learning and intelligent lecturer monitoring through learning analytics.

## Guides & Architecture
- [Environment Selection & Configuration Architecture](./ENVIRONMENT_GUIDE.md) — Comprehensive guide on `.env.*` resolution, Vite modes, Docker Compose interpolation, Keycloak/Kong credential propagation, and backend environment management.
- [Server Database & Migration Guide](./SERVER_DATABASE_GUIDE.md) — Guide on Supabase dual-connection pooling (ports 6543 vs 5432), environment variables, Alembic migration commands, and running the server.
- [Team Development Guide](./TEAM_DEVELOPMENT_GUIDE.md) — Request flow (Frontend → Core API → AI Backend → Main Orchestrator → agent), where each member implements their agent, the shared `AgentRequest` / `AgentResponse` contracts, agent registration, and the no-direct-agent-calls rule.
- [Common Foundation Report](./COMMON_FOUNDATION_REPORT.md) — What the common foundation implements: architecture, fast and slow request paths with the file and function for each step, shared contracts, orchestrator, files changed, test results and open items.
- [Backend Common Workflow Proposal](./BACKEND_COMMON_WORKFLOW_PROPOSAL.md) — The approved target architecture and phased plan behind the common foundation.
- [Server & Agentic Framework Communication Guide](./AGENT_COMMUNICATION_GUIDE.md) — Complete guide on the asynchronous `agent_jobs` queue, Option A 24-hour cleanup, and concrete examples for all 4 research modules (performance, planning, security, tutor).

