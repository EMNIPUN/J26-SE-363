# Security Assistant report: vuln_py_repo

> **INCOMPLETE RUN.** This is not a clean result.
> - stage interpret skipped: --allow-external-llm was not given: nothing was sent to any LLM
> - stage trace skipped: needs interpret
> - stage risk skipped: needs interpret
> - stage questions skipped: needs interpret

## Stages

| stage | status | detail |
|---|---|---|
| fetch | **completed** | local folder |
| scan | **completed** | reused saved findings (python_full.json); nothing was scanned now; agent loop (review, no tool can run): 1 step(s), goal met: every category is FULL or has nothing to scan, and there is no coverage gap |
| governance | **completed** | enforcing; tool allow-list ok; 4 README/commit message(s) scanned, 0 prompt-injection indicator(s) logged (an indicator, not proof) |
| interpret | **skipped** | --allow-external-llm was not given: nothing was sent to any LLM |
| trace | **skipped** | needs interpret |
| risk | **skipped** | needs interpret |
| guidance | **completed** | 10 standard fix entr(ies) apply |
| questions | **skipped** | needs interpret |

## Findings overview

| rank | group | finding | where | status | conf. | evidence | introducing commit | links | risk | probe question |
|---|---|---|---|---|---|---|---|---|---|---|
| - | G01 | V1 security-assistant/py/missing-ownership-check | app.py:22 | **not interpreted** | - | - | - | - | - | - |
| - | G02 | V2 py/sql-injection | app.py:22 | **not interpreted** | - | - | - | - | - | - |
| - | G03 | V3 security-assistant-cfg-005 | app.py:13 | **not interpreted** | - | - | - | - | - | - |
| - | G04 | V3 security-assistant-cfg-001 | app.py:14 | **not interpreted** | - | - | - | - | - | - |
| - | G05 | V3 security-assistant-cfg-003 | app.py:8 | **not interpreted** | - | - | - | - | - | - |
| - | G06 | V3 security-assistant-cfg-007 | app.py:11 | **not interpreted** | - | - | - | - | - | - |
| - | G07 | V4 aws-access-token | settings_old.py:1 | **not interpreted** | - | - | - | - | - | - |
| - | G08 | V5 PYSEC-2018-28 | requirements.txt | **not interpreted** | - | - | - | - | - | - |
| - | G09 | V5 zizmor:dangerous-triggers | .github/workflows/ci.yml:1 | **not interpreted** | - | - | - | - | - | - |
| - | G10 | V5 zizmor:unpinned-uses | .github/workflows/ci.yml:6 | **not interpreted** | - | - | - | - | - | - |

# Security scan report

- **Source:** vuln_py_repo
- **Scanned:** 2026-10-20 16:03:26 UTC
- **Languages:** python
- **Findings:** 12
- **Result:** every tool that ran finished.

## Tools

| tool | status | findings | seconds | note |
|---|---|---|---|---|
| config-scan | succeeded | 4 | 0.1 |  |
| gitleaks | succeeded | 1 | 0.6 |  |
| trufflehog | succeeded | 1 | 4.2 |  |
| osv-scanner | succeeded | 1 | 5.1 |  |
| npm-audit | not_applicable | 0 | 0.0 | no javascript/typescript files in repository |
| pip-audit | succeeded | 1 | 3.0 |  |
| actionlint | succeeded | 0 | 0.2 |  |
| zizmor | succeeded | 2 | 0.4 |  |
| codeql | succeeded | 2 | 212.0 |  |

## Coverage by category

A category with level NONE has not been checked: 0 findings there says nothing.

| category | coverage | findings | detail |
|---|---|---|---|
| V1 Broken access control | **FULL** | 1 | codeql ran |
| V2 Injection | **FULL** | 1 | codeql ran |
| V3 Authentication failures | **FULL** | 4 | codeql, config-scan ran |
| V4 Sensitive data exposure / hard-coded secrets | **FULL** | 2 | gitleaks, trufflehog ran |
| V5 Vulnerable dependencies and insecure CI/CD | **FULL** | 4 | osv-scanner, pip-audit, actionlint, zizmor ran |

## V1 Broken access control (1)

### V1.1 `security-assistant/py/missing-ownership-check` - app.py:22

