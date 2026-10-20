# Security Assistant report: vuln_py_repo

> All stages completed. Read the limitations below before relying on the result.

## Stages

| stage | status | detail |
|---|---|---|
| fetch | **completed** | local folder |
| scan | **completed** | reused saved findings (python_full.json); nothing was scanned now; agent loop (review, no tool can run): 1 step(s), goal met: every category is FULL or has nothing to scan, and there is no coverage gap |
| governance | **completed** | enforcing; tool allow-list ok; 4 README/commit message(s) scanned, 0 prompt-injection indicator(s) logged (an indicator, not proof) |
| interpret | **completed** | 10 call(s): confirmed 12, dismissed 0, uncertain 0 |
| trace | **completed** | 9/10 with an introducing commit; links 17 verified, 0 candidate |
| risk | **completed** | 10 ranked, 0 dismissed (not ranked) |
| guidance | **completed** | 10 standard fix entr(ies) apply |
| questions | **completed** | 10 finding(s): 6 closed, 4 escalated to lecturer review, 27 question(s) asked (MOCK TUTOR) |

## Findings overview

| rank | group | finding | where | status | conf. | evidence | introducing commit | links | risk | probe question |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | G02 | V2 py/sql-injection | app.py:22 | **confirmed** | 0.8 | E1 | `1555c03` C-961f654c | T-101 (verified), US-01 (verified) | 90.5 | closed after 2 question(s) (last score 0.74, MOCK) |
| 2 | G01 | V1 security-assistant/py/missing-ownership-check | app.py:22 | **confirmed** | 0.8 | E1 | `1555c03` C-961f654c | T-101 (verified), US-01 (verified), US-02 (verified) | 90.5 | escalated after 3 question(s) (last score 0.64, MOCK) |
| 3 | G09 | V5 zizmor:dangerous-triggers | .github/workflows/ci.yml:1 | **confirmed** | 0.8 | E1 | `30266a6` C-961f654c | T-105 (verified) | 87.5 | escalated after 3 question(s) (last score 0.60, MOCK) |
| 4 | G04 | V3 security-assistant-cfg-001 | app.py:14 | **confirmed** | 0.8 | E1 | `1555c03` C-961f654c | T-101 (verified), US-01 (verified) | 71.0 | closed after 3 question(s) (last score 0.72, MOCK) |
| 5 | G05 | V3 security-assistant-cfg-003 | app.py:8 | **confirmed** | 0.8 | E1 | `1555c03` C-961f654c | T-101 (verified), US-01 (verified) | 71.0 | escalated after 3 question(s) (last score 0.60, MOCK) |
| 6 | G06 | V3 security-assistant-cfg-007 | app.py:11 | **confirmed** | 0.8 | E1 | `1555c03` C-961f654c | T-101 (verified), US-01 (verified) | 71.0 | closed after 3 question(s) (last score 0.81, MOCK) |
| 7 | G07 | V4 aws-access-token | settings_old.py:1 | **confirmed** | 0.8 | E1 | - | - | 70.0 | closed after 1 question(s) (last score 0.70, MOCK) |
| 8 | G03 | V3 security-assistant-cfg-005 | app.py:13 | **confirmed** | 0.8 | E1 | `1555c03` C-961f654c | T-101 (verified), US-01 (verified) | 69.5 | closed after 3 question(s) (last score 0.83, MOCK) |
| 9 | G08 | V5 PYSEC-2018-28 | requirements.txt | **confirmed** | 0.8 | E1 | `1555c03` C-961f654c | T-101 (verified), US-01 (verified) | 68.0 | escalated after 3 question(s) (last score 0.69, MOCK) |
| 10 | G10 | V5 zizmor:unpinned-uses | .github/workflows/ci.yml:6 | **confirmed** | 0.8 | E1 | `30266a6` C-961f654c | T-105 (verified) | 62.0 | closed after 3 question(s) (last score 0.72, MOCK) |

# Security scan report

- **Source:** vuln_py_repo
- **Scanned:** 2026-10-20 14:53:36 UTC
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


<!-- llm-interpretation -->
## LLM interpretation

> The LLM judges findings that a scanner already reported; it cannot add findings. Its answers are opinions to review, not scanner output: **dismissed** means the model argued for a false positive.

- **Model:** mock-model  **Prompt:** interpreter-v4  **Calls:** 10 (delay 0.0 s, retries 2)

| scanner-only findings | confirmed | dismissed | uncertain | not analysed |
|---|---|---|---|---|
| 12 | 12 | 0 | 0 | 0 |

Uncertain because: LLM error 0, output rejected 0, downgraded (missing or fake evidence id, or an unsupported secret dismissal) 0, stopped by governance before sending 0, the model said uncertain 0. Counts are findings: a call about a package answers for every advisory of it.

### Merged and grouped before the calls

