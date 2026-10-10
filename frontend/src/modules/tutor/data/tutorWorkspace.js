// Sample Adaptive Tutor workspace.
// Competency figures, gaps, and recommendations are pre-authored fixtures.
// The UI must display them as returned. It must not derive new estimates.

export const SAMPLE_NOTICE =
  'Sample tutor output. These estimates and recommendations are fixtures for the interface. They are not validated research results, and this page does not calculate competency.'

export const PROJECT = {
  id: 'proj-campus-sample',
  name: 'SELVIA Campus Portal (sample)',
  sprintId: 'sprint-02',
  sprintName: 'Sprint 2 — Access control',
}

export const TASKS = [
  {
    id: 'task-jwt',
    projectId: 'proj-campus-sample',
    sprintId: 'sprint-02',
    title: 'Implement JWT authentication',
    description:
      'Issue and validate access tokens so the campus API can recognise a signed-in student without storing a password in the browser.',
    status: 'In progress',
    progress: 40,
    requirements: [
      'Sign-in returns a signed JWT.',
      'Protected routes reject a missing or expired token.',
      'A role claim limits who can open lecturer routes.',
    ],
    acceptance: [
      'A valid token reaches a protected endpoint.',
      'An expired token returns 401.',
      'A student token cannot open a lecturer-only route.',
    ],
    conceptIds: ['concept-rest', 'concept-auth', 'concept-jwt', 'concept-token', 'concept-authz'],
  },
  {
    id: 'task-profile',
    projectId: 'proj-campus-sample',
    sprintId: 'sprint-02',
    title: 'Build the student profile API',
    description: 'Expose the signed-in student profile after authentication, without returning secrets.',
    status: 'Not started',
    progress: null,
    requirements: ['GET /me returns the signed-in profile.', 'The response never includes a password hash.'],
    acceptance: ['The JSON matches the profile contract.', 'Secrets are absent from the payload.'],
    conceptIds: ['concept-rest', 'concept-resource'],
  },
]

export const CONCEPTS = {
  'concept-rest': {
    id: 'concept-rest',
    label: 'REST APIs',
    description: 'Resources, HTTP methods, and status codes used by the campus API.',
    prerequisites: [],
    resourceIds: ['mat-rest'],
    status: 'Demonstrated',
  },
  'concept-auth': {
    id: 'concept-auth',
    label: 'Authentication',
    description: 'Checking that a request comes from the person it claims to come from.',
    prerequisites: ['REST APIs'],
    resourceIds: ['mat-auth'],
    status: 'Developing',
  },
  'concept-jwt': {
    id: 'concept-jwt',
    label: 'JWT',
    description: 'A signed token with a header, payload, and signature. The signature is how the API trusts the claims.',
    prerequisites: ['Authentication'],
    resourceIds: ['mat-jwt'],
    status: 'Needs Attention',
  },
  'concept-token': {
    id: 'concept-token',
    label: 'Token validation',
    description: 'Checking the signature, expiry, and audience before a route handler runs.',
    prerequisites: ['JWT'],
    resourceIds: ['mat-token'],
    status: 'Needs Attention',
  },
  'concept-authz': {
    id: 'concept-authz',
    label: 'Authorization',
    description: 'Deciding what an already authenticated person is allowed to do.',
    prerequisites: ['Authentication'],
    resourceIds: ['mat-authz'],
    status: 'Insufficient Evidence',
  },
  'concept-resource': {
    id: 'concept-resource',
    label: 'Resource modelling',
    description: 'Choosing the fields a profile resource should expose.',
    prerequisites: ['REST APIs'],
    resourceIds: ['mat-rest'],
    status: 'Insufficient Evidence',
  },
}

export const MATERIALS = {
  'mat-rest': { id: 'mat-rest', title: 'Reading: REST resources and status codes', minutes: 12, conceptId: 'concept-rest' },
  'mat-auth': { id: 'mat-auth', title: 'Reading: authentication versus authorization', minutes: 10, conceptId: 'concept-auth' },
  'mat-jwt': { id: 'mat-jwt', title: 'Worked example: a JWT header and payload', minutes: 15, conceptId: 'concept-jwt' },
  'mat-token': { id: 'mat-token', title: 'Reading: validating signature and expiry', minutes: 12, conceptId: 'concept-token' },
  'mat-authz': { id: 'mat-authz', title: 'Reading: role checks on a route', minutes: 8, conceptId: 'concept-authz' },
}

