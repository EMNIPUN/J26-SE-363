// Frontend-only mock evidence for the AEGIS Security module.
// Shape mirrors the finding-record schema from the security subsystem's
// project definition (Section 9): category, evidence, traceability,
// risk score, fix pattern and probe question. Backend integration will
// replace this file with real scanner + LLM output via securityService.js.

export const CATEGORY_OPTIONS = [
  { value: 'access-control', label: 'Access control', owasp: 'OWASP A01', cwe: 'CWE-862' },
  { value: 'injection', label: 'Injection', owasp: 'OWASP A03', cwe: 'CWE-89' },
  { value: 'authentication', label: 'Authentication', owasp: 'OWASP A07', cwe: 'CWE-287' },
  { value: 'secrets', label: 'Secrets/sensitive data', owasp: 'OWASP A02', cwe: 'CWE-798' },
  { value: 'dependencies', label: 'Dependencies & CI/CD', owasp: 'CICD-SEC', cwe: 'CWE-1104' },
]

export const STATUS_LABELS = {
  open: 'Open',
  review: 'Awaiting review',
  learning: 'Awaiting learning check',
  closed: 'Closed',
}

export const PRIORITY_TONE = {
  Critical: 'destructive',
  High: 'destructive',
  Medium: 'warning',
  Low: 'success',
}