| what | package | detail |
|---|---|---|
| same place reported by several tools | settings_old.py:1 | kept gitleaks:aws-access-token, merged trufflehog:AWS |
| same advisory and package reported by several tools | requests | kept osv-scanner:PYSEC-2018-28, merged pip-audit:PYSEC-2018-28 |
| grouped per package | requests | 2 finding(s), advisories PYSEC-2018-28 |

### Results

| group | category | rule | where | status | conf. | evidence | rationale |
|---|---|---|---|---|---|---|---|
| G01 | V1 | security-assistant/py/missing-ownership-check | app.py:22 | **confirmed** | 0.80 | E1 | the evidence shows it |
| G02 | V2 | py/sql-injection | app.py:22 | **confirmed** | 0.80 | E1 | the evidence shows it |
| G03 | V3 | security-assistant-cfg-005 | app.py:13 | **confirmed** | 0.80 | E1 | the evidence shows it |
| G04 | V3 | security-assistant-cfg-001 | app.py:14 | **confirmed** | 0.80 | E1 | the evidence shows it |
| G05 | V3 | security-assistant-cfg-003 | app.py:8 | **confirmed** | 0.80 | E1 | the evidence shows it |
| G06 | V3 | security-assistant-cfg-007 | app.py:11 | **confirmed** | 0.80 | E1 | the evidence shows it |
| G07 | V4 | aws-access-token | settings_old.py:1 (+1 merged) | **confirmed** | 0.80 | E1 | the evidence shows it |
| G08 | V5 | PYSEC-2018-28 | requests (2 findings) | **confirmed** | 0.80 | E1 | the evidence shows it |
| G09 | V5 | zizmor:dangerous-triggers | .github/workflows/ci.yml:1 | **confirmed** | 0.80 | E1 | the evidence shows it |
| G10 | V5 | zizmor:unpinned-uses | .github/workflows/ci.yml:6 | **confirmed** | 0.80 | E1 | the evidence shows it |

### How to fix the confirmed findings

The standard advice for each type of issue is in the section "How to fix (by type of issue)" above. The text below is a note the LLM wrote for this code: a suggestion to review and test, not a finished patch.

**G01 `security-assistant/py/missing-ownership-check` - app.py:22** (standard advice: Check that the logged-in user owns the record)

_The model gave no tailored advice; use the standard advice._

**G02 `py/sql-injection` - app.py:22** (standard advice: Use parameterised queries instead of building SQL text)

_The model gave no tailored advice; use the standard advice._

**G03 `security-assistant-cfg-005` - app.py:13** (standard advice: Hash passwords with bcrypt or Argon2)

_The model gave no tailored advice; use the standard advice._

**G04 `security-assistant-cfg-001` - app.py:14** (standard advice: Give tokens and sessions an expiry)

_The model gave no tailored advice; use the standard advice._

**G05 `security-assistant-cfg-003` - app.py:8** (standard advice: Set the Secure and HttpOnly flags on session cookies)

_The model gave no tailored advice; use the standard advice._

**G06 `security-assistant-cfg-007` - app.py:11** (standard advice: Limit how often the login can be tried)

_The model gave no tailored advice; use the standard advice._

**G07 `aws-access-token` - settings_old.py:1** (standard advice: Remove the secret, rotate it, and keep secrets out of code)

_The model gave no tailored advice; use the standard advice._

**G08 `PYSEC-2018-28` - requirements.txt** (standard advice: Upgrade the vulnerable package)

_The model gave no tailored advice; use the standard advice._

**G09 `zizmor:dangerous-triggers` - .github/workflows/ci.yml:1** (standard advice: Do not run untrusted pull request code with secrets)

_The model gave no tailored advice; use the standard advice._

**G10 `zizmor:unpinned-uses` - .github/workflows/ci.yml:6** (standard advice: Pin actions to a full commit SHA)

_The model gave no tailored advice; use the standard advice._


<!-- traceability -->
## Traceability

> Each confirmed finding is traced to its *introducing commit* (the commit that added the line, found read-only with `git log -L`). This says where the code came from, not who is at fault: a contributor appears only as a pseudonymous id. A link is **verified** only when a rule supports it (commit message or task names the id, or the file/endpoint appears in exactly one story or task); links the model proposed are **candidates** to confirm.

Link proposals by `mock-model` (trace-v1), checked by rules afterwards.

- **Confirmed findings:** 10; with an introducing commit 9, without 1
- **Links:** 17 verified, 0 candidate, 0 rejected

