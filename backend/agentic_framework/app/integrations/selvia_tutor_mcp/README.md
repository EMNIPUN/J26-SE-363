# SELVIA tutor MCP client

Shared Python client for the **SELVIA Learning Assessment Platform** Streamable HTTP MCP
server. Used by the Adaptive AI Tutor (and any other agent that needs the same tools). Lives
under `app/integrations/`, not inside `app/agents/adaptive_tutor/`.

## Platform contract

| Item | Value |
|---|---|
| Endpoint path | `/mcp` |
| Transport | Streamable HTTP (official Python SDK `mcp` + `streamable_http_client`) |
| Auth | `Authorization: Bearer <short-lived tutor token>` |
| Audience | Platform `MCP_RESOURCE_URL` (must match this client's `mcp_url`) |

Tools:

- `get_current_evidence` — scope `tutor:evidence.read`; optional `courseId`, `conceptId`
- `get_learning_activities` — scope `tutor:activity.read`; optional filters plus `limit`
  (default 50, max 200)

Responses use Contract C envelopes (`ok` / `data.records` or `ok` / `error`). Records map to
`PerformanceEvidenceRecord` and `LearningBehaviourRecord` in
`app.agents.adaptive_tutor.schemas`. Null fields stay null. This client does **not** estimate
competency, mastery, or interventions.

## Configuration

Set the MCP resource URL to the same absolute URL the platform uses for `MCP_RESOURCE_URL`
(example shape only):

```text
# Settings field TUTOR_MCP_URL is loaded from AI_BACKEND_TUTOR_MCP_URL
# (must match SLAP MCP_RESOURCE_URL / tutor-token audience exactly).
# AI_BACKEND_TUTOR_MCP_URL=http://localhost:5000/mcp
#
# Full cross-repo live-test checklist (secrets stay local; public tutor route stays fail-closed):
# docs/MCP_LIVE_TEST_CHECKLIST.md
# Opt-in smoke script (disabled by default): scripts/mcp_smoke_test.py
```

Optional placeholder in `backend/agentic_framework/.env.example`. Do **not** put
`MCP_TUTOR_TOKEN_SECRET`, login JWTs, or any signing secret in this service.

### Live authentication (token path)

Tutor tokens are **minted by SLAP** (`POST /api/v1/internal/tutor-access-tokens`) for the
trusted J26 Core API only. The AI Backend must never hold `MCP_TUTOR_TOKEN_SECRET` or
`INTERNAL_TUTOR_MINT_TOKEN`.

Production path:

1. Core authenticates the student (Keycloak).
2. Core mints a short-lived tutor token from SLAP using Keycloak `iss` + `sub`.
3. Core forwards that token to the AI Backend in `X-SELVIA-Tutor-Token`.
4. `RequestScopedTutorTokenProvider` supplies it to `SelviaTutorMcpClient`.

Minting requires an active `ADMIN_VERIFIED` ExternalIdentity link on SLAP. Operator tooling
(no HTTP admin API): `SELVIA-…-SLAP-/server/scripts/provision-admin-verified-external-identity.js`.

`UnconfiguredTokenProvider` remains the fail-closed default when no request-scoped token is set.
Unit tests inject a mock session factory; they never call production or Supabase.

## Tests

From `backend/agentic_framework/`:

```bash
uv run pytest app/integrations/selvia_tutor_mcp/tests -q
```
