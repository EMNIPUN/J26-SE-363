# Integrations

Clients for **external** systems used by agents (MCP servers, GitHub, external learning or
assessment platforms, security scanners). Shared by all agents; not owned by one agent.

Internal communication between agents never goes through here: agents return results to the
Main Orchestrator, which decides the next step.

## Packages

| Package | Purpose |
|---|---|
| `selvia_tutor_mcp/` | Streamable HTTP MCP client for the SELVIA Learning Assessment Platform (`/mcp`). See that package's README for auth and configuration. |

Live tutor MCP authentication requires an injected `TokenProvider`. Token minting is **not**
implemented in this repository step; do not add `MCP_TUTOR_TOKEN_SECRET` here.
