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
  TERMS: {
    LIST: '/terms',
  },
  INVITATIONS: {
    MINE: '/me/invitations',
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
}

export default ENDPOINTS
