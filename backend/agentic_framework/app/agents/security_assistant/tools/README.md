# Security Assistant detection tools

Deterministic scanners only (no LLM). Input: a local repo path. Output: normalised `Finding`s
plus one `ToolRun` per tool (`app/agents/security_assistant/schemas.py`).

```python
result = await run_all(Path("/path/to/repo"))   # tools/runner.py
result.complete   # False if any tool failed/timed out/was unavailable: no findings != clean
```

| Category | Tools |
|---|---|
| V1, V2, V3 (code) | `codeql.py` (Python, Java, JS/TS; `--build-mode=none`) |
| V3 (config) | `config_scan.py` (in-process, Flask/Django/Express/Spring) |
| V4 | `secret_scanners.py` (Gitleaks, TruffleHog) |
| V5 deps | `dependencies.py` (OSV-Scanner, npm audit, pip-audit) |
| V5 CI/CD | `workflow_lint.py` (actionlint, zizmor) |

Check what is installed: `python -m app.agents.security_assistant.tools.check`. Scan a folder:
`python -m app.agents.security_assistant.tools.runner <path>`. Tool image: `../Dockerfile`.

Tests: `uv run pytest app/agents/security_assistant` is the fast suite; real scanners only with `-m integration` (fixtures: seeded Python, Java and JS/TS
repos; real-tool tests are skipped when a binary is missing).

Tools run one after another by default (quick ones first, CodeQL last); set
`SECURITY_ASSISTANT_MAX_PARALLEL` or pass `max_parallel` to `run_all` to run several at once.
A tool applies only to some languages, see the table below.

Rules: never run student code, no package installs/builds, fixed argv, per-tool timeout,
secrets masked before storing, raw output saved outside the repo (`SECURITY_ASSISTANT_SCAN_DIR`).
Known gaps: the custom V1 CodeQL queries are heuristics (see `queries/README.md`); on Windows
the worker's selector event loop cannot spawn subprocesses, so run scans in the Linux image.

## Which tools run for which language

| Tool | Runs for | Needs |
|---|---|---|
| codeql | Python, Java, JavaScript, TypeScript | source files |
| config-scan | Python, Java, JavaScript, TypeScript | source/config files |
| gitleaks, trufflehog | any language | files and git history |
| osv-scanner | any language it knows | a manifest or lockfile (`requirements.txt`, `pom.xml`, `package-lock.json`, `gradle.lockfile`, ...) |
| npm-audit | JavaScript, TypeScript | `package.json` + `package-lock.json` |
| pip-audit | Python | `requirements.txt` (pinned versions) |
| actionlint, zizmor | any language | `.github/workflows/*.yml` |

A tool with nothing to scan is reported as `not_applicable` with the reason. For Java, dependencies
are checked by osv-scanner only.

## Java (Spring Boot): what is covered and the limits

Python, Java and JavaScript/TypeScript are all in scope. Java support targets **Spring Boot** (Spring MVC
controllers, Spring Security, `application.properties` / `application.yml`). Plain servlets,
Jakarta EE, Micronaut and Quarkus get only the generic checks (CodeQL's standard rules, secrets,
dependencies, workflows).

**V1 (CodeQL, `queries/java-kotlin/MissingOwnershipCheck.ql`).** A controller method that passes a
`@PathVariable` / `@RequestParam` / `@RequestBody` value to a database call is reported unless it is
covered by an authorisation rule or checks the user:

| Counts as an authorisation check | Does not count |
|---|---|
| `@Secured`, `@RolesAllowed` (method or class) | `@PreAuthorize("isAuthenticated()")`, `permitAll()` |
| `@PreAuthorize` / `@PostAuthorize` with any other expression (`hasRole`, `#id == principal.id`, ...) | `anyRequest().authenticated()` in the `SecurityFilterChain` (any logged-in user can still read another user's data) |
| `SecurityFilterChain` rule `requestMatchers("/admin/**").hasRole(..)` / `hasAuthority` / `access` covering the handler path (class + method mapping), or `anyRequest().hasRole(..)` | |
| `Principal` / `Authentication` / `@AuthenticationPrincipal` parameter, `SecurityContextHolder`, `getPrincipal()` | |

**V3 / V1 (config scanner, `config_scan.py`).** `application*.properties` and `application*.yml` (nested
keys are flattened): session cookie `secure` / `http-only` off, session timeout of a day or more,
all actuator endpoints exposed, H2 console, hard-coded `spring.security.user.password`. In Java
code: weak or no-op password encoders (`NoOpPasswordEncoder`, `StandardPasswordEncoder`,
`MessageDigestPasswordEncoder`, `{noop}`, BCrypt strength < 10), CSRF disabled, JWT (jjwt) without
expiry, login route without rate limiting. Reported as V1: `anyRequest().permitAll()`, and Spring
controllers in a project with no Spring Security at all.

**Dependencies (OSV-Scanner only; `mvn` and `gradle` are never run on student code).**

| Build | What OSV-Scanner reads | Transitive dependencies | Needs internet |
|---|---|---|---|
| Maven `pom.xml` | the pom, including `<parent>` / BOM-managed versions | **Resolved** through Maven Central (deps.dev). The Spring Boot fixture: 2 declared dependencies became 18 packages and 129 advisories. | Yes. If only the registry is unreachable, the adapter retries with `--no-resolve` (declared versions only) and records this in the run note. With no network at all the run is `failed`. |
| Gradle with `gradle.lockfile` | the lockfile only | Only what the lockfile lists. A lockfile generated by Gradle includes transitives; one written by hand does not. | Yes (advisory lookup) |
| Gradle **without** `gradle.lockfile` | nothing: `build.gradle(.kts)` is not read | **Not scanned.** The run note says "Gradle dependencies NOT scanned: no gradle.lockfile"; if nothing else is scannable the run is `not_applicable`. | - |

Missing transitive dependencies therefore happen in two cases: a hand-written or outdated
`gradle.lockfile`, and a Maven run where the registry could not be reached. Both are noted on
the run (`ScanResult.warnings`) instead of being silent.

**CodeQL limitation (`--build-mode=none`, on purpose).** `mvn` / `gradle` are never run on student code, and
this was tested, not assumed. Even with `--build-mode=none`, CodeQL 2.20 *does* run build tools to collect the
dependency classpath: the repo's own `./gradlew` (when a Gradle wrapper layout exists), and any `gradle` / `mvn`
on the PATH (observed with canary scripts). Two things keep that from happening:

1. The image has no Maven, Gradle or JDK compiler (only a Java runtime, which CodeQL needs to start its
   Gradle detection).
2. `codeql.py` sets `CODEQL_EXTRACTOR_JAVA_OPTION_BUILDLESS_CLASSPATH_FROM_BUILD_FILES=false` and
   `CODEQL_EXTRACTOR_JAVA_DISABLE_GRADLE_INIT=true` for every `database create`. With these, canary
   `gradlew`, `mvnw`, `gradle` and `mvn` scripts are never executed
   (`tests/test_integration_java.py::test_codeql_never_executes_build_tools_or_wrapper_scripts`; re-run it
   after every CodeQL upgrade).

The cost: CodeQL does not see the project's libraries. Types and methods from Spring or other dependencies
are unresolved, so findings that need library models (data flow through a library call, generated code such
as Lombok or MapStruct) can be missed, and annotation values cannot be read by element name (the V1 query
matches Spring annotations by name and reads the string literals inside them). Without a JRE on the PATH, Java
extraction of Gradle projects fails (and is reported as `failed`).
