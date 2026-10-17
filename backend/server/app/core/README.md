# Server Core

| File | Holds |
|---|---|
| `config.py` | Settings from the environment (database, Keycloak, email, CORS, invitations) |
| `security.py` | Keycloak JWT verification: signature, issuer, expiry, client; `get_current_user`, `require_roles` (admin only, from the token) |
| `errors.py` | `ApiError`: errors with a stable `code` next to the message |

Roles other than admin are not in the token: see `app/api/deps.py`.
