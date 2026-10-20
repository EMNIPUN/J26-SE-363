# Planted bugs in the seeded fixtures

Tick these off against `report.md`. "CodeQL" means the finding disappears when you run with `--skip codeql`.
Lines are in the files under this folder. Findings from the same rule can appear more than once (for example the
workflow rules are reported for every fixture, OSV also reports transitive packages you did not write).

Create scannable copies (they need a real git history for the secret) with:

```
python -m app.agents.security_assistant.tools.tests.demo_repos <dest>
```

That adds one more planted bug to every copy: **V4** `settings_old.py` holds an AWS key pair in a commit that is
deleted again in the last commit, so only the git history shows it (Gitleaks and TruffleHog).

## vuln_py_repo (Flask)  - files: app.py, requirements.txt, .github/workflows/ci.yml

| # | Cat | Bug | Where | Expected from | CodeQL needed |
|---|---|---|---|---|---|
| 1 | V1 | order of any user readable: no ownership check | app.py:19-22 (`orders`) | codeql `security-assistant/py/missing-ownership-check` | yes |
| 2 | V2 | SQL built from request input | app.py:22 | codeql `py/sql-injection` | yes |
| 3 | V3 | password hashed with MD5 | app.py:13 | config-scan `-cfg-005`, codeql `py/weak-sensitive-data-hashing` | no (config-scan) |
| 4 | V3 | JWT issued without `exp` | app.py:14 | config-scan `-cfg-001` | no |
| 5 | V3 | session cookie without Secure flag | app.py:8 | config-scan `-cfg-003` | no |
| 6 | V3 | login route without rate limiting | app.py:11 | config-scan `-cfg-007` | no |
| 7 | V4 | AWS key pair in deleted commit | `settings_old.py` (history, demo copy only) | gitleaks `aws-access-token`, trufflehog `AWS` | no |
| 8 | V5 | vulnerable `requests==2.19.0`, `flask==1.0` | requirements.txt | pip-audit, osv-scanner | no |
| 9 | V5 | `pull_request_target` workflow | ci.yml:1 | zizmor `dangerous-triggers` | no |
| 10 | V5 | no `permissions:` block | ci.yml:1,3 | zizmor `excessive-permissions` | no |
| 11 | V5 | unpinned `actions/checkout@latest` | ci.yml:6 | zizmor `unpinned-uses` | no |

## vuln_js_repo (Express + one TypeScript file)  - files: server.js, client.ts, package.json, package-lock.json, ci.yml

