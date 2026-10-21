"""V3 configuration scanner: in-process, pattern based, never imports or executes repo files.

Covers Python (Flask/Django), JavaScript/TypeScript (Express) and Java (Spring Boot) settings:
JWT expiry, session cookie flags, debug mode, password hashing / password encoders, CSRF, login
rate limiting, and Spring Boot `application.properties` / `application.yml` and Spring Security
configuration (a few rules are access control, so they are reported as V1).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.agents.security_assistant.schemas import Category, Finding
from app.agents.security_assistant.tools.base import BaseTool, ScanContext, ScanOutput
from app.agents.security_assistant.tools.languages import walk_repo

MAX_FILE_BYTES = 1_000_000
CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java"}
CONFIG_SUFFIXES = {".properties", ".yml", ".yaml", ".env"}
BUILD_FILES = {"pom.xml", "build.gradle", "build.gradle.kts"}
RULE = "security-assistant-cfg"
V3, V1 = Category.V3, Category.V1

# (rule_id, cwe, message, regex, suffixes the rule applies to, category)
LINE_RULES = [
    (f"{RULE}-003", "CWE-614", "Session cookie sent without the Secure flag",
     re.compile(r"(SESSION_COOKIE_SECURE|CSRF_COOKIE_SECURE)[\x22\x27]?\]?\s*=\s*False|cookie\.secure\s*[=:]\s*false|secure\s*:\s*false", re.I),
     CODE_SUFFIXES | CONFIG_SUFFIXES, V3),
    (f"{RULE}-003", "CWE-1004", "Session cookie readable by scripts (HttpOnly off)",
     re.compile(r"(SESSION_COOKIE_HTTPONLY)[\x22\x27]?\]?\s*=\s*False|http-only\s*[=:]\s*false|httpOnly\s*:\s*false", re.I),
     CODE_SUFFIXES | CONFIG_SUFFIXES, V3),
    (f"{RULE}-004", "CWE-489", "Debug mode enabled or management endpoints fully exposed",
     re.compile(r"^\s*DEBUG\s*=\s*True\b|\bdebug\s*=\s*True\b|management\.endpoints\.web\.exposure\.include\s*[=:]\s*[\x22\x27]?\*|spring\.h2\.console\.enabled\s*[=:]\s*true", re.I),
     CODE_SUFFIXES | CONFIG_SUFFIXES, V3),
    (f"{RULE}-005", "CWE-916", "Weak or unsalted password hashing / password encoder",
     re.compile(r"hashlib\.(md5|sha1)\(|createHash\(\s*['\"](md5|sha1)['\"]|MessageDigest\.getInstance\(\s*\"(MD5|SHA-?1)\"|"
                r"NoOpPasswordEncoder|MessageDigestPasswordEncoder|StandardPasswordEncoder|Md4PasswordEncoder|"
                r"LdapShaPasswordEncoder|withDefaultPasswordEncoder|BCryptPasswordEncoder\(\s*[4-9]\s*\)|"
                r"\{(noop|MD5|SHA-1|sha|ldap|MD4)\}|PASSWORD_HASHERS.*(MD5|SHA1|Unsalted)", re.I),
     CODE_SUFFIXES, V3),
    (f"{RULE}-006", "CWE-352", "CSRF protection disabled",
     re.compile(r"csrf\s*\(.*(disable|ignoringRequestMatchers)|csrf\(\)\.disable|WTF_CSRF_ENABLED\s*=\s*False", re.I),
     CODE_SUFFIXES, V3),
]

# Rules that can span lines (fluent Spring Security configuration): (rule_id, cwe, message, regex, category)
TEXT_RULES = [
    (f"{RULE}-008", "CWE-862", "Spring Security allows every request without authentication (anyRequest().permitAll())",
     re.compile(r"anyRequest\(\)\s*\.\s*permitAll\(\)|requestMatchers\(\s*\"/\*\*\"\s*\)\s*\.\s*permitAll\(\)"), V1),
]

JWT_CALLS = [  # (regex for the call start, tokens that mean an expiry is set)
    (re.compile(r"\bjwt\.(?:encode|sign)\s*\("), ("exp", "expiresIn", "expires_delta")),
    (re.compile(r"\bJwts\.builder\s*\(\s*\)"), ("setExpiration", "expiration(")),
]
LOGIN_ROUTE = re.compile(r"""(route|get|post|Mapping|path|url)\s*\(\s*["'][^"']*login[^"']*["']""", re.I)
RATE_LIMIT = re.compile(r"flask_limiter|Limiter\(|django_ratelimit|ratelimit|express-rate-limit|rateLimit\(|bucket4j|Bucket4j|RateLimiter|throttle", re.I)
SPRING_CONTROLLER = re.compile(r"@(RestController|Controller)\b")
SPRING_SECURITY = re.compile(
    r"spring-boot-starter-security|spring-security|SecurityFilterChain|EnableWebSecurity|"
    r"WebSecurityConfigurerAdapter|EnableMethodSecurity|EnableGlobalMethodSecurity|PreAuthorize|@Secured|RolesAllowed")


def _call_text(text: str, start: int, limit: int = 600) -> str:
    """Text of a call from its opening parenthesis to the matching one (bounded)."""
    depth, i = 0, text.find("(", start)
    end = min(len(text), start + limit)
    for j in range(i, end):
        depth += text[j] == "("
        depth -= text[j] == ")"
        if depth == 0:
            return text[i:j + 1]
    return text[i:end]


def _builder_chain(text: str, start: int, limit: int = 800) -> str:
    """For `Jwts.builder()` the expiry is set later in the fluent chain, up to `.compact()`."""
    end = text.find(".compact()", start, start + limit)
    return text[start:end if end != -1 else start + limit]


# --- Spring Boot application.properties / application.yml -----------------------------------------
def flatten_config(path: Path, text: str) -> dict[str, str]:
    """Flatten a .properties or .yml file to {"dotted.key": "value"}. Parsed as data only."""
    flat: dict[str, str] = {}
    if path.suffix.lower() in (".yml", ".yaml"):
        try:
            docs = list(yaml.safe_load_all(text))
        except yaml.YAMLError:
            return flat

        def walk(node, prefix=""):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, f"{prefix}.{k}" if prefix else str(k))
            elif isinstance(node, list):
                flat[prefix] = ",".join(str(x) for x in node)
            elif node is not None:
                flat[prefix] = str(node)

        for doc in docs:
            walk(doc)
    else:
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line[0] in "#!" or not re.search(r"[=:]", line):
                continue
            m = re.match(r"([^=:\s]+)\s*[=:]\s*(.*)", line)
            if m:
                flat[m.group(1)] = m.group(2).strip()
    return flat


