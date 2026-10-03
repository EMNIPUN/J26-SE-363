// Centralised mock data for the Adaptive AI Tutor.
//
// Every value the Tutor UI displays originates here and is served through
// services/mockApi.js. Components must never import this file directly —
// they go through services/tutorApi.js so the mock layer can be swapped for
// the FastAPI backend without touching the UI.
//
// Shapes mirror the planned backend payloads. Derived values (gaps, gap
// status, suggestions, recommendations, updated competency) are produced by
// the mock API, standing in for the backend; React only displays them.

// ---------------------------------------------------------------------------
// Concepts
// ---------------------------------------------------------------------------

export const concepts = {
  'rest-api': {
    id: 'rest-api',
    name: 'REST API',
    description: 'Designing resource-oriented HTTP endpoints with correct methods and status codes.',
  },
  authentication: {
    id: 'authentication',
    name: 'Authentication',
    description: 'Verifying who a user is before granting access to the system.',
  },
  jwt: {
    id: 'jwt',
    name: 'JWT',
    description: 'JSON Web Tokens: compact, signed tokens that carry identity claims between parties.',
  },
  authorization: {
    id: 'authorization',
    name: 'Authorization',
    description: 'Deciding what an authenticated user is allowed to do, e.g. role-based access.',
  },
  'token-validation': {
    id: 'token-validation',
    name: 'Token Validation',
    description: 'Checking a token’s signature, expiry and claims before trusting it.',
  },
}

// ---------------------------------------------------------------------------
// Project context
// ---------------------------------------------------------------------------

export const tutorContext = {
  project: {
    id: 'proj-ecommerce',
    name: 'E-Commerce System',
    description: 'A full-stack online store with product catalogue, cart, checkout and user accounts.',
  },
  sprint: {
    id: 'sprint-3',
    number: 3,
    name: 'Authentication & Authorization',
    goal: 'Secure the API so only authenticated users can access protected resources.',
    startDate: '2026-09-28',
    endDate: '2026-10-09',
  },
  task: {
    id: 'task-jwt-auth',
    title: 'Implement JWT Authentication',
    description:
      'Issue a signed JWT on login and protect the /orders and /cart routes with middleware that validates the token.',
    status: 'in_progress',
    priority: 'high',
    projectRelevance: 'high',
    dueDate: '2026-10-06',
  },
}

// ---------------------------------------------------------------------------
// Competency model
// ---------------------------------------------------------------------------

// `required` is the competency the current task demands; `current` is the
// student's estimated competency from learning evidence.
export const conceptCompetencies = [
  { conceptId: 'rest-api', required: 70, current: 82 },
  { conceptId: 'authentication', required: 75, current: 68 },
  { conceptId: 'jwt', required: 80, current: 42 },
  { conceptId: 'authorization', required: 70, current: 61 },
  { conceptId: 'token-validation', required: 80, current: 38 },
]

export const competencySummary = {
  confidence: 81,
  updatedAt: '2026-10-01T09:15:00+05:30',
  evidence: {
    total: 7,
    breakdown: [
      { type: 'lesson', label: 'Lessons', count: 3 },
      { type: 'quiz', label: 'Quizzes', count: 2 },
      { type: 'exercise', label: 'Exercises', count: 1 },
      { type: 'commit', label: 'Commits', count: 1 },
    ],
  },
}

// Thresholds the mock "backend" uses to classify gaps.
export const gapPolicy = {
  majorGapMin: 15,
}

// Competency bands the mock "backend" uses to pick a resource level.
export const levelPolicy = {
  beginnerBelow: 50,
  intermediateBelow: 75,
}

// Why the Tutor orders learning material the way it does at each level.
export const levelGuidance = {
  beginner: 'You are building the foundations, so introductory material comes first.',
  intermediate: 'You know the basics, so material on applying them and common mistakes comes first.',
  advanced: 'You already meet the basics, so in-depth material comes first.',
}

