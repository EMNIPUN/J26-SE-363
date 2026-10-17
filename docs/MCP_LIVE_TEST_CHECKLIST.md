# MCP live-test environment checklist (SELVIA)

Controlled preparation for a **dedicated local/test** MCP smoke run between:

- **SLAP** (`SELVIA-Learning-Assessment-Platform-SLAP-/server`) — MCP at `/mcp`, tutor tokens, internal mint
- **J26 Core API** (`backend/server`) — Keycloak auth, SLAP mint client (not public tutor chat)
- **J26 AI Backend** (`backend/agentic_framework`) — Adaptive Tutor + Python MCP client

**Status today:** offline contract and unit tests are verified. Live MCP is **not** claimed until this checklist is completed on an isolated test stack.

**Hard rules**

- Prefer a dedicated local/test stack. Remote app DBs (e.g. Supabase) only with **explicit** operator approval and `SELVIA_ALLOW_REMOTE_APP_DB=1`.
- After mint→MCP smoke passes and Adaptive Tutor is registered, `is_adaptive_tutor_execution_ready()` may be **True**. Live Keycloak tutor chat still needs a real `sub` linked via ExternalIdentity (not only a smoke placeholder).
- Do **not** commit real secrets. Put them only in gitignored `.env` files or shell session variables.
- Do **not** paste secrets into chat, tickets, or logs.
- Do **not** auto-link identities by email or student number.

---

## 1. Where configuration lives

| Service | Settings file (gitignored) | Template (committed) |
| --- | --- | --- |
| SLAP API | `SELVIA-…-SLAP-/server/.env` | `server/.env.example` |
| J26 Core | `J26-SE-363/backend/server/.env` | `backend/server/.env.example` |
| J26 AI Backend | `J26-SE-363/backend/agentic_framework/.env` | `backend/agentic_framework/.env.example` |

Copy each `.env.example` → `.env` locally. Leave MCP/mint secrets **commented/unset** until you intentionally prepare a test stack.

---

## 2. Required variables (placeholders only)

### SLAP (`server/.env`)

| Variable | Role | Placeholder example |
| --- | --- | --- |
| `MCP_RESOURCE_URL` | Exact MCP resource URL; **tutor token audience** | `http://localhost:5000/mcp` |
| `MCP_TUTOR_TOKEN_SECRET` | HS256 signing secret for tutor MCP JWTs (≥32 chars) | `[DEDICATED_MCP_TUTOR_TOKEN_SECRET]` |
| `MCP_TUTOR_TOKEN_ISSUER` | Optional; default `selvia-platform` | `selvia-platform` |
| `INTERNAL_TUTOR_MINT_TOKEN` | Bearer for `POST /api/v1/internal/tutor-access-tokens` (≥32 chars) | `[SHARED_INTERNAL_MINT_CREDENTIAL]` |
| `JWT_SECRET` | Login JWT only — **must differ** from MCP and mint secrets | (existing login secret) |
| `PORT` | HTTP listen port (must match URL host/port you choose) | `5000` |
| `DATABASE_URL` / `DIRECT_URL` | App DB (local); **not** used by guarded integration tests from this file | local non-production only |

### J26 Core (`backend/server/.env`)

| Variable | Role | Placeholder example |
| --- | --- | --- |
| `KEYCLOAK_SERVER_URL` | Public Keycloak base | `http://localhost:8000/auth` |
| `KEYCLOAK_REALM` | Realm name | `mentor` |
| Trusted issuer (derived) | `{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}` | `http://localhost:8000/auth/realms/mentor` |
| `AI_BACKEND_URL` | AI Backend base URL | `http://localhost:8003` |
| `AI_BACKEND_INTERNAL_TOKEN` | Core→AI service Bearer (≥32 chars) | `[SHARED_CORE_AI_BACKEND_SERVICE_CREDENTIAL]` |
| `SLAP_BASE_URL` | SLAP HTTP origin (**no** `/mcp` path) | `http://localhost:5000` |
| `INTERNAL_TUTOR_MINT_TOKEN` | Same value as SLAP mint credential | `[SHARED_INTERNAL_MINT_CREDENTIAL]` |
| `SLAP_TUTOR_MINT_TIMEOUT_SECONDS` | Mint HTTP timeout (default `8`) | `8` |

### J26 AI Backend (`backend/agentic_framework/.env`)

| Variable | Role | Placeholder example |
| --- | --- | --- |
| `AI_BACKEND_INTERNAL_TOKEN` | Same Core→AI service Bearer | `[SHARED_CORE_AI_BACKEND_SERVICE_CREDENTIAL]` |
| `AI_BACKEND_TUTOR_MCP_URL` | Loaded as `Settings.TUTOR_MCP_URL` | `http://localhost:5000/mcp` |

Never put `MCP_TUTOR_TOKEN_SECRET` or `INTERNAL_TUTOR_MINT_TOKEN` in the AI Backend `.env`.

---

## 3. Matching vs independent secrets