- **Tool:** codeql
- **CWE:** CWE-639   **Severity (from tool):** 7.5
- **Where:** app.py:22 in `orders`
- **Message:** Route handler 'orders' uses parameter 'user_id' in a SQL query without checking the authenticated user.
- **How to fix:** Check that the logged-in user owns the record (see "How to fix" below)

```
    19 | def orders(user_id):  # V1: no check that user_id is the logged-in user
    20 |     db = sqlite3.connect("shop.db")
    21 |     name = request.args.get("name")
>   22 |     db.execute("SELECT * FROM orders WHERE user_id = " + user_id + " AND name = '" + name + "'")  # V2
    23 |     return "ok"
```


## V2 Injection (1)

### V2.1 `py/sql-injection` - app.py:22

- **Tool:** codeql
- **CWE:** CWE-89   **Severity (from tool):** 8.8
- **Where:** app.py:22
- **Message:** This SQL query depends on a user-provided value.
- **How to fix:** Use parameterised queries instead of building SQL text (see "How to fix" below)
- **Source -> sink:** app.py:21 -> app.py:22

```
    19 | def orders(user_id):  # V1: no check that user_id is the logged-in user
    20 |     db = sqlite3.connect("shop.db")
    21 |     name = request.args.get("name")
>   22 |     db.execute("SELECT * FROM orders WHERE user_id = " + user_id + " AND name = '" + name + "'")  # V2
    23 |     return "ok"
```


## V3 Authentication failures (4)

### V3.1 `security-assistant-cfg-003` - app.py:8

- **Tool:** config-scan
- **CWE:** CWE-614   **Severity (from tool):** -
- **Where:** app.py:8
- **Message:** Session cookie sent without the Secure flag
- **How to fix:** Set the Secure and HttpOnly flags on session cookies (see "How to fix" below)

```
     5 | from flask import Flask, request
     6 | 
     7 | app = Flask(__name__)
>    8 | app.config["SESSION_COOKIE_SECURE"] = False
     9 | 
    10 | 
    11 | @app.route("/login", methods=["POST"])
```

### V3.2 `security-assistant-cfg-007` - app.py:11

- **Tool:** config-scan
- **CWE:** CWE-307   **Severity (from tool):** -
- **Where:** app.py:11
- **Message:** Login route found but no rate limiting library or middleware in the repository
- **How to fix:** Limit how often the login can be tried (see "How to fix" below)

```
     8 | app.config["SESSION_COOKIE_SECURE"] = False
     9 | 
    10 | 
>   11 | @app.route("/login", methods=["POST"])
    12 | def login():
    13 |     pw = hashlib.md5(request.form["password"].encode()).hexdigest()  # V3: weak hash
    14 |     token = jwt.encode({"user": request.form["user"]}, "key", algorithm="HS256")  # V3: no exp
```

### V3.3 `security-assistant-cfg-005` - app.py:13

- **Tool:** config-scan
- **CWE:** CWE-916   **Severity (from tool):** -
- **Where:** app.py:13
- **Message:** Weak or unsalted password hashing / password encoder
- **How to fix:** Hash passwords with bcrypt or Argon2 (see "How to fix" below)

```
    10 | 
    11 | @app.route("/login", methods=["POST"])
    12 | def login():
>   13 |     pw = hashlib.md5(request.form["password"].encode()).hexdigest()  # V3: weak hash
    14 |     token = jwt.encode({"user": request.form["user"]}, "key", algorithm="HS256")  # V3: no exp
    15 |     return token
    16 | 
```

### V3.4 `security-assistant-cfg-001` - app.py:14

- **Tool:** config-scan
- **CWE:** CWE-613   **Severity (from tool):** -
- **Where:** app.py:14
- **Message:** JWT issued without an expiry
- **How to fix:** Give tokens and sessions an expiry (see "How to fix" below)

```
    11 | @app.route("/login", methods=["POST"])
    12 | def login():
    13 |     pw = hashlib.md5(request.form["password"].encode()).hexdigest()  # V3: weak hash
>   14 |     token = jwt.encode({"user": request.form["user"]}, "key", algorithm="HS256")  # V3: no exp
    15 |     return token
    16 | 
    17 | 
```