// Returned as-is. Missing estimated values stay null. They are not zeroes.
export const ESTIMATES = [
  {
    conceptId: 'concept-rest',
    required: 70,
    estimated: 78,
    gap: 0,
    evidence: ['REST quiz, 4 of 5, 12 Sep.'],
    confidence: 'Sufficient for this snapshot',
    status: 'Demonstrated',
  },
  {
    conceptId: 'concept-auth',
    required: 70,
    estimated: 58,
    gap: 12,
    evidence: ['Short answer on sessions, partial credit, 18 Sep.'],
    confidence: 'Limited — one short answer',
    status: 'Developing',
  },
  {
    conceptId: 'concept-jwt',
    required: 75,
    estimated: 46,
    gap: 29,
    evidence: ['Concept quiz, 2 of 5, 2 Oct. A single quiz is not a mastery claim.'],
    confidence: 'Limited — one quiz',
    status: 'Needs Attention',
  },
  {
    conceptId: 'concept-token',
    required: 80,
    estimated: 40,
    gap: 40,
    evidence: ['Same 2 Oct quiz: the token-validation items were missed.'],
    confidence: 'Limited — one quiz',
    status: 'Needs Attention',
  },
  {
    conceptId: 'concept-authz',
    required: 70,
    estimated: null,
    gap: null,
    evidence: [],
    confidence: 'Insufficient evidence',
    status: 'Insufficient Evidence',
  },
  {
    conceptId: 'concept-resource',
    required: 60,
    estimated: null,
    gap: null,
    evidence: [],
    confidence: 'Insufficient evidence',
    status: 'Insufficient Evidence',
  },
]

export const RECOMMENDATIONS = {
  initial: {
    id: 'rec-practice-token',
    phase: 'initial',
    intervention: 'Practise token validation',
    conceptId: 'concept-token',
    taskId: 'task-jwt',
    explanation:
      'Practise JWT token validation because this concept is required for your current project task and previous assessment evidence indicates difficulty with it.',
    durationMinutes: 25,
    evidence: ['Concept quiz on 2 Oct: token-validation items were missed (2 of 5 overall).'],
    why: [
      'The task acceptance criteria require an expired token to be rejected.',
      'The only token-validation evidence on file is that quiz, so the next step is practice, not a claim that the concept is mastered or failed outright.',
      'A later reassessment is required before an updated competency estimate should be trusted.',
    ],
    practiceId: 'ex-debug-token',
    materialId: 'mat-token',
    assessmentId: 'as-reassess-token',
  },
  practised: {
    id: 'rec-reassess-token',
    phase: 'practised',
    intervention: 'Take the token-validation reassessment',
    conceptId: 'concept-token',
    taskId: 'task-jwt',
    explanation:
      'The practice attempt is now on file. The next prepared step is a short reassessment. This sample service still returns the same competency estimate until a tutor service sends a new one.',
    durationMinutes: 15,
    evidence: ['Practice submission recorded locally in this browser session.', 'Prior quiz on 2 Oct.'],
    why: [
      'Practice is new evidence of an attempt, not a new competency percentage.',
      'The reassessment is the follow-up the sample decision table specifies after this exercise.',
    ],
    practiceId: 'ex-debug-token',
    materialId: 'mat-token',
    assessmentId: 'as-reassess-token',
  },
  reassessed: {
    id: 'rec-await-estimate',
    phase: 'reassessed',
    intervention: 'Wait for an updated competency estimate',
    conceptId: 'concept-token',
    taskId: 'task-jwt',
    explanation:
      'The reassessment was stored as evidence. The quiz score is not a competency estimate. This sample workspace will not change the percentage until the tutor service returns a new estimate.',
    durationMinutes: null,
    evidence: ['Reassessment submitted in this session.', 'Competency snapshot is unchanged.'],
    why: [
      'Score, competency estimate, and confidence are separate values.',
      'Opening materials or submitting practice does not prove competency.',
    ],
    practiceId: null,
    materialId: 'mat-token',
    assessmentId: 'as-reassess-token',
  },
}