| group | finding | introducing commit | contributor | links | notes |
|---|---|---|---|---|---|
| G01 | security-assistant/py/missing-ownership-check app.py:22 | `1555c03` 2026-10-20 T-101 US-01: login and orders | C-961f654c | task T-101 **verified** (commit_message_reference, 0.95)<br>story US-01 **verified** (commit_message_reference, task_linked_story, 0.95)<br>story US-02 **verified** (file_or_endpoint_mentioned, 0.70) | 'orders' appears in 2 tasks (T-101, T-102): too vague to verify |
| G02 | py/sql-injection app.py:22 | `1555c03` 2026-10-20 T-101 US-01: login and orders | C-961f654c | task T-101 **verified** (commit_message_reference, file_or_endpoint_mentioned, 0.95)<br>story US-01 **verified** (commit_message_reference, task_linked_story, 0.95) | - |
| G03 | security-assistant-cfg-005 app.py:13 | `1555c03` 2026-10-20 T-101 US-01: login and orders | C-961f654c | task T-101 **verified** (commit_message_reference, file_or_endpoint_mentioned, 0.95)<br>story US-01 **verified** (commit_message_reference, task_linked_story, 0.95) | - |
| G04 | security-assistant-cfg-001 app.py:14 | `1555c03` 2026-10-20 T-101 US-01: login and orders | C-961f654c | task T-101 **verified** (commit_message_reference, file_or_endpoint_mentioned, 0.95)<br>story US-01 **verified** (commit_message_reference, task_linked_story, 0.95) | - |
| G05 | security-assistant-cfg-003 app.py:8 | `1555c03` 2026-10-20 T-101 US-01: login and orders | C-961f654c | task T-101 **verified** (commit_message_reference, file_or_endpoint_mentioned, 0.95)<br>story US-01 **verified** (commit_message_reference, task_linked_story, 0.95) | - |
| G06 | security-assistant-cfg-007 app.py:11 | `1555c03` 2026-10-20 T-101 US-01: login and orders | C-961f654c | task T-101 **verified** (commit_message_reference, file_or_endpoint_mentioned, 0.95)<br>story US-01 **verified** (commit_message_reference, task_linked_story, 0.95) | - |
| G07 | aws-access-token settings_old.py:1 | none found | - | - | no matching story; no introducing commit found: the line has no history in this repository |
| G08 | PYSEC-2018-28 requirements.txt | `1555c03` 2026-10-20 T-101 US-01: login and orders | C-961f654c | task T-101 **verified** (commit_message_reference, 0.95)<br>story US-01 **verified** (commit_message_reference, task_linked_story, 0.95) | - |
| G09 | zizmor:dangerous-triggers .github/workflows/ci.yml:1 | `30266a6` 2026-10-20 T-105: add CI workflow | C-961f654c | task T-105 **verified** (commit_message_reference, 0.95) | no matching story |
| G10 | zizmor:unpinned-uses .github/workflows/ci.yml:6 | `30266a6` 2026-10-20 T-105: add CI workflow | C-961f654c | task T-105 **verified** (commit_message_reference, 0.95) | no matching story |

<!-- risk-prioritisation -->
## Risk prioritisation

> A rule-based ranking, no LLM scoring. Score = 100 x sum of (weight x factor); the table shows each contribution, so the breakdown adds up to the score. Dismissed findings are not ranked; uncertain ones count with a lower weight. It helps to choose what to fix first; it is not a measured probability.

Weights: severity 0.3, category 0.15, llm_status 0.2, llm_confidence 0.1, exposure 0.15, presence 0.1.

| # | group | finding | where | status | score | severity | category | llm_status | llm_confidence | exposure | presence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | G02 | V2 py/sql-injection | app.py:22 | confirmed | **90.50** | 24.00 | 15.00 | 20.00 | 8.00 | 13.50 | 10.00 |
| 2 | G01 | V1 security-assistant/py/missing-ownership-check | app.py:22 | confirmed | **90.50** | 24.00 | 15.00 | 20.00 | 8.00 | 13.50 | 10.00 |
| 3 | G09 | V5 zizmor:dangerous-triggers | .github/workflows/ci.yml:1 | confirmed | **87.50** | 24.00 | 10.50 | 20.00 | 8.00 | 15.00 | 10.00 |
| 4 | G04 | V3 security-assistant-cfg-001 | app.py:14 | confirmed | **71.00** | 12.00 | 12.00 | 20.00 | 8.00 | 9.00 | 10.00 |
| 5 | G05 | V3 security-assistant-cfg-003 | app.py:8 | confirmed | **71.00** | 12.00 | 12.00 | 20.00 | 8.00 | 9.00 | 10.00 |
| 6 | G06 | V3 security-assistant-cfg-007 | app.py:11 | confirmed | **71.00** | 12.00 | 12.00 | 20.00 | 8.00 | 9.00 | 10.00 |
| 7 | G07 | V4 aws-access-token | settings_old.py:1 | confirmed | **70.00** | 12.00 | 13.50 | 20.00 | 8.00 | 10.50 | 6.00 |
| 8 | G03 | V3 security-assistant-cfg-005 | app.py:13 | confirmed | **69.50** | 12.00 | 12.00 | 20.00 | 8.00 | 7.50 | 10.00 |
| 9 | G08 | V5 PYSEC-2018-28 | requirements.txt | confirmed | **68.00** | 12.00 | 10.50 | 20.00 | 8.00 | 7.50 | 10.00 |
| 10 | G10 | V5 zizmor:unpinned-uses | .github/workflows/ci.yml:6 | confirmed | **62.00** | 6.00 | 10.50 | 20.00 | 8.00 | 7.50 | 10.00 |

