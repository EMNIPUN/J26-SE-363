# AI Tutor Module

Pedagogical tutoring sessions, interactive chat history, and student comprehension reviews.

Public entry: `POST /api/v1/tutor/chat` (student Keycloak auth).

Secure Core→AI channels (when enabled):
- Service auth: `X-Internal-Token: <AI_BACKEND_INTERNAL_TOKEN>`
- Tutor MCP token: `X-SELVIA-Tutor-Token` (never in JSON)

Public tutor chat is enabled when `is_adaptive_tutor_execution_ready()` is true and
`AI_BACKEND_INTERNAL_TOKEN` is configured. The Adaptive Tutor is registered in the AI
Backend; minting still requires an `ADMIN_VERIFIED` ExternalIdentity link on SLAP.

Login model: SELVIA (J26) uses Keycloak; SLAP uses local email/password. Same person is
joined only via ExternalIdentity (not SSO).

Live MCP test environment checklist (no secrets):
`docs/MCP_LIVE_TEST_CHECKLIST.md`.