```text
MUST MATCH (exact string)
─────────────────────────
AI_BACKEND_TUTOR_MCP_URL  ==  MCP_RESOURCE_URL          (incl. scheme, host, port, path, no accidental slash drift)
AI_BACKEND_INTERNAL_TOKEN (Core)  ==  AI_BACKEND_INTERNAL_TOKEN (AI Backend)
INTERNAL_TUTOR_MINT_TOKEN (Core)  ==  INTERNAL_TUTOR_MINT_TOKEN (SLAP)
Keycloak issuer string used at mint time  ==  ExternalIdentity.issuer
  (Core: settings.keycloak_issuer = KEYCLOAK_SERVER_URL/realms/KEYCLOAK_REALM)
Keycloak subject (JWT sub) used at mint time  ==  ExternalIdentity.subject

MUST BE INDEPENDENT
───────────────────
MCP_TUTOR_TOKEN_SECRET  ≠  JWT_SECRET
MCP_TUTOR_TOKEN_SECRET  ≠  INTERNAL_TUTOR_MINT_TOKEN
INTERNAL_TUTOR_MINT_TOKEN  ≠  JWT_SECRET
AI_BACKEND_INTERNAL_TOKEN  ≠  MCP_TUTOR_TOKEN_SECRET
AI_BACKEND_INTERNAL_TOKEN  ≠  INTERNAL_TUTOR_MINT_TOKEN
Tutor MCP access tokens (minted JWTs) are short-lived and separate from all of the above
```

Audience note: SLAP signs tutor tokens with `audience = MCP_RESOURCE_URL`. The Python client connects to that same URL with `Authorization: Bearer <tutor token>`.

---

## 4. Confirm the endpoint is isolated (before any live call)

Use this checklist; do not contact production.

1. **Host:** prefer `localhost` / `127.0.0.1` for the smoke script default. Remote hosts require an explicit, approved override (`SELVIA_MCP_SMOKE_ALLOW_REMOTE=1`) **only** for a dedicated test instance you control.
2. **Data:** SLAP points at a local PostgreSQL you own — not Supabase pooler URLs used for shared environments.
3. **Secrets:** MCP and mint secrets exist only in local gitignored env / session env — not in git history.
4. **Process:** SLAP `npm run test:db:check` / integration runner refuse non-`*_test` and non-local hosts; do not bypass those guards.
5. **Scope:** smoke test uses read-only MCP tools only; it must not write application data.

If any item is unclear, **stop** — do not run live mode.

---

## 5. Dedicated local / test deployment (repository-supported)

Use the projects’ existing runbooks; do not invent a new topology.

1. **Keycloak** — as documented in [ENVIRONMENT_GUIDE.md](./ENVIRONMENT_GUIDE.md) (local Compose defaults: `KEYCLOAK_SERVER_URL` / realm `mentor`).
2. **SLAP server** — from `SELVIA-…-SLAP-/server/`: configure local `.env`, then `npm run dev` or `npm start` (see SLAP server README / `.env.example`). MCP mounts when `MCP_RESOURCE_URL` + `MCP_TUTOR_TOKEN_SECRET` are configured.
3. **J26 Core** — from `backend/server/` with its `.env` (see [SERVER_DATABASE_GUIDE.md](./SERVER_DATABASE_GUIDE.md)).
4. **J26 AI Backend** — from `backend/agentic_framework/` with its `.env`.

This checklist does **not** require Docker unless your team already runs Keycloak/Postgres that way.

---

## 6. External identity links (manual; do not create records in doc-only prep)

Minting resolves **only** `(issuer, subject)` → active `ExternalIdentity` → active STUDENT + Student profile.

**Approved process (code):** `createAdminVerifiedExternalIdentityLink` in SLAP `externalIdentity.service.js` with link method `ADMIN_VERIFIED`. It does **not** match email or student number.

**Important:** there is **no** HTTP route under `server/src/routes` for external identities (by design). Use the opt-in operator script instead of ad-hoc SQL:

`SELVIA-…-SLAP-/server/scripts/provision-admin-verified-external-identity.js`

Requires `SELVIA_PROVISION_EXTERNAL_IDENTITY=1` plus `SELVIA_EI_ISSUER`, `SELVIA_EI_SUBJECT`, `SELVIA_EI_USER_ID`, `SELVIA_EI_ADMIN_USER_ID`. Non-local app DBs also need `SELVIA_ALLOW_REMOTE_APP_DB=1`. Do **not** invent links in this documentation step.

For isolation testing later, prepare **two** distinct Keycloak subjects, each linked to a different Student profile with only that student’s evidence/activities.

Issuer string must match Core `settings.keycloak_issuer` character-for-character (including trailing-slash normalization already applied by Core).

