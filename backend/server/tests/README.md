# Server Test Suite

Unit, integration and API tests for the web server.

- The API tests (`test_accounts_api.py`, `test_teams_api.py`, ...) use the `api` fixture in
  `conftest.py`: an in-memory SQLite database, a switchable signed-in identity (`api.sign_in(...)`
  stands in for Keycloak) and a captured outbox for email.
- Set `SELVIA_API_TEST_DATABASE_URL` to a local, migrated PostgreSQL to run the same tests there. Every
  table is emptied first, so it must be a database on `localhost` that you do not mind emptying.
- `SERVER_TEST_DATABASE_URL` enables the migration and queue tests (`docs/SCHEMA_CHANGE_GUIDE.md`).
- `test_route_protection.py` fails if any `/api/v1` route answers without a token.
