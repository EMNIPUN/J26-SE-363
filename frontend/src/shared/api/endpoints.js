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
    // User Stories + Decomposition Agent
    STORIES: '/planning/stories',
    STORY: (ref) => `/planning/stories/${ref}`,
    STORY_TASKS: (ref) => `/planning/stories/${ref}/tasks`,
    STORY_TASK: (ref, taskId) => `/planning/stories/${ref}/tasks/${taskId}`,
    STORY_TASKS_VALIDATE: (ref) => `/planning/stories/${ref}/tasks/validate`,
    STORY_TASKS_VALIDATION: (ref) => `/planning/stories/${ref}/tasks/validation`,
    DECOMPOSITION: '/planning/decomposition',
    DECOMPOSITION_HISTORY: (ref) => `/planning/decomposition/${ref}/history`,
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