## V4 Sensitive data exposure / hard-coded secrets (2)

### V4.1 `aws-access-token` - settings_old.py:1

- **Tool:** gitleaks
- **CWE:** CWE-798   **Severity (from tool):** -
- **Where:** settings_old.py:1
- **Message:** Identified a pattern that may indicate AWS credentials
- **How to fix:** Remove the secret, rotate it, and keep secrets out of code (see "How to fix" below)
- **Source -> sink:** commit:4f2c9d1 -> -
- **Masked value:** `REDACTED`

### V4.2 `AWS` - settings_old.py:1

- **Tool:** trufflehog
- **CWE:** CWE-798   **Severity (from tool):** -
- **Where:** settings_old.py:1
- **Message:** AWS candidate
- **How to fix:** Remove the secret, rotate it, and keep secrets out of code (see "How to fix" below)
- **Source -> sink:** commit:4f2c9d1 -> -
- **Masked value:** `AK****M2`


## V5 Vulnerable dependencies and insecure CI/CD (4)

### V5.1 `PYSEC-2018-28` - requirements.txt

- **Tool:** osv-scanner
- **CWE:** CWE-1104   **Severity (from tool):** -
- **Where:** requirements.txt
- **Message:** CVE-2018-18074: Authorization header leaked on redirect
- **How to fix:** Upgrade the vulnerable package (see "How to fix" below)
- **Source -> sink:** - -> requests@2.19.0 (PyPI)

### V5.2 `PYSEC-2018-28` - requirements.txt

- **Tool:** pip-audit
- **CWE:** CWE-1104   **Severity (from tool):** -
- **Where:** requirements.txt
- **Message:** CVE-2018-18074: leak (fix: 2.20.0)
- **How to fix:** Upgrade the vulnerable package (see "How to fix" below)
- **Source -> sink:** - -> requests==2.19.0

### V5.3 `zizmor:dangerous-triggers` - .github/workflows/ci.yml:1

- **Tool:** zizmor
- **CWE:** CWE-829   **Severity (from tool):** High
- **Where:** .github/workflows/ci.yml:1
- **Message:** use of fundamentally insecure workflow trigger
- **How to fix:** Do not run untrusted pull request code with secrets (see "How to fix" below)

```
>    1 | on: pull_request_target
     2 | jobs:
     3 |   build:
     4 |     runs-on: ubuntu-latest
```

### V5.4 `zizmor:unpinned-uses` - .github/workflows/ci.yml:6

- **Tool:** zizmor
- **CWE:** CWE-829   **Severity (from tool):** Low
- **Where:** .github/workflows/ci.yml:6
- **Message:** unpinned action reference
- **How to fix:** Pin actions to a full commit SHA (see "How to fix" below)

```
     3 |   build:
     4 |     runs-on: ubuntu-latest
     5 |     steps:
>    6 |       - uses: actions/checkout@latest
     7 |         with:
     8 |           ref: ${{ github.event.pull_request.head.sha }}
     9 |       - run: ./build.sh
```


## How to fix (by type of issue)

Standard advice, written by the course team. Every finding above points to one of these. The examples are short suggestions: adapt them to your code and run your tests.

### V1: Check that the logged-in user owns the record

**Why it matters.** If the id from the URL goes straight into a query, any logged-in user (or anyone, if there is no login) can read or change other people's data by changing the number in the URL.

**How to fix it**

1. Find the query that uses the id from the request (path variable, query string or body).
2. Get the current user from the session or token, never from a value the client sends.
3. Make the query match both the id and the owner (or compare the owner to the current user), and answer 403 or 404 when it does not match.
4. Add a test: user B asks for user A's record and must be refused.

Example (python):

```
order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
```

Read more: https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html, https://cwe.mitre.org/data/definitions/639.html

Applies to: `app.py:22`

### V2: Use parameterised queries instead of building SQL text

**Why it matters.** When request input is glued into a SQL string, an attacker can add their own SQL (read, change or delete data).

**How to fix it**

1. Never build SQL with +, f-strings or string formatting from request input.
2. Put a placeholder (? or :name) in the query and pass the values separately.
3. Use an ORM's query methods where possible and validate the type of ids (for example convert to int).

Example (python):