export const INITIAL_FINDINGS = [
  {
    id: 'auth-otp-bypass',
    category: 'authentication',
    status: 'open',
    priority: 'Critical',
    owasp: 'A07:2021 – Identification and Authentication Failures',
    cwe: 'CWE-287 (Improper Authentication)',
    cvss: 9.8,
    cvssVector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
    detector: 'CodeQL + configuration-file scanner',
    detectionMethod: 'Static data-flow tracing of the async control path',
    confidence: 'Confirmed',
    confidenceValue: 0.97,
    title: 'Password reset bypass via unawaited promise truthiness',
    endpoint: 'POST /user/reset-password',
    file: 'Backend/src/controllers/userManagement/UserData.js',
    line: 153,
    code: [
      'const IsOTPValidated = async (email) => { ... }',
      '',
      "if (IsOTPValidated(email)) { // unawaited async call is always truthy",
      '  const user = await User.findOne({ email })',
      '  user.password = await bcrypt.hash(password, 10)',
      '  await user.save()',
      '}',
    ],
    vulnerableLine: 2,
    explanation:
      'IsOTPValidated is async and returns a Promise. Called without await, the Promise object itself is truthy, so the reset branch runs on every request regardless of whether an OTP was ever verified.',
    whyItMatters:
      'Any unauthenticated caller can overwrite any account password without ever receiving a valid OTP, which is a full authentication bypass and account-takeover path.',
    context: {
      linked: true,
      requirement: 'US-04 — Reset password with OTP verification',
      commit: '9f31ac2',
      sprintTask: 'Sprint 3 — Password recovery flow',
      contributor: 'introducing-commit-3',
    },
    riskScore: 98,
    learningPriority: 'High',
    before: `const IsOTPValidated = async (email) => {
  const otpBuffer = await OTPBuffer.findOne({ email })
  if (!otpBuffer) return false
  return otpBuffer.validated
}

export const ResetPassword = async (req, res) => {
  const { email, password } = req.body
  if (IsOTPValidated(email)) {           // BUG: missing await
    const user = await User.findOne({ email })
    user.password = await bcrypt.hash(password, 10)
    await user.save()
    res.status(200).json({ message: 'Password reset successful' })
  }
}`,
    after: `const IsOTPValidated = async (email) => {
  const otpBuffer = await OTPBuffer.findOne({ email })
  if (!otpBuffer) return false
  return Boolean(otpBuffer.validated)
}

export const ResetPassword = async (req, res) => {
  const { email, password } = req.body
  if (!email || !password || password.length < 8) {
    return res.status(400).json({ message: 'Invalid request.' })
  }

  const isValidated = await IsOTPValidated(email)      // FIX: awaited
  if (!isValidated) {
    return res.status(403).json({ message: 'OTP not verified or expired.' })
  }

  const user = await User.findOne({ email })
  if (!user) return res.status(404).json({ message: 'User not found' })

  user.password = await bcrypt.hash(password, 10)
  await user.save()
  await OTPBuffer.deleteOne({ email })                 // FIX: single-use token

  res.status(200).json({ message: 'Password reset successful.' })
}`,
    probeQuestion:
      'Why does calling an async function without await let the "if" branch run even when validation should fail?',
    verification: null,
  },
  {
    id: 'sql-injection-search',
    category: 'injection',
    status: 'review',
    priority: 'Critical',
    owasp: 'A03:2021 – Injection',
    cwe: 'CWE-89 (SQL Injection)',
    cvss: 9.1,
    cvssVector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N',
    detector: 'CodeQL taint-tracking',
    detectionMethod: 'Source-to-sink taint analysis (request param -> execute())',
    confidence: 'Confirmed',
    confidenceValue: 0.94,
    title: 'Unsanitised query parameter reaches raw SQL execute()',
    endpoint: 'GET /search',
    file: 'Backend/src/controllers/catalog/SearchController.js',
    line: 42,
    code: [
      "const q = req.query.q",
      "const sql = `SELECT * FROM products WHERE name LIKE '%${q}%'`",
      'const rows = await db.execute(sql)',
    ],
    vulnerableLine: 1,
    explanation:
      'The search term is concatenated directly into a SQL string instead of using a parameterised query, so any SQL metacharacters in q are executed against the database.',
    whyItMatters:
      'An externally reachable, unauthenticated endpoint with a database sink is a high-value target — an attacker can read, modify, or exfiltrate the entire product/order tables.',
    context: {
      linked: true,
      requirement: 'US-12 — Search products',
      commit: 'c14e7a0',
      sprintTask: 'Sprint 4 — Catalog search',
      contributor: 'introducing-commit-7',
    },
    riskScore: 92,
    learningPriority: 'High',
    before: `const q = req.query.q
const sql = \`SELECT * FROM products WHERE name LIKE '%\${q}%'\`
const rows = await db.execute(sql)`,
    after: `const q = req.query.q ?? ''
const rows = await db.execute(
  'SELECT * FROM products WHERE name LIKE ?',
  [\`%\${q}%\`],
)`,
    probeQuestion:
      'Why does parameter binding stop this attack when input-length validation alone would not?',
    verification: null,
  },
  {
    id: 'env-secret-leak',
    category: 'secrets',
    status: 'learning',
    priority: 'High',
    owasp: 'A02:2021 – Cryptographic Failures',
    cwe: 'CWE-798 (Use of Hard-coded Credentials)',
    cvss: 7.5,
    cvssVector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N',
    detector: 'Gitleaks (full history) + TruffleHog (entropy)',
    detectionMethod: 'Regex + Shannon-entropy secret scanning of Git history',
    confidence: 'Confirmed',
    confidenceValue: 0.89,
    title: 'Live SMTP credential committed to repository history',
    endpoint: null,
    file: 'Backend/.env.production.bak',
    line: 6,
    code: [
      'SMTP_HOST=smtp.selvia-platform.dev',
      'SMTP_USER=notifications@selvia-platform.dev',
      'SMTP_PASS=Kx7!mPq2v_Live',
    ],
    vulnerableLine: 2,
    explanation:
      'A backup env file containing a live SMTP password was committed. Gitleaks confirmed the pattern matched a real credential format, and the string is still reachable in Git history even though the file was later deleted.',
    whyItMatters:
      'Anyone who clones the repository can read this credential from history and send mail as the platform, enabling phishing against students and staff.',
    context: {
      linked: false,
      requirement: null,
      commit: '5b2af91',
      sprintTask: null,
      contributor: 'introducing-commit-2',
    },
    riskScore: 74,
    learningPriority: 'Medium',
    before: `# Backend/.env.production.bak (committed by mistake)
SMTP_HOST=smtp.selvia-platform.dev
SMTP_USER=notifications@selvia-platform.dev
SMTP_PASS=Kx7!mPq2v_Live`,
    after: `# Removed from the repository and history (git filter-repo).
# Runtime value now injected via the deployment secret manager:
SMTP_PASS=\${SECRET_MANAGER:smtp_pass}`,
    probeQuestion:
      'Why is deleting the file in a later commit not enough to remove this secret from the repository?',
    verification: null,
  },
  {
    id: 'missing-owner-check',
    category: 'access-control',
    status: 'open',
    priority: 'High',
    owasp: 'A01:2021 – Broken Access Control',
    cwe: 'CWE-862 (Missing Authorization)',
    cvss: 8.2,
    cvssVector: 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N',
    detector: 'CodeQL custom query (IDOR pattern)',
    detectionMethod: 'Route-handler vs. resource-owner comparison analysis',
    confidence: 'Confirmed',
    confidenceValue: 0.91,
    title: 'Order endpoint returns any user’s data without an ownership check',
    endpoint: 'GET /orders/:id',
    file: 'Backend/src/controllers/orders/OrderController.js',
    line: 28,
    code: [
      'export const GetOrder = async (req, res) => {',
      '  const order = await Order.findById(req.params.id)',
      '  res.status(200).json(order)',
      '}',
    ],
    vulnerableLine: 1,
    explanation:
      'The handler fetches an order purely by its ID and never compares req.user.id against the order’s owner, so a signed-in user can view any other user’s order by guessing sequential IDs.',
    whyItMatters:
      'This is an Insecure Direct Object Reference: authenticated attackers can enumerate and read other customers’ order and address data.',
    context: {
      linked: true,
      requirement: 'US-19 — View my order history',
      commit: 'a7601de',
      sprintTask: 'Sprint 5 — Orders module',
      contributor: 'introducing-commit-9',
    },
    riskScore: 85,
    learningPriority: 'High',
    before: `export const GetOrder = async (req, res) => {
  const order = await Order.findById(req.params.id)
  res.status(200).json(order)
}`,
    after: `export const GetOrder = async (req, res) => {
  const order = await Order.findById(req.params.id)
  if (!order || order.userId.toString() !== req.user.id) {
    return res.status(404).json({ message: 'Order not found' })
  }
  res.status(200).json(order)
}`,
    probeQuestion:
      'Why does returning 404 (instead of 403) for a mismatched owner reduce information leakage here?',
    verification: null,
  },
  {
    id: 'vulnerable-dependency',
    category: 'dependencies',
    status: 'closed',
    priority: 'Medium',
    owasp: 'A03:2025 – Software Supply Chain',
    cwe: 'CWE-1104 (Use of Unmaintained Third-Party Components)',
    cvss: 6.5,
    cvssVector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:L',
    detector: 'OSV-Scanner / npm audit',
    detectionMethod: 'Dependency manifest CVE lookup + reachability check',
    confidence: 'Confirmed',
    confidenceValue: 0.86,
    title: 'lodash 4.17.15 pulls in a known prototype-pollution CVE',
    endpoint: null,
    file: 'Backend/package.json',
    line: 34,
    code: ['"lodash": "^4.17.15"'],
    vulnerableLine: 0,
    explanation:
      'The pinned lodash range resolves to a version affected by CVE-2020-8203. The vulnerable merge/defaultsDeep path is reachable from the config-merging utility used at startup.',
    whyItMatters:
      'Prototype pollution in a startup-time utility can let crafted input alter object prototypes application-wide, leading to denial of service or logic bypass.',
    context: {
      linked: true,
      requirement: 'NFR-02 — Dependencies kept free of known critical/high CVEs',
      commit: 'e02f118',
      sprintTask: 'Sprint 6 — Dependency remediation',
      contributor: 'introducing-commit-1',
    },
    riskScore: 58,
    learningPriority: 'Low',
    before: `"lodash": "^4.17.15"`,
    after: `"lodash": "^4.17.21"`,
    probeQuestion: 'Why does a transitive dependency need a reachability check, not just a version bump?',
    verification: {
      taught: 'Semantic-version ranges can silently resolve to CVE-affected releases; reachability, not just presence, drives real risk.',
      checkResult: 'Passed on first attempt (score 4/4)',
      outcome: 'Confirmed the fixed range and explained why reachability mattered for this specific call path.',
    },
  },
  {
    id: 'unpinned-workflow-action',
    category: 'dependencies',
    status: 'open',
    priority: 'Medium',
    owasp: 'OWASP Top 10 CI/CD Security Risks',
    cwe: 'CWE-937 (Component with Known Vulnerabilities, CI/CD)',
    cvss: 6.0,
    cvssVector: 'CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:C/C:L/I:H/A:N',
    detector: 'GitHub Actions workflow linter',
    detectionMethod: 'Static analysis of workflow YAML against the OWASP CI/CD checklist',
    confidence: 'Likely',
    confidenceValue: 0.72,
    title: 'Workflow runs an unpinned @latest action with write permissions',
    endpoint: null,
    file: '.github/workflows/deploy.yml',
    line: 11,
    code: [
      'permissions: write-all',
      'jobs:',
      '  deploy:',
      '    steps:',
      '      - uses: some-org/deploy-action@latest',
    ],
    vulnerableLine: 4,
    explanation:
      'The workflow grants write-all permissions and pins a third-party action to @latest rather than a commit SHA, so a compromised upstream release would execute with repository write access on the next run.',
    whyItMatters:
      'This is a supply-chain foothold: whoever controls the referenced action effectively controls the repository’s CI environment and secrets.',
    context: {
      linked: false,
      requirement: null,
      commit: '2d99b6a',
      sprintTask: 'Sprint 2 — CI/CD pipeline setup',
      contributor: 'introducing-commit-4',
    },
    riskScore: 61,
    learningPriority: 'Medium',
    before: `permissions: write-all
jobs:
  deploy:
    steps:
      - uses: some-org/deploy-action@latest`,
    after: `permissions:
  contents: read
  deployments: write
jobs:
  deploy:
    steps:
      - uses: some-org/deploy-action@a1b2c3d4e5f6...   # pinned to a commit SHA`,
    probeQuestion:
      'Why does pinning to a commit SHA protect you in a way that pinning to a version tag does not?',
    verification: null,
  },
]
