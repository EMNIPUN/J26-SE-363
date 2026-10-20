# GitHub linking (GitHub App)

A shared platform service: any feature that needs to know "which repository is this team's, and which GitHub account is this person" uses it. The performance assessment is the first user, not the owner.

Keycloak keeps its own GitHub OAuth app, only for signing in to the platform. Team linking is a separate **GitHub App**.

## How it works

1. **The team leader installs the App** on the team's repository (team page, Repository section, "Install on GitHub") and picks the repository. Until this is done, members cannot connect.
2. **Each member connects their GitHub account** from the same page ("Connect GitHub"). GitHub itself says which account it is, so the link is verified, not typed.
3. The Core API asks GitHub, with the installation token, what permission each linked account has on the repository (`none`, `read`, `write`, `admin`) and stores the answer. A member is **ready** when it is `write` or `admin`.

Only GitHub's answers are stored (`user_github_accounts`, `team_github`, `team_github_access`). No GitHub token of a person is kept. Installation tokens are minted when needed, live for an hour, and are never written to disk or to the database.

Who may do what: the team leader and the team's lecturers (and administrators) link the repository; every member connects only their own account; a plain member sees the repository and their own row, not the others'.

## Routes

| | |
|---|---|
| `GET /github/config` | is the App set up |
| `POST /teams/{team}/github/install` | the address to install the App (leader or lecturer) |
| `GET /github/installed` | GitHub sends the browser back here after the install (signed state, no token) |
| `GET /teams/{team}/github/repos`, `PUT /teams/{team}/github/repo` | choose the repository |
| `GET /teams/{team}/github`, `POST /teams/{team}/github/refresh`, `DELETE /teams/{team}/github` | status per member, check access again, unlink |
| `POST /me/github/connect?team=`, `GET /github/callback`, `GET/DELETE /me/github` | a person signs in to GitHub for a team, and unlinks |

## Setting the App up (once)

GitHub > Settings > Developer settings > GitHub Apps > New.

| Field | Value |
|---|---|
| Callback URL | `<web app>/api/github/callback` (local: `http://localhost:5173/api/github/callback`) |
| Request user authorization (OAuth) during installation | **off** (otherwise the Setup URL is disabled) |
| Setup URL | `<web app>/api/github/installed`, "Redirect on update" ticked |
| Webhook | off for local development |
| Repository permissions | Metadata: read, Contents: read, Pull requests: read, Issues: read. Nothing else |
| Where can it be installed | Any account |

Then generate a **client secret** and a **private key** (`.pem`). Settings, in `backend/server/.env` and, for the worker, `backend/agentic_framework/.env`:

```
GITHUB_APP_ID=
GITHUB_APP_SLUG=
GITHUB_APP_CLIENT_ID=
GITHUB_APP_CLIENT_SECRET=        # Core API only
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"   # one line, \n for line breaks; or GITHUB_APP_PRIVATE_KEY_PATH=
GITHUB_CALLBACK_BASE=http://localhost:5173/api
```

`*.pem` is git-ignored. Never commit a key.

## The assessment agent

A run for a platform team is started from these verified facts only: the repository, the installation id, and for each student the platform user id, the verified login and GitHub's no-reply commit addresses. A typed GitHub username is never used to attribute work or to show someone a result. The worker mints its own installation token to clone and read the repository (a private one works, and the rate limit is the App's, not 60 an hour).

Tests: `backend/server/tests/test_github_app.py`, `test_github_api.py`, `test_performance_platform.py`.

## The gate in front of a team (students only)

A student reaches a team's dashboard only after `GET /teams/{team}/gate` says `ok`. The answer is made live against GitHub every time the page loads (and again every five minutes and when the tab regains focus), so access removed on GitHub closes the door here too.

| Answer | Meaning | What the page asks |
|---|---|---|
| `repo_not_linked` | the leader has not installed the App and chosen the repository | the leader links it; a member waits and checks again |
| `account_not_linked` | the student has not signed in with GitHub | "Continue with GitHub" |
| `read_only` / `no_access` | the connected account is not a collaborator with write access | check again, or "Use a different GitHub account" (GitHub is asked to let the person choose) |
| `github_unavailable` | GitHub could not be asked | try again; the person is not let in meanwhile |
| `ok` | in | |

One GitHub account belongs to one person on the whole platform, so two members of a team can never share an account. Lecturers and administrators supervise and are not gated. When the App is not set up on the server nothing can be verified and nobody is locked out.

The gate protects the dashboard pages. Other modules' API routes are not yet refused server-side for a student who skipped it; that needs the same check as a dependency on each route.