### Why each finding scored as it did

**#1 G02 py/sql-injection** (score 90.50)
- severity: 0.8 x 0.3 -> 24.00 (tool severity 8.8)
- category: 1 x 0.15 -> 15.00 (category V2)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 0.9 x 0.15 -> 13.50 (request input reaches a query)
- presence: 1 x 0.1 -> 10.00 (found by scanning the current files)

**#2 G01 security-assistant/py/missing-ownership-check** (score 90.50)
- severity: 0.8 x 0.3 -> 24.00 (tool severity 7.5)
- category: 1 x 0.15 -> 15.00 (category V1)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 0.9 x 0.15 -> 13.50 (a request handler any logged-in user can reach)
- presence: 1 x 0.1 -> 10.00 (found by scanning the current files)

**#3 G09 zizmor:dangerous-triggers** (score 87.50)
- severity: 0.8 x 0.3 -> 24.00 (tool severity 'high')
- category: 0.7 x 0.15 -> 10.50 (category V5)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 1 x 0.15 -> 15.00 (the workflow can be triggered by outside contributors)
- presence: 1 x 0.1 -> 10.00 (found by scanning the current files)

**#4 G04 security-assistant-cfg-001** (score 71.00)
- severity: 0.4 x 0.3 -> 12.00 (the tool gave no usable severity)
- category: 0.8 x 0.15 -> 12.00 (category V3)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 0.6 x 0.15 -> 9.00 (needs a stolen token first)
- presence: 1 x 0.1 -> 10.00 (found by scanning the current files)

**#5 G05 security-assistant-cfg-003** (score 71.00)
- severity: 0.4 x 0.3 -> 12.00 (the tool gave no usable severity)
- category: 0.8 x 0.15 -> 12.00 (category V3)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 0.6 x 0.15 -> 9.00 (needs a network or script attacker)
- presence: 1 x 0.1 -> 10.00 (found by scanning the current files)

**#6 G06 security-assistant-cfg-007** (score 71.00)
- severity: 0.4 x 0.3 -> 12.00 (the tool gave no usable severity)
- category: 0.8 x 0.15 -> 12.00 (category V3)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 0.6 x 0.15 -> 9.00 (the login is reachable by anyone)
- presence: 1 x 0.1 -> 10.00 (found by scanning the current files)

**#7 G07 aws-access-token** (score 70.00)
- severity: 0.4 x 0.3 -> 12.00 (the tool gave no usable severity (highest of the group))
- category: 0.9 x 0.15 -> 13.50 (category V4)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 0.7 x 0.15 -> 10.50 (anyone with the repository can read it)
- presence: 0.6 x 0.1 -> 6.00 (the file is not in the current files)

**#8 G03 security-assistant-cfg-005** (score 69.50)
- severity: 0.4 x 0.3 -> 12.00 (the tool gave no usable severity)
- category: 0.8 x 0.15 -> 12.00 (category V3)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 0.5 x 0.15 -> 7.50 (matters only after the database leaks)
- presence: 1 x 0.1 -> 10.00 (found by scanning the current files)

**#9 G08 PYSEC-2018-28** (score 68.00)
- severity: 0.4 x 0.3 -> 12.00 (the tool gave no usable severity (highest of the group))
- category: 0.7 x 0.15 -> 10.50 (category V5)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 0.5 x 0.15 -> 7.50 (reachability of the vulnerable code is not known)
- presence: 1 x 0.1 -> 10.00 (found by scanning the current files)

