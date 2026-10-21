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