// What the Tutor suggests for each gap status. `kinds` are activity kinds
// from the external learning platform, in suggestion order.
export const suggestionPolicy = {
  major_gap: {
    kinds: ['learning', 'exercise', 'quiz'],
    includeWebResources: true,
    summary:
      'Major gap: start with the learning material, then practise with coding exercises and adaptive quizzes.',
  },
  moderate_gap: {
    kinds: ['quiz', 'exercise'],
    includeWebResources: false,
    summary:
      'Small gap: you already know the basics, so adaptive quizzes and coding exercises are enough to close it.',
  },
  sufficient: {
    kinds: ['quiz'],
    challengeOnly: true,
    includeWebResources: false,
    summary: 'No action needed: you already meet the requirement. Try the optional challenge if you want to go further.',
  },
}

// ---------------------------------------------------------------------------
// External learning platform (reached by the backend through MCP)
// ---------------------------------------------------------------------------

// `mockLaunchPath` points at the stand-in app in public/mock-learning-app.
// The real backend returns an absolute launch URL for each activity instead.
export const externalPlatform = {
  name: 'Learning Lab',
  mockLaunchPath: '/mock-learning-app/index.html',
}

// Activity catalogue the external platform exposes. `mockResult` is what the
// platform would report on completion: an overall score, per-concept scores
// (defaulting to the overall score for the activity's concept) and the
// competency gain the backend's model derives from them.
export const externalActivities = [
  // JWT
  {
    id: 'act-jwt-fundamentals',
    conceptId: 'jwt',
    kind: 'learning',
    title: 'JWT Fundamentals',
    summary: 'What a JWT is, why stateless authentication is useful, and where tokens fit in a REST API.',
    level: 'beginner',
    estimatedMinutes: 10,
    initialProgress: 100,
    mockResult: { score: 90, competencyGain: { jwt: 6 } },
  },
  {
    id: 'act-jwt-token-structure',
    conceptId: 'jwt',
    kind: 'learning',
    title: 'JWT Token Structure',
    summary: 'The header, payload and signature, and what each standard claim means.',
    level: 'beginner',
    estimatedMinutes: 12,
    initialProgress: 60,
    mockResult: { score: 88, competencyGain: { jwt: 8 } },
  },
  {
    id: 'act-jwt-implementation',
    conceptId: 'jwt',
    kind: 'learning',
    title: 'JWT Implementation',
    summary: 'End-to-end: issuing tokens on login and protecting Express routes with middleware.',
    level: 'advanced',
    estimatedMinutes: 25,
    mockResult: {
      score: 85,
      conceptScores: { jwt: 88, 'token-validation': 78 },
      competencyGain: { jwt: 8, 'token-validation': 4 },
    },
  },
  {
    id: 'act-ex-jwt-middleware',
    conceptId: 'jwt',
    kind: 'exercise',
    title: 'Implement JWT validation middleware',
    summary: 'Protect /orders and /cart with middleware that validates the Bearer token.',
    level: 'intermediate',
    estimatedMinutes: 30,
    itemCount: 5,
    mockResult: {
      score: 80,
      conceptScores: { jwt: 84, 'token-validation': 70 },
      competencyGain: { jwt: 12, 'token-validation': 6 },
    },
  },
  {
    id: 'act-quiz-jwt',
    conceptId: 'jwt',
    kind: 'quiz',
    title: 'JWT Adaptive Quiz',
    summary: 'Token structure, signing and claims. Questions adapt to your answers.',
    level: 'intermediate',
    estimatedMinutes: 8,
    itemCount: 6,
    mockResult: {
      score: 76,
      conceptScores: { jwt: 76, 'token-validation': 64 },
      competencyGain: { jwt: 10, 'token-validation': 4 },
    },
  },

  // Token Validation
  {
    id: 'act-signature-validation',
    conceptId: 'token-validation',
    kind: 'learning',
    title: 'Signature Validation',
    summary: 'How the server proves a token was not tampered with, and how to keep the secret safe.',
    level: 'intermediate',
    estimatedMinutes: 15,
    mockResult: { score: 90, competencyGain: { 'token-validation': 8 } },
  },
  {
    id: 'act-token-expiration',
    conceptId: 'token-validation',
    kind: 'learning',
    title: 'Token Expiration',
    summary: 'Using the exp claim, handling expired tokens, and when to introduce refresh tokens.',
    level: 'beginner',
    estimatedMinutes: 12,
    mockResult: { score: 92, competencyGain: { 'token-validation': 8 } },
  },
  {
    id: 'act-ex-token-errors',
    conceptId: 'token-validation',
    kind: 'exercise',
    title: 'Handle expired and tampered tokens',
    summary: 'Return the right 401 responses for expired, malformed and badly signed tokens.',
    level: 'intermediate',
    estimatedMinutes: 20,
    itemCount: 4,
    mockResult: { score: 75, competencyGain: { 'token-validation': 12 } },
  },
  {
    id: 'act-quiz-token-validation',
    conceptId: 'token-validation',
    kind: 'quiz',
    title: 'Token Validation Adaptive Quiz',
    summary: 'Signature checks, expiry and claim validation. Questions adapt to your answers.',
    level: 'intermediate',
    estimatedMinutes: 8,
    itemCount: 6,
    mockResult: { score: 70, competencyGain: { 'token-validation': 10 } },
  },

  // Authorization
  {
    id: 'act-rbac-basics',
    conceptId: 'authorization',
    kind: 'learning',
    title: 'Role-Based Access Control',
    summary: 'Roles, permissions and deny-by-default checks on every request.',
    level: 'beginner',
    estimatedMinutes: 12,
    mockResult: { score: 90, competencyGain: { authorization: 6 } },
  },
  {
    id: 'act-ex-role-middleware',
    conceptId: 'authorization',
    kind: 'exercise',
    title: 'Restrict admin routes by role',
    summary: 'Write middleware that returns 403 unless req.user has the admin role.',
    level: 'intermediate',
    estimatedMinutes: 20,
    itemCount: 4,
    mockResult: { score: 85, competencyGain: { authorization: 10 } },
  },
  {
    id: 'act-quiz-authorization',
    conceptId: 'authorization',
    kind: 'quiz',
    title: 'Authorization Adaptive Quiz',
    summary: '401 vs 403, role checks and access rules. Questions adapt to your answers.',
    level: 'intermediate',
    estimatedMinutes: 6,
    itemCount: 5,
    mockResult: { score: 80, competencyGain: { authorization: 5 } },
  },

  // Authentication
  {
    id: 'act-login-flow',
    conceptId: 'authentication',
    kind: 'learning',
    title: 'Secure Login Flow',
    summary: 'Password hashing, login error messages and issuing a token after a successful login.',
    level: 'beginner',
    estimatedMinutes: 12,
    mockResult: { score: 90, competencyGain: { authentication: 5 } },
  },
  {
    id: 'act-ex-login-endpoint',
    conceptId: 'authentication',
    kind: 'exercise',
    title: 'Build the login endpoint',
    summary: 'Verify the password with bcrypt and return a signed JWT from POST /auth/login.',
    level: 'intermediate',
    estimatedMinutes: 25,
    itemCount: 5,
    mockResult: {
      score: 85,
      conceptScores: { authentication: 88, jwt: 74 },
      competencyGain: { authentication: 8, jwt: 4 },
    },
  },
  {
    id: 'act-quiz-authentication',
    conceptId: 'authentication',
    kind: 'quiz',
    title: 'Authentication Adaptive Quiz',
    summary: 'Credentials, hashing and login responses. Questions adapt to your answers.',
    level: 'intermediate',
    estimatedMinutes: 6,
    itemCount: 5,
    mockResult: { score: 82, competencyGain: { authentication: 4 } },
  },

  // Optional challenges, suggested once a concept is sufficient
  {
    id: 'act-quiz-jwt-challenge',
    conceptId: 'jwt',
    kind: 'quiz',
    title: 'JWT Challenge Quiz',
    summary: 'Algorithm choice, key rotation and token revocation for students who meet the requirement.',
    level: 'advanced',
    estimatedMinutes: 8,
    itemCount: 6,
    challenge: true,
    mockResult: { score: 85, competencyGain: { jwt: 3 } },
  },
  {
    id: 'act-quiz-token-validation-challenge',
    conceptId: 'token-validation',
    kind: 'quiz',
    title: 'Token Validation Challenge Quiz',
    summary: 'Algorithm confusion attacks, clock skew and audience checks.',
    level: 'advanced',
    estimatedMinutes: 8,
    itemCount: 6,
    challenge: true,
    mockResult: { score: 85, competencyGain: { 'token-validation': 3 } },
  },
  {
    id: 'act-quiz-authorization-challenge',
    conceptId: 'authorization',
    kind: 'quiz',
    title: 'Authorization Challenge Quiz',
    summary: 'Resource ownership checks, permission hierarchies and access-control pitfalls.',
    level: 'advanced',
    estimatedMinutes: 8,
    itemCount: 6,
    challenge: true,
    mockResult: { score: 85, competencyGain: { authorization: 3 } },
  },
  {
    id: 'act-quiz-authentication-challenge',
    conceptId: 'authentication',
    kind: 'quiz',
    title: 'Authentication Challenge Quiz',
    summary: 'Brute-force protection, account enumeration and secure password reset flows.',
    level: 'advanced',
    estimatedMinutes: 8,
    itemCount: 6,
    challenge: true,
    mockResult: { score: 85, competencyGain: { authentication: 3 } },
  },
  {

    id: 'act-quiz-rest-challenge',
    conceptId: 'rest-api',
    kind: 'quiz',
    title: 'REST API Challenge Quiz',
    summary: 'Status codes, idempotency and resource design for experienced students.',
    level: 'advanced',
    estimatedMinutes: 8,
    itemCount: 6,
    challenge: true,
    mockResult: { score: 88, competencyGain: { 'rest-api': 3 } },
  },
]

