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
    // Requirement Quality Agent
    SRS: '/planning/srs',
    SRS_TEMPLATE: '/planning/srs/template',
    QUALITY: '/planning/quality',
    QUALITY_HISTORY: (ref) => `/planning/quality/${ref}/history`,
    // User Stories + Decomposition Agent
    STORIES: '/planning/stories',
    STORY: (ref) => `/planning/stories/${ref}`,
    DECOMPOSITION: '/planning/decomposition',
    DECOMPOSITION_HISTORY: (ref) => `/planning/decomposition/${ref}/history`,
    // DART — Diagnostic Arbitration using Reasoning Traces
    DART_ARBITRATE: '/planning/dart/arbitrate',
    DART_CASES: '/planning/dart/cases',
    DART_CASE: (ref) => `/planning/dart/cases/${ref}`,
    DART_RESOLVE: (ref) => `/planning/dart/cases/${ref}/resolve`,
    // Sprint Tasks
    SPRINT_TASKS: '/planning/sprint-tasks',
    SPRINT_TASK: (ref) => `/planning/sprint-tasks/${ref}`,
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