| # | Cat | Bug | Where | Expected from | CodeQL needed |
|---|---|---|---|---|---|
| 1 | V1 | query by `req.params.id` without owner check | server.js:14 | codeql `security-assistant/js/missing-ownership-check` | yes |
| 2 | V2 | command injection `exec('ls ' + req.query.dir)` | server.js:15 | codeql `js/command-line-injection` | yes |
| 3 | V2 | reflected XSS | server.js:16 | codeql `js/reflected-xss` | yes |
| 4 | V2 | SQL concatenation `db.query(... + req.params.id)` | server.js:14 | **not detected** by standard CodeQL rules (known miss) | - |
| 5 | V2 | `innerHTML = html` in TypeScript | client.ts:2 | **not detected** (known miss) | - |
| 6 | V3 | JWT signed without expiry | server.js:9 | config-scan `-cfg-001` | no |
| 7 | V3 | cookie `secure: false` | server.js:6 | config-scan `-cfg-003`, codeql `js/clear-text-cookie` | no |
| 8 | V3 | login route without rate limiting | server.js:8 | config-scan `-cfg-007`, codeql `js/missing-rate-limiting` | no |
| 9 | V4 | hard-coded JWT signing key `'key'` | server.js:9 | codeql `js/hardcoded-credentials` | yes |
| 10 | V4 | AWS key pair in deleted commit | `settings_old.py` (history, demo copy only) | gitleaks, trufflehog | no |
| 11 | V5 | vulnerable `lodash 4.17.15` (`express 4.17.1` is only in package.json: the fixture's package-lock.json lists lodash alone, so no scanner reports express) | package-lock.json | npm-audit, osv-scanner | no |
| 12 | V5 | workflow: `pull_request_target`, no permissions, `@latest` | ci.yml:1,3,6 | zizmor | no |

## vuln_java_repo (Spring Boot, Maven)  - files: UserController.java, SecurityConfig.java, application.properties, pom.xml, ci.yml

| # | Cat | Bug | Where | Expected from | CodeQL needed |
|---|---|---|---|---|---|
| 1 | V1 | no ownership check on `/users/{id}/orders` | UserController.java:11 | codeql `security-assistant/java/missing-ownership-check` | yes |
| 2 | V1 | Spring controllers but no Spring Security at all | UserController.java:6 | config-scan `-cfg-013` | no |
| 3 | V2 | SQL injection via `executeQuery` | UserController.java:11 | codeql `java/sql-injection` | yes |
| 4 | V3 | JWT built without expiration | UserController.java:17 | config-scan `-cfg-001` | no |
| 5 | V3 | login route without rate limiting | UserController.java:15 | config-scan `-cfg-007` | no |
| 6 | V3 | `NoOpPasswordEncoder` | SecurityConfig.java:3,6 | config-scan `-cfg-005` | no |
| 7 | V3 | CSRF disabled | SecurityConfig.java:7 | config-scan `-cfg-006` | no |
| 8 | V3 | session cookie `secure=false` | application.properties:1 | config-scan `-cfg-003` | no |
| 9 | V3 | all actuator endpoints exposed | application.properties:2 | config-scan `-cfg-004` | no |
| 10 | V4 | AWS key pair in deleted commit | `settings_old.py` (history, demo copy only) | gitleaks, trufflehog | no |
| 11 | V5 | `log4j-core 2.14.1` (direct) and tomcat, spring, jackson ... (transitive) | pom.xml:6,8 | osv-scanner (needs internet: resolves via Maven Central) | no |
| 12 | V5 | workflow findings | ci.yml:1,3,6 | zizmor | no |

## vuln_java_gradle_repo (Spring Boot, Gradle)  - files: UserController.java (same as above), SecurityConfig.java, application.yml, build.gradle, gradle.lockfile, ci.yml

| # | Cat | Bug | Where | Expected from | CodeQL needed |
|---|---|---|---|---|---|
| 1 | V1 | no ownership check on `/users/{id}/orders` | UserController.java:11 | codeql `.../java/missing-ownership-check` | yes |
| 2 | V1 | `anyRequest().permitAll()` | SecurityConfig.java:19 | config-scan `-cfg-008` | no |
| 3 | V2 | SQL injection via `executeQuery` | UserController.java:11 | codeql `java/sql-injection` | yes |
| 4 | V3 | `StandardPasswordEncoder` | SecurityConfig.java:7,14 | config-scan `-cfg-005` | no |
| 5 | V3 | CSRF disabled | SecurityConfig.java:19 | config-scan `-cfg-006` | no |
| 6 | V3 | JWT without expiration; login without rate limiting | UserController.java:17,15 | config-scan `-cfg-001`, `-cfg-007` | no |
| 7 | V3 | session timeout `7d` | application.yml:4 | config-scan `-cfg-012` | no |
| 8 | V3 | session cookie `secure: false` | application.yml:6 | config-scan `-cfg-003` | no |
| 9 | V3 | actuator `include: "*"` | application.yml:11 | config-scan `-cfg-004` | no |
| 10 | V3 | default Spring Security password in config | application.yml:15 | config-scan `-cfg-011` | no |
| 11 | V4 | AWS key pair in deleted commit | `settings_old.py` (history, demo copy only) | gitleaks, trufflehog | no |
| 12 | V5 | `log4j-core 2.14.1`, `tomcat-embed-core 9.0.46`, `spring-web 5.3.7` | gradle.lockfile:4-8 | osv-scanner (only what the lockfile lists; `build.gradle` is not read) | no |
| 13 | V5 | workflow findings | ci.yml:1,3,6 | zizmor | no |