// ---------------------------------------------------------------------------
// Adaptive recommendation wording
// ---------------------------------------------------------------------------

// Templates the mock "backend" fills in when it chooses the next activity.
// Placeholders: {concept}, {current}, {required}, {platform}.
export const recommendationText = {
  summary: {
    learning: 'Study this material in {platform} before you practise {concept}.',
    exercise: 'Apply {concept} directly to the kind of code your current task needs.',
    quiz: 'A short adaptive quiz will measure exactly what you still need for {concept}.',
  },
  reasons: {
    largestGap: '{concept} has the largest gap for your current task ({current}% of {required}%)',
    major_gap: 'It is a major gap, so the Tutor suggests learning material, exercises and quizzes',
    moderate_gap: 'It is a small gap, so practice is enough and no new material is needed',
    learning: 'You have not finished this learning material yet',
    exercise: 'Hands-on practice builds the application skills your task needs',
    quiz: 'An adaptive quiz adjusts to your answers and finds what is still missing',
    evidence: 'Your result in {platform} will update your competency and knowledge gap',
  },
  actionLabel: {
    learning: 'Start Learning',
    exercise: 'Start Exercise',
    quiz: 'Start Quiz',
  },
}

// Activity kind names the Tutor uses in chat context ("Recommended: …").
export const activityKindLabels = {
  learning: 'Learning Material',
  exercise: 'Coding Exercise',
  quiz: 'Adaptive Quiz',
}

