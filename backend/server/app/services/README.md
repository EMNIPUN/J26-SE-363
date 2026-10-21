# Core Services

Business logic, kept out of the route functions.

| Module | Does |
|---|---|
| `accounts.py` | The user row for a login, onboarding, profile changes |
| `teams.py` | Creating and editing teams, removing members, leadership offers |
| `invitations.py` | Inviting, answering, resending and withdrawing invitations |
| `team_rules.py` | The leader and status rules, and the helpers the services share |
| `team_views.py` | Builds API responses from teams (who sees emails and invitations) |
| `email/` | Sending email (SMTP, console, in-memory) and the message templates |
| `ai_jobs.py` | Starting background AI jobs |

How these fit together: `docs/REGISTRATION_AND_TEAMS.md`.