export const ROADMAPS = {
  initial: [
    { id: 'step-review', label: 'Review token validation', state: 'ready' },
    { id: 'step-example', label: 'Study the worked JWT example', state: 'ready' },
    { id: 'step-exercise', label: 'Complete the targeted debugging exercise', state: 'current' },
    { id: 'step-quiz', label: 'Take the adaptive reassessment', state: 'upcoming' },
    { id: 'step-reassess', label: 'Wait for a competency re-estimate', state: 'upcoming' },
    { id: 'step-task', label: 'Continue the JWT task on the sprint board', state: 'upcoming' },
  ],
  practised: [
    { id: 'step-review', label: 'Review token validation', state: 'done' },
    { id: 'step-example', label: 'Study the worked JWT example', state: 'done' },
    { id: 'step-exercise', label: 'Complete the targeted debugging exercise', state: 'done' },
    { id: 'step-quiz', label: 'Take the adaptive reassessment', state: 'current' },
    { id: 'step-reassess', label: 'Wait for a competency re-estimate', state: 'upcoming' },
    { id: 'step-task', label: 'Continue the JWT task on the sprint board', state: 'upcoming' },
  ],
  reassessed: [
    { id: 'step-review', label: 'Review token validation', state: 'done' },
    { id: 'step-example', label: 'Study the worked JWT example', state: 'done' },
    { id: 'step-exercise', label: 'Complete the targeted debugging exercise', state: 'done' },
    { id: 'step-quiz', label: 'Take the adaptive reassessment', state: 'done' },
    { id: 'step-reassess', label: 'Wait for a competency re-estimate', state: 'current' },
    { id: 'step-task', label: 'Continue the JWT task on the sprint board', state: 'upcoming' },
  ],
}

export const EXERCISES = [
  {
    id: 'ex-debug-token',
    title: 'Find the token-validation mistake',
    type: 'code-debug',
    conceptId: 'concept-token',
    taskId: 'task-jwt',
    difficulty: 'Focused',
    minutes: 20,
    recommended: true,
    objectives: ['Recognise a check that ignores token expiry.'],
    prompt:
      'This handler checks that a token exists, then calls the route. What is missing before the request should be trusted?',
    starter: `function protect(req, res, next) {
  const token = req.headers.authorization
  if (!token) return res.status(401).send('Missing token')
  next()
}`,
    promptNote: 'Sample check only. This code is not executed.',
    acceptedIncludes: ['expir', 'signature', 'verify'],
    successFeedback:
      'The sample check found a relevant idea (expiry, signature, or verify). The code was not run. This submission is evidence of an attempt, not a new competency score.',
    retryFeedback:
      'The sample check did not see expiry, signature, or verify. Mention what the handler should check before calling next(). The code was not run.',
  },
  {
    id: 'ex-mcq-jwt',
    title: 'What does the JWT signature protect?',
    type: 'multiple-choice',
    conceptId: 'concept-jwt',
    taskId: 'task-jwt',
    difficulty: 'Foundation',
    minutes: 8,
    recommended: true,
    objectives: ['Distinguish a readable payload from a trusted payload.'],
    prompt: 'Why does the API check the JWT signature?',
    choices: [
      { id: 'a', label: 'To hide the payload so nobody can read the claims.' },
      { id: 'b', label: 'To detect that the claims were changed after the token was issued.' },
      { id: 'c', label: 'To encrypt the student password inside the token.' },
    ],
    answerId: 'b',
    successFeedback: 'Recorded. The signature supports integrity of the claims. This item score is not a competency estimate.',
    retryFeedback: 'Not the keyed answer. The payload is readable; the signature is what makes a change detectable.',
  },
  {
    id: 'ex-short-auth',
    title: 'Authentication in one sentence',
    type: 'short-answer',
    conceptId: 'concept-auth',
    taskId: 'task-jwt',
    difficulty: 'Foundation',
    minutes: 10,
    recommended: false,
    objectives: ['State what authentication establishes.'],
    prompt: 'In one or two sentences, what does authentication establish that authorization does not?',
    acceptedIncludes: ['who', 'identity', 'person', 'user'],
    successFeedback: 'Recorded. The sample check looked for identity language. It did not grade writing quality.',
    retryFeedback: 'Add who the request is from. Authorization is the separate question of what they may do.',
  },
  {
    id: 'ex-complete-guard',
    title: 'Complete the expiry guard',
    type: 'code-completion',
    conceptId: 'concept-token',
    taskId: 'task-jwt',
    difficulty: 'Focused',
    minutes: 15,
    recommended: false,
    objectives: ['Name the claim used for expiry.'],
    prompt: 'Fill the condition that rejects an expired token. Use the exp claim.',
    starter: `if (payload.____ < now) {
  return res.status(401).send('Expired')
}`,
    promptNote: 'Sample check only. This code is not executed.',
    acceptedIncludes: ['exp'],
    successFeedback: 'Recorded. The sample check saw the exp claim. The snippet was not executed.',
    retryFeedback: 'The sample answer uses the exp claim. The snippet was not executed.',
  },
  {
    id: 'ex-impl-profile',
    title: 'Sketch GET /me',
    type: 'implementation',
    conceptId: 'concept-resource',
    taskId: 'task-profile',
    difficulty: 'Open',
    minutes: 25,
    recommended: false,
    objectives: ['Return a profile without a secret field.'],
    prompt: 'Describe or sketch the JSON for GET /me. Say which fields you would leave out.',
    acceptedIncludes: ['password', 'hash', 'secret'],
    successFeedback:
      'Recorded as a sketch. Nothing was executed, and no competency estimate was updated. There is still insufficient evidence for resource modelling.',
    retryFeedback: 'Name at least one field you would omit, such as a password hash.',
  },
]