// ---------------------------------------------------------------------------
// Adaptive learning loop
// ---------------------------------------------------------------------------

// Wording for each step of the loop the mock "backend" reports. Placeholders
// are filled from live state; see getLearningLoop in services/mockApi.js.
export const learningLoopText = {
  task: { label: 'Current Task' },
  required: { label: 'Required Knowledge', detail: '{count} concepts for this task' },
  competency: { label: 'Competency', detail: 'Confidence {confidence}%' },
  gaps: {
    label: 'Knowledge Gaps',
    detail: '{major} major · {moderate} small',
    noneDetail: 'All requirements met',
  },
  recommendation: { label: 'Recommendation', noneDetail: 'No action needed' },
  learning: { label: 'Learning' },
  exercise: { label: 'Practice' },
  quiz: { label: 'Quiz' },
  kindDetail: '{done} of {total} done · {concept}',
  kindSkipped: 'Not needed for a small gap',
  kindNone: 'Nothing to do right now',
  evidence: { label: 'New Evidence', detail: '{total} pieces of evidence', pendingDetail: 'Comes from your next result' },
  updated: { label: 'Updated Competency', detail: '{concept} {before}% → {after}%', pendingDetail: 'After your first result' },
  next: { label: 'New Recommendation', detail: 'Recalculated from your updated gaps', pendingDetail: 'After your first result' },
}

