# API Version 1

Mounted under `/api/v1` by `router.py`.

| Module | Routes |
|---|---|
| `auth.py` | `GET /auth/me`: who the token says the caller is |
| `me.py` | `GET /me`, `POST /me/onboarding`, `PATCH /me/profile`: the account behind the login |
| `teams.py` | `GET /me/teams`, `POST /teams`, `GET`/`PATCH /teams/{team}`, invitations, members, leadership |
| `invitations.py` | `GET /me/invitations`, `POST /invitations/lookup`, `/invitations/{id}/accept`, `/decline` |
| `jobs.py` | Agent job queue (admins only) |

Every router is registered on `protected_router` in `router.py`, which requires a verified Keycloak
user, so a route is closed unless someone deliberately adds it to `public_router`. The list of
endpoints with who may call each is in `docs/REGISTRATION_AND_TEAMS.md`.