```
db.execute("SELECT * FROM orders WHERE user_id = ? AND name = ?", (user_id, name))
```

Read more: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html, https://cwe.mitre.org/data/definitions/89.html

Applies to: `app.py:22`

### V3: Give tokens and sessions an expiry

**Why it matters.** A token without an expiry stays valid forever: if it leaks, the attacker keeps access.

**How to fix it**

1. Add an expiry claim (exp) of minutes or hours to every token you issue and check it when the token is used.
2. For sessions set a timeout of minutes to a few hours, not days.
3. Use short-lived access tokens with a separate refresh mechanism if users must stay logged in.

Example (python):

```
payload = {"user": user_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=30)}
token = jwt.encode(payload, SECRET, algorithm="HS256")
```

Read more: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html, https://cwe.mitre.org/data/definitions/613.html

Applies to: `app.py:14`

### V3: Hash passwords with bcrypt or Argon2

**Why it matters.** MD5, SHA-1 and plain SHA-256 are fast, so stolen hashes can be cracked quickly; unsalted or no-op encoders store passwords almost in plain text.

**How to fix it**

1. Use a slow password hashing function with a built-in salt: bcrypt, Argon2 or PBKDF2 from a library.
2. Never write your own hashing; do not use MD5/SHA-1 for passwords and do not use NoOpPasswordEncoder.
3. Change the stored hashes: re-hash each password the next time its user logs in.

Example (python):

```
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
ok = bcrypt.checkpw(password.encode(), hashed)
```

Read more: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html, https://cwe.mitre.org/data/definitions/916.html

Applies to: `app.py:13`

### V3: Limit how often the login can be tried

**Why it matters.** Without a limit an attacker can try thousands of passwords per minute.

**How to fix it**

1. Add rate limiting to the login route (per IP and per account).
2. Lock or slow down the account after repeated failures, and log them.

Example (python):

```
limiter = Limiter(get_remote_address, app=app)
@app.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login(): ...
```

Read more: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html, https://cwe.mitre.org/data/definitions/307.html

Applies to: `app.py:11`

### V3: Set the Secure and HttpOnly flags on session cookies

**Why it matters.** Without Secure the cookie can travel over plain HTTP; without HttpOnly a script on the page can read it.

**How to fix it**

1. Turn on Secure and HttpOnly (and SameSite) for the session cookie.
2. Use HTTPS everywhere so Secure cookies work.

Example (python):

```
app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
```

Read more: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html, https://cwe.mitre.org/data/definitions/614.html

Applies to: `app.py:8`

### V4: Remove the secret, rotate it, and keep secrets out of code

**Why it matters.** A key or password committed to Git can be found by anyone who can read the repository, and it stays in the history even after you delete the file.

**How to fix it**

1. Treat the secret as leaked: revoke or rotate it first (create a new key and disable the old one).
2. Remove it from the code and load it from an environment variable or a secret manager; add .env to .gitignore.
3. Remove it from the Git history too (git filter-repo or BFG) if it was committed, then force-push and ask others to re-clone.
4. Add a secret scanner (for example Gitleaks) as a pre-commit hook or CI step.

Example (python):

```
import os
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]   # set outside the code
```

Read more: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html, https://cwe.mitre.org/data/definitions/798.html

Applies to: `settings_old.py:1`

### V5: Do not run untrusted pull request code with secrets

**Why it matters.** pull_request_target runs with the repository's permissions and secrets. If the workflow then checks out and runs the pull request's code, a stranger's code runs with those permissions.

**How to fix it**

1. Use the pull_request trigger for workflows that build or test pull request code.
2. If pull_request_target is really needed, do not check out or run the pull request's code in it.
3. Do not pass secrets to steps that run code you do not control.

Example (ci):

```
on: pull_request            # instead of pull_request_target
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<full commit sha>
      - run: ./build.sh
```

Read more: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions, https://cwe.mitre.org/data/definitions/829.html

Applies to: `.github/workflows/ci.yml:1`

### V5: Pin actions to a full commit SHA

**Why it matters.** A reference such as @latest or @v4 can change without you noticing, so a hijacked action would run in your pipeline.

**How to fix it**

1. Replace the tag or @latest with the full commit SHA of the release you reviewed (keep the version as a comment).
2. Let Dependabot update the pinned SHA.