// Message the Tutor adds to the chat when an activity result arrives.
export const resultChatText = {
  content: 'You finished “{title}” in {platform} with a score of {score}%. {changes}',
  change: '{concept} went from {before}% to {after}%',
  next: 'Next, I recommend “{title}” to keep closing your {concept} gap.',
  done: 'You now meet every requirement for this task. Nice work!',
}

// ---------------------------------------------------------------------------
// Tutor conversation
// ---------------------------------------------------------------------------

// Message `context` omits the competency value on purpose: the mock API
// fills it from the student's live competency so it stays correct after
// new assessment evidence.

export const initialConversation = [
  {
    id: 'msg-001',
    role: 'tutor',
    content:
      'Hi! I can see you are working on “Implement JWT Authentication” in the Authentication & Authorization sprint. Ask me anything about the task, or pick a quick action below.',
    createdAt: '2026-10-01T09:20:00+05:30',
  },
  {
    id: 'msg-002',
    role: 'student',
    content: 'I don’t understand JWT validation.',
    createdAt: '2026-10-01T09:21:00+05:30',
  },
  {
    id: 'msg-003',
    role: 'tutor',
    content:
      'JWT validation verifies that the token is correctly signed, has not expired, and contains the claims required by the application.\n\nFor your E-Commerce API, that means your middleware should reject a request to /orders if the token signature does not match your server secret, if the exp claim is in the past, or if the token is missing the user id you need to load the cart.',
    createdAt: '2026-10-01T09:21:10+05:30',
    context: {
      conceptId: 'token-validation',
      conceptLabel: 'JWT Validation',
      recommendedAction: 'Learning Material',
    },
    action: { kind: 'activity', targetId: 'act-signature-validation', label: 'Open Learning Material' },
  },
]

export const quickActions = [
  { id: 'explain_concept', label: 'Explain Concept', prompt: 'Explain JWT in the context of my current task.' },
  { id: 'help_with_task', label: 'Help With Task', prompt: 'Help me plan the JWT authentication task.' },
  { id: 'give_practice', label: 'Give Practice', prompt: 'Give me a practice activity for JWT validation.' },
  { id: 'generate_quiz', label: 'Generate Quiz', prompt: 'Generate a quiz on JWT authentication.' },
  { id: 'debug_code', label: 'Debug Code', prompt: 'Help me debug my JWT middleware.' },
]

export const quickActionReplies = {
  explain_concept: {
    content:
      'A JWT is a signed string with three parts: header.payload.signature. Your login endpoint creates it after checking the password, and every protected route in the E-Commerce API checks it before running.\n\nThe signature is what makes it trustworthy — if anyone edits the payload (for example changing the user id), the signature no longer matches and the server rejects it.',
    context: { conceptId: 'jwt', conceptLabel: 'JWT', recommendedAction: 'Learning Material' },
    action: { kind: 'activity', targetId: 'act-jwt-token-structure', label: 'Open Learning Material' },
  },
  help_with_task: {
    content:
      'Here is a plan for “Implement JWT Authentication”:\n\n1. On POST /auth/login, verify the password and sign a token containing the user id and role (expiry: 1 hour).\n2. Write an authenticate middleware that reads the Bearer token and verifies it.\n3. Apply the middleware to /orders and /cart.\n4. Return 401 for missing or invalid tokens.\n\nStep 2 is where your competency is lowest, so I recommend the coding exercise before you implement it in the project.',
    context: { conceptId: 'jwt', conceptLabel: 'JWT', recommendedAction: 'Coding Exercise' },
    action: { kind: 'activity', targetId: 'act-ex-jwt-middleware', label: 'Start Exercise' },
  },
  give_practice: {
    content:
      'Try this coding exercise: handle expired and tampered tokens in your middleware. It has automated test cases for expired tokens, malformed headers and bad signatures — the exact cases your task needs.',
    context: {
      conceptId: 'token-validation',
      conceptLabel: 'Token Validation',
      recommendedAction: 'Coding Exercise',
    },
    action: { kind: 'activity', targetId: 'act-ex-token-errors', label: 'Open Exercise' },
  },
  generate_quiz: {
    content:
      'I have prepared an adaptive quiz on JWT authentication. It adjusts the questions to your answers and focuses on signing and claims, since that is where your gap is. Your result will be used as new learning evidence.',
    context: { conceptId: 'jwt', conceptLabel: 'JWT', recommendedAction: 'Adaptive Quiz' },
    action: { kind: 'activity', targetId: 'act-quiz-jwt', label: 'Start Quiz' },
  },
  debug_code: {
    content:
      'Paste the part of your middleware that is failing and describe what happens. The most common JWT bugs I see in this task are:\n\n• Reading req.headers.Authorization (capital A) — Express lower-cases headers.\n• Forgetting to strip the "Bearer " prefix before verifying.\n• Calling next() after already sending a 401 response.',
    context: {
      conceptId: 'token-validation',
      conceptLabel: 'Token Validation',
      recommendedAction: 'Debug Guidance',
    },
  },
}