export const ASSESSMENTS = [
  {
    id: 'as-diag-access',
    title: 'Access-control diagnostic',
    kind: 'Diagnostic',
    taskId: 'task-jwt',
    conceptIds: ['concept-auth', 'concept-jwt', 'concept-authz'],
    objectives: ['See which access-control ideas already have an answer.'],
    minutes: 12,
    questions: [
      {
        id: 'q1',
        conceptId: 'concept-auth',
        prompt: 'Authentication mainly answers which question?',
        choices: ['Who is this?', 'What may they open?', 'How fast is the API?'],
        answerIndex: 0,
        explanation: 'Authentication is about identity. Permission is authorization.',
      },
      {
        id: 'q2',
        conceptId: 'concept-jwt',
        prompt: 'A JWT payload is typically:',
        choices: ['Encrypted and unreadable', 'Readable, with a signature beside it', 'The student password'],
        answerIndex: 1,
        explanation: 'The payload is encoded, not secret. Trust comes from the signature.',
      },
      {
        id: 'q3',
        conceptId: 'concept-authz',
        prompt: 'A lecturer-only route should reject a student token because of:',
        choices: ['A failed signature only', 'A role or permission check', 'A slow database'],
        answerIndex: 1,
        explanation: 'A valid student token can still lack permission.',
      },
    ],
  },
  {
    id: 'as-quiz-jwt',
    title: 'JWT concept quiz',
    kind: 'Concept quiz',
    taskId: 'task-jwt',
    conceptIds: ['concept-jwt'],
    objectives: ['Check the header, payload, and signature roles.'],
    minutes: 8,
    questions: [
      {
        id: 'q1',
        conceptId: 'concept-jwt',
        prompt: 'Which part lets the API detect a changed claim?',
        choices: ['Header alg alone', 'Signature', 'The word Bearer'],
        answerIndex: 1,
        explanation: 'The signature is checked against the header and payload.',
      },
      {
        id: 'q2',
        conceptId: 'concept-jwt',
        prompt: 'Putting a password inside a JWT is:',
        choices: ['Required for sign-in', 'A poor idea, because the payload is readable', 'How expiry works'],
        answerIndex: 1,
        explanation: 'Anyone who has the token can read the payload.',
      },
    ],
  },
  {
    id: 'as-reassess-token',
    title: 'Token validation reassessment',
    kind: 'Reassessment',
    taskId: 'task-jwt',
    conceptIds: ['concept-token'],
    objectives: ['Recheck expiry and signature after practice.'],
    minutes: 10,
    questions: [
      {
        id: 'q1',
        conceptId: 'concept-token',
        prompt: 'An expired token with a valid-looking signature should be:',
        choices: ['Accepted, because the signature matches', 'Rejected', 'Treated as a new sign-in'],
        answerIndex: 1,
        explanation: 'Expiry is checked as well as the signature.',
      },
      {
        id: 'q2',
        conceptId: 'concept-token',
        prompt: 'Validation belongs:',
        choices: ['Only in the React page', 'Before the protected handler runs', 'After the response is sent'],
        answerIndex: 1,
        explanation: 'The guard runs before the route handler.',
      },
    ],
  },
  {
    id: 'as-adaptive-authz',
    title: 'Authorization follow-up',
    kind: 'Adaptive quiz',
    taskId: 'task-jwt',
    conceptIds: ['concept-authz'],
    objectives: ['Collect a first piece of evidence where none is stored.'],
    minutes: 8,
    questions: [
      {
        id: 'q1',
        conceptId: 'concept-authz',
        prompt: 'A signed token proves the claims were issued. It does not by itself prove:',
        choices: ['The token has a header', 'The person may perform this action', 'The token is a string'],
        answerIndex: 1,
        explanation: 'Permission is a separate check.',
      },
    ],
  },
]