def _seconds(value: str) -> float | None:
    """Parse '30m', '2h', '1d', '1800', or ISO 'PT30M' to seconds; None if not understood."""
    v = value.strip().lower()
    m = re.fullmatch(r"(-?\d+)\s*(ms|s|m|h|d)?", v)
    if m:
        unit = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, None: 1}[m.group(2)]
        return int(m.group(1)) * unit
    m = re.fullmatch(r"p(?:(\d+)d)?(?:t(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?)?", v)
    if m and any(m.groups()):
        d, h, mi, s = (int(g or 0) for g in m.groups())
        return d * 86400 + h * 3600 + mi * 60 + s
    return None


def spring_property_findings(path: Path, rel: str, text: str) -> list[Finding]:
    """Rules on the flattened keys. Also catches the nested YAML forms line rules cannot see."""
    flat = flatten_config(path, text)
    out: list[Finding] = []

    def line_of(key: str) -> int | None:
        last = key.split(".")[-1]
        for no, ln in enumerate(text.splitlines(), 1):
            if re.match(rf"\s*({re.escape(key)}|{re.escape(last)})\s*[=:]", ln):
                return no
        return None

    def add(rule: str, cwe: str, msg: str, key: str, cat: Category = V3):
        out.append(Finding(category=cat, cwe=cwe, file_path=rel, line=line_of(key), rule_id=rule,
                           message=msg, sink=key))

    is_yaml = path.suffix.lower() in (".yml", ".yaml")
    for key, value in flat.items():
        k, v = key.lower(), value.strip().lower()
        if is_yaml:  # for .properties the line rules already cover these dotted keys
            if k.endswith("session.cookie.secure") and v == "false":
                add(f"{RULE}-003", "CWE-614", "Session cookie sent without the Secure flag", key)
            if k.endswith("session.cookie.http-only") and v == "false":
                add(f"{RULE}-003", "CWE-1004", "Session cookie readable by scripts (HttpOnly off)", key)
            if k.endswith("exposure.include") and "*" in v:
                add(f"{RULE}-004", "CWE-489", "All management endpoints are exposed", key)
            if k == "spring.h2.console.enabled" and v == "true":
                add(f"{RULE}-004", "CWE-489", "H2 database console enabled", key)
        if k == "spring.security.user.password" and v and not v.startswith("${"):
            add(f"{RULE}-011", "CWE-259", "Default Spring Security user password is set in the config file", key)
        if k == "server.servlet.session.timeout":
            secs = _seconds(v)
            if secs is not None and (secs <= 0 or secs >= 86400):
                add(f"{RULE}-012", "CWE-613", "Session timeout is a day or longer (or never expires)", key)
    return out


