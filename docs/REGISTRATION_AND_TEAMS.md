# Registration, Onboarding and Teams

How a person joins SELVIA and gets into a team: sign-up, onboarding, creating teams, invitations
and the team leader. Read this before changing any of them.

- [1. The flow](#1-the-flow)
- [2. Rules](#2-rules)
- [3. How it is built](#3-how-it-is-built)
- [4. Data model](#4-data-model)
- [5. API](#5-api)
- [6. Email](#6-email)
- [7. Setting it up](#7-setting-it-up)
- [8. Testing](#8-testing)
- [9. Limits and open items](#9-limits-and-open-items)

---

## 1. The flow

```text
Sign up / sign in (Keycloak: email + password, Google, Microsoft or GitHub)
        |  verified email
        v
Onboarding (first time only, 3 steps)
   1. Account type     student or lecturer
   2. Your details     name, institution; students: GitHub username; lecturers: department, title
   3. Review and agree consent to how SELVIA uses project information
        |
        v
Home  /home   the teams you belong to, and invitations waiting for you
        |
        +-- lecturer: Create team  /teams/new   (team, people, review)
        |                -> invitations are emailed
        |
        +-- student: Accept an invitation -> the team appears
        |
        v
A team  /teams/:code/...   the existing workspace (planning, performance, tutor, security)
        /teams/:code/members   members, invitations, leadership, repository
```

An invitation can also arrive as a link in an email (`/invitations?token=...`). Someone who has
no account yet signs up first; after onboarding they are returned to the link.

## 2. Rules

| Topic | Rule |
| --- | --- |
| Account type | Chosen once, in onboarding. There is no approval step. It cannot be changed afterwards. Administrators come from Keycloak (the `admin` realm role) and skip onboarding |
| Creating teams | Lecturers only |
| Lecturers in a team | Several are allowed. The creator adds others by invitation. They **evaluate**; they take no part in development |
| One team per term | A student can be in one team per term (a team has a `term` such as `2026-S1`). Accepting a second team in the same term is refused |
| Team leader | At most one, always a student member. The lecturer can flag one invited student; otherwise the **first student on the list** is flagged. The flag takes effect when that student accepts. If the flagged student declines, the student who joined first becomes leader. A team with students always has a leader |
| Changing the leader | The leader (or a lecturer) offers leadership to another student member. It only changes when that student **accepts** |
| Leaving | Anyone can leave. A leader with teammates must hand over first. A team always keeps one lecturer |
| Removing | Lecturers remove members |
| Invitations | Sent to an email address, matched to the account whose **verified** email is that address. They expire after `INVITATION_TTL_DAYS` (14). A lecturer can send again (the old link stops working) or withdraw |
| Visibility | A team is visible to its members and to administrators. Anyone else gets "not found" |
| Repository URL | Set by the leader or a lecturer |

## 3. How it is built

| Part | Where | Does |
| --- | --- | --- |
| Keycloak | `docker/keycloak/` | Passwords, social sign-in, email verification, the sign-in pages. See `docker/keycloak/README.md` |
| Core API | `backend/server/` | Accounts, teams, invitations, email. Every route requires a verified token |
| Frontend | `frontend/src/shared/` | Onboarding, home, team creation, invitations, members |

Keycloak proves **who** a person is. What they are in SELVIA (student or lecturer) is chosen in the
app and stored in the Core API database, so the role is not in the token and cannot be forged by
editing a token or by browser storage. The frontend takes the role from `GET /api/v1/me`.

Backend code map (`backend/server/app/`):

| File | Holds |
| --- | --- |
| `api/deps.py` | `get_account`, `get_onboarded_account`, `require_account_role` |
| `services/accounts.py` | Creating the user row on first sight, onboarding, profile |
| `services/teams.py` | Creating and editing teams, removing members, leadership |
| `services/invitations.py` | Inviting, answering, resending, withdrawing |
| `services/team_rules.py` | The leader and status rules, shared by the services |
| `services/team_views.py` | Turns teams into API responses (who sees emails, invitations) |
| `services/email/` | Sending email (SMTP, console, in-memory) and the message templates |
| `api/v1/me.py`, `teams.py`, `invitations.py` | The routes |

Frontend map (`frontend/src/shared/`): `auth/` (`AuthContext`, `RequireAccount`), `pages/onboarding`,
`pages/home`, `pages/teams`, `pages/invitations`, `pages/profile`, `layout/HubLayout.jsx`,
`hooks/useTeams.js`, `services/accountService.js` and `teamService.js`.

## 4. Data model

Added by migration `ec66f4d17052` (see `docs/SCHEMA_CHANGE_GUIDE.md`).

| Table | New in this feature |
| --- | --- |
| `users` | `email`, `institution`, `department`, `title`, `github_username` (unique, lower case), `consent_version`, `consent_at`, `onboarding_completed_at`. `role` is empty until onboarding is finished |
| `groups` (shown as teams) | `term`, `status` (`forming` / `active`), `repo_url`, `created_by_id`, `leader_id`, `pending_leader_id` |
| `group_members` | `role` (`lecturer` / `member`), `term` (students only; `unique(user_id, term)` is the one-team-per-term rule), `joined_at` |
| `team_invitations` | New: team, `email`, role, `as_leader`, status (`pending` / `accepted` / `declined` / `revoked`), `token_hash` (SHA-256; the link secret is never stored), `expires_at`, `invited_by_id`. "Expired" is not stored: it is `expires_at` in the past |

The leader and the pending leadership offer are columns on the team, not rows, so a team cannot
have two leaders.

## 5. API

All under `/api/v1`, all require `Authorization: Bearer <token>`. Errors are
`{"detail": "<message>", "code": "<code>"}`; the frontend branches on `code`.

| Method and path | Who | Does |
| --- | --- | --- |
| `GET /me` | anyone signed in | The account (created on first call), role, whether onboarding is done |
| `POST /me/onboarding` | not yet onboarded | Choose student or lecturer, give details, accept the consent version |
| `PATCH /me/profile` | onboarded | Change details (not the role) |
| `GET /me/teams` | onboarded | My teams |
| `GET /me/invitations` | onboarded | Invitations waiting for my verified email |
| `POST /teams` | lecturers | Create a team and its project, invite people |
| `GET /teams/{team}` | members, admins | Team, members, and for lecturers the invitations. `{team}` is the id or the code |
| `PATCH /teams/{team}` | lecturers (name), lecturers and the leader (repository) | Edit |
| `POST /teams/{team}/invitations` | the team's lecturers | Invite students or lecturers |
| `POST /teams/{team}/invitations/{id}/resend` | the team's lecturers | New link, new expiry |
| `DELETE /teams/{team}/invitations/{id}` | the team's lecturers | Withdraw |
| `DELETE /teams/{team}/members/{user}` | lecturers, or the person themselves | Remove or leave |
| `POST /teams/{team}/leader-transfer` | the leader, lecturers | Offer leadership to a student member |
| `POST /teams/{team}/leader-transfer/accept` and `/decline` | the offered student | Answer |
| `DELETE /teams/{team}/leader-transfer` | the leader, lecturers | Withdraw the offer |
| `POST /invitations/lookup` | onboarded | What an email link is about |
| `POST /invitations/{id}/accept` and `/decline` | the invited person | Answer |

Common error codes: `onboarding_required`, `role_not_allowed`, `lecturer_only`, `already_onboarded`,
`consent_outdated`, `github_username_taken`, `student_number_taken`, `team_code_taken`,
`already_in_team_for_term`, `role_mismatch`, `email_not_verified`, `invitation_wrong_account`,
`invitation_invalid`, `leader_must_transfer`, `last_lecturer`, `too_many_invitations`.

Every route is behind authentication. `backend/server/tests/test_route_protection.py` fails if a
route answers anything but 401 without a token, so a new open route cannot slip in.

## 6. Email

Two senders, one provider is enough for both.

| Sender | Sends | Configure |
| --- | --- | --- |
| Keycloak | Verify your email, reset your password | `KC_SMTP_*` in the root `.env`, applied with `docker/keycloak/configure_realm.py` |
| Core API | Team invitation; invitation accepted or declined; leadership offered and answered | `EMAIL_BACKEND`, `SMTP_*`, `APP_BASE_URL` in `backend/server/.env` |

The Core API sends mail from a background task: a mail outage is logged and never fails the
request that caused it. `EMAIL_BACKEND=console` (the default) only logs messages. For development,
run Mailpit (`docker compose --profile dev up -d mailpit`, inbox on http://localhost:8025).

There is also a one-time-code email (`EmailService.verification_code`, `generate_code`) ready for
features that need one. Nothing uses it yet: Keycloak's email verification is a link, not a code.

## 7. Setting it up

1. **Apply the migration to Supabase** (one person, see `docs/SCHEMA_CHANGE_GUIDE.md`, step 8),
   then deploy the Core API. The migration adds columns and one table; running code is unaffected.
2. **Mail server.** Pick any SMTP provider. Put its settings in `backend/server/.env` (Core API)
   and in the root `.env` as `KC_SMTP_*` (Keycloak).
3. **Keycloak.** Run `python docker/keycloak/configure_realm.py` (see `docker/keycloak/README.md`):
   it applies the mail server, turns on email verification, adds Google, Microsoft and GitHub for
   the providers whose credentials you set, and restricts the web app's addresses
   (`FRONTEND_URLS`). The sign-in theme comes with the repository; restart Keycloak after pulling.
4. **Core API settings.** `KEYCLOAK_SERVER_URL` must be the address Keycloak reports as its issuer.
   `REQUIRE_VERIFIED_EMAIL` stays `true` outside local development.
5. **Web app.** In development the Vite proxy sends `/api/*` to the Core API (`VITE_API_PROXY_TARGET`).
   A deployed build needs `VITE_API_BASE_URL` pointing at the API, and the API's `CORS_ORIGINS` to
   include the web app.

## 8. Testing

```powershell
# Core API: everything, including the migration and the PostgreSQL-only checks
cd backend/server
$env:SERVER_TEST_DATABASE_URL = "..."      # see docs/SCHEMA_CHANGE_GUIDE.md, section 3
uv run pytest -q

# the account and team API on a real local PostgreSQL as well (empties its tables, localhost only)
$env:SELVIA_API_TEST_DATABASE_URL = "postgresql+psycopg://...@localhost:5433/selvia_dev"
uv run pytest -q tests/test_accounts_api.py tests/test_teams_api.py

# web app
cd frontend
npm run lint
npm test
```

The API tests (`tests/conftest.py`) replace Keycloak with `api.sign_in(...)`; everything after the
token (accounts, teams, invitations, email) is the real code. To try the whole thing by hand:
start Keycloak (`docker/keycloak/README.md`, "Changing the pages"), Mailpit, the Core API and
`npm run dev`, register, and read the emails in Mailpit.

## 9. Limits and open items

- **Anyone can sign up as a lecturer.** There is no approval step by design. A lecturer can invite up
  to 200 people at a time (`MAX_OPEN_INVITATIONS_PER_PERSON`), and the AI features run on the team's
  data, so watch usage. If it becomes a problem, add an approval state to `users` before widening
  access.
- **GitHub username is typed, not verified.** Signing in with GitHub proves a GitHub identity, but
  the username on the account is what the student entered. Matching them is a possible next step.
- **Module pages still show prototype data.** Planning, performance, security and tutor pages use
  mock content; they now open under the team the person actually belongs to.
- **Consent text.** The onboarding step summarises how project information is used. Have it
  reviewed, and bump `CONSENT_VERSION` in `services/accounts.py` whenever it changes: everyone is
  then asked again.
- **Email deliverability.** Mail from your own domain needs the provider's SPF and DKIM records.