**#10 G10 zizmor:unpinned-uses** (score 62.00)
- severity: 0.2 x 0.3 -> 6.00 (tool severity 'low')
- category: 0.7 x 0.15 -> 10.50 (category V5)
- llm_status: 1 x 0.2 -> 20.00 (the model judged it confirmed)
- llm_confidence: 0.8 x 0.1 -> 8.00 (the model's confidence in its own status)
- exposure: 0.5 x 0.15 -> 7.50 (needs a compromised third-party action)
- presence: 1 x 0.1 -> 10.00 (found by scanning the current files)


<!-- probe-questions -->
## Probe questions and comprehension check

> **MOCK TUTOR (simulated; no student answered and nothing was graded)**
>
> One question per confirmed finding, built from the student's own code; none states the fix. A finding is closed only when the comprehension score reaches the threshold (0.7). Closed means the student showed they understand the problem; not that the code was fixed. Below the threshold the agent asks a follow-up from a different angle (a higher hint level, never the fix), up to 2 time(s), and then escalates the finding to lecturer review.

- **Findings:** 10; closed 6, escalated to lecturer review 4; 27 question(s) asked

### G01 V1 app.py:22

**Attempt 1 (hint level 0)** - In `orders` (app.py:22), `user_id` comes from the request. Suppose two different customers, A and B, are both logged in and A types B's identifier into the address. Walk through the code line by line: what does it return, and which line, if any, tells A apart from B?

Score 0.34 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 2 (hint level 1)** - Start from `user_id` in `orders` (app.py:22). Where does its value come from, which line first uses it to pick the data that is returned, and what does the code know about who is asking at that line?

Score 0.49 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 3 (hint level 2)** - Answer in three short parts about app.py:22: (1) which value does an outsider control, (2) which line uses it first, (3) what is the worst thing that could happen with a value they choose, and why does nothing in this code get in the way?

Score 0.64 (threshold 0.7) -> open - simulated by the mock Tutor

```
     18  @app.route("/users/<user_id>/orders")
     19  def orders(user_id):  # V1: no check that user_id is the logged-in user
     20      db = sqlite3.connect("shop.db")
     21      name = request.args.get("name")
>>   22      db.execute("SELECT * FROM orders WHERE user_id = " + user_id + " AND name = '" + name + "'")  # V2
     23      return "ok"
```

**Result: escalated** - 3 attempt(s), last score 0.64 below 0.7; the limit of 2 follow-up(s) is reached

### G02 V2 app.py:22

**Attempt 1 (hint level 0)** - On app.py:22, the text of a database query is put together in `orders` using `user_id`. If that value contained a quote character followed by more SQL, what exactly would the database receive? Which part of the statement could the person typing it change?

Score 0.59 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 2 (hint level 1)** - Find the line in `orders` where the query text is assembled (app.py:22). Which pieces come from `user_id` and which are text you typed in the code? Write the final text the database would receive for the input O'Brien, and then for the input ' OR '1'='1.

Score 0.74 (threshold 0.7) -> closed - simulated by the mock Tutor

```
     18  @app.route("/users/<user_id>/orders")
     19  def orders(user_id):  # V1: no check that user_id is the logged-in user
     20      db = sqlite3.connect("shop.db")
     21      name = request.args.get("name")
>>   22      db.execute("SELECT * FROM orders WHERE user_id = " + user_id + " AND name = '" + name + "'")  # V2
     23      return "ok"
```

**Result: closed**

### G03 V3 app.py:13

**Attempt 1 (hint level 0)** - app.py:13 stores a value derived from the password. If an attacker got a copy of the stored values and could try a billion guesses per second, what could they learn, and how long would it take? Explain your reasoning about the function used here.

Score 0.53 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 2 (hint level 1)** - Name the function used at app.py:13. What do you know about how fast it is, and whether two identical passwords give the same stored value? What does that mean for someone holding a copy of the stored values?

Score 0.68 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 3 (hint level 2)** - Answer in three short parts about app.py:13: (1) which value does an outsider control, (2) which line uses it first, (3) what is the worst thing that could happen with a value they choose, and why does nothing in this code get in the way?

Score 0.83 (threshold 0.7) -> closed - simulated by the mock Tutor

```
     11  @app.route("/login", methods=["POST"])
     12  def login():
>>   13      pw = hashlib.md5(request.form["password"].encode()).hexdigest()  # V3: weak hash
     14      token = jwt.encode({"user": request.form["user"]}, "key", algorithm="HS256")  # V3: no exp
     15      return token
```

**Result: closed**

### G04 V3 app.py:14

**Attempt 1 (hint level 0)** - A token is created at app.py:14. Suppose one is stolen on Monday. Using only this code, until when can the thief use it, and who or what could stop them?

Score 0.42 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 2 (hint level 1)** - List every claim or setting that the token at app.py:14 carries. Does any of them limit how long it keeps working? What would you expect to find in the token if a limit existed?

Score 0.57 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 3 (hint level 2)** - Answer in three short parts about app.py:14: (1) which value does an outsider control, (2) which line uses it first, (3) what is the worst thing that could happen with a value they choose, and why does nothing in this code get in the way?

Score 0.72 (threshold 0.7) -> closed - simulated by the mock Tutor

```
     11  @app.route("/login", methods=["POST"])
     12  def login():
     13      pw = hashlib.md5(request.form["password"].encode()).hexdigest()  # V3: weak hash
>>   14      token = jwt.encode({"user": request.form["user"]}, "key", algorithm="HS256")  # V3: no exp
     15      return token
```

**Result: closed**

### G05 V3 app.py:8

**Attempt 1 (hint level 0)** - app.py:8 configures how the browser handles the session. Describe an attack by a malicious web page or a person on the same Wi-Fi that this configuration allows. What would the victim see?

Score 0.30 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 2 (hint level 1)** - Write down each browser-side setting at app.py:8 with its name and value. For each one, what could a script on the page or someone watching the network do because of that setting?

Score 0.45 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 3 (hint level 2)** - Answer in three short parts about app.py:8: (1) which value does an outsider control, (2) which line uses it first, (3) what is the worst thing that could happen with a value they choose, and why does nothing in this code get in the way?

Score 0.60 (threshold 0.7) -> open - simulated by the mock Tutor

```
      3  
      4  import jwt
      5  from flask import Flask, request
      6  
      7  app = Flask(__name__)
>>    8  app.config["SESSION_COOKIE_SECURE"] = False
      9  
     10  
     11  @app.route("/login", methods=["POST"])
     12  def login():
     13      pw = hashlib.md5(request.form["password"].encode()).hexdigest()  # V3: weak hash
```

**Result: escalated** - 3 attempt(s), last score 0.60 below 0.7; the limit of 2 follow-up(s) is reached

### G06 V3 app.py:11

**Attempt 1 (hint level 0)** - this code (app.py:11) accepts login attempts. How many passwords per minute could one person try against one account with this code, and what in the code would slow them down?

Score 0.51 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 2 (hint level 1)** - Count the lines in this code (app.py:11) between a request arriving and the password being compared. Is there anything there that remembers earlier attempts from the same person?

Score 0.66 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 3 (hint level 2)** - Answer in three short parts about app.py:11: (1) which value does an outsider control, (2) which line uses it first, (3) what is the worst thing that could happen with a value they choose, and why does nothing in this code get in the way?

Score 0.81 (threshold 0.7) -> closed - simulated by the mock Tutor

```
      6  
      7  app = Flask(__name__)
      8  app.config["SESSION_COOKIE_SECURE"] = False
      9  
     10  
>>   11  @app.route("/login", methods=["POST"])
     12  def login():
     13      pw = hashlib.md5(request.form["password"].encode()).hexdigest()  # V3: weak hash
     14      token = jwt.encode({"user": request.form["user"]}, "key", algorithm="HS256")  # V3: no exp
     15      return token
     16  
```

**Result: closed**

### G07 V4 settings_old.py:1

**Attempt 1 (hint level 0)** - the value on that line (settings_old.py:1) is written in the code. Who can read it today, including people who only have an old copy of the repository, and what could they do with it?

Score 0.70 (threshold 0.7) -> closed - simulated by the mock Tutor

**Result: closed**

### G08 V5 requirements.txt

**Attempt 1 (hint level 0)** - The project depends on requests (requirements.txt). Which of your features call into it, and what would an attacker gain if that package had a flaw that runs code when it reads their input?

Score 0.39 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 2 (hint level 1)** - Open requirements.txt and find the exact version of requests. Which of its functions does your code call, and with data that comes from where?

Score 0.54 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 3 (hint level 2)** - Answer in three short parts about requirements.txt: (1) which value does an outsider control, (2) which line uses it first, (3) what is the worst thing that could happen with a value they choose, and why does nothing in this code get in the way?

Score 0.69 (threshold 0.7) -> open - simulated by the mock Tutor

**Result: escalated** - 3 attempt(s), last score 0.69 below 0.7; the limit of 2 follow-up(s) is reached

### G09 V5 .github/workflows/ci.yml:1

**Attempt 1 (hint level 0)** - .github/workflows/ci.yml:1 defines an automated workflow. Who can start it, which secrets or token permissions does it have while it runs, and what could a stranger's pull request make it do?

Score 0.30 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 2 (hint level 1)** - List the events that start the workflow at .github/workflows/ci.yml:1 and the secrets it can read. Who can trigger each event?

Score 0.45 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 3 (hint level 2)** - Answer in three short parts about .github/workflows/ci.yml:1: (1) which value does an outsider control, (2) which line uses it first, (3) what is the worst thing that could happen with a value they choose, and why does nothing in this code get in the way?

Score 0.60 (threshold 0.7) -> open - simulated by the mock Tutor

```
>>    1  on: pull_request_target
      2  jobs:
      3    build:
      4      runs-on: ubuntu-latest
      5      steps:
      6        - uses: actions/checkout@latest
```

**Result: escalated** - 3 attempt(s), last score 0.60 below 0.7; the limit of 2 follow-up(s) is reached

### G10 V5 .github/workflows/ci.yml:6

**Attempt 1 (hint level 0)** - .github/workflows/ci.yml:6 defines an automated workflow. Who can start it, which secrets or token permissions does it have while it runs, and what could a stranger's pull request make it do?

Score 0.42 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 2 (hint level 1)** - List the events that start the workflow at .github/workflows/ci.yml:6 and the secrets it can read. Who can trigger each event?

Score 0.57 (threshold 0.7) -> open - simulated by the mock Tutor

**Attempt 3 (hint level 2)** - Answer in three short parts about .github/workflows/ci.yml:6: (1) which value does an outsider control, (2) which line uses it first, (3) what is the worst thing that could happen with a value they choose, and why does nothing in this code get in the way?

Score 0.72 (threshold 0.7) -> closed - simulated by the mock Tutor

```
      1  on: pull_request_target
      2  jobs:
      3    build:
      4      runs-on: ubuntu-latest
      5      steps:
>>    6        - uses: actions/checkout@latest
      7          with:
      8            ref: ${{ github.event.pull_request.head.sha }}
      9        - run: ./build.sh
```

**Result: closed**


## Governance

> Deterministic checks around the LLM stages (no LLM). Governance never changes a verdict and never removes a finding; it can stop a call, record, or remove a leaked value from this report.

- **Mode:** enforce; **audit log:** `audit.jsonl` (89 lines: hashes, counts and reason codes only, never prompt text).
- **LLM calls checked before sending:** 16; **blocked:** 0.
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

### Question Generation

| step | subject | policy | chosen | why | result |
|---|---|---|---|---|---|
| 1 | G01 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.34 -> open |
| 2 | G01 | rules | `ask_followup:level 1` | score 0.34 is below 0.7; a follow-up from a different angle (hint level 1); it never states the fix | attempt 2: score 0.49 -> open |
| 3 | G01 | rules | `ask_followup:level 2` | score 0.49 is below 0.7; a follow-up from a different angle (hint level 2); it never states the fix | attempt 3: score 0.64 -> open |
| 4 | G01 | rules | `escalate_to_lecturer` | 3 attempt(s), last score 0.64 below 0.7; the limit of 2 follow-up(s) is reached | escalated to lecturer review |
| 5 | G02 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.59 -> open |
| 6 | G02 | rules | `ask_followup:level 1` | score 0.59 is below 0.7; a follow-up from a different angle (hint level 1); it never states the fix | attempt 2: score 0.74 -> closed |
| 7 | G02 | rules | `close_finding` | score 0.74 reached the threshold 0.7 on attempt 2 | closed after 2 attempt(s) |
| 8 | G03 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.53 -> open |
| 9 | G03 | rules | `ask_followup:level 1` | score 0.53 is below 0.7; a follow-up from a different angle (hint level 1); it never states the fix | attempt 2: score 0.68 -> open |
| 10 | G03 | rules | `ask_followup:level 2` | score 0.68 is below 0.7; a follow-up from a different angle (hint level 2); it never states the fix | attempt 3: score 0.83 -> closed |
| 11 | G03 | rules | `close_finding` | score 0.83 reached the threshold 0.7 on attempt 3 | closed after 3 attempt(s) |
| 12 | G04 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.42 -> open |
| 13 | G04 | rules | `ask_followup:level 1` | score 0.42 is below 0.7; a follow-up from a different angle (hint level 1); it never states the fix | attempt 2: score 0.57 -> open |
| 14 | G04 | rules | `ask_followup:level 2` | score 0.57 is below 0.7; a follow-up from a different angle (hint level 2); it never states the fix | attempt 3: score 0.72 -> closed |
| 15 | G04 | rules | `close_finding` | score 0.72 reached the threshold 0.7 on attempt 3 | closed after 3 attempt(s) |
| 16 | G05 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.30 -> open |
| 17 | G05 | rules | `ask_followup:level 1` | score 0.30 is below 0.7; a follow-up from a different angle (hint level 1); it never states the fix | attempt 2: score 0.45 -> open |
| 18 | G05 | rules | `ask_followup:level 2` | score 0.45 is below 0.7; a follow-up from a different angle (hint level 2); it never states the fix | attempt 3: score 0.60 -> open |
| 19 | G05 | rules | `escalate_to_lecturer` | 3 attempt(s), last score 0.60 below 0.7; the limit of 2 follow-up(s) is reached | escalated to lecturer review |
| 20 | G06 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.51 -> open |
| 21 | G06 | rules | `ask_followup:level 1` | score 0.51 is below 0.7; a follow-up from a different angle (hint level 1); it never states the fix | attempt 2: score 0.66 -> open |
| 22 | G06 | rules | `ask_followup:level 2` | score 0.66 is below 0.7; a follow-up from a different angle (hint level 2); it never states the fix | attempt 3: score 0.81 -> closed |
| 23 | G06 | rules | `close_finding` | score 0.81 reached the threshold 0.7 on attempt 3 | closed after 3 attempt(s) |
| 24 | G07 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.70 -> closed |
| 25 | G07 | rules | `close_finding` | score 0.70 reached the threshold 0.7 on attempt 1 | closed after 1 attempt(s) |
| 26 | G08 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.39 -> open |
| 27 | G08 | rules | `ask_followup:level 1` | score 0.39 is below 0.7; a follow-up from a different angle (hint level 1); it never states the fix | attempt 2: score 0.54 -> open |
| 28 | G08 | rules | `ask_followup:level 2` | score 0.54 is below 0.7; a follow-up from a different angle (hint level 2); it never states the fix | attempt 3: score 0.69 -> open |
| 29 | G08 | rules | `escalate_to_lecturer` | 3 attempt(s), last score 0.69 below 0.7; the limit of 2 follow-up(s) is reached | escalated to lecturer review |
| 30 | G09 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.30 -> open |
| 31 | G09 | rules | `ask_followup:level 1` | score 0.30 is below 0.7; a follow-up from a different angle (hint level 1); it never states the fix | attempt 2: score 0.45 -> open |
| 32 | G09 | rules | `ask_followup:level 2` | score 0.45 is below 0.7; a follow-up from a different angle (hint level 2); it never states the fix | attempt 3: score 0.60 -> open |
| 33 | G09 | rules | `escalate_to_lecturer` | 3 attempt(s), last score 0.60 below 0.7; the limit of 2 follow-up(s) is reached | escalated to lecturer review |
| 34 | G10 | rules | `ask_question:level 0` | the first question, from the scenario angle | attempt 1: score 0.42 -> open |
| 35 | G10 | rules | `ask_followup:level 1` | score 0.42 is below 0.7; a follow-up from a different angle (hint level 1); it never states the fix | attempt 2: score 0.57 -> open |
| 36 | G10 | rules | `ask_followup:level 2` | score 0.57 is below 0.7; a follow-up from a different angle (hint level 2); it never states the fix | attempt 3: score 0.72 -> closed |
| 37 | G10 | rules | `close_finding` | score 0.72 reached the threshold 0.7 on attempt 3 | closed after 3 attempt(s) |

### Governance

| step | subject | policy | chosen | why | result |
|---|---|---|---|---|---|
| 1 | 72587de3c009 | rules | `allow_call` | no check failed | sent |
| 2 | 6b461cb4f593 | rules | `allow_call` | no check failed | sent |
| 3 | c708d8b16a27 | rules | `allow_call` | no check failed | sent |
| 4 | 0bfbc5bfe698 | rules | `allow_call` | no check failed | sent |
| 5 | 2ff24efad703 | rules | `allow_call` | no check failed | sent |
| 6 | 2f7e05128120 | rules | `allow_call` | no check failed | sent |
| 7 | 642ab42d7c1d | rules | `allow_call` | no check failed | sent |
| 8 | 6361782962f3 | rules | `allow_call` | no check failed | sent |
| 9 | 3d37bcfbe4f8 | rules | `allow_call` | no check failed | sent |
| 10 | 5aadf05183c1 | rules | `allow_call` | no check failed | sent |
| 11 | 72587de3c009 | rules | `allow_call` | no check failed | sent |
| 12 | 6b461cb4f593 | rules | `allow_call` | no check failed | sent |
| 13 | c708d8b16a27 | rules | `allow_call` | no check failed | sent |
| 14 | 642ab42d7c1d | rules | `allow_call` | no check failed | sent |
| 15 | 6361782962f3 | rules | `allow_call` | no check failed | sent |
| 16 | 3d37bcfbe4f8 | rules | `allow_call` | no check failed | sent |


## Limitations

- The report lists scanner findings and the LLM's opinion of them. The LLM can be wrong; 'dismissed' is an argument for a false positive, not proof. No student code was executed, so nothing was confirmed by running an exploit.
- Scanner coverage is limited to what the tools support. A category with 0 findings only means something when its coverage is FULL (see the coverage table).
- The scan was reused from a saved findings.json: line numbers and commit ids refer to the repository that was scanned then (a history lookup finds nothing if they do not exist in the fetched copy), and the coverage table describes that earlier run.
- Requirements and tasks come from local files, not from the Requirements agent; a link is 'verified' only when a simple rule supports it (commit message or task names the id, or the file/endpoint appears in one story/task).
- The 'introducing commit' is the commit that added the line. It shows where the code came from, not who is at fault.
- The risk score is a rule-based ranking with weights chosen by the developers; it is not a measured probability and it does not know whether a vulnerable dependency's code is actually called.
- The Tutor is a MOCK: no student was asked and no answer was graded. The comprehension scores and the closed/open decisions are simulated and only demonstrate the flow.
- A probe question is built from the flagged function with simple extraction (Python ast; text search for Java and JS/TS); it can pick the wrong function in unusual code.
- Only https://github.com repositories can be fetched. Gradle dependencies are only read with a gradle.lockfile; Maven transitive dependencies need the registry to be reachable.