@dataclass
class FileResult:
    findings: list[Finding] = field(default_factory=list)
    rate_limit_hint: bool = False
    login: tuple[int, str] | None = None
    spring_controller_line: int | None = None
    spring_security_hint: bool = False


def scan_file(path: Path, rel: str) -> FileResult:
    res = FileResult()
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return res
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return res
    suffix = ".env" if path.name.startswith(".env") else path.suffix.lower()
    res.rate_limit_hint = bool(RATE_LIMIT.search(text))
    res.spring_security_hint = bool(SPRING_SECURITY.search(text))
    if path.name in BUILD_FILES:
        return res  # only used for the repo-level Spring Security check
    lines = text.splitlines()

    for rule_id, cwe, message, regex, suffixes, category in LINE_RULES:
        if suffix not in suffixes:
            continue
        for no, line in enumerate(lines, 1):
            if line.lstrip().startswith(("#", "//", "*")):
                continue
            if regex.search(line):
                res.findings.append(Finding(category=category, cwe=cwe, file_path=rel, line=no,
                                            rule_id=rule_id, message=message))

    if suffix == ".java":
        for rule_id, cwe, message, regex, category in TEXT_RULES:
            for m in regex.finditer(text):
                res.findings.append(Finding(category=category, cwe=cwe, file_path=rel,
                                            line=text.count("\n", 0, m.start()) + 1,
                                            rule_id=rule_id, message=message))
        m = SPRING_CONTROLLER.search(text)
        if m:
            res.spring_controller_line = text.count("\n", 0, m.start()) + 1

    if suffix in CODE_SUFFIXES:
        for call, expiry_tokens in JWT_CALLS:
            for m in call.finditer(text):
                body = _builder_chain(text, m.start()) if "builder" in call.pattern else _call_text(text, m.start())
                if not any(tok in body for tok in expiry_tokens):
                    no = text.count("\n", 0, m.start()) + 1
                    res.findings.append(Finding(category=V3, cwe="CWE-613", file_path=rel, line=no,
                                                rule_id=f"{RULE}-001", message="JWT issued without an expiry"))
        for no, line in enumerate(lines, 1):
            if LOGIN_ROUTE.search(line):
                res.login = (no, line.strip()[:120])
                break

    if suffix in (".properties", ".yml", ".yaml") and re.match(r"(application|bootstrap)[\w.-]*$", path.stem):
        res.findings += spring_property_findings(path, rel, text)
    return res


@dataclass
class ConfigScanTool(BaseTool):
    name: str = "config-scan"
    binary: str | None = None
    languages: frozenset[str] | None = frozenset({"python", "java", "javascript", "typescript"})

    async def scan(self, ctx: ScanContext, exe: str | None) -> ScanOutput:
        findings: list[Finding] = []
        rate_limited = spring_security = False
        first_login: tuple[str, int] | None = None
        first_controller: tuple[str, int] | None = None
        files = 0
        for directory, names in walk_repo(ctx.repo):
            for name in names:
                p = directory / name
                if p.suffix.lower() not in CODE_SUFFIXES | CONFIG_SUFFIXES and not name.startswith(".env") \
                        and name not in BUILD_FILES:
                    continue
                files += 1
                rel = p.relative_to(ctx.repo).as_posix()
                r = scan_file(p, rel)
                findings += r.findings
                rate_limited |= r.rate_limit_hint
                spring_security |= r.spring_security_hint
                if r.login and first_login is None:
                    first_login = (rel, r.login[0])
                if r.spring_controller_line and first_controller is None:
                    first_controller = (rel, r.spring_controller_line)
        if first_login and not rate_limited:
            findings.append(Finding(category=V3, cwe="CWE-307", file_path=first_login[0], line=first_login[1],
                                    rule_id=f"{RULE}-007",
                                    message="Login route found but no rate limiting library or middleware in the repository"))
        if first_controller and not spring_security:
            findings.append(Finding(category=V1, cwe="CWE-306", file_path=first_controller[0],
                                    line=first_controller[1], rule_id=f"{RULE}-013",
                                    message="Spring controllers found but no Spring Security (dependency, filter chain "
                                            "or method security): every endpoint is public"))
        raw = "\n".join(f"{f.rule_id} {f.file_path}:{f.line}" for f in findings)
        return ScanOutput(findings, raw or f"scanned {files} files, no findings", 0, rule_pack_version="security-assistant-cfg-2")
