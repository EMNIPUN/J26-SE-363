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
  BATCHES: {
    LIST: '/v1/batches',
    CREATE: '/v1/batches',
    DETAIL: (id) => `/v1/batches/${id}`,
    UPDATE: (id) => `/v1/batches/${id}`,
  },
  PROJECTS: {
    LIST: '/v1/projects',
    CREATE: '/v1/projects',
    DETAIL: (id) => `/v1/projects/${id}`,
  },
  TEAMS: {
    LIST: '/v1/teams',
    BULK: '/v1/teams/bulk',
    DETAIL: (id) => `/v1/teams/${id}`,
    ADD_MEMBER: (id) => `/v1/teams/${id}/members`,
    REMOVE_MEMBER: (teamId, studentId) => `/v1/teams/${teamId}/members/${studentId}`,
  },
  STUDENTS: {
    ME: '/v1/students/me',
    LINK_GITHUB: '/v1/students/me/github',
    DETAIL: (id) => `/v1/students/${id}`,
  },
  JOBS: {
    PUBLISH: '/v1/jobs',
    DETAIL: (id) => `/v1/jobs/${id}`,
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