export const ATTEMPT_HISTORY = [
  {
    id: 'attempt-jwt-oct',
    assessmentId: 'as-quiz-jwt',
    title: 'JWT concept quiz',
    when: '2 Oct, sample record',
    scoreText: '2 of 5',
    conceptIds: ['concept-jwt', 'concept-token'],
    note: 'Historical fixture. Not recomputed from this session.',
  },
]

export const EVIDENCE = [
  {
    id: 'ev-rest-quiz',
    kind: 'Quiz attempt',
    title: 'REST basics',
    when: '12 Sep, sample record',
    detail: '4 of 5. Used as evidence for the REST snapshot.',
    conceptId: 'concept-rest',
  },
  {
    id: 'ev-auth-short',
    kind: 'Short answer',
    title: 'Sessions versus tokens',
    when: '18 Sep, sample record',
    detail: 'Partial credit. Limited evidence for authentication.',
    conceptId: 'concept-auth',
  },
  {
    id: 'ev-jwt-quiz',
    kind: 'Assessment result',
    title: 'JWT concept quiz',
    when: '2 Oct, sample record',
    detail: '2 of 5. Token-validation items missed. Not treated as zero on other concepts.',
    conceptId: 'concept-token',
  },
]

export const RECOMMENDATION_HISTORY = [
  {
    id: 'hist-rec-1',
    intervention: 'Review authentication versus authorization',
    conceptId: 'concept-auth',
    reason: 'The short answer on 18 Sep was only partial.',
    completed: true,
    followUp: 'No follow-up quiz is stored for this item.',
  },
  {
    id: 'hist-rec-2',
    intervention: 'JWT concept quiz',
    conceptId: 'concept-jwt',
    reason: 'The JWT task was selected and no earlier JWT evidence was on file.',
    completed: true,
    followUp: 'Quiz on 2 Oct, 2 of 5. That score stayed a quiz result, not a competency percentage.',
  },
]

export const PROGRESS_EXPLANATION =
  'The REST snapshot is supported by a quiz on 12 Sep. Authentication rests on one partial short answer, so the status stays Developing. JWT and token validation rest on the 2 Oct quiz, which is enough to justify practice and not enough to claim mastery. Authorization and resource modelling have no stored evidence, so they stay Insufficient Evidence rather than zero. Time spent reading is not listed as evidence.'

export const CHAT_PROMPTS = [
  'Explain this concept simply.',
  'Help me understand my current task.',
  'Give me a worked example.',
  'Give me a practice exercise.',
  'Help me debug my code.',
  'Why did you recommend this activity?',
]

export const CHAT_SESSIONS = [
  { id: 'new', title: 'New conversation', when: 'Now' },
  { id: 's-jwt', title: 'JWT task questions', when: 'Sample, 2 Oct' },
]

export const CHAT_TRANSCRIPTS = {
  's-jwt': [
    {
      id: 'm1',
      role: 'user',
      content: 'Why did the quiz say my token check was incomplete?',
    },
    {
      id: 'm2',
      role: 'assistant',
      content:
        'Sample reply, not from the tutor service.\n\nThe fixture quiz marked the token-validation items wrong. A handler that only checks the header is present still accepts an expired token.\n\n```js\nif (!token) return res.status(401).send("Missing token")\n// still need verify(token) and an expiry check\n```',
    },
  ],
}