// Free-text replies keyed by a keyword the mock API looks for.
export const keywordReplies = [
  {
    keywords: ['expire', 'expiry', 'expiration'],
    content:
      'The exp claim stores the expiry time as a Unix timestamp. jwt.verify() checks it automatically and throws a TokenExpiredError when it has passed — your middleware should catch that and return 401 so the client knows to log in again.',
    context: { conceptId: 'token-validation', conceptLabel: 'Token Expiration', recommendedAction: 'Learning Material' },
    action: { kind: 'activity', targetId: 'act-token-expiration', label: 'Open Learning Material' },
  },
  {
    keywords: ['signature', 'secret'],
    content:
      'The signature is an HMAC of the header and payload using your server secret. When the token comes back, the server recomputes it — if it does not match, the token was tampered with. Keep the secret in an environment variable, never in the client.',
    context: { conceptId: 'token-validation', conceptLabel: 'Signature Validation', recommendedAction: 'Learning Material' },
    action: { kind: 'activity', targetId: 'act-signature-validation', label: 'Open Learning Material' },
  },
  {
    keywords: ['role', 'permission', 'authoriz', 'admin'],
    content:
      'Authentication tells you who the user is; authorization decides what they can do. After your JWT middleware sets req.user, a second middleware can check req.user.role — for example only admins can access /admin/products. Return 403 when the user is authenticated but not allowed.',
    context: { conceptId: 'authorization', conceptLabel: 'Authorization', recommendedAction: 'Adaptive Quiz' },
    action: { kind: 'activity', targetId: 'act-quiz-authorization', label: 'Start Quiz' },
  },
]

export const defaultReply = {
  content:
    'Good question. In the context of your current task (Implement JWT Authentication), the key idea is that every protected request must carry a valid token, and the server must verify it before trusting the user id inside it. Would you like an explanation, a practice exercise, or a quick quiz?',
  context: { conceptId: 'jwt', conceptLabel: 'JWT', recommendedAction: 'Coding Exercise' },
}

// ---------------------------------------------------------------------------
// Web resources (suggested alongside learning material for major gaps)
// ---------------------------------------------------------------------------