**Login mapping (not SSO):** SELVIA/J26 students log in with Keycloak; SLAP users log in with local JWT email/password (`scripts/ensure-dev-login-accounts.js` with `SEED_DEV_PASSWORD`). The ExternalIdentity row is the only join for tutor minting. For Core `POST /api/v1/tutor/chat`, `SELVIA_EI_SUBJECT` must be the real Keycloak JWT `sub` (a smoke placeholder subject is only for mint→MCP smoke).

Operator scripts (opt-in):

- `server/scripts/ensure-dev-login-accounts.js` — ADMIN + STUDENT with passwords
- `server/scripts/provision-admin-verified-external-identity.js` — create the link

---

## 7. Disposable `_test` database (future guarded SLAP integration)

Do **not** run migrations or connect as part of this checklist. When you later need SLAP DB integration tests:

Follow `SELVIA-…-SLAP-/server/tests/integration/README.md`:

```powershell
# Session-only; never from server/.env; never Supabase.
$env:DATABASE_URL = "postgresql://<user>:<password>@localhost:5432/selvia_test"
$env:DIRECT_URL   = $env:DATABASE_URL

npm run test:db:check
# Then verify / migrate / integration:safe only against that disposable DB
```

Requirements (summary): local host, database name ending in `_test`, disposable marker comment, non-privileged owner role. See the integration README for the full guard list.

J26 Core migration/job tests similarly require an explicit shell `SERVER_TEST_DATABASE_URL` to a local `*_test` database (see server test docs / `SERVER_DATABASE_GUIDE.md`) — never fall back to application URLs.

---

## 8. Smoke test script (inspect only — live mode NOT RUN in Step 7.4)

**Path:** `backend/agentic_framework/scripts/mcp_smoke_test.py`

| Env | Required? | Purpose |
| --- | --- | --- |
| `SELVIA_MCP_SMOKE_TEST=1` | Yes to opt in | Without this, exit `2` (disabled) |
| `AI_BACKEND_TUTOR_MCP_URL` | Yes | MCP resource URL (or legacy alias `TUTOR_MCP_URL`) |
| `SELVIA_MCP_SMOKE_ALLOW_REMOTE=1` | Only if not localhost | Explicit approval for non-local test host |
| **Token option A** | | |
| `SELVIA_MCP_SMOKE_TUTOR_TOKEN` | One option | Already-minted short-lived tutor token |
| **Token option B** | | |
| `SLAP_BASE_URL` | With mint | SLAP origin |
| `INTERNAL_TUTOR_MINT_TOKEN` | With mint | Shared mint credential |
| `SELVIA_MCP_SMOKE_ISSUER` | With mint | Keycloak issuer |
| `SELVIA_MCP_SMOKE_SUBJECT` | With mint | Keycloak `sub` |

The script never prints tokens. It prints only record **counts** on success.

### Future invocation (NOT RUN in this step)

From `backend/agentic_framework/` after all checklist items pass:

```powershell
# DISABLED BY DEFAULT — do not run until a dedicated test MCP and identity exist.
$env:SELVIA_MCP_SMOKE_TEST = "1"
$env:AI_BACKEND_TUTOR_MCP_URL = "http://localhost:5000/mcp"
# Prefer mint path or a pre-minted token set only in the local shell (never commit):
# $env:SLAP_BASE_URL = "http://localhost:5000"
# $env:INTERNAL_TUTOR_MINT_TOKEN = "<from local .env — do not paste into chat>"
# $env:SELVIA_MCP_SMOKE_ISSUER = "http://localhost:8000/auth/realms/mentor"
# $env:SELVIA_MCP_SMOKE_SUBJECT = "<test-keycloak-sub>"

python scripts/mcp_smoke_test.py
```

**Exit codes:** `0` OK · `2` missing/unsafe config or disabled · `3` MCP/auth failure · `4` unexpected error.

Safe dry-check (no network when opt-in is off):

```powershell
python scripts/mcp_smoke_test.py
# Expected: exit 2, message that the test is disabled
```

---

## 9. What this checklist does **not** enable

- Public Core `POST /api/v1/tutor/chat` end-to-end chat
- Flipping `is_adaptive_tutor_execution_ready()`
- Adaptive learning / competency / decision algorithms
- Production or Supabase MCP testing

---

## 10. Manual remaining steps (operator)

1. Generate and store secrets **locally** (do not ask chat to invent or receive them): MCP tutor secret, mint credential, Core↔AI internal token — all ≥32 chars and pairwise distinct where required.
2. Set matching URLs on SLAP + AI Backend; set `SLAP_BASE_URL` on Core without `/mcp`.
3. Start local Keycloak + SLAP + (optionally) Core/AI Backend per existing guides.
4. Provision **one**, preferably **two**, admin-verified ExternalIdentity links via the approved process.
5. Confirm isolation checklist in §4.
6. Only then run the smoke command in §8.
7. After mint→MCP smoke passes and Adaptive Tutor is registered, Core
   `is_adaptive_tutor_execution_ready()` may be **True**. Public chat still needs a
   real Keycloak `sub` linked via ExternalIdentity (smoke placeholder is not enough for
   live Keycloak logins).
