# Custom CodeQL queries

One folder per CodeQL language (`python/`, `java-kotlin/`, `javascript-typescript/`), each with a
`qlpack.yml`. `codeql.py` adds a folder to the analysis when it contains `.ql` files. Tag a
query with `external/security-assistant/V1` (or V2/V3) and its CWE (`external/cwe/cwe-862`) so results map to
a category.

## MissingOwnershipCheck.ql (V1, all three languages)

Reports a route/controller handler that passes one of its request parameters to a database call
(SQL execution or an ORM/repository lookup) and never refers to the authenticated user.
It counts as "refers to the user" when the handler mentions `current_user` / `session` /
`Principal` / `req.user` and similar, is covered by a login or method-security decorator or
annotation (`@login_required`, `@PreAuthorize`, ...), or (Express) the route has extra middleware.

It is a heuristic with `@precision low`: it cannot tell whether a custom helper checks ownership,
and it only sees direct flow inside the handler. Expect false positives and misses; the later
review stage decides. Tests: `tests/test_integration.py` (seeded repos must be flagged, handlers
that use the user must not be).

Note: CodeQL compiles these queries on every scan (about 1-2 minutes per language) and needs
about 3 GB of RAM for Java (`SECURITY_ASSISTANT_CODEQL_RAM_MB`, `SECURITY_ASSISTANT_CODEQL_THREADS`).