Example (ci):

```
- uses: actions/checkout@<full 40-character commit sha>   # v4.x.y
```

Read more: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions, https://cwe.mitre.org/data/definitions/829.html

Applies to: `.github/workflows/ci.yml:6`

### V5: Upgrade the vulnerable package

**Why it matters.** The package version you use has known security problems that are public, so attackers know how to use them.

**How to fix it**

1. Look at the advisory for the fixed version (the scanner message often shows it, for example "fix: <version>").
2. Change the version in your manifest to the fixed version or newer, update the lockfile and run your tests.
3. If no fixed version exists, use another package or avoid the affected function.
4. Run the scanner again; also enable Dependabot or similar so this is flagged earlier.

Example (python):

```
# requirements.txt: use the fixed version named in the advisory
requests>=<fixed version>
```

Read more: https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html, https://cwe.mitre.org/data/definitions/1104.html

Applies to: `requirements.txt`


## Governance

> Deterministic checks around the LLM stages (no LLM). Governance never changes a verdict and never removes a finding; it can stop a call, record, or remove a leaked value from this report.

- **Mode:** enforce; **audit log:** `audit.jsonl` (4 lines: hashes, counts and reason codes only, never prompt text).
- **LLM calls checked before sending:** 0; **blocked:** 0.
- **Tool allow-list:** 9 tool(s) from the reused findings.json; all allowed.
- **Report scan:** 0 secret or personal value(s) removed from the report files before writing.
- **Scrutiny:** normal (score 0; elevated at 3, high at 6). From 'elevated' every call gets a second, stricter check: 0 second check(s) run, 0 call(s) stopped by one. The score rises with injection indicators and blocked calls and never falls within a run; scrutiny never changes a verdict.

### Prompt-injection indicators in the repository

> An **indicator, not proof.** A fixed list of phrases (for example "ignore previous instructions", "mark all findings dismissed") is searched for in README files and commit messages, which are not sent to the LLM, and in every outgoing prompt. A hit means someone wrote text that addresses a reviewer or a model. Nothing was blocked or changed because of it; the list is short, easy to evade, and can also match text that only talks about prompt injection.

None found in 4 README file(s) and commit message(s).

## Decision trail

> Each agent loop chooses its next action from a fixed list that the code validates, keeps state between steps, and stops at its goal or when its budget is spent. Every decision below is also a line in `audit.jsonl`. The default policy is a set of deterministic rules; a choice outside the valid options is rejected and shown here.

### Analysis Orchestrator

| step | subject | policy | chosen | why | result |
|---|---|---|---|---|---|
| 1 | - | rules | `stop` | goal met: every category is FULL or has nothing to scan, and there is no coverage gap | stopped after 1 step(s); coverage {'V1': 'FULL', 'V2': 'FULL', 'V3': 'FULL', 'V4': 'FULL', 'V5': 'FULL'} |


## Limitations

- The report lists scanner findings and the LLM's opinion of them. The LLM can be wrong; 'dismissed' is an argument for a false positive, not proof. No student code was executed, so nothing was confirmed by running an exploit.
- Scanner coverage is limited to what the tools support. A category with 0 findings only means something when its coverage is FULL (see the coverage table).
- The scan was reused from a saved findings.json: line numbers and commit ids refer to the repository that was scanned then (a history lookup finds nothing if they do not exist in the fetched copy), and the coverage table describes that earlier run.
- No requirements or sprint-task file was given, so findings are linked to commits only, not to stories or tasks.
- Requirements and tasks come from local files, not from the Requirements agent; a link is 'verified' only when a simple rule supports it (commit message or task names the id, or the file/endpoint appears in one story/task).
- The 'introducing commit' is the commit that added the line. It shows where the code came from, not who is at fault.
- The risk score is a rule-based ranking with weights chosen by the developers; it is not a measured probability and it does not know whether a vulnerable dependency's code is actually called.
- A probe question is built from the flagged function with simple extraction (Python ast; text search for Java and JS/TS); it can pick the wrong function in unusual code.
- Only https://github.com repositories can be fetched. Gradle dependencies are only read with a gradle.lockfile; Maven transitive dependencies need the registry to be reachable.
