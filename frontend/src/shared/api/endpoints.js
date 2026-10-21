/**
 * Centralized API Endpoint Registry
 *
 * Single source of truth for all backend route paths across the SELVIA architecture.
 * Developers never hardcode string URLs inside components.
 */
export const ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    ME: '/auth/me',
  },
  ACCOUNT: {
    ME: '/me',
    ONBOARDING: '/me/onboarding',
    PROFILE: '/me/profile',
    PICTURE: '/me/picture',
  },
  TEAMS: {
    MINE: '/me/teams',
    CREATE: '/teams',
    DETAIL: (team) => `/teams/${team}`,
    PROJECT: (team) => `/teams/${team}/project`,
    ACTIVATE: (team) => `/teams/${team}/activate`,
    INVITATIONS: (team) => `/teams/${team}/invitations`,
    INVITATION: (team, invitationId) => `/teams/${team}/invitations/${invitationId}`,
    RESEND_INVITATION: (team, invitationId) => `/teams/${team}/invitations/${invitationId}/resend`,
    MEMBER: (team, userId) => `/teams/${team}/members/${userId}`,
    LEADER_TRANSFER: (team) => `/teams/${team}/leader-transfer`,
    LEADER_ACCEPT: (team) => `/teams/${team}/leader-transfer/accept`,
    LEADER_DECLINE: (team) => `/teams/${team}/leader-transfer/decline`,
  },
  NOTIFICATIONS: {
    LIST: '/me/notifications',
    READ_ALL: '/me/notifications/read-all',
    ONE: (id) => `/me/notifications/${id}`,
    READ: (id) => `/me/notifications/${id}/read`,
    PREFERENCES: '/me/notification-preferences',
  },
  STUDENTS: {
    AVAILABLE: '/students/available',
  },
  TERMS: {
    LIST: '/terms',
  },
  INVITATIONS: {
    MINE: '/me/invitations',
    SENT: '/invitations/sent',
    LOOKUP: '/invitations/lookup',
    ACCEPT: (invitationId) => `/invitations/${invitationId}/accept`,
    DECLINE: (invitationId) => `/invitations/${invitationId}/decline`,
  },
  PLANNING: {
    PROJECTS: '/planning/projects',
    PROJECT_DETAIL: (id) => `/planning/projects/${id}`,
    TASKS: '/planning/tasks',
    TASK_DETAIL: (id) => `/planning/tasks/${id}`,
    TIMELINE: (projectId) => `/planning/projects/${projectId}/timeline`,
    // Pipeline session
    SESSIONS: '/planning/sessions',
    SESSION_ACTIVE: '/planning/sessions/active',
    SESSION_DETAIL: (id) => `/planning/sessions/${id}`,
    // Requirement Quality Agent
    SRS: '/planning/srs',
    SRS_TEMPLATE: '/planning/srs/template',
    QUALITY: '/planning/quality',
    QUALITY_GATE: '/planning/quality/gate',
    QUALITY_HISTORY: (ref) => `/planning/quality/${ref}/history`,
    QUALITY_PROCEED_TO_DECOMPOSITION: (ref) => `/planning/quality/${ref}/proceed-to-decomposition`,
    // User Stories + Decomposition Agent
    STORIES: '/planning/stories',
    STORY: (ref) => `/planning/stories/${ref}`,
    STORY_TASKS: (ref) => `/planning/stories/${ref}/tasks`,
    STORY_TASK: (ref, taskId) => `/planning/stories/${ref}/tasks/${taskId}`,
    STORY_TASKS_VALIDATE: (ref) => `/planning/stories/${ref}/tasks/validate`,
    STORY_TASKS_VALIDATION: (ref) => `/planning/stories/${ref}/tasks/validation`,
    DECOMPOSITION: '/planning/decomposition',
    DECOMPOSITION_HISTORY: (ref) => `/planning/decomposition/${ref}/history`,
    DECOMPOSITION_PROCEED_TO_EFFORT: (ref) => `/planning/decomposition/${ref}/proceed-to-effort`,
    // Estimation
    ESTIMATES: '/planning/estimates',
    ESTIMATE_CONFIRM: (ref) => `/planning/estimates/${ref}/confirm`,
    // Sprint Backlog
    BACKLOG: '/planning/backlog',
    BACKLOG_ITEM: (id) => `/planning/backlog/${id}`,
    // DART — Diagnostic Arbitration using Reasoning Traces
    DART_ARBITRATE: '/planning/dart/arbitrate',
    DART_CASES: '/planning/dart/cases',
    DART_CASE: (ref) => `/planning/dart/cases/${ref}`,
    DART_RESOLVE: (ref) => `/planning/dart/cases/${ref}/resolve`,
    // Feedback & instructor alerts
    FEEDBACK: '/planning/feedback',
    FEEDBACK_VIEW: (id) => `/planning/feedback/${id}/view`,
    INSTRUCTOR_ALERTS: '/planning/instructor/alerts',
    INSTRUCTOR_ALERT: (id) => `/planning/instructor/alerts/${id}`,
    // Jira Integration
    JIRA_STATUS: '/planning/jira/status',
    JIRA_SYNC_BACKLOG: '/planning/jira/sync/backlog',
    JIRA_SYNC_SPRINT: '/planning/jira/sync/sprint',
    JIRA_RESET_LINKS: '/planning/jira/reset-links',
    JIRA_FETCH: '/planning/jira/fetch',
    JIRA_TRANSITION: '/planning/jira/transition',
    // Backlog Readiness Passport
    PASSPORTS: '/planning/passports',
    PASSPORT: (ref) => `/planning/passports/${ref}`,
    PASSPORTS_EVALUATE: '/planning/passports/evaluate',
  },
  TUTOR: {
    SESSIONS: '/tutor/sessions',
    CHAT: (sessionId) => `/tutor/sessions/${sessionId}/chat`,
    FEEDBACK: (sessionId) => `/tutor/sessions/${sessionId}/feedback`,
    REVIEWS: '/tutor/reviews',
  },
  PERFORMANCE: {
    OVERVIEW: '/performance/overview',
    STUDENTS: '/performance/students',
    STUDENT_DETAIL: (id) => `/performance/students/${id}`,
    ANALYTICS: '/performance/analytics',
  },
  SECURITY: {
    AUDIT_LOGS: '/security/audit-logs',
    SCAN: '/security/scan',
    POLICIES: '/security/policies',
  },
  // Security Assistant results (read-only), see modules/security/assistant
  SECURITY_ASSISTANT: {
    RUNS: (team) => `/security-assistant/teams/${team}/runs`,
    STUDENTS: (team) => `/security-assistant/teams/${team}/students`,
    RUN: (team, run) => `/security-assistant/teams/${team}/runs/${run}`,
    FINDINGS: (team, run) => `/security-assistant/teams/${team}/runs/${run}/findings`,
    FINDING: (team, run, groupId) => `/security-assistant/teams/${team}/runs/${run}/findings/${groupId}`,
    LEARNING: (team, run) => `/security-assistant/teams/${team}/runs/${run}/learning`,
    AGENTS: (team, run) => `/security-assistant/teams/${team}/runs/${run}/agents`,
    AUDIT: (team, run) => `/security-assistant/teams/${team}/runs/${run}/audit`,
    WORKFLOW: (team, run) => `/security-assistant/teams/${team}/runs/${run}/workflow`,
    EVIDENCE: (team) => `/security-assistant/teams/${team}/evidence`,
    COMPARE: (team) => `/security-assistant/teams/${team}/compare`,
  },
}

export default ENDPOINTS
