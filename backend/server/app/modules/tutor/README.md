# AI Tutor Module

Pedagogical tutoring sessions, interactive chat history, and student comprehension reviews.

Public entry: `POST /api/v1/tutor/chat` (student Keycloak auth).

Secure Core→AI channels (when enabled):
- Service auth: `Authorization: Bearer <AI_BACKEND_INTERNAL_TOKEN>`
- Tutor MCP token: `X-SELVIA-Tutor-Token` (never in JSON)

Public tutor chat remains fail-closed until the Adaptive Tutor is registered and
operational (`is_adaptive_tutor_execution_ready()`), even though the header handoff
is implemented.

Live MCP test environment checklist (no secrets; readiness gate stays false):
`docs/MCP_LIVE_TEST_CHECKLIST.md`.