export const webResources = [
  {
    id: 'ext-w3s-json',
    conceptId: 'jwt',
    provider: 'W3Schools',
    title: 'JSON Introduction',
    description: 'JWT payloads are JSON — refresh the syntax and how JSON is parsed in JavaScript.',
    url: 'https://www.w3schools.com/js/js_json_intro.asp',
    format: 'tutorial',
    level: 'beginner',
    estimatedMinutes: 10,
  },
  {
    id: 'ext-jwtio-intro',
    conceptId: 'jwt',
    provider: 'jwt.io',
    title: 'Introduction to JSON Web Tokens',
    description: 'The official introduction to JWT structure, claims and when to use tokens.',
    url: 'https://jwt.io/introduction',
    format: 'article',
    level: 'beginner',
    estimatedMinutes: 12,
  },
  {
    id: 'ext-npm-jsonwebtoken',
    conceptId: 'jwt',
    provider: 'npm',
    title: 'jsonwebtoken package documentation',
    description: 'API reference for jwt.sign() and jwt.verify(), including options such as expiresIn and algorithms.',
    url: 'https://www.npmjs.com/package/jsonwebtoken',
    format: 'reference',
    level: 'intermediate',
    estimatedMinutes: 15,
  },
  {
    id: 'ext-rfc7519',
    conceptId: 'jwt',
    provider: 'IETF',
    title: 'RFC 7519: JSON Web Token',
    description: 'The JWT specification — registered claims, validation rules and security considerations.',
    url: 'https://datatracker.ietf.org/doc/html/rfc7519',
    format: 'specification',
    level: 'advanced',
    estimatedMinutes: 40,
  },
  {
    id: 'ext-owasp-jwt',
    conceptId: 'token-validation',
    provider: 'OWASP',
    title: 'JSON Web Token Cheat Sheet',
    description: 'Common JWT validation mistakes — algorithm confusion, missing expiry checks and token storage.',
    url: 'https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html',
    format: 'cheat-sheet',
    level: 'intermediate',
    estimatedMinutes: 20,
  },
  {
    id: 'ext-mdn-authorization-header',
    conceptId: 'token-validation',
    provider: 'MDN Web Docs',
    title: 'Authorization request header',
    description: 'How the Bearer scheme is sent in the Authorization header and read by the server.',
    url: 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Authorization',
    format: 'reference',
    level: 'beginner',
    estimatedMinutes: 8,
  },
  {
    id: 'ext-express-middleware',
    conceptId: 'token-validation',
    provider: 'Express',
    title: 'Using middleware',
    description: 'How Express middleware works — the foundation for your authenticate middleware.',
    url: 'https://expressjs.com/en/guide/using-middleware.html',
    format: 'guide',
    level: 'intermediate',
    estimatedMinutes: 15,
  },
  {
    id: 'ext-mdn-http-auth',
    conceptId: 'authentication',
    provider: 'MDN Web Docs',
    title: 'HTTP authentication',
    description: 'The general HTTP authentication framework and the difference between 401 and 403.',
    url: 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication',
    format: 'guide',
    level: 'beginner',
    estimatedMinutes: 12,
  },
  {
    id: 'ext-owasp-authentication',
    conceptId: 'authentication',
    provider: 'OWASP',
    title: 'Authentication Cheat Sheet',
    description: 'Secure password handling, login error messages and session management practices.',
    url: 'https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html',
    format: 'cheat-sheet',
    level: 'advanced',
    estimatedMinutes: 25,
  },
  {
    id: 'ext-owasp-authorization',
    conceptId: 'authorization',
    provider: 'OWASP',
    title: 'Authorization Cheat Sheet',
    description: 'Role-based access control, deny-by-default and checking permissions on every request.',
    url: 'https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html',
    format: 'cheat-sheet',
    level: 'intermediate',
    estimatedMinutes: 20,
  },
  {
    id: 'ext-w3s-http-status',
    conceptId: 'rest-api',
    provider: 'W3Schools',
    title: 'HTTP Status Messages',
    description: 'Quick reference for status codes your API returns, such as 200, 401, 403 and 404.',
    url: 'https://www.w3schools.com/tags/ref_httpmessages.asp',
    format: 'reference',
    level: 'beginner',
    estimatedMinutes: 8,
  },
  {
    id: 'ext-w3s-nodejs',
    conceptId: 'rest-api',
    provider: 'W3Schools',
    title: 'Node.js Tutorial',
    description: 'Node.js fundamentals for building the E-Commerce API server.',
    url: 'https://www.w3schools.com/nodejs/',
    format: 'tutorial',
    level: 'beginner',
    estimatedMinutes: 30,
  },
]

// ---------------------------------------------------------------------------
// New learning evidence
// ---------------------------------------------------------------------------

export const evidenceUpdateMessage = 'Your competency has been updated based on your new learning evidence.'

// Maps an activity kind to the evidence bucket it is counted in.
export const evidenceTypeByKind = {
  learning: 'lesson',
  exercise: 'exercise',
  quiz: 'quiz',
}

// How the mock "backend" labels a per-concept score.
export const performancePolicy = {
  strongMin: 80,
  developingMin: 60,
}

export const confidencePolicy = {
  gainPerActivity: 2,
  max: 95,
}
